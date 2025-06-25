from pydantic_settings import BaseSettings
import os
from typing import Optional


class Settings(BaseSettings):
    # Database connection string.
    # Examples:
    #   SQLite: "sqlite:///./test.db"
    #   PostgreSQL: "postgresql://user:password@host:port/dbname"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ar_trade.db")  # Defaulted to ar_trade.db

    # Exchange API keys are generally not defined here directly in the Settings model.
    # Instead, they are loaded on-demand by services (like order_manager.py)
    # using os.getenv("EXCHANGENAME_API_KEY") and os.getenv("EXCHANGENAME_API_SECRET").
    # This approach avoids needing to list every possible exchange's keys here.
    # See .env.example for the naming convention (e.g., BINANCE_API_KEY).
    #
    # Example if you wanted to strongly type specific keys (less flexible for many exchanges):
    # BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    # BINANCE_API_SECRET: Optional[str] = os.getenv("BINANCE_API_SECRET")

    # Caching Configuration
    CACHE_DIRECTORY: str = "market_cache/"  # Path relative to the project root
    MAX_CANDLES_TO_CACHE: int = 3000       # Max number of candles to store and use for analysis
    EXTREMA_ORDER: int = 10                # Order for extremeness (window size for finding local S/R)
    ATR_MULTIPLIER_FOR_GAP: float = 1.2    # ATR multiplier for gap calculation

    # Rational Gap Configuration - Removed BASE_BTC_USD_GAP and DEFAULT_MIN_PRICE_GAP_USD

    model_config = {"extra": "ignore"}


settings = Settings()
