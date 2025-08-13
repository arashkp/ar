import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient # Moved import to top
from src.database.base import Base # Assuming your SQLAlchemy Base is here
from src.main import app # Your FastAPI app
from src.database.session import get_db
from src.utils.auth import verify_api_key
from config.config import get_settings, Settings
import os
from dotenv import load_dotenv

load_dotenv()

# Use an in-memory SQLite database for testing for speed, or a file if preferred.
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db" # Use a separate test DB file
# SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:" # Alternative: in-memory

# Ensure a clean DB environment for the test session
if SQLALCHEMY_DATABASE_URL.startswith("sqlite:///") and SQLALCHEMY_DATABASE_URL != "sqlite:///:memory:":
    db_file_path = SQLALCHEMY_DATABASE_URL.split("sqlite:///./")[1]
    if os.path.exists(db_file_path):
        os.remove(db_file_path)

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """
    Dependency override for FastAPI to use the test database session.
    """
    db = TestingSessionLocal()
    try:
        Base.metadata.create_all(bind=engine) # Ensure tables are created for this session if in-memory
        yield db
    finally:
        db.close()
        if SQLALCHEMY_DATABASE_URL == "sqlite:///:memory:":
             Base.metadata.drop_all(bind=engine) # Clean up if in-memory for each session

# Apply the override to the FastAPI app.
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Provides a transactional database session for each test function.
    This fixture ensures that each test has a clean database state.
    """
    # Create tables for each test if using in-memory SQLite, otherwise create once
    if SQLALCHEMY_DATABASE_URL == "sqlite:///:memory:":
        Base.metadata.create_all(bind=engine)

    connection = engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)

    yield db

    db.close()
    transaction.rollback()
    connection.close()

    if SQLALCHEMY_DATABASE_URL == "sqlite:///:memory:":
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    Provides a TestClient that is configured for isolated test runs.
    It handles database, authentication, and settings overrides.
    Yields both the client and the test settings object.
    """
    test_settings = Settings(
        DATABASE_URL=SQLALCHEMY_DATABASE_URL,
        EXCHANGE_API_KEY="test_global_key",
        EXCHANGE_API_SECRET="test_global_secret",
        BINANCE_API_KEY="binance_test_key_from_settings",
        BINANCE_API_SECRET="binance_test_secret_from_settings",
    )

    def override_get_db_for_client():
        yield db_session

    async def override_verify_api_key_for_client():
        return True

    def override_get_settings_for_client():
        return test_settings

    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db_for_client
    app.dependency_overrides[verify_api_key] = override_verify_api_key_for_client
    app.dependency_overrides[get_settings] = override_get_settings_for_client

    with TestClient(app) as c:
        yield c, test_settings

    app.dependency_overrides = original_overrides
