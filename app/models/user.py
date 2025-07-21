from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base
from .preference import Preference

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name            = Column(String, nullable=True)
    surname         = Column(String, nullable=True)

    # One-to-one relationship to Preference
    preference = relationship(
        "app.models.preference.Preference",
        back_populates="user",
        uselist=False,
    )

    daily_motivations = relationship(
        "DailyMotivation",
        back_populates="user",
        cascade="all, delete-orphan"
    )