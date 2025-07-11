from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_db_session, get_current_user
from app.models.preference import Preference
from app.models.goal       import Goal
from app.schemas.preference import PreferenceCreate, PreferenceOut

router = APIRouter()

@router.post(
    "/", 
    response_model=PreferenceOut, 
    status_code=status.HTTP_201_CREATED
)
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
    return pref
