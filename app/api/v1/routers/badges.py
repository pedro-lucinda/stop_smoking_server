from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.dependencies.auth0 import get_current_user, require_permission
from app.api.v1.dependencies.db import get_async_db
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
async def create_badge(
    badge_in: BadgesIn,
    db: AsyncSession = Depends(get_async_db),
):
    badge = Badge(**badge_in.dict())
    db.add(badge)  # add is sync; flush/commit does the I/O
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        if "uq_badges_condition_time" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A badge with that condition_time already exists.",
            ) from e
        raise
    await db.refresh(badge)
    return badge


@router.get("/", response_model=BadgesListOut)
async def list_badges(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
):
    total = await db.scalar(select(func.count()).select_from(Badge))
    result = await db.execute(select(Badge).offset(skip).limit(limit))
    badges = result.scalars().all()
    return BadgesListOut(badges=badges, total=total or 0)


@router.get("/me", response_model=BadgesListOut)
async def list_current_user_badges(
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
) -> BadgesListOut:
    # Total count (DISTINCT to be safe on M2M joins)
    total = await db.scalar(
        select(func.count(func.distinct(Badge.id)))
        .select_from(Badge)
        .join(User.badges)  # requires relationship User.badges -> Badge
        .where(User.id == current_user.id)  # swap to .sub if that's your key
    )

    # Page of badges
    result = await db.execute(
        select(Badge)
        .join(User.badges)
        .where(User.id == current_user.id)
        .order_by(Badge.id)
        .offset(skip)
        .limit(limit)
    )
    badges = result.scalars().all()
    return BadgesListOut(badges=badges, total=total or 0)


@router.get("/{badge_id}", response_model=BadgesOut)
async def get_badge(
    badge_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    badge = await db.get(Badge, badge_id)
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
async def update_badge(
    badge_id: int,
    badge_in: BadgesUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    badge = await db.get(Badge, badge_id)
    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found"
        )

    for field, value in badge_in.dict(exclude_unset=True).items():
        setattr(badge, field, value)

    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
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

    await db.refresh(badge)
    return badge


@router.delete(
    "/{badge_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("manage:badges"))],
)
async def delete_badge(
    badge_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    badge = await db.get(Badge, badge_id)
    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Badge not found"
        )

    try:
        await db.delete(badge)
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        # FK/cascade block – surface as 409
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Badge is referenced by other records",
        ) from e

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{badge_id}/assign",
    response_model=UserBadgeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("manage:badges"))],
)
async def assign_badge_to_user(
    badge_id: int,
    assign_in: UserBadgeCreate,
    db: AsyncSession = Depends(get_async_db),
):
    if badge_id != assign_in.badge_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Badge ID mismatch"
        )

    user = await db.get(User, assign_in.user_id, options=(selectinload(User.badges),))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    badge = await db.get(Badge, badge_id)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")

    if any(b.id == badge_id for b in user.badges):
        raise HTTPException(status_code=400, detail="Badge already assigned to user")

    user.badges.append(badge)  # relationship op is sync
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Could not assign badge") from e

    return assign_in
