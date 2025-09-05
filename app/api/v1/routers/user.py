import anyio
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete

from app.api.v1.dependencies.auth0 import (
    can_update_email,
    get_current_user,
    update_user_email,
)
from app.api.v1.dependencies.async_db_session import get_async_db
from app.models.user import User as UserModel
from app.models.craving import Craving
from app.models.diary import Diary
from app.models.preference import Preference
from app.models.motivation import DailyMotivation
from app.models.user_badge import user_badges
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


@router.delete("/me/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_user_data(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    """
    Reset all user data by deleting cravings, diary entries, preferences, 
    daily motivations, and user badge associations.
    This action cannot be undone.
    """
    try:
        # Delete user's cravings
        await db.execute(
            delete(Craving).where(Craving.user_id == current_user.id)
        )
        
        # Delete user's diary entries
        await db.execute(
            delete(Diary).where(Diary.user_id == current_user.id)
        )
        
        # Delete user's daily motivations
        await db.execute(
            delete(DailyMotivation).where(DailyMotivation.user_id == current_user.id)
        )
        
        # Delete user's preferences (this will cascade to goals due to the relationship)
        await db.execute(
            delete(Preference).where(Preference.user_id == current_user.id)
        )
        
        # Delete user's badge associations
        await db.execute(
            delete(user_badges).where(user_badges.c.user_id == current_user.id)
        )
        
        # Commit all deletions
        await db.commit()
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset user data: {str(e)}"
        ) from e
