from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.api.v1.dependencies.auth0 import get_current_user
from app.api.v1.dependencies.db import get_async_db
from app.models.diary import Diary
from app.schemas.diary import DiaryIn, DiaryListOut, DiaryOut, DiaryUpdate

router = APIRouter()


@router.get("/", response_model=DiaryListOut, status_code=status.HTTP_200_OK)
async def list_diary_entries(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
) -> DiaryListOut:
    total = await db.scalar(
        select(func.count(Diary.id)).where(Diary.user_id == current_user.id)
    )
    result = await db.execute(
        select(Diary)
        .where(Diary.user_id == current_user.id)
        .order_by(Diary.date.desc())
        .offset(skip)
        .limit(limit)
    )
    diaries = result.scalars().all()
    return DiaryListOut(diaries=diaries, total=total or 0)


@router.get("/{diary_id}", response_model=DiaryOut, status_code=status.HTTP_200_OK)
async def get_diary_entry(
    diary_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
) -> DiaryOut:
    result = await db.execute(
        select(Diary).where(Diary.id == diary_id, Diary.user_id == current_user.id)
    )
    diary = result.scalar_one_or_none()
    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found"
        )
    return DiaryOut.from_orm(diary)


@router.post("/", response_model=DiaryOut, status_code=status.HTTP_201_CREATED)
async def create_diary_entry(
    diary_in: DiaryIn,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
) -> DiaryOut:
    # Enforce one diary entry per day
    exists = await db.scalar(
        select(Diary.id)
        .where(
            Diary.user_id == current_user.id,
            Diary.date == diary_in.date,
        )
        .limit(1)
    )
    if exists:
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
    await db.commit()
    await db.refresh(new_diary)
    return DiaryOut.from_orm(new_diary)


@router.patch("/{diary_id}", response_model=DiaryOut, status_code=status.HTTP_200_OK)
async def update_diary_entry(
    diary_id: int,
    diary_update: DiaryUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
) -> DiaryOut:
    result = await db.execute(
        select(Diary).where(Diary.id == diary_id, Diary.user_id == current_user.id)
    )
    diary = result.scalar_one_or_none()
    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found"
        )

    updates = diary_update.dict(exclude_unset=True)

    # If date changes, keep the (user_id, date) uniqueness
    if "date" in updates and updates["date"] != diary.date:
        clash = await db.scalar(
            select(Diary.id)
            .where(
                Diary.user_id == current_user.id,
                Diary.date == updates["date"],
                Diary.id != diary_id,
            )
            .limit(1)
        )
        if clash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another diary entry already exists for that date",
            )

    for key, value in updates.items():
        setattr(diary, key, value)

    await db.commit()
    await db.refresh(diary)
    return DiaryOut.from_orm(diary)


@router.delete("/{diary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_diary_entry(
    diary_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Diary).where(Diary.id == diary_id, Diary.user_id == current_user.id)
    )
    diary = result.scalar_one_or_none()
    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found"
        )

    try:
        await db.delete(diary)  # async delete
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Diary entry is referenced by other records",
        ) from e

    return Response(status_code=status.HTTP_204_NO_CONTENT)
