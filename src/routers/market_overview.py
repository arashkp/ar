from fastapi import APIRouter, HTTPException
import logging
from typing import List
import pandas as pd
import pandas_ta as ta
import ccxt.async_support as ccxt
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MarketOverviewItem(BaseModel):
    symbol: str
    current_price: float
    ema_20: float | None = None
    sma_50: float | None = None
    support_levels: List[float]
    resistance_levels: List[float]


SYMBOL_CONFIG = [
    {"symbol": "BTC/USDT", "exchange_id": "binance", "name": "Bitcoin"},
    {"symbol": "ETH/USDT", "exchange_id": "binance", "name": "Ethereum"},
    {"symbol": "DOGE/USDT", "exchange_id": "binance", "name": "Dogecoin"},
    {"symbol": "SUI/USDT", "exchange_id": "binance", "name": "Sui"},
    {"symbol": "POPCAT/USDT", "exchange_id": "mexc", "name": "Popcat"},
    {"symbol": "HYPE/USDT", "exchange_id": "mexc", "name": "HypeCoin"},
]

router = APIRouter()


@router.get("/market-overview/", response_model=List[MarketOverviewItem])
async def get_market_overview():
    results = []
    active_exchanges = {}  # Dictionary to store active exchange instances

    try:
        for config_item in SYMBOL_CONFIG:
            symbol = config_item["symbol"]
            exchange_id = config_item["exchange_id"]

            try:
                # Get or create the exchange instance
                if exchange_id in active_exchanges:
                    exchange = active_exchanges[exchange_id]
                else:
                    try:
                        exchange_class = getattr(ccxt, exchange_id)
                        exchange = exchange_class({'enableRateLimit': True})
                        active_exchanges[exchange_id] = exchange
                        logger.info(f"Initialized {exchange_id} for {symbol}")
                    except AttributeError:
                        logger.critical(
                            f"Exchange ID '{exchange_id}' for symbol {symbol} is not a valid ccxt exchange. Skipping.")
                        results.append(MarketOverviewItem(
                            symbol=symbol, current_price=0.0, ema_20=None, sma_50=None,
                            support_levels=[], resistance_levels=[]
                        ))
                        continue
                    except Exception as e:
                        logger.critical(
                            f"Error initializing exchange {exchange_id} for symbol {symbol}: {e}. Skipping.")
                        results.append(MarketOverviewItem(
                            symbol=symbol, current_price=0.0, ema_20=None, sma_50=None,
                            support_levels=[], resistance_levels=[]
                        ))
                        continue

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

                if len(df) < 50:  # Minimum needed for SMA50
                    logger.warning(
                        f"Not enough data points for {symbol} to calculate SMA50 (need 50, got {len(df)}). Skipping TA calculations.")
                    results.append(MarketOverviewItem(
                        symbol=symbol, current_price=current_price, ema_20=None, sma_50=None,
                        support_levels=sorted(df['low'].nsmallest(5).tolist()) if not df.empty else [],
                        resistance_levels=sorted(df['high'].nlargest(5).tolist()) if not df.empty else []
                    ))
                    continue

                # Calculate EMA(20) and SMA(50)
                df['ema_20'] = df.ta.ema(length=20)
                df['sma_50'] = df.ta.sma(length=50)

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
                logger.error(f"Network error for {symbol} on {exchange_id}: {e}. Default data returned.")
                results.append(
                    MarketOverviewItem(symbol=symbol, current_price=0.0, ema_20=None, sma_50=None, support_levels=[],
                                       resistance_levels=[]))
            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error for {symbol} on {exchange_id}: {e}. Default data returned.")
                results.append(
                    MarketOverviewItem(symbol=symbol, current_price=0.0, ema_20=None, sma_50=None, support_levels=[],
                                       resistance_levels=[]))
            except Exception as e:
                logger.error(f"An unexpected error occurred for {symbol} on {exchange_id}: {e}. Default data returned.")
                results.append(
                    MarketOverviewItem(symbol=symbol, current_price=0.0, ema_20=None, sma_50=None, support_levels=[],
                                       resistance_levels=[]))

    finally:
        for ex_id, ex_instance in active_exchanges.items():
            if ex_instance:
                try:
                    await ex_instance.close()
                    print(f"Closed {ex_id} exchange.")
                except Exception as e:
                    print(f"Error closing {ex_id} exchange: {e}")

    if not results and SYMBOL_CONFIG:  # Only raise if SYMBOL_CONFIG was not empty and still no results
        logger.error("Could not fetch any market data for the configured symbols.")
        raise HTTPException(status_code=500, detail="Could not fetch any market data for the configured symbols.")
    return results
