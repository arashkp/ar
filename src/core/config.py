from pydantic_settings import BaseSettings
import os
from typing import Optional

class Settings(BaseSettings):
    # Database connection string.
    # Examples:
    #   SQLite: "sqlite:///./test.db"
    #   PostgreSQL: "postgresql://user:password@host:port/dbname"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ar_trade.db") # Defaulted to ar_trade.db

    # Exchange API keys are generally not defined here directly in the Settings model.
    # Instead, they are loaded on-demand by services (like order_manager.py)
    # using os.getenv("EXCHANGENAME_API_KEY") and os.getenv("EXCHANGENAME_API_SECRET").
    # This approach avoids needing to list every possible exchange's keys here.
    # See .env.example for the naming convention (e.g., BINANCE_API_KEY).
    #
    # Example if you wanted to strongly type specific keys (less flexible for many exchanges):
    # BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    # BINANCE_API_SECRET: Optional[str] = os.getenv("BINANCE_API_SECRET")

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
