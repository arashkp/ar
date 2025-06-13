from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from src.services.trading_api import fetch_ohlcv as fetch_ohlcv_service, fetch_balance as fetch_balance_service
from config.config import Settings, get_settings # Assuming you will have settings for API keys

router = APIRouter()

@router.get("/api/v1/exchange/ohlcv")
async def get_ohlcv(
    exchange_id: str = Query(..., description="Exchange ID (e.g., 'binance', 'coinbasepro')"),
    symbol: str = Query(..., description="Trading symbol (e.g., 'BTC/USDT')"),
    timeframe: str = Query("1h", description="Timeframe for OHLCV data (e.g., '1m', '5m', '1h', '1d')"),
    limit: int = Query(100, description="Number of data points to retrieve"),
    # API keys are optional for public data like OHLCV on many exchanges
    api_key: Optional[str] = Query(None, description="Optional API Key for the exchange"),
    api_secret: Optional[str] = Query(None, description="Optional API Secret for the exchange"),
    settings: Settings = Depends(get_settings) # Allow global settings if keys are there
):
    """
    Fetches OHLCV (Open, High, Low, Close, Volume) data for a specific symbol
    from a given exchange.
    """
    # Use provided keys first, then fallback to settings if available and needed by an exchange
    # For many public OHLCV endpoints, keys are not strictly required by ccxt if the exchange allows it.
    # The trading_api.py handles the logic of when to use keys.
    effective_api_key = api_key or getattr(settings, f"{exchange_id.upper()}_API_KEY", None)
    effective_api_secret = api_secret or getattr(settings, f"{exchange_id.upper()}_API_SECRET", None)

    try:
        ohlcv_data = await fetch_ohlcv_service(
            exchange_id=exchange_id,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            api_key=effective_api_key,
            api_secret=effective_api_secret
        )
        return ohlcv_data
    except HTTPException as e:
        raise e # Re-raise HTTPException from service layer
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/api/v1/exchange/balance")
async def get_balance(
    exchange_id: str = Query(..., description="Exchange ID (e.g., 'binance')"),
    # API keys can be passed as query params or ideally loaded from config/env
    api_key: Optional[str] = Query(None, description="API Key for the exchange"),
    api_secret: Optional[str] = Query(None, description="API Secret for the exchange"),
    settings: Settings = Depends(get_settings)
):
    """
    Fetches account balance from a specific exchange.
    Requires API key and secret, which can be provided as query parameters
    or configured via environment variables (e.g., BINANCE_API_KEY).
    """
    # Prioritize query parameters, then fall back to environment/settings
    final_api_key = api_key or getattr(settings, f"{exchange_id.upper()}_API_KEY", None)
    final_api_secret = api_secret or getattr(settings, f"{exchange_id.upper()}_API_SECRET", None)

    if not final_api_key or not final_api_secret:
        raise HTTPException(
            status_code=400,
            detail=f"API key and secret are required for {exchange_id}. "
                   f"Provide them as query parameters or set them as environment variables "
                   f" (e.g., {exchange_id.upper()}_API_KEY, {exchange_id.upper()}_API_SECRET)."
        )

    try:
        balance_data = await fetch_balance_service(
            exchange_id=exchange_id,
            api_key=final_api_key,
            api_secret=final_api_secret
        )
        return balance_data
    except HTTPException as e:
        raise e # Re-raise HTTPException from service layer
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
