from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Phrase(Base):
    __tablename__ = "phrases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    notes = Column(String, nullable=True)
    context = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    translations = relationship(
        "PhraseTranslation",
        back_populates="phrase",
        cascade="all, delete-orphan",
    )
    source = relationship("Source")


class PhraseTranslation(Base):
    __tablename__ = "phrase_translations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phrase_id = Column(Integer, ForeignKey("phrases.id", ondelete="CASCADE"), nullable=False)
    language_id = Column(Integer, ForeignKey("languages.id"), nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    phrase = relationship("Phrase", back_populates="translations")
    language = relationship("Language")
