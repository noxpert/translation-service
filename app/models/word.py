from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_of_speech_id = Column(Integer, ForeignKey("parts_of_speech.id"), nullable=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    notes = Column(String, nullable=True)
    context = Column(String, nullable=True)
    is_verified = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    translations = relationship(
        "WordTranslation",
        back_populates="word",
        cascade="all, delete-orphan",
    )
    part_of_speech = relationship("PartOfSpeech")
    source = relationship("Source")


class WordTranslation(Base):
    __tablename__ = "word_translations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word_id = Column(Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False)
    language_id = Column(Integer, ForeignKey("languages.id"), nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    word = relationship("Word", back_populates="translations")
    language = relationship("Language")
