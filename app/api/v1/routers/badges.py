from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth0 import get_current_user, require_permission
from app.api.v1.dependencies.db import get_db_session
from app.models.badge import Badge
from app.models.user import User
from app.schemas.badges import (
    BadgesIn,
    BadgesListOut,
    BadgesOut,
    BadgesUpdate,
    UserBadgeCreate,
    UserBadgeResponse,
)

router = APIRouter()


@router.post(
    "/",
    response_model=BadgesOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("manage:badges"))],
)
def create_badge(
    badge_in: BadgesIn,
    db: Session = Depends(get_db_session),
):
    badge = Badge(**badge_in.dict())
    db.add(badge)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        if "uq_badges_condition_time" in str(e.orig):
            raise HTTPException(
                status_code=400,
                detail="A badge with that condition_time already exists.",
            ) from e
        raise
    db.refresh(badge)
    return badge


@router.get("/", response_model=BadgesListOut)
def list_badges(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session),
):
    query = db.query(Badge)
    total = query.count()
    badges = query.offset(skip).limit(limit).all()
    return BadgesListOut(badges=badges, total=total)


@router.get("/me", response_model=BadgesListOut)
def list_current_user_badges(
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> BadgesListOut:
    badges = current_user.badges
    total = len(badges)
    sliced = badges[skip : skip + limit]
    return BadgesListOut(badges=sliced, total=total)


@router.get("/{badge_id}", response_model=BadgesOut)
def get_badge(
    badge_id: int,
    db: Session = Depends(get_db_session),
):
    badge = db.query(Badge).get(badge_id)
    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found"
        )
    return badge


@router.put(
    "/{badge_id}",
    response_model=BadgesOut,
    dependencies=[Depends(require_permission("manage:badges"))],
)
def update_badge(
    badge_id: int,
    badge_in: BadgesUpdate,
    db: Session = Depends(get_db_session),
):
    badge = db.get(Badge, badge_id)
    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found"
        )

    # only update the fields that were actually sent
    for field, value in badge_in.dict(exclude_unset=True).items():
        setattr(badge, field, value)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # dig into e.orig to pick out which constraint failed
        err_msg = str(e.orig).lower()
        if "badges_name_key" in err_msg or "uq_badges_name" in err_msg:
            detail = "A badge with that name already exists."
        elif (
            "badges_condition_time_key" in err_msg
            or "uq_badges_condition_time" in err_msg
        ):
            detail = "A badge with that condition_time already exists."
        else:
            detail = "Badge update failed due to a unique constraint violation."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail
        ) from e

    db.refresh(badge)
    return badge


@router.delete(
    "/{badge_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("manage:badges"))],
)
def delete_badge(
    badge_id: int,
    db: Session = Depends(get_db_session),
):
    badge = db.query(Badge).get(badge_id)
    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found"
        )
    db.delete(badge)
    db.commit()


@router.post(
    "/{badge_id}/assign",
    response_model=UserBadgeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("manage:badges"))],
)
def assign_badge_to_user(
    badge_id: int,
    assign_in: UserBadgeCreate,
    db: Session = Depends(get_db_session),
):
    if badge_id != assign_in.badge_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Badge ID mismatch"
        )
    user = db.query(User).get(assign_in.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    badge = db.query(Badge).get(badge_id)
    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found"
        )
    if badge in user.badges:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Badge already assigned to user",
        )
    user.badges.append(badge)
    db.commit()
    return assign_in
