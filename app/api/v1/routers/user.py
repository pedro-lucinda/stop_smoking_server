import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth0 import (
    can_update_email,
    get_current_user,
    update_user_email,
)
from app.api.v1.dependencies.db import get_db_session
from app.models.user import User as UserModel
from app.schemas.user import UserOut, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserOut, status_code=status.HTTP_200_OK)
def read_current_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Return the currently authenticated user."""
    return current_user


@router.patch("/me", response_model=UserOut, status_code=status.HTTP_200_OK)
def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db_session),
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """
    Update the current user's profile.
    If `email` is included, we first sync it with Auth0, then mirror locally.
    """
    data = user_update.model_dump(exclude_unset=True)

    # 1) Email change → Auth0 → local DB
    if "email" in data:
        new_email = data.pop("email")
        # 1) Only allow native DB users to proceed
        if not can_update_email(current_user.auth0_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Your account is managed by an external provider. "
                    "To change your email, please update it through your identity provider (e.g. Google)."
                ),
            )
        try:
            update_user_email(current_user.auth0_id, new_email)
        except httpx.HTTPStatusError as exc:
            # e.g. 409 Conflict: email already in use
            detail = exc.response.json().get("message", exc.response.text)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Auth0 rejected email change: {detail}",
            ) from exc
        # on success:
        current_user.email = new_email

    # 2) Other updatable fields (never allow ID fields)
    data.pop("auth0_id", None)
    for field, value in data.items():
        setattr(current_user, field, value)

    # 3) Persist and return
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
