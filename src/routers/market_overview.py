from fastapi import APIRouter, HTTPException
import logging
from typing import List, Optional
import decimal
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import pandas_ta as ta
import ccxt.async_support as ccxt
from pydantic import BaseModel
import os
from src.services.cache_manager import read_ohlcv_from_cache, \
    write_ohlcv_to_cache
from src.core.config import settings

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


def generate_fibonacci_levels(
        swing_low_price: float,
        swing_high_price: float,
        current_price: float,
        is_support: bool,
        num_needed: int,
        existing_levels_raw: list[float],  # These are the levels already selected by extrema logic (raw values)
        effective_min_gap: float,
        atr_value: float,
        price_precision: int,
        logger
) -> list[float]:
    """
    Generates Fibonacci levels based on a swing, filtering for support/resistance
    and attempting to maintain an ATR-based gap.

    Args:
        swing_low_price: The low price of the significant swing.
        swing_high_price: The high price of the significant swing.
        current_price: The current market price.
        is_support: True if generating support levels, False for resistance.
        num_needed: The number of Fibonacci levels to generate.
        existing_levels_raw: A list of raw (unformatted) prices of already selected S/R levels.
        effective_min_gap: The calculated effective minimum gap for S/R level spacing.
        atr_value: The current ATR value (for secondary heuristic checks).
        price_precision: The precision for formatting the level values.
        logger: Logger instance for logging.
    Returns:
        A list of formatted Fibonacci level prices.
    """
    if swing_high_price <= swing_low_price or num_needed == 0:
        return []

    fib_levels_config = {
        'retracement': [0.236, 0.382, 0.5, 0.618, 0.786],
        'extension_above': [1.272, 1.618, 2.0, 2.618],
        'extension_below': [-0.272, -0.618]
    }

    price_diff = swing_high_price - swing_low_price
    potential_fib_levels = []

    # Retracements
    for ratio in fib_levels_config['retracement']:
        potential_fib_levels.append(swing_high_price - price_diff * ratio)
        potential_fib_levels.append(swing_low_price + price_diff * ratio)

    # Extensions
    for ratio in fib_levels_config['extension_above']:
        potential_fib_levels.append(swing_high_price + price_diff * (ratio - 1))

    for ratio in fib_levels_config['extension_below']:
        potential_fib_levels.append(swing_low_price + price_diff * ratio)

    # Deduplicate and sort
    potential_fib_levels = sorted(list(set(potential_fib_levels)))

    generated_levels = []

    # This list will hold *formatted* levels already accepted either from existing_levels_raw
    # or newly generated Fibonacci levels, for consistent gap checking.
    accepted_levels_for_gap_check = [format_value(lvl, price_precision) for lvl in existing_levels_raw if
                                     format_value(lvl, price_precision) is not None]

    if is_support:
        # For support, we want levels below current_price, sorted descending (closer to current price first)
        potential_fib_levels = [lvl for lvl in potential_fib_levels if lvl < current_price]
        potential_fib_levels.sort(reverse=True)

        for level_raw in potential_fib_levels:
            if len(generated_levels) >= num_needed:
                break

            formatted_level = format_value(level_raw, price_precision)
            if formatted_level is None:
                continue

            # Check gap against all levels already accepted (existing + Fibs generated so far)
            is_far_enough = True
            for existing_formatted_lvl in accepted_levels_for_gap_check:
                if abs(formatted_level - existing_formatted_lvl) < effective_min_gap:
                    is_far_enough = False
                    break

            # Additional heuristic check: avoid adding a level too close to any *raw* existing level
            too_close_to_existing_raw = False
            # Ensure atr_value is not None and not NaN for multiplication
            atr_heuristic_threshold = atr_value * 0.5 if atr_value is not None and pd.notna(atr_value) else 0.0
            for ex_lvl_raw in existing_levels_raw:
                if abs(level_raw - ex_lvl_raw) < atr_heuristic_threshold:
                    too_close_to_existing_raw = True
                    break

            if is_far_enough and not too_close_to_existing_raw:
                if formatted_level not in generated_levels:  # Avoid duplicate formatted levels within generated list
                    generated_levels.append(formatted_level)
                    accepted_levels_for_gap_check.append(
                        formatted_level)  # Add newly accepted Fib level for future checks

    else:  # For resistance
        # For resistance, we want levels above current_price, sorted ascending
        potential_fib_levels = [lvl for lvl in potential_fib_levels if lvl > current_price]
        potential_fib_levels.sort()

        for level_raw in potential_fib_levels:
            if len(generated_levels) >= num_needed:
                break

            formatted_level = format_value(level_raw, price_precision)
            if formatted_level is None:
                continue

            # Check gap against all levels already accepted (existing + Fibs generated so far)
            is_far_enough = True
            for existing_formatted_lvl in accepted_levels_for_gap_check:
                if abs(formatted_level - existing_formatted_lvl) < effective_min_gap:
                    is_far_enough = False
                    break

            # Additional heuristic check: avoid adding a level too close to any *raw* existing level
            too_close_to_existing_raw = False
            atr_heuristic_threshold = atr_value * 0.5 if atr_value is not None and pd.notna(atr_value) else 0.0
            for ex_lvl_raw in existing_levels_raw:
                if abs(level_raw - ex_lvl_raw) < atr_heuristic_threshold:
                    too_close_to_existing_raw = True
                    break

            if is_far_enough and not too_close_to_existing_raw:
                if formatted_level not in generated_levels:  # Avoid duplicate formatted levels within generated list
                    generated_levels.append(formatted_level)
                    accepted_levels_for_gap_check.append(
                        formatted_level)  # Add newly accepted Fib level for future checks

    # Final sort based on is_support
    if is_support:
        generated_levels.sort(key=lambda x: x if x is not None else float('-inf'),
                              reverse=True)  # Handle None if somehow present
    else:
        generated_levels.sort(key=lambda x: x if x is not None else float('inf'))  # Handle None if somehow present

    # Return up to num_needed levels
    return generated_levels[:num_needed]


