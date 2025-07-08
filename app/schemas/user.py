"""
Pydantic schemas for user operations.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """
    Shared properties of a user.
    """

    email: EmailStr = Field(..., description="Unique user email address")


class UserCreate(UserBase):
    """
    Properties required to create a new user.
    """

    password: str = Field(..., description="Plain-text password")


class UserRead(UserBase):
    """
    Properties returned when reading a user.
    """

    id: int = Field(..., description="Unique identifier of the user")
    created_at: datetime = Field(..., description="Timestamp when the user was created")

    class Config:
        from_attributes = True
