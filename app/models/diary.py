from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class Diary(TimestampMixin, Base):
    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date = Column(Date, nullable=False, index=True)
    notes = Column(Text, nullable=False)
    have_smoked = Column(Boolean, default=False, nullable=False)
    craving_range = Column(Integer, nullable=True, default=0)
    number_of_cravings = Column(Integer, nullable=True, default=0)
    number_of_cigarets_smoked = Column(Integer, nullable=True, default=0)

    user = relationship("User", back_populates="diaries")
