from fastapi import APIRouter, HTTPException
from typing import List
import pandas as pd
import talib
import ccxt.async_support as ccxt
from pydantic import BaseModel

class MarketOverviewItem(BaseModel):
    symbol: str
    current_price: float
    ema_20: float | None = None # Use None for default if calculation fails
    sma_50: float | None = None # Use None for default if calculation fails
    support_levels: List[float]
    resistance_levels: List[float]

router = APIRouter()

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "DOGE/USDT", "SUI/USDT",
    "POPCAT/USDT", "HYPE/USDT"
]
# POPCAT and HYPE might not be on Binance, handle potential errors.

@router.get("/market-overview/", response_model=List[MarketOverviewItem])
async def get_market_overview():
    results = []
    # Initialize Binance exchange client from ccxt
    # Use a generic exchange ID first, then try to fetch from Binance
    exchange_id = 'binance'
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
        'enableRateLimit': True, # Required by some exchanges
    })

    try:
        for symbol in SYMBOLS:
            try:
                # Fetch Ticker for current price
                ticker = await exchange.fetch_ticker(symbol)
                current_price = ticker['last'] if ticker and 'last' in ticker and ticker['last'] else 0.0

                # Fetch OHLCV data for H1 timeframe (e.g., last 100 periods for calculations)
                # Limit to 100 as more might not be needed for these indicators and S/R
                ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
                if not ohlcv:
                    # Add entry with minimal data if OHLCV fails
                    results.append(MarketOverviewItem(
                        symbol=symbol,
                        current_price=current_price,
                        ema_20=None,
                        sma_50=None,
                        support_levels=[],
                        resistance_levels=[]
                    ))
                    continue

                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                # Ensure we have enough data for calculations
                if len(df) < 50: # Minimum needed for SMA50, EMA20 needs less but use 50 as a general threshold
                    results.append(MarketOverviewItem(
                        symbol=symbol,
                        current_price=current_price,
                        ema_20=None,
                        sma_50=None,
                        support_levels=sorted(df['low'].nsmallest(5).tolist()),
                        resistance_levels=sorted(df['high'].nlargest(5).tolist())
                    ))
                    continue

                # Calculate EMA(20) and SMA(50)
                df['ema_20'] = talib.EMA(df['close'], timeperiod=20)
                df['sma_50'] = talib.SMA(df['close'], timeperiod=50)

                latest_ema_20 = df['ema_20'].iloc[-1]
                latest_sma_50 = df['sma_50'].iloc[-1]

                # Identify 5 support and 5 resistance levels
                # Using n-smallest lows for support and n-largest highs for resistance from the fetched data
                support_levels = sorted(df['low'].nsmallest(5).tolist())
                resistance_levels = sorted(df['high'].nlargest(5).tolist())

                results.append(MarketOverviewItem(
                    symbol=symbol,
                    current_price=current_price,
                    ema_20=latest_ema_20 if pd.notna(latest_ema_20) else None,
                    sma_50=latest_sma_50 if pd.notna(latest_sma_50) else None,
                    support_levels=support_levels,
                    resistance_levels=resistance_levels
                ))

            except ccxt.NetworkError as e:
                # Handle network errors (e.g., connection issues)
                # Log error or add placeholder data
                print(f"Network error for {symbol}: {e}") # Basic logging
                results.append(MarketOverviewItem(symbol=symbol, current_price=0.0, ema_20=None, sma_50=None, support_levels=[], resistance_levels=[]))
            except ccxt.ExchangeError as e:
                # Handle exchange errors (e.g., symbol not found, API rate limits)
                print(f"Exchange error for {symbol}: {e}") # Basic logging
                results.append(MarketOverviewItem(symbol=symbol, current_price=0.0, ema_20=None, sma_50=None, support_levels=[], resistance_levels=[]))
            except Exception as e:
                # Catch any other unexpected errors during processing for a symbol
                print(f"An unexpected error occurred for {symbol}: {e}")
                results.append(MarketOverviewItem(symbol=symbol, current_price=0.0, ema_20=None, sma_50=None, support_levels=[], resistance_levels=[]))

    finally:
        # Always ensure the exchange client is closed
        if exchange:
            await exchange.close()

    if not results:
            raise HTTPException(status_code=500, detail="Could not fetch any market data.")
    return results
