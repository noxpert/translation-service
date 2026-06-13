import logging

from app.database import Base, SessionLocal, engine
from app.models import Language, PartOfSpeech  # noqa: F401 - registers all models

logger = logging.getLogger(__name__)


def init_db():
    """Create all tables and insert seed data if needed. Idempotent."""
    # Import all models so they are registered with Base.metadata
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(Language).count()
        if existing > 0:
            logger.info("Database already initialized, skipping seed")
            return

        # Seed languages
        db.add_all(
            [
                Language(code="en", name="English"),
                Language(code="hu", name="Hungarian"),
            ]
        )

        # Seed parts of speech
        db.add_all(
            [
                PartOfSpeech(code="noun", label="Noun"),
                PartOfSpeech(code="verb", label="Verb"),
                PartOfSpeech(code="adj", label="Adjective"),
                PartOfSpeech(code="adv", label="Adverb"),
                PartOfSpeech(code="other", label="Other"),
            ]
        )

        db.commit()
        logger.info("Database initialized with seed data")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
