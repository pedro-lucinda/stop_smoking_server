from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth0 import get_current_user
from app.api.v1.dependencies.db import get_async_db
from app.models.craving import Craving
from app.schemas.cravings import CravingIn, CravingListOut, CravingOut

router = APIRouter()


@router.get("/", response_model=CravingListOut, status_code=status.HTTP_200_OK)
async def list_cravings(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
) -> CravingListOut:
    total = await db.scalar(
        select(func.count(Craving.id)).where(Craving.user_id == current_user.id)
    )
    result = await db.execute(
        select(Craving)
        .where(Craving.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    cravings = result.scalars().all()
    return CravingListOut(cravings=cravings, total=total or 0)


@router.get("/{craving_id}", response_model=CravingOut, status_code=status.HTTP_200_OK)
async def get_craving(
    craving_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
) -> CravingOut:
    result = await db.execute(
        select(Craving).where(
            Craving.id == craving_id, Craving.user_id == current_user.id
        )
    )
    craving = result.scalar_one_or_none()
    if not craving:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Craving not found"
        )
    return CravingOut.from_orm(craving)


@router.post("/", response_model=CravingOut, status_code=status.HTTP_201_CREATED)
async def create_craving(
    craving_in: CravingIn,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
) -> CravingOut:
    craving = Craving(**craving_in.dict(), user_id=current_user.id)
    db.add(craving)  # add/delete are not awaited
    await db.commit()
    await db.refresh(craving)
    return CravingOut.from_orm(craving)


@router.put("/{craving_id}", response_model=CravingOut, status_code=status.HTTP_200_OK)
async def update_craving(
    craving_id: int,
    craving_update: CravingIn,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
) -> CravingOut:
    result = await db.execute(
        select(Craving).where(
            Craving.id == craving_id, Craving.user_id == current_user.id
        )
    )
    craving = result.scalar_one_or_none()
    if not craving:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Craving not found"
        )

    for key, value in craving_update.dict(exclude_unset=True).items():
        setattr(craving, key, value)

    await db.commit()
    await db.refresh(craving)
    return CravingOut.from_orm(craving)


@router.delete("/{craving_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_craving(
    craving_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Craving)
        .where(Craving.id == craving_id)
        .where(Craving.user_id == current_user.id)
    )
    craving = result.scalar_one_or_none()

    if not craving:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Craving not found"
        )

    await db.delete(craving)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
