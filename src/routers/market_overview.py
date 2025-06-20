from fastapi import APIRouter, HTTPException
import logging
from typing import List
import decimal  # Added import
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import pandas_ta as ta
import ccxt.async_support as ccxt
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Helper functions for price precision
def get_price_precision(price: float) -> int:
    price_str = str(price)
    if '.' in price_str:
        return len(price_str.split('.')[1])
    return 0


def format_value(value: float | None, precision: int) -> float | None:
    if value is None:
        return None
    # Use decimal for accurate rounding
    return float(
        decimal.Decimal(str(value)).quantize(decimal.Decimal('1e-' + str(precision)), rounding=decimal.ROUND_HALF_UP))


class LevelItem(BaseModel):
    level: float
    strength: int  # Changed from description: str


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
                current_price_raw = ticker['last'] if ticker and 'last' in ticker and ticker['last'] else 0.0

                if current_price_raw == 0.0:
                    price_precision = 2  # Default precision
                else:
                    price_precision = get_price_precision(current_price_raw)
                current_price = format_value(current_price_raw, price_precision)

                # Fetch OHLCV data
                ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='1h', limit=350)  # Increased limit for SMA300
                if not ohlcv:
                    # Ensure current_price is formatted even if we continue early
                    formatted_current_price_on_error = format_value(current_price_raw,
                                                                    price_precision if current_price_raw != 0.0 else 2)
                    results.append(MarketOverviewItem(
                        symbol=symbol, current_price=formatted_current_price_on_error, ema_21=None, ema_89=None,
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
                        # current_price here is already formatted. For comparison with unformatted df values, use current_price_raw
                        recent_supports = sorted([low for low in local_lows if low < current_price_raw], reverse=True)
                        for s_level in recent_supports[:5]:
                            tolerance = s_level * 0.0005  # Use original level for tolerance calculation
                            touch_count = df['low'].apply(lambda x: abs(x - s_level) <= tolerance).sum()
                            formatted_level = format_value(s_level, price_precision)
                            if formatted_level is not None:
                                support_level_items.append(LevelItem(level=formatted_level, strength=touch_count))

                        # Fill with historical lows if needed
                        if len(support_level_items) < 5:
                            num_needed = 5 - len(support_level_items)
                            existing_levels = {item.level for item in
                                               support_level_items}  # These levels are already formatted
                            # To compare historical_lows (unformatted) with existing_levels (formatted), we format historical_lows before check.
                            # However, it's simpler to select from df['low'] that are not in the raw values used to create existing_levels.
                            # For simplicity, we'll re-filter from unique local_lows that are not yet added.
                            # This part of logic might need refinement if strict non-overlap with formatted levels is critical.
                            # The current approach uses original unformatted levels for touch calculation and formats right before append.

                            # Let's fetch historical lows again and ensure they are not already processed (based on original value)
                            processed_s_levels = {sl.level for sl in support_level_items}  # these are formatted

                            # Simpler: just get more from historical, format, and add if total < 5
                            # This might lead to slight overlaps if formatting causes collisions, but acceptable for now.

                            historical_low_candidates = df['low'][
                                ~df['low'].isin([item.level for item in support_level_items])].nsmallest(
                                num_needed + 5).unique()  # get a few more

                            for h_level in historical_low_candidates:
                                if len(support_level_items) >= 5:
                                    break
                                # Avoid adding a level that, after formatting, would be identical to an existing one
                                formatted_h_level = format_value(h_level, price_precision)
                                if formatted_h_level is not None and formatted_h_level not in {item.level for item in
                                                                                               support_level_items}:
                                    if h_level < current_price_raw:  # ensure it's still a support
                                        tolerance = h_level * 0.0005
                                        touch_count = df['low'].apply(lambda x: abs(x - h_level) <= tolerance).sum()
                                        support_level_items.append(
                                            LevelItem(level=formatted_h_level, strength=touch_count))
                            support_level_items.sort(key=lambda x: x.level,
                                                     reverse=True)  # Sort all supports, now formatted

                        # Find local maxima for resistance levels
                        high_extrema_indices = argrelextrema(df['high'].values, np.greater, order=extrema_order)[0]
                        local_highs = df['high'].iloc[high_extrema_indices].unique()

                        # Filter, sort, and select resistance levels
                        # current_price here is already formatted. For comparison with unformatted df values, use current_price_raw
                        recent_resistances = sorted([high for high in local_highs if high > current_price_raw])
                        for r_level in recent_resistances[:5]:
                            tolerance = r_level * 0.0005  # Use original level for tolerance calculation
                            touch_count = df['high'].apply(lambda x: abs(x - r_level) <= tolerance).sum()
                            formatted_level = format_value(r_level, price_precision)
                            if formatted_level is not None:
                                resistance_level_items.append(LevelItem(level=formatted_level, strength=touch_count))

                        # Fill with historical highs if needed
                        if len(resistance_level_items) < 5:
                            num_needed = 5 - len(resistance_level_items)
                            # Similar to supports, fetch more candidates and filter
                            historical_high_candidates = df['high'][
                                ~df['high'].isin([item.level for item in resistance_level_items])].nlargest(
                                num_needed + 5).unique()

                            for h_level in historical_high_candidates:
                                if len(resistance_level_items) >= 5:
                                    break
                                formatted_h_level = format_value(h_level, price_precision)
                                if formatted_h_level is not None and formatted_h_level not in {item.level for item in
                                                                                               resistance_level_items}:
                                    if h_level > current_price_raw:  # ensure it's still a resistance
                                        tolerance = h_level * 0.0005
                                        touch_count = df['high'].apply(lambda x: abs(x - h_level) <= tolerance).sum()
                                        resistance_level_items.append(
                                            LevelItem(level=formatted_h_level, strength=touch_count))
                            resistance_level_items.sort(key=lambda x: x.level)  # Sort all resistances, now formatted

                    else:  # Not enough data for reliable extrema detection, use n-smallest/n-largest
                        logger.info(
                            f"Using n-smallest/n-largest for S/R for {symbol} due to insufficient data for extrema (got {len(df)}, need {min_data_for_extrema})")
                        raw_supports = sorted(df['low'].nsmallest(5).tolist())
                        raw_resistances = sorted(df['high'].nlargest(5).tolist())

                        support_level_items = []
                        for sl_raw in raw_supports:
                            formatted_sl = format_value(sl_raw, price_precision)
                            if formatted_sl is not None:
                                # For these, actual touch count might be low as they are just n-smallest/largest
                                # Assign strength 1 as per requirement
                                support_level_items.append(LevelItem(level=formatted_sl, strength=1))

                        resistance_level_items = []
                        for rl_raw in raw_resistances:
                            formatted_rl = format_value(rl_raw, price_precision)
                            if formatted_rl is not None:
                                resistance_level_items.append(LevelItem(level=formatted_rl, strength=1))

                if len(df) < 300:  # Minimum needed for all TAs
                    logger.warning(
                        f"Not enough data points for {symbol} to calculate all TAs (need 300, got {len(df)}). Skipping TA calculations.")
                    # Support and resistance already calculated above if possible (and formatted)
                    results.append(MarketOverviewItem(
                        symbol=symbol, current_price=current_price, ema_21=None, ema_89=None,
                        # current_price is already formatted
                        sma_30=None, sma_150=None, sma_300=None,
                        support_levels=support_level_items,
                        resistance_levels=resistance_level_items
                    ))
                    continue

                # Calculate EMAs and SMAs
                df['ema_21'] = df.ta.ema(length=21)
                df['ema_89'] = df.ta.ema(length=89)
                df['sma_30'] = df.ta.sma(length=30)
                df['sma_150'] = df.ta.sma(length=150)
                df['sma_300'] = df.ta.sma(length=300)

                raw_ema_21 = df['ema_21'].iloc[-1]
                formatted_ema_21 = format_value(raw_ema_21, price_precision) if pd.notna(raw_ema_21) else None
                raw_ema_89 = df['ema_89'].iloc[-1]
                formatted_ema_89 = format_value(raw_ema_89, price_precision) if pd.notna(raw_ema_89) else None
                raw_sma_30 = df['sma_30'].iloc[-1]
                formatted_sma_30 = format_value(raw_sma_30, price_precision) if pd.notna(raw_sma_30) else None
                raw_sma_150 = df['sma_150'].iloc[-1]
                formatted_sma_150 = format_value(raw_sma_150, price_precision) if pd.notna(raw_sma_150) else None
                raw_sma_300 = df['sma_300'].iloc[-1]
                formatted_sma_300 = format_value(raw_sma_300, price_precision) if pd.notna(raw_sma_300) else None

                results.append(MarketOverviewItem(
                    symbol=symbol, current_price=current_price,  # current_price is already formatted
                    ema_21=formatted_ema_21,
                    ema_89=formatted_ema_89,
                    sma_30=formatted_sma_30,
                    sma_150=formatted_sma_150,
                    sma_300=formatted_sma_300,
                    support_levels=support_level_items,  # Already formatted
                    resistance_levels=resistance_level_items  # Already formatted
                ))

            except ccxt.NetworkError as e:
                logger.error(f"Network error for {symbol} on {exchange_id}: {e}. Default data returned.")
                # Ensure current_price is formatted (0.0 becomes 0.00 if precision is 2)
                formatted_current_price_on_error = format_value(0.0, 2)  # Default to 2 for error cases with 0.0 price
                results.append(
                    MarketOverviewItem(symbol=symbol, current_price=formatted_current_price_on_error, ema_21=None,
                                       ema_89=None, sma_30=None, sma_150=None, sma_300=None, support_levels=[],
                                       resistance_levels=[]))
            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error for {symbol} on {exchange_id}: {e}. Default data returned.")
                formatted_current_price_on_error = format_value(0.0, 2)
                results.append(
                    MarketOverviewItem(symbol=symbol, current_price=formatted_current_price_on_error, ema_21=None,
                                       ema_89=None, sma_30=None, sma_150=None, sma_300=None, support_levels=[],
                                       resistance_levels=[]))
            except Exception as e:
                logger.error(f"An unexpected error occurred for {symbol} on {exchange_id}: {e}. Default data returned.")
                formatted_current_price_on_error = format_value(0.0, 2)
                results.append(
                    MarketOverviewItem(symbol=symbol, current_price=formatted_current_price_on_error, ema_21=None,
                                       ema_89=None, sma_30=None, sma_150=None, sma_300=None, support_levels=[],
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
