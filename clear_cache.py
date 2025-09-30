#!/usr/bin/env python3
"""
Simple script to clear all cached OHLCV data.
Run this when switching exchanges or when cache becomes stale.
"""

from src.services.cache_manager import clear_all_cache
from src.core.config import settings

if __name__ == "__main__":
    print("Clearing all cached OHLCV data...")
    clear_all_cache(settings.CACHE_DIRECTORY)
    print("Cache cleared successfully!")
    print("\nYou can now restart your backend to fetch fresh data from MEXC.")
