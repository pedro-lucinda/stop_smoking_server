from sqlalchemy import Column, Date, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.db_config.base import Base, TimestampMixin
from app.models.goal import Goal


class Preference(TimestampMixin, Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    reason = Column(Text, nullable=False)
    quit_date = Column(Date, nullable=False)
    language = Column(Text, nullable=True, default="en-us")
    cig_per_day = Column(Integer, nullable=True, default=0)
    years_smoking = Column(Integer, nullable=True, default=0)
    cig_price = Column(
        Integer,
        nullable=True,
        default=0,
        comment="Price per cigarette in local currency",
    )

    goals = relationship(
        Goal,
        back_populates="preference",
        cascade="all, delete-orphan",
    )

    user = relationship(
        "User",
        back_populates="preference",
        uselist=False,
    )
