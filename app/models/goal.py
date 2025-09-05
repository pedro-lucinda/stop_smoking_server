from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db_config.base import Base, TimestampMixin


class Goal(TimestampMixin, Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    preference_id = Column(
        Integer, ForeignKey("preferences.id", ondelete="CASCADE"), nullable=False
    )
    description = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)

    preference = relationship("Preference", back_populates="goals")
