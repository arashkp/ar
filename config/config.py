import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@host:port/dbname"

    # Generic Exchange API Keys (optional)
    EXCHANGE_API_KEY: str | None = None
    EXCHANGE_API_SECRET: str | None = None

    # Specific Exchange API Keys (examples, add more as needed)
    # These allow fetching from environment variables like BINANCE_API_KEY, COINBASEPRO_API_KEY etc.
    BINANCE_API_KEY: str | None = None
    BINANCE_API_SECRET: str | None = None

    COINBASEPRO_API_KEY: str | None = None
    COINBASEPRO_API_SECRET: str | None = None
    COINBASEPRO_PASSWORD: str | None = None # Some exchanges require a passphrase

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

@lru_cache()
def get_settings():
    return Settings()

# For direct access if needed, though Depends(get_settings) is preferred in FastAPI
settings = get_settings()
