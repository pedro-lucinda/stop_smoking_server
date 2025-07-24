from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies.db import get_db_session
from app.api.v1.dependencies.auth0 import get_current_user
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
    """Update fields of the current user and return the updated record."""
    data = user_update.dict(exclude_unset=True)
    # Prevent updating auth0_id
    data.pop("auth0_id", None)

    for field, value in data.items():
        setattr(current_user, field, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
