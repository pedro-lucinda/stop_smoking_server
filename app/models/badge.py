from sqlalchemy import Column, Integer, Text, String
from sqlalchemy.orm import relationship
from app.db.base import Base


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, unique=True, nullable=False)
    image = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    # Back-reference for Preference.badges
    preferences = relationship(
        "Preference",
        secondary="preference_badges",
        back_populates="badges",
    )

    user = relationship(
        "User",
        back_populates="badges",
        cascade="all, delete-orphan",
    )
