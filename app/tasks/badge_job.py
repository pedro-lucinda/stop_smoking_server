from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.badge import Badge
from app.models.preference import Preference
from app.models.user import User

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def assign_due_badges() -> None:
    now = datetime.utcnow()
    async with AsyncSessionLocal() as db:
        prefs = (await db.execute(select(Preference))).scalars().all()
        badges = (await db.execute(select(Badge))).scalars().all()

        for pref in prefs:
            user = await db.get(User, pref.user_id)
            if not user:
                continue
            minutes_since_quit = int((now.date() - pref.quit_date).days * 24 * 60)
            for badge in badges:
                if (
                    badge.id not in {b.id for b in user.badges}
                    and minutes_since_quit >= badge.condition_time
                ):
                    user.badges.append(badge)
        await db.commit()
