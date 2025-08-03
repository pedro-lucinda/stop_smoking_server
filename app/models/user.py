from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    auth0_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    surname = Column(String, nullable=True)
    img = Column(String, nullable=True)

    preference = relationship(
        "app.models.preference.Preference",
        back_populates="user",
        uselist=False,
    )
    daily_motivations = relationship(
        "DailyMotivation", back_populates="user", cascade="all, delete-orphan"
    )
    cravings = relationship(
        "Craving", back_populates="user", cascade="all, delete-orphan"
    )
    diaries = relationship("Diary", back_populates="user", cascade="all, delete-orphan")

    badges = relationship(
        "Badge",
        back_populates="user",
        cascade="all, delete-orphan",
    )
