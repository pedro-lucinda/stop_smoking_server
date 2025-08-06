from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class BadgesOut(BaseModel):
    id: int
    name: str
    description: str
    image: str
    condition_time: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BadgesIn(BaseModel):
    name: str
    description: str
    image: str
    condition_time: int

    class Config:
        from_attributes = True


class BadgesUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    condition_time: Optional[int] = None

    class Config:
        from_attributes = True


class BadgesDelete(BaseModel):
    id: int

    class Config:
        from_attributes = True


class BadgesListOut(BaseModel):
    badges: List[BadgesOut]
    total: int

    class Config:
        from_attributes = True


class UserBadgeBase(BaseModel):
    user_id: int
    badge_id: int


class UserBadgeCreate(UserBadgeBase):
    """Schema for assigning a badge to a user."""

    pass


class UserBadgeResponse(UserBadgeBase):
    """Response schema for a user-badge assignment."""

    class Config:
        orm_mode = True
