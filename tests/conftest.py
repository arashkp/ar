import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.database.base import Base # Assuming your SQLAlchemy Base is here
from src.main import app # Your FastAPI app
from src.database.session import get_db # The dependency to override
import os

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

@pytest.fixture(scope="session", autouse=True)
def setup_test_db_session():
    """
    Fixture to create all tables in the test database once per test session for file-based DB.
    For in-memory, table creation is often handled per session or test.
    """
    if SQLALCHEMY_DATABASE_URL != "sqlite:///:memory:":
        Base.metadata.create_all(bind=engine) # Create tables for file-based test DB
    yield
    if SQLALCHEMY_DATABASE_URL != "sqlite:///:memory:":
        # Optional: Clean up the test database file after tests run
        db_file_path = SQLALCHEMY_DATABASE_URL.split("sqlite:///./")[1]
        # if os.path.exists(db_file_path):
        #     os.remove(db_file_path) # Commented out to inspect DB after tests
        pass


@pytest.fixture(scope="function")
def db_session(setup_test_db_session) -> Session:
    """
    Provides a transactional database session for each test function.
    - For file-based DB: creates tables once per session, then uses transactions per test.
    - For in-memory DB: creates tables per test essentially (via override_get_db or here).
    """
    connection = engine.connect()
    transaction = connection.begin()
    # Bind the session to the connection for the transaction
    db = TestingSessionLocal(bind=connection)

    # If you need to ensure tables are created for each test (e.g. if tests modify schema or are destructive)
    # Base.metadata.create_all(bind=connection) # Creates tables within the transaction

    yield db

    db.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="module") # Changed to module for potentially faster test runs if client setup is heavy
def test_client() -> TestClient:
    """
    Provides a TestClient for making API requests in tests.
    This client uses the app with the overridden get_db dependency.
    """
    from fastapi.testclient import TestClient
    # Ensures the app's overridden dependencies are in place before client is created.
    # Table creation for the test DB should be handled by session-scoped or function-scoped fixtures.
    client = TestClient(app)
    return client
