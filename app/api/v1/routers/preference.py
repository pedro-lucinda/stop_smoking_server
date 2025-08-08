from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.dependencies.auth0 import get_current_user
from app.api.v1.dependencies.db import get_async_db
from app.models.goal import Goal
from app.models.motivation import DailyMotivation
from app.models.preference import Preference
from app.schemas.preference import PreferenceCreate, PreferenceOut, PreferenceUpdate
from app.services.motivation_service import generate_and_save_for_user

router = APIRouter()


@router.get("/", response_model=PreferenceOut, status_code=status.HTTP_200_OK)
async def list_preference(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
) -> PreferenceOut:
    # Eager-load goals to avoid async lazy-loads
    res = await db.execute(
        select(Preference)
        .options(selectinload(Preference.goals))
        .where(Preference.user_id == current_user.id)
    )
    preference = res.scalar_one_or_none()
    if not preference:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No preference set"
        )
    return preference


@router.post("/", response_model=PreferenceOut, status_code=status.HTTP_201_CREATED)
async def create_preferences(
    pref_in: PreferenceCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
) -> PreferenceOut:
    # Ensure user doesn't already have a preference
    exists = await db.scalar(
        select(Preference.id).where(Preference.user_id == current_user.id).limit(1)
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Preferences already set"
        )

    pref = Preference(
        user_id=current_user.id,
        reason=pref_in.reason,
        quit_date=pref_in.quit_date,
    )

    for goal_data in pref_in.goals or []:
        goal = Goal(
            description=goal_data.description,
            is_completed=goal_data.is_completed,
        )
        pref.goals.append(goal)

    db.add(pref)
    await db.commit()
    await db.refresh(pref)

    # Generate today's motivation (async service)
    await generate_and_save_for_user(db=db, user_id=current_user.id)
    return pref


@router.patch("/", response_model=PreferenceOut, status_code=status.HTTP_200_OK)
async def update_preferences(
    pref_in: PreferenceUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
) -> PreferenceOut:
    # Load current preference with goals
    res = await db.execute(
        select(Preference)
        .options(selectinload(Preference.goals))
        .where(Preference.user_id == current_user.id)
    )
    pref = res.scalar_one_or_none()
    if not pref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found"
        )

    # Update scalar fields (except goals)
    for field, value in pref_in.model_dump(
        exclude_unset=True, exclude={"goals"}
    ).items():
        setattr(pref, field, value)

    # Handle nested goals if provided
    if pref_in.goals is not None:
        existing = {g.id: g for g in pref.goals if g.id is not None}
        new_list: List[Goal] = []
        for g in pref_in.goals:
            if g.id and g.id in existing:
                goal = existing[g.id]
                if g.description is not None:
                    goal.description = g.description
                if g.is_completed is not None:
                    goal.is_completed = g.is_completed
                new_list.append(goal)
            else:
                new_list.append(
                    Goal(
                        description=g.description or "",
                        is_completed=(
                            bool(g.is_completed)
                            if g.is_completed is not None
                            else False
                        ),
                    )
                )
        pref.goals[:] = new_list

    await db.commit()
    await db.refresh(pref)

    # Remove today's old motivation and regenerate
    today = date.today()
    await db.execute(
        delete(DailyMotivation).where(
            DailyMotivation.user_id == current_user.id,
            DailyMotivation.date == today,
        )
    )
    await db.commit()

    await generate_and_save_for_user(db=db, user_id=current_user.id)
    return pref
