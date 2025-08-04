from datetime import date
from typing import Optional

from pydantic import BaseModel


class CravingOut(BaseModel):
    id: int
    date: date
    comments: str
    have_smoked: bool
    desire_range: Optional[int] = 0
    number_of_cigarets_smoked: Optional[int] = 0
    feeling: Optional[str] = None
    activity: Optional[str] = None
    company: Optional[str] = None

    class Config:
        from_attributes = True

class CravingIn(BaseModel):
    date: date
    comments: str
    have_smoked: bool
    desire_range: Optional[int] = 0
    number_of_cigarets_smoked: Optional[int] = 0
    feeling: Optional[str] = None
    activity: Optional[str] = None
    company: Optional[str] = None

    class Config:
        from_attributes = True

class CravingUpdate(BaseModel):
    comments: Optional[str] = None
    have_smoked: Optional[bool] = None
    desire_range: Optional[int] = None
    number_of_cigarets_smoked: Optional[int] = None
    feeling: Optional[str] = None
    activity: Optional[str] = None
    company: Optional[str] = None

    class Config:
        from_attributes = True

class CravingListOut(BaseModel):
    cravings: list[CravingOut]
    total: int

    class Config:
        from_attributes = True
