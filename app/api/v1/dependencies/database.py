
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_config.async_session import async_session


async def get_async_db() -> AsyncSession:
    async with async_session() as session:
        yield session
