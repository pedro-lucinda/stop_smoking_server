"""
Pydantic schema for returning JWT access tokens.
"""

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """
    JWT token response schema.

    Attributes:
        access_token: The JWT string to use for authenticated requests.
        token_type: Must be 'bearer'.
    """

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(
        "bearer", description="Type of the token, typically 'bearer'"
    )


class LoginIn(BaseModel):
    """Schema for user login input."""

    email: EmailStr
    password: str
