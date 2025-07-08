"""
Engine and session setup for PostgreSQL.

Creates a single SQLAlchemy Engine for the app, a sessionmaker
to produce per-request Session objects, and a FastAPI dependency
to provide & close sessions around each request.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# 1 Create the SQAlchemy Engine
# pool_pre_ping=True ensures stale connections are recycled.
engine = create_engine(
    settings.sqlalchemy_database_uri,
    pool_pre_ping=True,
)

# 2. Create a configured "SessionLocal" class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session and
    ensures it’s closed once the request is finished.

    Yields:
        Session: a SQLAlchemy Session bound to the engine.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
