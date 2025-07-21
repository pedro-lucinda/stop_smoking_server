from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import openai

from app.core.config import settings
from app.api.v1.dependencies import get_db_session, get_current_user
from app.models.motivation import DailyMotivation
from app.schemas.motivation import DailyMotivationOut
from app.services.motivation_service import generate_and_save_for_user

router = APIRouter()

openai.api_key = settings.openai_api_key


@router.get(
    "/detailed-text",
    response_model=DailyMotivationOut,
    status_code=status.HTTP_200_OK,
)
def detailed_text(
    db: Session = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> DailyMotivationOut:
    """
    Return today's DailyMotivation; if none exists, generate via AI,
    persist it, and return it.
    """
    today = date.today()
    existing = (
        db.query(DailyMotivation).filter_by(user_id=current_user.id, date=today).first()
    )
    if existing:
        return existing

    return generate_and_save_for_user(db, current_user.id)
