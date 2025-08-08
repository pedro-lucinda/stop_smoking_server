from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth0 import get_current_user
from app.api.v1.dependencies.db import get_async_db
from app.models.motivation import DailyMotivation
from app.schemas.motivation import DailyMotivationOut
from app.services.motivation_service import generate_and_save_for_user

router = APIRouter()


@router.get(
    "/detailed-text",
    response_model=DailyMotivationOut,
    status_code=status.HTTP_200_OK,
)
async def detailed_text(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
) -> DailyMotivationOut:
    """
    Return today's DailyMotivation; if none exists, generate via AI,
    persist it, and return it.
    """
    today = date.today()
    res = await db.execute(
        select(DailyMotivation).where(
            DailyMotivation.user_id == current_user.id,
            DailyMotivation.date == today,
        )
    )
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    try:
        record = await generate_and_save_for_user(db, current_user.id)
        return record
    except HTTPException:
        raise
    except Exception as e:
        # log if you want, then surface a clean API error
        raise HTTPException(
            status_code=502, detail="Failed to generate motivation"
        ) from e
