from fastapi import APIRouter, HTTPException
import logging
from typing import List
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import pandas_ta as ta
import ccxt.async_support as ccxt
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LevelItem(BaseModel):
    level: float
    description: str

class MarketOverviewItem(BaseModel):
    symbol: str
    current_price: float
    ema_21: float | None = None
    ema_89: float | None = None
    sma_30: float | None = None
    sma_150: float | None = None
    sma_300: float | None = None
    support_levels: List[LevelItem]
    resistance_levels: List[LevelItem]


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
                            symbol=symbol, current_price=0.0, ema_21=None, ema_89=None,
                            sma_30=None, sma_150=None, sma_300=None,
                            support_levels=[], resistance_levels=[]
                        ))
                        continue
                    except Exception as e:
                        logger.critical(
                            f"Error initializing exchange {exchange_id} for symbol {symbol}: {e}. Skipping.")
                        results.append(MarketOverviewItem(
                            symbol=symbol, current_price=0.0, ema_21=None, ema_89=None,
                            sma_30=None, sma_150=None, sma_300=None,
                            support_levels=[], resistance_levels=[]
                        ))
                        continue

                # Fetch Ticker for current price
                ticker = await exchange.fetch_ticker(symbol)
                current_price = ticker['last'] if ticker and 'last' in ticker and ticker['last'] else 0.0

                # Fetch OHLCV data
                ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='1h', limit=350) # Increased limit for SMA300
                if not ohlcv:
                    results.append(MarketOverviewItem(
                        symbol=symbol, current_price=current_price, ema_21=None, ema_89=None,
                        sma_30=None, sma_150=None, sma_300=None,
                        support_levels=[], resistance_levels=[]
                    ))
                    continue

                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                # Initialize support and resistance items
                support_level_items = []
                resistance_level_items = []

                # Define order for argrelextrema (like window size / 2)
                extrema_order = 5
                min_data_for_extrema = extrema_order * 2

                if not df.empty:
                    if len(df) >= min_data_for_extrema:
                        # Find local minima for support levels
                        low_extrema_indices = argrelextrema(df['low'].values, np.less, order=extrema_order)[0]
                        local_lows = df['low'].iloc[low_extrema_indices].unique()

                        # Filter, sort, and select support levels
                        recent_supports = sorted([low for low in local_lows if low < current_price], reverse=True)
                        for level in recent_supports[:5]:
                            support_level_items.append(LevelItem(level=level, description="Recent Low"))

                        # Fill with historical lows if needed
                        if len(support_level_items) < 5:
                            num_needed = 5 - len(support_level_items)
                            existing_levels = {item.level for item in support_level_items}
                            historical_lows = df['low'][~df['low'].isin(existing_levels)].nsmallest(num_needed).unique()
                            for level in historical_lows:
                                if len(support_level_items) < 5:
                                    support_level_items.append(LevelItem(level=level, description="Historical Low"))
                                else:
                                    break
                            support_level_items.sort(key=lambda x: x.level, reverse=True) # Sort all supports

                        # Find local maxima for resistance levels
                        high_extrema_indices = argrelextrema(df['high'].values, np.greater, order=extrema_order)[0]
                        local_highs = df['high'].iloc[high_extrema_indices].unique()

                        # Filter, sort, and select resistance levels
                        recent_resistances = sorted([high for high in local_highs if high > current_price])
                        for level in recent_resistances[:5]:
                            resistance_level_items.append(LevelItem(level=level, description="Recent High"))

                        # Fill with historical highs if needed
                        if len(resistance_level_items) < 5:
                            num_needed = 5 - len(resistance_level_items)
                            existing_levels = {item.level for item in resistance_level_items}
                            historical_highs = df['high'][~df['high'].isin(existing_levels)].nlargest(num_needed).unique()
                            for level in historical_highs:
                                if len(resistance_level_items) < 5:
                                    resistance_level_items.append(LevelItem(level=level, description="Historical High"))
                                else:
                                    break
                            resistance_level_items.sort(key=lambda x: x.level) # Sort all resistances

                    else: # Not enough data for reliable extrema detection, use n-smallest/n-largest
                        logger.info(f"Using n-smallest/n-largest for S/R for {symbol} due to insufficient data for extrema (got {len(df)}, need {min_data_for_extrema})")
                        raw_supports = sorted(df['low'].nsmallest(5).tolist())
                        raw_resistances = sorted(df['high'].nlargest(5).tolist())
                        support_level_items = [LevelItem(level=sl, description="Historical Low") for sl in raw_supports]
                        resistance_level_items = [LevelItem(level=rl, description="Historical High") for rl in raw_resistances]

                if len(df) < 300: # Minimum needed for all TAs
                    logger.warning(f"Not enough data points for {symbol} to calculate all TAs (need 300, got {len(df)}). Skipping TA calculations.")
                    # Support and resistance already calculated above if possible
                    results.append(MarketOverviewItem(
                        symbol=symbol, current_price=current_price, ema_21=None, ema_89=None,
                        sma_30=None, sma_150=None, sma_300=None,
                        support_levels=support_level_items, # Use already computed S/R
                        resistance_levels=resistance_level_items # Use already computed S/R
                    ))
                    continue

                # Calculate EMAs and SMAs
                df['ema_21'] = df.ta.ema(length=21)
                df['ema_89'] = df.ta.ema(length=89)
                df['sma_30'] = df.ta.sma(length=30)
                df['sma_150'] = df.ta.sma(length=150)
                df['sma_300'] = df.ta.sma(length=300)

                latest_ema_21 = df['ema_21'].iloc[-1]
                latest_ema_89 = df['ema_89'].iloc[-1]
                latest_sma_30 = df['sma_30'].iloc[-1]
                latest_sma_150 = df['sma_150'].iloc[-1]
                latest_sma_300 = df['sma_300'].iloc[-1]

                # Support and resistance levels are already calculated above using the new logic
                # So, we just pass support_level_items and resistance_level_items

                results.append(MarketOverviewItem(
                    symbol=symbol, current_price=current_price,
                    ema_21=latest_ema_21 if pd.notna(latest_ema_21) else None,
                    ema_89=latest_ema_89 if pd.notna(latest_ema_89) else None,
                    sma_30=latest_sma_30 if pd.notna(latest_sma_30) else None,
                    sma_150=latest_sma_150 if pd.notna(latest_sma_150) else None,
                    sma_300=latest_sma_300 if pd.notna(latest_sma_300) else None,
                    support_levels=support_level_items, # Use already computed S/R
                    resistance_levels=resistance_level_items # Use already computed S/R
                ))

            except ccxt.NetworkError as e:
                logger.error(f"Network error for {symbol} on {exchange_id}: {e}. Default data returned.")
                results.append(MarketOverviewItem(symbol=symbol, current_price=0.0, ema_21=None, ema_89=None, sma_30=None, sma_150=None, sma_300=None, support_levels=[], resistance_levels=[]))
            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error for {symbol} on {exchange_id}: {e}. Default data returned.")
                results.append(MarketOverviewItem(symbol=symbol, current_price=0.0, ema_21=None, ema_89=None, sma_30=None, sma_150=None, sma_300=None, support_levels=[], resistance_levels=[]))
            except Exception as e:
                logger.error(f"An unexpected error occurred for {symbol} on {exchange_id}: {e}. Default data returned.")
                results.append(MarketOverviewItem(symbol=symbol, current_price=0.0, ema_21=None, ema_89=None, sma_30=None, sma_150=None, sma_300=None, support_levels=[], resistance_levels=[]))

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
