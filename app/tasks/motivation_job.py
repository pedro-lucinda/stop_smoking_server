from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.preference import Preference
from app.services.motivation_service import generate_and_save_for_user

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def generate_and_store_daily_text():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Preference))
        for pref in res.scalars().all():
            try:
                await generate_and_save_for_user(db, pref.user_id)
            except Exception:
                pass
