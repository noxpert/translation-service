from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class PartOfSpeech(Base):
    __tablename__ = "parts_of_speech"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    label = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
