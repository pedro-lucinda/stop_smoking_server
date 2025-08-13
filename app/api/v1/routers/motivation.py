from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth0 import get_current_user
from app.api.v1.dependencies.db import get_async_db
from app.models.motivation import DailyMotivation
from app.models.user import User
from app.schemas.motivation import DailyMotivationOut
from app.services.motivation_service import generate_and_save_for_user

router = APIRouter()


@router.get("/detailed-text", response_model=DailyMotivationOut)
async def detailed_text(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Return today's motivation for the current user (latest if duplicates exist)."""
    today = date.today()

    stmt = (
        select(DailyMotivation)
        .where(
            DailyMotivation.user_id == current_user.id,
            DailyMotivation.date == today,
        )
        .order_by(DailyMotivation.created_at.desc())
        .limit(1)
    )

    res = await db.execute(stmt)
    # Use unique() to guard against row duplication if a joinedload was added elsewhere.
    existing = res.unique().scalars().first()
    if not existing:
        new_motivation = await generate_and_save_for_user(db, current_user.id)
        return new_motivation
    return existing


@router.get("/", response_model=list[DailyMotivationOut])
async def list_motivations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    skip: int = 0,
    limit: int = 100,
):
    stmt = (
        select(DailyMotivation)
        .where(DailyMotivation.user_id == current_user.id)
        .order_by(DailyMotivation.date.desc(), DailyMotivation.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(stmt)
    return res.unique().scalars().all()


@router.get("/count", response_model=int)
async def count_motivations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    stmt = (
        select(func.count())
        .select_from(DailyMotivation)
        .where(DailyMotivation.user_id == current_user.id)
    )
    return int(await db.scalar(stmt) or 0)
