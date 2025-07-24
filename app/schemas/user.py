from pydantic import BaseModel, EmailStr
from typing import Optional


class UserOut(BaseModel):
    id: int
    auth0_id: str
    email: EmailStr
    name: Optional[str]
    surname: Optional[str]
    img: Optional[str]

    class Config:
        orm_mode = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    surname: Optional[str] = None
    img: Optional[str] = None

    class Config:
        orm_mode = True
