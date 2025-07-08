"""
Authentication router for user signup and login.
Provides endpoints to create a new user and obtain JWT access tokens.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_db_session
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.token import LoginIn, Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter(tags=["auth"])


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, db: Session = Depends(get_db_session)) -> UserRead:
    """
    Register a new user by hashing their password and storing their record.

    Args:
        user_in: UserCreate schema with email and plain-text password.
        db: Database session dependency.

    Returns:
        UserRead: Public user data excluding the password.
    """

    # Check if user already exists
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash the password
    hashed = hash_password(user_in.password)
    user = User(email=user_in.email, password_hash=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login_json(data: LoginIn, db: Session = Depends(get_db_session)):
    """
    Authenticate a user and issue a JWT.

    - **email**: the user's email
    - **password**: the user's password
    """
    # 1) Look up the user by email
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):  # type: ignore[arg-type]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2) Create a token with the user ID as the "sub" claim
    access_token = create_access_token({"sub": str(user.id)})

    return Token(access_token=access_token, token_type="bearer")