class LevelItem(BaseModel):
    level: float
    strength: int


class MarketOverviewItem(BaseModel):
    symbol: str
    current_price: float
    ema_21: float | None = None
    ema_89: float | None = None
    sma_30: float | None = None
    sma_150: float | None = None
    sma_300: float | None = None
    atr_14: float | None = None
    support_levels: List[LevelItem]
    resistance_levels: List[LevelItem]
    # DCA Analysis Fields
    dca_signal: str | None = None  # "strong_buy", "buy", "hold", "wait", "avoid"
    dca_confidence: float | None = None  # 0-100
    dca_amount_multiplier: float | None = None  # 0.5-2.0x
    dca_reasoning: List[str] | None = None
    rsi_14: float | None = None
    volume_ratio: float | None = None  # Current volume vs 20-period EMA
    volume_ratio_avg: float | None = None  # 5-period average of volume ratios
    vol_price_ratio: float | None = None  # Volume ratio * abs(price_change)
    volume_status: str | None = None  # "very_high", "high", "normal", "low"
    market_sentiment: str | None = None  # "bullish", "bearish", "neutral"


SYMBOL_CONFIG = [
    {"symbol": "BTC/USDT", "exchange_id": "binance", "name": "Bitcoin", "desired_gap_usdt": 500.0},
    {"symbol": "ETH/USDT", "exchange_id": "binance", "name": "Ethereum", "desired_gap_usdt": 40},
    {"symbol": "DOGE/USDT", "exchange_id": "binance", "name": "Dogecoin", "desired_gap_usdt": 0.003},
    {"symbol": "SUI/USDT", "exchange_id": "binance", "name": "Sui", "desired_gap_usdt": 0.05},
    {"symbol": "POPCAT/USDT", "exchange_id": "mexc", "name": "Popcat", "desired_gap_usdt": 0.005},
    {"symbol": "HYPE/USDT", "exchange_id": "mexc", "name": "HypeCoin", "desired_gap_usdt": 0.7}
]

router = APIRouter()


