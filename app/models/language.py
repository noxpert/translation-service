from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class Language(Base):
    __tablename__ = "languages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
