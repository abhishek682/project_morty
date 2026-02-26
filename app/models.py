from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.db import Base


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    status = Column(String(64), nullable=False, index=True)
    species = Column(String(128), nullable=False, index=True)
    origin_name = Column(String(255), nullable=False, index=True)
    origin_url = Column(String(512), nullable=True)
    image = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
