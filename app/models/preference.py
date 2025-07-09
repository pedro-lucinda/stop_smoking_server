from sqlalchemy import Column, Integer, Text, Date, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin
from .association import preference_badges
from .badge import Badge
from .goal import Goal

class Preference(TimestampMixin, Base):
    __tablename__ = "preferences"
    __table_args__ = (
        CheckConstraint("quit_date <= CURRENT_DATE", name="chk_quit_not_in_future"),
    )

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    reason    = Column(Text, nullable=False)
    quit_date = Column(Date, nullable=False)

    # Relationships
    goals  = relationship(
        "Goal",
        back_populates="preference",
        cascade="all, delete-orphan",
    )
    badges = relationship(
        "Badge",
        secondary="preference_badges",
        back_populates="preferences",
    )

    user = relationship("User", back_populates="preference")