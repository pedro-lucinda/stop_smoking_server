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


class GoalUpdate(BaseModel):
    id: Optional[int] = Field(
        None,
        description="If omitted, a new goal will be created; if provided, the existing goal will be updated",
    )
    description: Optional[str] = Field(
        None, example="Take a smoke-free walk instead of a break"
    )
    is_completed: Optional[bool] = Field(None, example=True)

    class Config:
        orm_mode = True


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
    language: Optional[str] = Field(..., example="en-us")


class PreferenceCreate(PreferenceBase):
    """Payload for creating a Preference; you can supply a list of initial goals."""

    goals: List[GoalCreate] = Field(default_factory=list)


class PreferenceUpdate(BaseModel):
    reason: Optional[str] = Field(None, example="Save money for a vacation")
    quit_date: Optional[date] = Field(None, example="2025-08-01")
    language: Optional[str] = Field(None, example="en-us")

    goals: Optional[List[GoalUpdate]] = Field(
        None,
        description="List of goals to add/update; existing goals matched by `id`, new goals when `id` is absent",
    )

    class Config:
        orm_mode = True


class PreferenceOut(PreferenceBase):
    id: int
    goals: List[GoalOut] = []
    badges: List[BadgeOut] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
