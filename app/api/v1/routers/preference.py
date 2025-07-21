from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from typing import List

from app.api.v1.dependencies import get_db_session, get_current_user
from app.models.preference import Preference
from app.models.goal import Goal
from app.schemas.preference import PreferenceCreate, PreferenceOut, PreferenceUpdate
from app.models.motivation import DailyMotivation
from app.services.motivation_service import generate_and_save_for_user

router = APIRouter()


@router.get("/", response_model=PreferenceOut, status_code=status.HTTP_200_OK)
def list_preference(current_user=Depends(get_current_user)) -> PreferenceOut:
    preference = current_user.preference
    if not preference:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No preference set",
        )
    return preference


@router.post("/", response_model=PreferenceOut, status_code=status.HTTP_201_CREATED)
def create_preferences(
    pref_in: PreferenceCreate,
    db: Session = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> PreferenceOut:
    if current_user.preference:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preferences already set",
        )

    # 1) Create the Preference itself
    pref = Preference(
        user_id=current_user.id,
        reason=pref_in.reason,
        quit_date=pref_in.quit_date,
    )

    # 2) Turn each GoalCreate into a Goal model instance
    for goal_data in pref_in.goals:
        goal = Goal(
            description=goal_data.description,
            is_completed=goal_data.is_completed,
        )
        pref.goals.append(goal)

    # 3) Persist both Preference and its Goals in one go
    db.add(pref)
    db.commit()
    db.refresh(pref)

    # Generate motivation
    generate_and_save_for_user(db=db, user_id=current_user.id)
    return pref


@router.patch("/", response_model=PreferenceOut, status_code=status.HTTP_200_OK)
def update_preferences(
    pref_in: PreferenceUpdate,
    db: Session = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> PreferenceOut:
    """
    Update the current user's Preference and immediately regenerate
    today's motivation text if the quit_date has changed.
    """
    pref = current_user.preference
    if not pref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found"
        )

    # Update scalar fields except goals
    for field, value in pref_in.dict(exclude_unset=True, exclude={"goals"}).items():
        setattr(pref, field, value)

    # Handle nested goals if provided
    if pref_in.goals is not None:
        existing_goals = {g.id: g for g in pref.goals}
        new_goals_list: List[Goal] = []
        for goal_data in pref_in.goals:
            if goal_data.id and goal_data.id in existing_goals:
                goal = existing_goals[goal_data.id]
                if goal_data.description is not None:
                    goal.description = goal_data.description
                if goal_data.is_completed is not None:
                    goal.is_completed = goal_data.is_completed
            else:
                goal = Goal(
                    description=goal_data.description or "",
                    is_completed=goal_data.is_completed or False,
                )
            new_goals_list.append(goal)
        pref.goals[:] = new_goals_list

    db.commit()
    db.refresh(pref)

    # Evict today's stale motivation (if any) and regenerate
    today = date.today()
    db.query(DailyMotivation).filter_by(user_id=current_user.id, date=today).delete()
    db.commit()

    # Regenerate motivation text immediately with updated quit_date
    generate_and_save_for_user(db=db, user_id=current_user.id)

    return pref
