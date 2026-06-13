import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app as fastapi_app
from app.models.language import Language
from app.models.part_of_speech import PartOfSpeech

# Import all models to register them with Base.metadata
import app.models  # noqa: F401


# In-memory SQLite with StaticPool so all connections share the same DB
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(TEST_ENGINE, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSession = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables and seed data before each test, drop after."""
    Base.metadata.create_all(bind=TEST_ENGINE)

    db = TestSession()
    try:
        db.add_all(
            [
                Language(code="en", name="English"),
                Language(code="hu", name="Hungarian"),
            ]
        )
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
    finally:
        db.close()

    yield

    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def db_session():
    """Provide a test database session."""
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    """TestClient with the test database injected."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c
    fastapi_app.dependency_overrides.clear()
