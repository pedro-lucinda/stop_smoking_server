from sqlalchemy import Column, Date, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.db_config.base import Base, TimestampMixin


class DailyMotivation(TimestampMixin, Base):
    __tablename__ = "daily_motivations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date = Column(Date, nullable=False, index=True)

    progress = Column(Text, nullable=False)
    motivation = Column(Text, nullable=False)
    cravings = Column(Text, nullable=False)
    ideas = Column(Text, nullable=False)
    recommendations = Column(Text, nullable=True)

    user = relationship("User", back_populates="daily_motivations")
    user = relationship("User", back_populates="daily_motivations")
