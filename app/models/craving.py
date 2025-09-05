from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.db_config.base import Base, TimestampMixin


class Craving(TimestampMixin, Base):
    __tablename__ = "cravings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date = Column(Date, nullable=False, index=True)
    comments = Column(Text, nullable=False)
    have_smoked = Column(Boolean, default=False, nullable=False)
    desire_range = Column(Integer, nullable=True, default=0)
    number_of_cigarets_smoked = Column(Integer, nullable=True, default=0)
    feeling = Column(Text, nullable=True)
    activity = Column(Text, nullable=True)
    company = Column(Text, nullable=True)

    user = relationship("User", back_populates="cravings")
