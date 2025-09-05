from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db_config.base import Base, TimestampMixin
from app.models.user_badge import user_badges


class Badge(TimestampMixin, Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, unique=True, nullable=False)
    image = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    condition_time = Column(
        Integer,
        unique=True,
        nullable=False,
        default=0,
        server_default="0",
    )

    users = relationship(
        "User",
        secondary="user_badges",
        back_populates="badges",
    )
