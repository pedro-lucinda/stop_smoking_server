from sqlalchemy import Column, ForeignKey, Integer, Table

from app.db.base import Base


user_badges = Table(
    "user_badges",
    Base.metadata,
    Column(
        "user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "badge_id",
        Integer,
        ForeignKey("badges.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
