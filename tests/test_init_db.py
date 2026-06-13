from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - registers all models with Base
from app.database import Base
from app.db.init_db import init_db


def _fresh_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


def test_init_db_seeds_languages_and_pos():
    engine = _fresh_engine()
    with patch("app.db.init_db.engine", engine):
        with patch("app.db.init_db.SessionLocal", sessionmaker(bind=engine)):
            init_db()

    from app.models.language import Language
    from app.models.part_of_speech import PartOfSpeech

    session = sessionmaker(bind=engine)()
    assert session.query(Language).count() == 2
    assert session.query(PartOfSpeech).count() == 5
    session.close()


def test_init_db_skips_seed_when_already_initialized():
    engine = _fresh_engine()
    SessionLocal = sessionmaker(bind=engine)

    with patch("app.db.init_db.engine", engine):
        with patch("app.db.init_db.SessionLocal", SessionLocal):
            init_db()  # first call — seeds
            init_db()  # second call — should skip

    from app.models.language import Language

    session = SessionLocal()
    # Still exactly 2 languages — not doubled
    assert session.query(Language).count() == 2
    session.close()


def test_init_db_rolls_back_on_exception():
    engine = _fresh_engine()
    SessionLocal = sessionmaker(bind=engine)

    with patch("app.db.init_db.engine", engine):
        with patch("app.db.init_db.SessionLocal", SessionLocal):
            with patch("app.db.init_db.SessionLocal") as mock_session_cls:
                mock_session = mock_session_cls.return_value
                mock_session.query.return_value.count.return_value = 0
                mock_session.add_all = lambda items: None
                mock_session.commit.side_effect = Exception("db error")

                with pytest.raises(Exception, match="db error"):
                    init_db()

                mock_session.rollback.assert_called_once()
                mock_session.close.assert_called_once()
