from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth0 import get_current_user
from app.api.v1.dependencies.db import get_db_session
from app.models.craving import Craving
from app.schemas.cravings import CravingIn, CravingListOut, CravingOut

router = APIRouter()


@router.get("/", response_model=CravingListOut, status_code=status.HTTP_200_OK)
def list_cravings(
    current_user=Depends(get_current_user),
) -> CravingListOut:
    """
    List all cravings for the current user.

    This endpoint retrieves all cravings associated with the authenticated user.
    It returns a list of cravings along with the total count.

    Returns:
        CravingListOut: A list of cravings and the total count.
    """
    cravings = current_user.cravings
    return CravingListOut(cravings=cravings, total=len(cravings))


@router.get("/{craving_id}", response_model=CravingOut, status_code=status.HTTP_200_OK)
def get_craving(
    craving_id: int,
    current_user=Depends(get_current_user),
) -> CravingOut:
    """
    Retrieve a specific craving by its ID.

    This endpoint fetches a craving for the authenticated user based on the provided ID.

    Args:
        craving_id (int): The ID of the craving to retrieve.
    Returns:
        CravingOut: The craving with the specified ID.
    Raises:
        HTTPException: If the craving does not exist or does not belong to the current user.
    """
    craving = next((c for c in current_user.cravings if c.id == craving_id), None)
    if not craving:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Craving not found",
        )
    return CravingOut.from_orm(craving)


@router.post("/", response_model=CravingOut, status_code=status.HTTP_201_CREATED)
def create_craving(
    craving_in: CravingIn,
    db: Session = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> CravingOut:
    """
    Create a new craving for the current user.

    This endpoint allows the authenticated user to create a new craving entry.

    Args:
        craving_in (CravingIn): The data for the new craving.
    Returns:
        CravingOut: The created craving entry.
    """
    craving = Craving(**craving_in.dict(), user_id=current_user.id)
    db.add(craving)
    db.commit()
    db.refresh(craving)
    return CravingOut.from_orm(craving)


@router.put("/{craving_id}", response_model=CravingOut, status_code=status.HTTP_200_OK)
def update_craving(
    craving_id: int,
    craving_update: CravingIn,
    db: Session = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> CravingOut:
    """
    Update an existing craving entry.

    This endpoint allows the authenticated user to update a craving entry by its ID.

    Args:
        craving_id (int): The ID of the craving to update.
        craving_update (CravingIn): The updated data for the craving.
    Returns:
        CravingOut: The updated craving entry.
    Raises:
        HTTPException: If the craving does not exist or does not belong to the current user.
    """
    craving = (
        db.query(Craving)
        .filter(Craving.id == craving_id, Craving.user_id == current_user.id)
        .first()
    )
    if not craving:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Craving not found",
        )

    for key, value in craving_update.dict(exclude_unset=True).items():
        setattr(craving, key, value)

    db.commit()
    db.refresh(craving)
    return CravingOut.from_orm(craving)


@router.delete("/{craving_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_craving(
    craving_id: int,
    db: Session = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """
    Delete a craving entry.

    This endpoint allows the authenticated user to delete a craving entry by its ID.

    Args:
        craving_id (int): The ID of the craving to delete.
    Raises:
        HTTPException: If the craving does not exist or does not belong to the current user.
    """
    craving = (
        db.query(Craving)
        .filter(Craving.id == craving_id, Craving.user_id == current_user.id)
        .first()
    )
    if not craving:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Craving not found",
        )

    db.delete(craving)
    db.commit()
    return {"detail": "Craving deleted successfully"}
