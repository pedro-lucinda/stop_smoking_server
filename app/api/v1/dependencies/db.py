from typing import Generator

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User as UserModel


def get_db_session() -> Generator[Session, None, None]:
    """
    Provide a database session for a request.
    """
    yield from get_db()
