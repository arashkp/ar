from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from src.services.trading_api import fetch_ohlcv as fetch_ohlcv_service, fetch_balance as fetch_balance_service
from src.core.config import Settings, get_settings
from sqlalchemy.orm import Session
from src.utils.error_handlers import exchange_error_handler, api_error_handler
from src.utils.api_key_manager import get_api_keys_for_public_data, get_api_keys_for_private_data

router = APIRouter()

@router.get("/api/v1/exchange/ohlcv")
@exchange_error_handler("exchange_id", "OHLCV data fetching")
async def get_ohlcv(
    exchange_id: str,
    symbol: str,
    timeframe: str = "4h",
    limit: int = 100,
    # API keys are optional for public data like OHLCV on many exchanges
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    settings: Settings = Depends(get_settings) # Allow global settings if keys are there
):
    """
    Fetches OHLCV (Open, High, Low, Close, Volume) data for a specific symbol
    from a given exchange.
    """
    # Use helper for API key management (optional for public data)
    effective_api_key, effective_api_secret = get_api_keys_for_public_data(
        exchange_id=exchange_id,
        query_api_key=api_key,
        query_api_secret=api_secret,
        settings=settings
    )

    ohlcv_data = await fetch_ohlcv_service(
        exchange_id=exchange_id,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        api_key=effective_api_key,
        api_secret=effective_api_secret
    )
    return ohlcv_data

@router.get("/api/v1/exchange/balance")
@exchange_error_handler("exchange_id", "balance fetching")
async def get_balance(
    exchange_id: str,
    # API keys can be passed as query params or ideally loaded from config/env
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    settings: Settings = Depends(get_settings)
):
    """
    Fetches account balance from a specific exchange.
    Requires API key and secret, which can be provided as query parameters
    or configured via environment variables (e.g., BINANCE_API_KEY).
    """
    # Use helper for API key management (required for private data)
    final_api_key, final_api_secret = get_api_keys_for_private_data(
        exchange_id=exchange_id,
        query_api_key=api_key,
        query_api_secret=api_secret,
        settings=settings,
        operation="balance fetching"
    )

    balance_data = await fetch_balance_service(
        exchange_id=exchange_id,
        api_key=final_api_key,
        api_secret=final_api_secret
    )
    return balance_data
