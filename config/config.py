import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@host:port/dbname"

    # Generic Exchange API Keys (optional)
    EXCHANGE_API_KEY: str | None = None
    EXCHANGE_API_SECRET: str | None = None

    # These allow fetching from environment variables like BITGET_API_KEY etc.
    BITGET_API_KEY: str | None = None
    BITGET_API_SECRET: str | None = None
    BITGET_PASSWORD: str | None = None # Passphrase, if required by Bitget

    MEXC_API_KEY: str | None = None
    MEXC_API_SECRET: str | None = None

    BITUNIX_API_KEY: str | None = None
    BITUNIX_API_SECRET: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

@lru_cache()
def get_settings():
    return Settings()

# For direct access if needed, though Depends(get_settings) is preferred in FastAPI
settings = get_settings()

DATABASE_URL = settings.DATABASE_URL
