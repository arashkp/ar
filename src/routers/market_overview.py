from fastapi import APIRouter, HTTPException
from typing import List
import pandas as pd
import talib
import ccxt.async_support as ccxt
from pydantic import BaseModel

class MarketOverviewItem(BaseModel):
    symbol: str
    current_price: float
    ema_20: float | None = None
    sma_50: float | None = None
    support_levels: List[float]
    resistance_levels: List[float]

router = APIRouter()

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "DOGE/USDT", "SUI/USDT",
    "POPCAT/USDT", "HYPE/USDT"
]

@router.get("/market-overview/", response_model=List[MarketOverviewItem])
async def get_market_overview():
    results = []

    # Initialize exchange clients
    # It's good practice to use the full class name for clarity if not aliasing ccxt
    binance_exchange = ccxt.binance({
        'enableRateLimit': True,
    })
    bitget_exchange = ccxt.bitget({
        'enableRateLimit': True,
    })

    try:
        for symbol in SYMBOLS:
            exchange = None # Initialize exchange to None for clarity
            try:
                # Select the appropriate exchange instance
                if symbol in ["POPCAT/USDT", "HYPE/USDT"]:
                    exchange = bitget_exchange
                else:
                    exchange = binance_exchange

                # Fetch Ticker for current price
                ticker = await exchange.fetch_ticker(symbol)
                current_price = ticker['last'] if ticker and 'last' in ticker and ticker['last'] else 0.0

                # Fetch OHLCV data
                ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
                if not ohlcv:
                    results.append(MarketOverviewItem(
                        symbol=symbol, current_price=current_price, ema_20=None, sma_50=None,
                        support_levels=[], resistance_levels=[]
                    ))
                    continue

                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                if len(df) < 50:
                    results.append(MarketOverviewItem(
                        symbol=symbol, current_price=current_price, ema_20=None, sma_50=None,
                        support_levels=sorted(df['low'].nsmallest(5).tolist()),
                        resistance_levels=sorted(df['high'].nlargest(5).tolist())
                    ))
                    continue

                df['ema_20'] = talib.EMA(df['close'], timeperiod=20)
                df['sma_50'] = talib.SMA(df['close'], timeperiod=50)

                latest_ema_20 = df['ema_20'].iloc[-1]
                latest_sma_50 = df['sma_50'].iloc[-1]

                support_levels = sorted(df['low'].nsmallest(5).tolist())
                resistance_levels = sorted(df['high'].nlargest(5).tolist())

                results.append(MarketOverviewItem(
                    symbol=symbol, current_price=current_price,
                    ema_20=latest_ema_20 if pd.notna(latest_ema_20) else None,
                    sma_50=latest_sma_50 if pd.notna(latest_sma_50) else None,
                    support_levels=support_levels, resistance_levels=resistance_levels
                ))

            except ccxt.NetworkError as e:
                print(f"Network error for {symbol} on {exchange.id if exchange else 'N/A'}: {e}")
                results.append(MarketOverviewItem(symbol=symbol, current_price=0.0, ema_20=None, sma_50=None, support_levels=[], resistance_levels=[]))
            except ccxt.ExchangeError as e:
                print(f"Exchange error for {symbol} on {exchange.id if exchange else 'N/A'}: {e}")
                results.append(MarketOverviewItem(symbol=symbol, current_price=0.0, ema_20=None, sma_50=None, support_levels=[], resistance_levels=[]))
            except Exception as e:
                print(f"An unexpected error occurred for {symbol}: {e}")
                results.append(MarketOverviewItem(symbol=symbol, current_price=0.0, ema_20=None, sma_50=None, support_levels=[], resistance_levels=[]))

    finally:
        # Always ensure both exchange clients are closed
        if binance_exchange:
            await binance_exchange.close()
        if bitget_exchange:
            await bitget_exchange.close()

    if not results: # This condition might be hard to hit if SYMBOLS is not empty, as errors append items.
         raise HTTPException(status_code=500, detail="Could not fetch any market data.")
    return results
