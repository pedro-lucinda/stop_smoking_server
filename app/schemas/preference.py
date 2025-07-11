from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---- Goal schemas ----

class GoalBase(BaseModel):
    description: str = Field(..., example="Run 5km instead of smoking break")
    is_completed: bool = Field(False, example=False)

class GoalCreate(GoalBase):
    """Incoming payload for creating a goal."""
    pass

class GoalOut(GoalBase):
    id: int
    preference_id: int

    class Config:
        orm_mode = True


# ---- Badge schemas (read-only) ----

class BadgeOut(BaseModel):
    id: int
    name: str
    image: Optional[str] = None
    description: Optional[str] = None

    class Config:
        orm_mode = True


# ---- Preference schemas ----

class PreferenceBase(BaseModel):
    reason: str = Field(..., example="Protect my health")
    quit_date: date = Field(..., example="2025-07-08")

class PreferenceCreate(PreferenceBase):
    """Payload for creating a Preference; you can supply a list of initial goals."""
    goals: List[GoalCreate] = Field(default_factory=list)

class PreferenceOut(PreferenceBase):
    id: int
    goals: List[GoalOut] = []
    badges: List[BadgeOut] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
