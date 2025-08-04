from datetime import date
from typing import Optional

from pydantic import BaseModel


class DiaryOut(BaseModel):
    id: int
    date: date
    notes: str
    have_smoked: bool
    craving_range: Optional[int] = None
    number_of_cravings: Optional[int] = None
    number_of_cigarets_smoked: Optional[int] = None

    class Config:
        from_attributes = True


class DiaryIn(BaseModel):
    date: date
    notes: str
    have_smoked: bool
    craving_range: Optional[int] = None
    number_of_cravings: Optional[int] = None
    number_of_cigarets_smoked: Optional[int] = None

    class Config:
        from_attributes = True


class DiaryUpdate(BaseModel):
    notes: Optional[str] = None
    have_smoked: Optional[bool] = None
    craving_range: Optional[int] = None
    number_of_cravings: Optional[int] = None
    number_of_cigarets_smoked: Optional[int] = None

    class Config:
        from_attributes = True


class DiaryListOut(BaseModel):
    diaries: list[DiaryOut]
    total: int

    class Config:
        from_attributes = True
