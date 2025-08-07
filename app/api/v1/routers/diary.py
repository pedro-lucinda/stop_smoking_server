from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth0 import get_current_user
from app.api.v1.dependencies.db import get_db_session
from app.models.diary import Diary
from app.schemas.diary import DiaryIn, DiaryListOut, DiaryOut, DiaryUpdate

router = APIRouter()


@router.get("/", response_model=DiaryListOut, status_code=status.HTTP_200_OK)
def list_diary_entries(
    skip: int = 0,
    limit: int = 100,
    current_user=Depends(get_current_user),
) -> DiaryListOut:
    """
    List all diary entries for the current user.

    This endpoint retrieves all diary entries associated with the authenticated user.
    It returns a list of diary entries along with the total count.

    Returns:
        DiaryListOut: A list of diary entries and the total count.
    """
    diaries = current_user.diaries[skip : skip + limit if limit else None]
    return DiaryListOut(diaries=diaries, total=len(current_user.diaries))


@router.get("/{diary_id}", response_model=DiaryOut, status_code=status.HTTP_200_OK)
def get_diary_entry(
    diary_id: int,
    current_user=Depends(get_current_user),
) -> DiaryOut:
    """
    Retrieve a specific diary entry by its ID.

    This endpoint fetches a diary entry for the authenticated user based on the provided ID.

    Args:
        diary_id (int): The ID of the diary entry to retrieve.
    Returns:
        DiaryOut: The diary entry with the specified ID.
    Raises:
        HTTPException: If the diary entry does not exist or does not belong to the current user.
    """
    diary = next((d for d in current_user.diaries if d.id == diary_id), None)
    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diary entry not found",
        )
    return DiaryOut.from_orm(diary)


@router.post("/", response_model=DiaryOut, status_code=status.HTTP_201_CREATED)
def create_diary_entry(
    diary_in: DiaryIn,
    db: Session = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> DiaryOut:
    """
    Create a new diary entry for the current user.

    This endpoint allows the authenticated user to create a new diary entry.

    Args:
        diary_in (DiaryIn): The data for the new diary entry.
    Returns:
        DiaryOut: The created diary entry.
    """
    # Only allow one diary entry per day
    existing_entry = next(
        (d for d in current_user.diaries if d.date == diary_in.date), None
    )
    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Diary entry for this date already exists",
        )

    new_diary = Diary(
        user_id=current_user.id,
        date=diary_in.date,
        notes=diary_in.notes,
        have_smoked=diary_in.have_smoked,
        craving_range=diary_in.craving_range,
        number_of_cravings=diary_in.number_of_cravings,
        number_of_cigarets_smoked=diary_in.number_of_cigarets_smoked,
    )

    db.add(new_diary)
    db.commit()
    db.refresh(new_diary)

    return DiaryOut.from_orm(new_diary)


@router.patch("/{diary_id}", response_model=DiaryOut, status_code=status.HTTP_200_OK)
def update_diary_entry(
    diary_id: int,
    diary_update: DiaryUpdate,
    db: Session = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> DiaryOut:
    """
    Update an existing diary entry.

    This endpoint allows the authenticated user to update a specific diary entry.

    Args:
        diary_id (int): The ID of the diary entry to update.
        diary_update (DiaryUpdate): The updated data for the diary entry.
    Returns:
        DiaryOut: The updated diary entry.
    Raises:
        HTTPException: If the diary entry does not exist or does not belong to the current user.
    """
    diary = next((d for d in current_user.diaries if d.id == diary_id), None)
    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diary entry not found",
        )

    for key, value in diary_update.dict(exclude_unset=True).items():
        setattr(diary, key, value)

    db.commit()
    db.refresh(diary)

    return DiaryOut.from_orm(diary)


@router.delete("/{diary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diary_entry(
    diary_id: int,
    db: Session = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """
    Delete a diary entry.

    This endpoint allows the authenticated user to delete a specific diary entry by its ID.

    Args:
        diary_id (int): The ID of the diary entry to delete.
    Raises:
        HTTPException: If the diary entry does not exist or does not belong to the current user
    """
    diary = next((d for d in current_user.diaries if d.id == diary_id), None)
    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diary entry not found",
        )

    db.delete(diary)
    db.commit()
    return {"message": "Diary entry deleted successfully"}
