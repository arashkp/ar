import os

# Set a default DATABASE_URL for test sessions BEFORE any application modules are imported.
# This helps prevent the global engine in database.database.py from failing due to
# an invalid default URL (like one with a placeholder "port") during test collection.
# The actual tests for routers/endpoints will typically override get_db and use
# their own specific test database (e.g., in-memory SQLite for router tests).
os.environ["DATABASE_URL"] = "sqlite:///:memory:" # A valid default for parsing
print(f"tests/conftest.py: Set DATABASE_URL to {os.environ['DATABASE_URL']}")
