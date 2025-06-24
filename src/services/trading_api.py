import ccxt.async_support as ccxt
from fastapi import HTTPException
from src.utils.exchange_helpers import (
    initialize_exchange, 
    validate_exchange_capability, 
    validate_symbol,
    safe_exchange_operation
)
from src.utils.error_handlers import handle_ccxt_exception, handle_generic_exception

async def fetch_ohlcv(exchange_id: str, symbol: str, timeframe: str = '1h', limit: int = 100, api_key: str = None, api_secret: str = None):
    """Fetches OHLCV data from the specified exchange."""
    # Initialize exchange using helper
    exchange = await initialize_exchange(exchange_id, api_key, api_secret)
    
    # Use safe exchange operation with automatic cleanup
    async with safe_exchange_operation(exchange, "OHLCV fetch", exchange_id):
        # Validate exchange capabilities
        await validate_exchange_capability(exchange, "fetchOHLCV", exchange_id)
        
        # Validate symbol availability
        await validate_symbol(exchange, symbol, exchange_id)
        
        # Fetch OHLCV data
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return ohlcv

async def fetch_balance(exchange_id: str, api_key: str, api_secret: str):
    """Fetches account balance from the specified exchange. Requires API key and secret."""
    if not api_key or not api_secret:
        raise HTTPException(status_code=400, detail="API key and secret are required to fetch balance.")

    # Initialize exchange using helper
    exchange = await initialize_exchange(exchange_id, api_key, api_secret)
    
    # Use safe exchange operation with automatic cleanup
    async with safe_exchange_operation(exchange, "balance fetch", exchange_id):
        # Validate exchange capabilities
        await validate_exchange_capability(exchange, "fetchBalance", exchange_id)
        
        # Fetch balance
        balance = await exchange.fetch_balance()
        return balance
