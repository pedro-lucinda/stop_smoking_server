from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class DetailedMotivationOut(BaseModel):
    progress: str
    motivation: str
    cravings: str
    ideas: str
    recommendations: Optional[str] = None

    class Config:
        orm_mode = True


class DailyMotivationCreate(BaseModel):
    date: date
    progress: str
    motivation: str
    cravings: str
    ideas: str
    recommendations: Optional[str] = None


class DailyMotivationOut(DailyMotivationCreate):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
