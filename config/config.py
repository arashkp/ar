import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@host:port/dbname")
# In a real application, consider using a settings management library like Pydantic.
