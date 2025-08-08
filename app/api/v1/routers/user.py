import anyio
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.api.v1.dependencies.auth0 import (
    can_update_email,
    get_current_user,
    update_user_email,
)
from app.api.v1.dependencies.db import get_async_db
from app.models.user import User as UserModel
from app.schemas.user import UserOut, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserOut, status_code=status.HTTP_200_OK)
async def read_current_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Return the currently authenticated user."""
    return current_user


@router.patch("/me", response_model=UserOut, status_code=status.HTTP_200_OK)
async def update_current_user(
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """
    Update the current user's profile.
    If `email` is included, we first sync it with Auth0, then mirror locally.
    """
    # Re-load the user in THIS session to avoid cross-session state issues
    user = await db.get(UserModel, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    data = user_update.model_dump(exclude_unset=True)

    # 1) Email change → Auth0 → local DB
    if "email" in data:
        new_email = data.pop("email")

        # Only allow native DB users (Auth0 "auth0" provider)
        can_update = await anyio.to_thread.run_sync(can_update_email, user.auth0_id)
        if not can_update:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Your account is managed by an external provider. "
                    "Update your email through your identity provider (e.g. Google)."
                ),
            )

        try:
            # Offload blocking HTTP call
            await anyio.to_thread.run_sync(update_user_email, user.auth0_id, new_email)
        except httpx.HTTPStatusError as exc:
            detail = exc.response.json().get("message", exc.response.text)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Auth0 rejected email change: {detail}",
            ) from exc

        user.email = new_email

    # 2) Other updatable fields (never allow ID fields)
    data.pop("auth0_id", None)
    for field, value in data.items():
        setattr(user, field, value)

    # 3) Persist and return
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        msg = str(e.orig).lower()
        if "unique" in msg and "email" in msg:
            raise HTTPException(status_code=400, detail="Email already in use") from e
        raise
    await db.refresh(user)

    return user
