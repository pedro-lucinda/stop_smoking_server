"""
SQLAlchemy model for the User.
"""

from sqlalchemy import TIMESTAMP, Column, Integer, Text, text

from app.db.base import Base


class User(Base):
    """
    Database model for users.

    Attributes:
        id: Primary key.
        email: Unique user email.
        password_hash: Bcrypt-hashed password.
        created_at: Timestamp when the record was created.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(Text, unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False
    )
