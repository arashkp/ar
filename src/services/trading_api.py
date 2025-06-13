import ccxt.async_support as ccxt
from fastapi import HTTPException

async def initialize_exchange(exchange_id: str, api_key: str = None, api_secret: str = None):
    """Initializes and returns an exchange instance using ccxt."""
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange_params = {}
        if api_key and api_secret:
            exchange_params['apiKey'] = api_key
            exchange_params['secret'] = api_secret

        # Add other necessary parameters like 'enableRateLimit': True
        # Some exchanges might require specific parameters, this should be made more robust
        # or allow passing them through.
        exchange_params['enableRateLimit'] = True

        exchange = exchange_class(exchange_params)
        # Forcing a non-blocking test call if possible, or just return the instance
        # await exchange.load_markets() # Example: Load markets to test credentials (can be slow)
        return exchange
    except AttributeError:
        raise HTTPException(status_code=400, detail=f"Exchange {exchange_id} not found.")
    except ccxt.AuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed for {exchange_id}: {str(e)}")
    except ccxt.NetworkError as e:
        raise HTTPException(status_code=502, detail=f"Network error connecting to {exchange_id}: {str(e)}")
    except ccxt.ExchangeError as e:
        raise HTTPException(status_code=500, detail=f"Error with {exchange_id}: {str(e)}")
    except Exception as e:
        # Generic catch-all for other ccxt or unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred with {exchange_id}: {str(e)}")

async def fetch_ohlcv(exchange_id: str, symbol: str, timeframe: str = '1h', limit: int = 100, api_key: str = None, api_secret: str = None):
    """Fetches OHLCV data from the specified exchange."""
    exchange = await initialize_exchange(exchange_id, api_key, api_secret)
    try:
        if not exchange.has['fetchOHLCV']:
            await exchange.close()
            raise HTTPException(status_code=501, detail=f"Exchange {exchange_id} does not support fetching OHLCV data.")

        # Check if symbol is available
        markets = await exchange.load_markets()
        if symbol not in markets:
            await exchange.close()
            raise HTTPException(status_code=400, detail=f"Symbol {symbol} not available on {exchange_id}.")

        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return ohlcv
    except ccxt.RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded for {exchange_id}: {str(e)}")
    except ccxt.BadSymbol as e: # Or ccxt.InvalidSymbol
        raise HTTPException(status_code=400, detail=f"Invalid symbol {symbol} for {exchange_id}: {str(e)}")
    except ccxt.NetworkError as e:
        raise HTTPException(status_code=502, detail=f"Network error fetching OHLCV from {exchange_id}: {str(e)}")
    except ccxt.ExchangeError as e: # Catch other exchange-specific errors
        raise HTTPException(status_code=500, detail=f"Error fetching OHLCV from {exchange_id}: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while fetching OHLCV from {exchange_id}: {str(e)}")
    finally:
        if exchange:
            await exchange.close()

async def fetch_balance(exchange_id: str, api_key: str, api_secret: str):
    """Fetches account balance from the specified exchange. Requires API key and secret."""
    if not api_key or not api_secret:
        raise HTTPException(status_code=400, detail="API key and secret are required to fetch balance.")

    exchange = await initialize_exchange(exchange_id, api_key, api_secret)
    try:
        if not exchange.has['fetchBalance']:
            await exchange.close()
            raise HTTPException(status_code=501, detail=f"Exchange {exchange_id} does not support fetching balance or requires specific permissions.")

        balance = await exchange.fetch_balance()
        return balance
    except ccxt.AuthenticationError as e: # Specific catch for auth issues during balance fetch
        raise HTTPException(status_code=401, detail=f"Authentication failed for {exchange_id} when fetching balance: {str(e)}")
    except ccxt.RateLimitExceeded as e:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded for {exchange_id}: {str(e)}")
    except ccxt.NetworkError as e:
        raise HTTPException(status_code=502, detail=f"Network error fetching balance from {exchange_id}: {str(e)}")
    except ccxt.ExchangeError as e: # Catch other exchange-specific errors
        raise HTTPException(status_code=500, detail=f"Error fetching balance from {exchange_id}: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while fetching balance from {exchange_id}: {str(e)}")
    finally:
        if exchange:
            await exchange.close()