@router.get("/market-overview/", response_model=List[MarketOverviewItem])
async def get_market_overview():
    results = []
    active_exchanges = {}

    try:
        for config_item in SYMBOL_CONFIG:
            symbol = config_item["symbol"]
            exchange_id = config_item["exchange_id"]

            cached_df: Optional[pd.DataFrame] = None
            last_cached_timestamp: Optional[int] = None

            logger.info(f"[{symbol}] Attempting to load OHLCV data from cache...")
            cached_df = read_ohlcv_from_cache(settings.CACHE_DIRECTORY, symbol, timeframe='1h')

            if cached_df is not None and not cached_df.empty:
                cached_df.sort_values(by='timestamp', ascending=True, inplace=True)
                last_cached_timestamp = cached_df['timestamp'].iloc[-1]

                logger.info(
                    f"[{symbol}] Cache hit. Last cached candle timestamp: {last_cached_timestamp}, Records: {len(cached_df)}")
            else:
                logger.info(
                    f"[{symbol}] No cache found or cache is empty. Will attempt to fetch {settings.MAX_CANDLES_TO_CACHE} candles for initial cache.")

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
                            sma_30=None, sma_150=None, sma_300=None, atr_14=None,
                            support_levels=[], resistance_levels=[]
                        ))
                        continue
                    except Exception as e:
                        logger.critical(
                            f"Error initializing exchange {exchange_id} for symbol {symbol}: {e}. Skipping.")
                        results.append(MarketOverviewItem(
                            symbol=symbol, current_price=0.0, ema_21=None, ema_89=None,
                            sma_30=None, sma_150=None, sma_300=None, atr_14=None,
                            support_levels=[], resistance_levels=[]
                        ))
                        continue

                # Fetch Ticker for current price
                ticker = await exchange.fetch_ticker(symbol)
                current_price_raw = ticker['last'] if ticker and 'last' in ticker and ticker['last'] else 0.0

                if current_price_raw == 0.0:
                    price_precision = 2
                else:
                    price_precision = get_price_precision(current_price_raw)
                current_price = format_value(current_price_raw, price_precision)

                ohlcv_from_exchange = []
                final_df = pd.DataFrame()

                fetch_limit = settings.MAX_CANDLES_TO_CACHE
                fetch_since = None

                if last_cached_timestamp is not None:
                    fetch_since = int(last_cached_timestamp)
                    fetch_limit = settings.MAX_CANDLES_TO_CACHE
                    logger.info(
                        f"[{symbol}] Cache found. Fetching new candles since: {fetch_since} (timestamp), limit: {fetch_limit}")
                else:
                    logger.info(f"[{symbol}] No cache. Fetching {fetch_limit} candles.")

                if exchange:
                    ohlcv_from_exchange = await exchange.fetch_ohlcv(symbol, timeframe='1h', since=fetch_since,
                                                                     limit=fetch_limit)
                    logger.info(f"[{symbol}] Fetched {len(ohlcv_from_exchange)} new candles from exchange.")
                else:
                    logger.error(f"[{symbol}] Exchange object not initialized during OHLCV fetch. Skipping fetch.")

                new_data_df = pd.DataFrame()
                if ohlcv_from_exchange:
                    new_data_df = pd.DataFrame(ohlcv_from_exchange,
                                               columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    new_data_df['timestamp'] = new_data_df['timestamp'].astype('int64')
                    new_data_df.sort_values(by='timestamp', ascending=True, inplace=True)

                if cached_df is not None and not cached_df.empty:
                    final_df = pd.concat([cached_df, new_data_df], ignore_index=True)
                else:
                    final_df = new_data_df

                if not final_df.empty:
                    final_df.drop_duplicates(subset=['timestamp'], keep='last', inplace=True)
                    final_df.sort_values(by='timestamp', ascending=True, inplace=True)

                    if len(final_df) > settings.MAX_CANDLES_TO_CACHE:
                        final_df = final_df.tail(settings.MAX_CANDLES_TO_CACHE)

                    final_df.reset_index(drop=True, inplace=True)

                    if not final_df.empty:
                        try:
                            write_ohlcv_to_cache(settings.CACHE_DIRECTORY, symbol, final_df, timeframe='1h')
                            logger.info(f"[{symbol}] Successfully updated cache with {len(final_df)} records.")
                        except Exception as e:
                            logger.error(f"[{symbol}] Error writing to cache: {e}")
                    else:
                        logger.info(f"[{symbol}] Final DataFrame is empty after processing. Nothing to cache.")
                else:
                    logger.info(f"[{symbol}] No data after combining cache and fetch. Nothing to cache or process.")

                df = final_df

                if df.empty:
                    logger.warning(
                        f"[{symbol}] DataFrame is empty after cache operations and fetching. Skipping analysis for this symbol.")
                    results.append(MarketOverviewItem(
                        symbol=symbol, current_price=current_price if current_price is not None else 0.0,
                        ema_21=None, ema_89=None, sma_30=None, sma_150=None, sma_300=None, atr_14=None,
                        support_levels=[], resistance_levels=[]
                    ))
                    continue

                logger.debug(f"[{symbol}] DataFrame shape before ATR: {df.shape}, initial dtypes:\n{df.dtypes}")
                if not df.empty and len(df) > 5:
                    logger.debug(f"[{symbol}] DataFrame head before ATR:\n{df.head()}")
                    logger.debug(f"[{symbol}] DataFrame tail before ATR:\n{df.tail()}")
                elif not df.empty:
                    logger.debug(f"[{symbol}] DataFrame contents before ATR:\n{df}")

                hlc_columns_present = True
                required_hlc_cols = ['high', 'low', 'close']
                for col in required_hlc_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        if df[col].isnull().all():
                            logger.warning(f"[{symbol}] Column '{col}' became all NaNs after numeric conversion.")
                            hlc_columns_present = False
                            break
                    else:
                        logger.error(
                            f"[{symbol}] Critical: Column '{col}' not found. Cannot calculate ATR or other HLC-dependent TAs.")
                        hlc_columns_present = False
                        break

                if not hlc_columns_present:
                    logger.error(f"[{symbol}] ATR calculation skipped due to missing HLC columns. ATR_14 set to NaN.")
                    df['ATR_14'] = np.nan
                else:
                    logger.debug(f"[{symbol}] Dtypes after HLC numeric conversion:\n{df.dtypes}")
                    MIN_ROWS_FOR_ATR = 20
                    if len(df) < MIN_ROWS_FOR_ATR:
                        logger.warning(
                            f"[{symbol}] DataFrame has {len(df)} rows, < minimum ({MIN_ROWS_FOR_ATR}) for stable ATR. ATR_14 set to NaN.")
                        df['ATR_14'] = np.nan
                    else:
                        try:
                            atr_series = df.ta.atr(length=14)
                            if atr_series is not None and not atr_series.empty:
                                df['ATR_14'] = atr_series
                                logger.debug(f"[{symbol}] Successfully calculated and assigned ATR_14 series.")
                            else:
                                logger.warning(
                                    f"[{symbol}] ATR calculation returned None or empty series. Assigning NaN to ATR_14 column.")
                                df['ATR_14'] = np.nan
                        except Exception as e:
                            logger.error(
                                f"[{symbol}] Error during ATR calculation: {e}. Assigning NaN to ATR_14 column.")
                            df['ATR_14'] = np.nan

                atr_value = None
                if 'ATR_14' in df.columns and not df['ATR_14'].empty:
                    if len(df['ATR_14']) > 0:
                        last_atr = df['ATR_14'].iloc[-1]
                        if pd.notna(last_atr):
                            atr_value = last_atr
                            logger.info(f"[{symbol}] Retrieved ATR value: {atr_value}")
                        else:
                            logger.warning(f"[{symbol}] Last value in 'ATR_14' column is NaN. atr_value remains None.")
                    else:
                        logger.warning(f"[{symbol}] 'ATR_14' column is present but empty. atr_value remains None.")
                else:
                    logger.warning(f"[{symbol}] 'ATR_14' column is missing or was empty. atr_value remains None.")

                formatted_atr_14 = None
                if atr_value is not None and pd.notna(atr_value):
                    formatted_atr_14 = format_value(atr_value, price_precision)
                elif atr_value is None:
                    logger.info(
                        f"[{symbol}] ATR could not be calculated or was invalid, formatted_atr_14 remains None.")
                else:  # atr_value is likely np.nan here
                    logger.warning(f"[{symbol}] Raw atr_value is NaN, formatted_atr_14 remains None.")

                logger.info(
                    f"Symbol: {symbol} - Calculated Raw ATR_14: {atr_value if atr_value is not None else 'N/A'}, Formatted ATR_14: {formatted_atr_14 if formatted_atr_14 is not None else 'N/A'}")
                if atr_value == 0:
                    logger.warning(
                        f"Symbol: {symbol} - ATR value is 0. This might be due to very low volatility or still an issue if data was sparse. S/R gap logic might not work as expected.")
                elif atr_value is None:
                    logger.warning(
                        f"Symbol: {symbol} - ATR value is None (could not be calculated). S/R gap logic will rely on desired_gap_usdt.")

                current_symbol_desired_gap = config_item.get('desired_gap_usdt')
                if current_symbol_desired_gap is None:
                    logger.error(
                        f"[{symbol}] 'desired_gap_usdt' not found in SYMBOL_CONFIG for this symbol. Defaulting its component to 0.")
                    current_symbol_desired_gap = 0.0

                atr_component = atr_value * settings.ATR_MULTIPLIER_FOR_GAP if atr_value is not None and pd.notna(
                    atr_value) else 0.0

                effective_minimum_gap = max(atr_component, current_symbol_desired_gap)

                atr_log_display = f"{atr_value:.4f}" if atr_value is not None and pd.notna(atr_value) else "N/A"
                logger.info(
                    f"[{symbol}] ATR: {atr_log_display}, ATR*{settings.ATR_MULTIPLIER_FOR_GAP}: {atr_component:.4f}, DesiredGapUSDT: {current_symbol_desired_gap:.4f} -> EffectiveMinGap: {effective_minimum_gap:.4f}")

                support_level_items = []
                resistance_level_items = []

                min_data_for_extrema = settings.EXTREMA_ORDER * 2

                if not df.empty:
                    if len(df) >= min_data_for_extrema:
                        low_extrema_indices = argrelextrema(df['low'].values, np.less, order=settings.EXTREMA_ORDER)[0]
                        local_lows = df['low'].iloc[low_extrema_indices].unique()

                        recent_supports = sorted([low for low in local_lows if low < current_price_raw], reverse=True)

                        support_level_items_filtered = []
                        last_selected_support_level = float('inf')

                        for s_level_raw in recent_supports:
                            if not support_level_items_filtered or (
                                    last_selected_support_level - s_level_raw >= effective_minimum_gap):
                                if len(support_level_items_filtered) < 5:
                                    tolerance = s_level_raw * 0.0005
                                    touch_count = df['low'].apply(lambda x: abs(x - s_level_raw) <= tolerance).sum()
                                    formatted_level = format_value(s_level_raw, price_precision)
                                    if formatted_level is not None:
                                        support_level_items_filtered.append(
                                            LevelItem(level=formatted_level, strength=touch_count))
                                        last_selected_support_level = s_level_raw
                                else:
                                    break
                        support_level_items = support_level_items_filtered
                        support_level_items.sort(key=lambda x: x.level, reverse=True)
                        logger.debug(
                            f"Symbol: {symbol} - Support levels after ATR filtering ({len(support_level_items)}): {[item.level for item in support_level_items]}")

                        if len(support_level_items) < 5:
                            num_needed_support = 5 - len(support_level_items)
                            if not df.empty and len(df) >= 2:
                                swing_low_price_for_fib = df['low'].min()
                                swing_high_price_for_fib = df['high'].max()

                                raw_existing_supports = [item.level for item in support_level_items]

                                logger.info(
                                    f"Symbol: {symbol} - Not enough support levels ({len(support_level_items)} found), trying to generate {num_needed_support} Fibonacci support levels.")
                                logger.debug(
                                    f"Symbol: {symbol} - Fibonacci params for support: swing_low={swing_low_price_for_fib}, swing_high={swing_high_price_for_fib}, current_price={current_price_raw}, num_needed={num_needed_support}, existing_raw_supports_count={len(raw_existing_supports)}, atr_value={atr_value}")

                                fib_support_levels_formatted = generate_fibonacci_levels(
                                    swing_low_price=swing_low_price_for_fib,
                                    swing_high_price=swing_high_price_for_fib,
                                    current_price=current_price_raw,
                                    is_support=True,
                                    num_needed=num_needed_support,
                                    existing_levels_raw=raw_existing_supports,
                                    effective_min_gap=effective_minimum_gap,
                                    atr_value=atr_value,
                                    price_precision=price_precision,
                                    logger=logger
                                )

                                logger.debug(
                                    f"Symbol: {symbol} - Generated {len(fib_support_levels_formatted)} Fibonacci support levels: {fib_support_levels_formatted}")

                                existing_formatted_levels_set = {item.level for item in support_level_items}
                                for fib_level_val in fib_support_levels_formatted:
                                    if fib_level_val not in existing_formatted_levels_set:
                                        support_level_items.append(LevelItem(level=fib_level_val, strength=1))
                                        existing_formatted_levels_set.add(fib_level_val)
                                        if len(support_level_items) >= 5:
                                            break
                            else:
                                logger.warning(
                                    f"Not enough data points in DataFrame for {symbol} to calculate Fibonacci support levels (need >= 2, got {len(df)}).")

                            support_level_items.sort(key=lambda x: x.level, reverse=True)
                            support_level_items = support_level_items[:5]

                        logger.info(
                            f"Final support levels for {symbol} ({len(support_level_items)} levels): {[item.level for item in support_level_items]}")

                        high_extrema_indices = \
                        argrelextrema(df['high'].values, np.greater, order=settings.EXTREMA_ORDER)[0]
                        local_highs = df['high'].iloc[high_extrema_indices].unique()

                        recent_resistances = sorted([high for high in local_highs if high > current_price_raw])

                        resistance_level_items_filtered = []
                        last_selected_resistance_level = float('-inf')

                        for r_level_raw in recent_resistances:
                            if not resistance_level_items_filtered or (
                                    r_level_raw - last_selected_resistance_level >= effective_minimum_gap):
                                if len(resistance_level_items_filtered) < 5:
                                    tolerance = r_level_raw * 0.0005
                                    touch_count = df['high'].apply(lambda x: abs(x - r_level_raw) <= tolerance).sum()
                                    formatted_level = format_value(r_level_raw, price_precision)
                                    if formatted_level is not None:
                                        resistance_level_items_filtered.append(
                                            LevelItem(level=formatted_level, strength=touch_count))
                                        last_selected_resistance_level = r_level_raw
                                else:
                                    break
                        resistance_level_items = resistance_level_items_filtered
                        resistance_level_items.sort(key=lambda x: x.level)
                        logger.debug(
                            f"Symbol: {symbol} - Resistance levels after ATR filtering ({len(resistance_level_items)}): {[item.level for item in resistance_level_items]}")

                        if len(resistance_level_items) < 5:
                            num_needed_resistance = 5 - len(resistance_level_items)
                            if not df.empty and len(df) >= 2:
                                swing_low_price_for_fib = df['low'].min()
                                swing_high_price_for_fib = df['high'].max()

                                raw_existing_resistances = [item.level for item in resistance_level_items]

                                logger.info(
                                    f"Symbol: {symbol} - Not enough resistance levels ({len(resistance_level_items)} found), trying to generate {num_needed_resistance} Fibonacci resistance levels.")
                                logger.debug(
                                    f"Symbol: {symbol} - Fibonacci params for resistance: swing_low={swing_low_price_for_fib}, swing_high={swing_high_price_for_fib}, current_price={current_price_raw}, num_needed={num_needed_resistance}, existing_raw_resistances_count={len(raw_existing_resistances)}, atr_value={atr_value}")

                                fib_resistance_levels_formatted = generate_fibonacci_levels(
                                    swing_low_price=swing_low_price_for_fib,
                                    swing_high_price=swing_high_price_for_fib,
                                    current_price=current_price_raw,
                                    is_support=False,
                                    num_needed=num_needed_resistance,
                                    existing_levels_raw=raw_existing_resistances,
                                    effective_min_gap=effective_minimum_gap,
                                    atr_value=atr_value,
                                    price_precision=price_precision,
                                    logger=logger
                                )

                                logger.debug(
                                    f"Symbol: {symbol} - Generated {len(fib_resistance_levels_formatted)} Fibonacci resistance levels: {fib_resistance_levels_formatted}")

                                existing_formatted_levels_set = {item.level for item in resistance_level_items}
                                for fib_level_val in fib_resistance_levels_formatted:
                                    if fib_level_val not in existing_formatted_levels_set:
                                        resistance_level_items.append(
                                            LevelItem(level=fib_level_val, strength=1))
                                        existing_formatted_levels_set.add(fib_level_val)
                                        if len(resistance_level_items) >= 5:
                                            break
                            else:
                                logger.warning(
                                    f"Not enough data points in DataFrame for {symbol} to calculate Fibonacci resistance levels (need >= 2, got {len(df)}).")

                            resistance_level_items.sort(key=lambda x: x.level)
                            resistance_level_items = resistance_level_items[:5]

                        logger.info(
                            f"Final resistance levels for {symbol} ({len(resistance_level_items)} levels): {[item.level for item in resistance_level_items]}")

                    else:
                        logger.info(
                            f"Using n-smallest/n-largest for S/R for {symbol} due to insufficient data for extrema (got {len(df)}, need {min_data_for_extrema})")
                        raw_supports = sorted(df['low'].nsmallest(5).tolist())
                        raw_resistances = sorted(df['high'].nlargest(5).tolist())

                        support_level_items = []
                        for sl_raw in raw_supports:
                            formatted_sl = format_value(sl_raw, price_precision)
                            if formatted_sl is not None:
                                support_level_items.append(LevelItem(level=formatted_sl, strength=1))

                        resistance_level_items = []
                        for rl_raw in raw_resistances:
                            formatted_rl = format_value(rl_raw, price_precision)
                            if formatted_rl is not None:
                                resistance_level_items.append(LevelItem(level=formatted_rl, strength=1))

                if len(df) < 300:
                    logger.warning(
                        f"Not enough data points for {symbol} to calculate all TAs (need 300, got {len(df)}). Skipping TA calculations.")
                    results.append(MarketOverviewItem(
                        symbol=symbol, current_price=current_price,
                        ema_21=None, ema_89=None, sma_30=None, sma_150=None, sma_300=None, atr_14=formatted_atr_14,
                        support_levels=support_level_items,
                        resistance_levels=resistance_level_items,
                        # DCA Analysis (minimal data available)
                        dca_signal="hold",
                        dca_confidence=50.0,
                        dca_amount_multiplier=1.0,
                        dca_reasoning=["Insufficient data for full analysis"],
                        rsi_14=None,
                        volume_ratio=None,
                        market_sentiment="neutral"
                    ))
                    continue

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

                # Calculate additional indicators for DCA analysis
                df['rsi_14'] = df.ta.rsi(length=14)
                
                # Enhanced Volume Analysis (EMA-based)
                df['volume_ema_20'] = df['volume'].ewm(span=20, adjust=False).mean()
                df['volume_ratio'] = df['volume'] / df['volume_ema_20']
                
                # Volume ratio trend (5-period average)
                df['volume_ratio_avg'] = df['volume_ratio'].rolling(window=5).mean()
                
                # Volume-price correlation
                df['price_change'] = df['close'].pct_change()
                df['vol_price_ratio'] = df['volume_ratio'] * df['price_change'].abs()
                
                # Volume status classification
                def volume_level(vr):
                    if vr > 2:
                        return "very_high"
                    elif vr > 1.2:
                        return "high"
                    elif vr < 0.5:
                        return "low"
                    else:
                        return "normal"
                
                df['volume_status'] = df['volume_ratio'].apply(volume_level)
                
                # Get latest values
                rsi_14 = df['rsi_14'].iloc[-1] if pd.notna(df['rsi_14'].iloc[-1]) else 50.0
                volume_ratio = df['volume_ratio'].iloc[-1] if pd.notna(df['volume_ratio'].iloc[-1]) else 1.0
                volume_ratio_avg = df['volume_ratio_avg'].iloc[-1] if pd.notna(df['volume_ratio_avg'].iloc[-1]) else 1.0
                vol_price_ratio = df['vol_price_ratio'].iloc[-1] if pd.notna(df['vol_price_ratio'].iloc[-1]) else 0.0
                volume_status = df['volume_status'].iloc[-1] if pd.notna(df['volume_status'].iloc[-1]) else "normal"
                
                # Perform DCA analysis
                dca_analysis = _analyze_dca_opportunity(
                    df, current_price_raw, formatted_atr_14, 
                    formatted_ema_21, formatted_sma_30, 
                    support_level_items, rsi_14, volume_ratio, 
                    volume_ratio_avg, vol_price_ratio, volume_status
                )

                results.append(MarketOverviewItem(
                    symbol=symbol, current_price=current_price,
                    ema_21=formatted_ema_21,
                    ema_89=formatted_ema_89,
                    sma_30=formatted_sma_30,
                    sma_150=formatted_sma_150,
                    sma_300=formatted_sma_300,
                    atr_14=formatted_atr_14,
                    support_levels=support_level_items,
                    resistance_levels=resistance_level_items,
                    # DCA Analysis
                    dca_signal=dca_analysis['signal'],
                    dca_confidence=dca_analysis['confidence'],
                    dca_amount_multiplier=dca_analysis['amount_multiplier'],
                    dca_reasoning=dca_analysis['reasoning'],
                    rsi_14=format_value(rsi_14, 2),
                    volume_ratio=format_value(volume_ratio, 2),
                    volume_ratio_avg=format_value(volume_ratio_avg, 2),
                    vol_price_ratio=format_value(vol_price_ratio, 3),
                    volume_status=volume_status,
                    market_sentiment=dca_analysis['sentiment']
                ))

            except ccxt.NetworkError as e:
                logger.error(f"Network error for {symbol} on {exchange_id}: {e}. Default data returned.")
                formatted_current_price_on_error = format_value(0.0, 2)
                results.append(
                    MarketOverviewItem(symbol=symbol, current_price=formatted_current_price_on_error, ema_21=None,
                                       ema_89=None, sma_30=None, sma_150=None, sma_300=None, atr_14=None,
                                       support_levels=[], resistance_levels=[],
                                       # DCA Analysis (error state)
                                       dca_signal="wait",
                                       dca_confidence=0.0,
                                       dca_amount_multiplier=0.5,
                                       dca_reasoning=["Network error - unable to analyze"],
                                       rsi_14=None,
                                       volume_ratio=None,
                                       volume_ratio_avg=None,
                                       vol_price_ratio=None,
                                       volume_status=None,
                                       market_sentiment="neutral"))
            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error for {symbol} on {exchange_id}: {e}. Default data returned.")
                formatted_current_price_on_error = format_value(0.0, 2)
                results.append(
                    MarketOverviewItem(symbol=symbol, current_price=formatted_current_price_on_error, ema_21=None,
                                       ema_89=None, sma_30=None, sma_150=None, sma_300=None, atr_14=None,
                                       support_levels=[], resistance_levels=[],
                                       # DCA Analysis (error state)
                                       dca_signal="wait",
                                       dca_confidence=0.0,
                                       dca_amount_multiplier=0.5,
                                       dca_reasoning=["Exchange error - unable to analyze"],
                                       rsi_14=None,
                                       volume_ratio=None,
                                       volume_ratio_avg=None,
                                       vol_price_ratio=None,
                                       volume_status=None,
                                       market_sentiment="neutral"))
            except Exception as e:
                logger.error(f"An unexpected error occurred for {symbol} on {exchange_id}: {e}. Default data returned.")
                formatted_current_price_on_error = format_value(0.0, 2)
                results.append(
                    MarketOverviewItem(symbol=symbol, current_price=formatted_current_price_on_error, ema_21=None,
                                       ema_89=None, sma_30=None, sma_150=None, sma_300=None, atr_14=None,
                                       support_levels=[], resistance_levels=[],
                                       # DCA Analysis (error state)
                                       dca_signal="wait",
                                       dca_confidence=0.0,
                                       dca_amount_multiplier=0.5,
                                       dca_reasoning=["Unexpected error - unable to analyze"],
                                       rsi_14=None,
                                       volume_ratio=None,
                                       volume_ratio_avg=None,
                                       vol_price_ratio=None,
                                       volume_status=None,
                                       market_sentiment="neutral"))

    finally:
        for ex_id, ex_instance in active_exchanges.items():
            if ex_instance:
                try:
                    await ex_instance.close()
                    print(f"Closed {ex_id} exchange.")
                except Exception as e:
                    print(f"Error closing {ex_id} exchange: {e}")

    if not results and SYMBOL_CONFIG:
        logger.error("Could not fetch any market data for the configured symbols.")
        raise HTTPException(status_code=500, detail="Could not fetch any market data for the configured symbols.")
    return results


def _analyze_dca_opportunity(
    df: pd.DataFrame,
    current_price: float,
    atr_14: float | None,
    ema_21: float | None,
    sma_30: float | None,
    support_levels: List[LevelItem],
    rsi_14: float,
    volume_ratio: float,
    volume_ratio_avg: float,
    vol_price_ratio: float,
    volume_status: str
) -> dict:
    """
    Analyze DCA opportunity based on market conditions.
    Returns: dict with signal, confidence, amount_multiplier, reasoning, and sentiment
    """
    reasoning = []
    confidence = 50.0
    signal = "hold"
    amount_multiplier = 1.0
    sentiment = "neutral"
    
    # RSI analysis
    if rsi_14 < 30:
        reasoning.append("RSI indicates oversold conditions")
        confidence += 15
        signal = "buy"
        amount_multiplier += 0.1
    elif rsi_14 < 40:
        reasoning.append("RSI shows potential buying opportunity")
        confidence += 10
        signal = "buy"
    elif rsi_14 > 70:
        reasoning.append("RSI indicates overbought conditions")
        confidence -= 20
        signal = "wait"
        amount_multiplier -= 0.1
    
    # Trend analysis
    if ema_21 and current_price > ema_21 * 1.02:
        reasoning.append("Price above EMA21 - short-term uptrend")
        confidence += 10
    elif ema_21 and current_price < ema_21 * 0.98:
        reasoning.append("Price below EMA21 - short-term downtrend")
        confidence -= 15
        signal = "wait"
        amount_multiplier -= 0.1
    
    if sma_30 and current_price > sma_30 * 1.05:
        reasoning.append("Strong medium-term uptrend")
        confidence += 10
    elif sma_30 and current_price < sma_30 * 0.95:
        reasoning.append("Medium-term downtrend")
        confidence -= 10
    
    # Volatility analysis
    if atr_14:
        atr_percent = (atr_14 / current_price) * 100
        if atr_percent > 5:  # High volatility
            reasoning.append("High volatility - consider smaller position")
            amount_multiplier -= 0.1
        elif atr_percent < 1:  # Low volatility
            reasoning.append("Low volatility - stable conditions")
            confidence += 5
    
    # Support level analysis
    if support_levels:
        nearest_support = max([s.level for s in support_levels if s.level < current_price], default=0)
        if nearest_support > 0:
            distance_to_support = ((current_price - nearest_support) / current_price) * 100
            if distance_to_support < 2:
                reasoning.append("Price near strong support level")
                confidence += 10
                signal = "strong_buy"
                amount_multiplier += 0.2
            elif distance_to_support < 5:
                reasoning.append("Price approaching support level")
                confidence += 5
                amount_multiplier += 0.1
    
    # Enhanced Volume Analysis
    if volume_status == "very_high":
        reasoning.append("Very high volume - potential breakout/breakdown")
        confidence += 15
        amount_multiplier += 0.2
        if vol_price_ratio > 1.5:
            reasoning.append("Volume confirms strong price movement")
            confidence += 10
    elif volume_status == "high":
        reasoning.append("High volume activity")
        confidence += 10
        amount_multiplier += 0.1
        if vol_price_ratio > 1.0:
            reasoning.append("Volume supports price movement")
            confidence += 5
    elif volume_status == "low":
        reasoning.append("Low volume - weak momentum")
        confidence -= 10
        amount_multiplier -= 0.1
        if vol_price_ratio < 0.5:
            reasoning.append("Price moving without volume support")
            confidence -= 5
    
    # Volume trend analysis
    if volume_ratio_avg > 1.3:
        reasoning.append("Volume trend is increasing")
        confidence += 5
    elif volume_ratio_avg < 0.7:
        reasoning.append("Volume trend is decreasing")
        confidence -= 5
    
    # Volume-price divergence detection
    if vol_price_ratio < 0.3 and abs(df['price_change'].iloc[-1]) > 0.02:
        reasoning.append("Price moving without volume confirmation")
        confidence -= 10
        signal = "wait"
    
    # Determine final signal and confidence
    if confidence >= 80:
        signal = "strong_buy"
        sentiment = "bullish"
    elif confidence >= 60:
        signal = "buy"
        sentiment = "bullish"
    elif confidence >= 40:
        signal = "hold"
        sentiment = "neutral"
    elif confidence >= 20:
        signal = "wait"
        sentiment = "bearish"
    else:
        signal = "avoid"
        sentiment = "bearish"
    
    # Clamp confidence to 0-100
    confidence = max(0, min(100, confidence))
    # Clamp amount multiplier to 0.5-2.0
    amount_multiplier = max(0.5, min(2.0, amount_multiplier))
    
    return {
        'signal': signal,
        'confidence': confidence,
        'amount_multiplier': amount_multiplier,
        'reasoning': reasoning,
        'sentiment': sentiment
    }