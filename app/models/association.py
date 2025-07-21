from datetime import datetime
from sqlalchemy import Table, Column, ForeignKey, DateTime
from app.db.base import Base

preference_badges = Table(
    "preference_badges",
    Base.metadata,
    Column(
        "preference_id",
        ForeignKey("preferences.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("badge_id", ForeignKey("badges.id", ondelete="CASCADE"), primary_key=True),
    Column("awarded_at", DateTime, default=datetime.utcnow, nullable=False),
)
