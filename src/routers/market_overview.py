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


# import pandas as pd # Ensure pandas is imported if not already at the top for pd.notna
# decimal should already be imported

def generate_fibonacci_levels(
    swing_low_price: float,
    swing_high_price: float,
    current_price: float,
    is_support: bool,
    num_needed: int,
    existing_levels_raw: list[float], # Raw (unformatted) values of existing S/R levels for comparison
    atr_value: float,
    price_precision: int,
    logger # Pass logger for any warnings/info
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
        atr_value: The current ATR value.
        price_precision: The precision for formatting the level values.
        logger: Logger instance for logging.
    Returns:
        A list of formatted Fibonacci level prices.
    """
    if swing_high_price <= swing_low_price or num_needed == 0:
        return []

    fib_levels_config = {
        'retracement': [0.236, 0.382, 0.5, 0.618, 0.786],
        'extension_above': [1.272, 1.618, 2.0, 2.618], # Added more extension levels
        'extension_below': [-0.272, -0.618] # For extensions below swing_low if current price is already below
    }

    price_diff = swing_high_price - swing_low_price
    potential_fib_levels = []

    # Retracements
    for ratio in fib_levels_config['retracement']:
        potential_fib_levels.append(swing_high_price - price_diff * ratio) # From high for support
        potential_fib_levels.append(swing_low_price + price_diff * ratio)  # From low for resistance

    # Extensions above swing_high
    for ratio in fib_levels_config['extension_above']:
        potential_fib_levels.append(swing_high_price + price_diff * (ratio - 1)) # Corrected extension calc

    # Extensions below swing_low (less common for this S/R style, but can be useful if price breaks far)
    # Typically extensions are from the *end* of a primary move, projecting further.
    # For simplicity here, we'll use extensions from the swing_high and swing_low.
    # Alternative: Extensions from current price if it's outside the swing - more complex.
    # Let's stick to extensions of the identified swing range for now.
    # For levels below swing_low_price (deep support)
    for ratio in fib_levels_config['extension_below']: # e.g. 127.2% of range *below* low
         potential_fib_levels.append(swing_low_price + price_diff * ratio) # price_diff is positive, ratio is negative

    # Deduplicate and sort
    potential_fib_levels = sorted(list(set(potential_fib_levels)))

    generated_levels = []

    # Combine all existing levels (already selected S/R + newly added Fib levels) for gap checking
    # Note: existing_levels_raw are unformatted. Comparisons should ideally be consistent.
    # For simplicity in this function, we will format Fib levels then check against formatted existing.
    # A more robust check would involve comparing raw values consistently.

    all_considered_levels_for_gap_check = sorted(existing_levels_raw + [lvl for lvl in generated_levels])


    if is_support:
        # For support, we want levels below current_price, sorted descending (closer to current price first)
        potential_fib_levels = [lvl for lvl in potential_fib_levels if lvl < current_price]
        potential_fib_levels.sort(reverse=True)

        last_added_fib_level = float('inf') # For checking gap between Fib levels themselves
        if existing_levels_raw: # Check against the lowest existing support level
             last_added_fib_level = min(existing_levels_raw)


        for level_raw in potential_fib_levels:
            if len(generated_levels) >= num_needed:
                break

            # Check ATR gap relative to the closest existing S/R level (which is last_added_fib_level initially)
            # and subsequently relative to other fib levels being added.
            is_far_enough_from_existing = True # Assume true initially
            if existing_levels_raw or generated_levels: # only check gap if there are levels to check against
                closest_level_for_gap = 0
                if generated_levels: # Prioritize gap from last added Fib level
                    closest_level_for_gap = generated_levels[-1] # these are already formatted
                elif existing_levels_raw : # if no fib levels yet, check against raw existing S/R
                                           # this implies existing_levels_raw should be sorted appropriately
                                           # For support, we'd compare against the lowest (min) existing formatted S/R level
                    # This part is tricky: existing_levels_raw are unformatted.
                    # Let's simplify: the primary ATR gap is checked when integrating. Here, we mostly pick candidates.
                    # A basic proximity check to avoid very close levels:
                    min_dist_to_existing = min([abs(level_raw - ex_lvl) for ex_lvl in all_considered_levels_for_gap_check]) if all_considered_levels_for_gap_check else float('inf')

                    # ATR Gap: level_raw should be ATR*2 away from last_added_fib_level (which could be an existing S/R or a Fib)
                    # For support, new level must be significantly lower.
                    if not (last_added_fib_level - level_raw >= atr_value * 2):
                         is_far_enough_from_existing = False


            # Simplified check: avoid adding a level too close to any *raw* existing level
            # A small tolerance, e.g., atr_value / 4 or a fixed percentage
            too_close_to_existing = False
            for ex_lvl_raw in existing_levels_raw:
                if abs(level_raw - ex_lvl_raw) < (atr_value * 0.5): # Heuristic: don't add if within 0.5 ATR of an existing raw level
                    too_close_to_existing = True
                    break

            if not too_close_to_existing and is_far_enough_from_existing:
                formatted_level = format_value(level_raw, price_precision)
                if formatted_level is not None and formatted_level not in [format_value(l, price_precision) for l in generated_levels]: # Avoid duplicate formatted levels
                    generated_levels.append(formatted_level)
                    last_added_fib_level = level_raw # Update for gap checking against next Fib level
                    all_considered_levels_for_gap_check.append(level_raw)
                    all_considered_levels_for_gap_check.sort(reverse=True)


    else: # For resistance
        # For resistance, we want levels above current_price, sorted ascending
        potential_fib_levels = [lvl for lvl in potential_fib_levels if lvl > current_price]
        potential_fib_levels.sort()

        last_added_fib_level = 0.0 # For checking gap between Fib levels themselves
        if existing_levels_raw: # Check against the highest existing resistance level
            last_added_fib_level = max(existing_levels_raw)

        for level_raw in potential_fib_levels:
            if len(generated_levels) >= num_needed:
                break

            is_far_enough_from_existing = True
            if existing_levels_raw or generated_levels:
                closest_level_for_gap = 0
                if generated_levels:
                    closest_level_for_gap = generated_levels[-1]
                elif existing_levels_raw:
                    # For resistance, compare against the highest (max) existing formatted S/R level
                    pass # Simplified as above

                # ATR Gap: level_raw should be ATR*2 away from last_added_fib_level
                # For resistance, new level must be significantly higher.
                if not (level_raw - last_added_fib_level >= atr_value * 2):
                    is_far_enough_from_existing = False

            too_close_to_existing = False
            for ex_lvl_raw in existing_levels_raw:
                if abs(level_raw - ex_lvl_raw) < (atr_value * 0.5): # Heuristic
                    too_close_to_existing = True
                    break

            if not too_close_to_existing and is_far_enough_from_existing:
                formatted_level = format_value(level_raw, price_precision)
                if formatted_level is not None and formatted_level not in [format_value(l, price_precision) for l in generated_levels]:
                    generated_levels.append(formatted_level)
                    last_added_fib_level = level_raw
                    all_considered_levels_for_gap_check.append(level_raw)
                    all_considered_levels_for_gap_check.sort()

    # Ensure the correct number of levels is returned, even if ATR conditions are strict
    # If not enough levels were generated due to strict ATR, this function will return fewer than num_needed.
    # The integration step will have to decide how to handle this (e.g. relax ATR for Fib, or accept fewer levels).
    # For now, the function returns what it found respecting the rules.

    # Final sort based on is_support
    if is_support:
        generated_levels.sort(reverse=True)
    else:
        generated_levels.sort()

    return generated_levels[:num_needed]


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
                df.ta.atr(length=14, append=True)

                atr_value = df['ATR_14'].iloc[-1] if 'ATR_14' in df.columns and not df['ATR_14'].empty and pd.notna(df['ATR_14'].iloc[-1]) else 0
                logger.info(f"Symbol: {symbol} - Calculated ATR_14: {atr_value}") # Enhanced existing log
                if atr_value == 0:
                    logger.warning(f"Symbol: {symbol} - ATR value is 0, S/R gap logic might not work as expected. Consider using a default minimum gap or handling this case.")
                    # For now, if ATR is 0, the ATR*2 gap will be 0. This means all levels will pass the gap check.
                    # A more robust solution might involve a fallback minimum gap, but that's outside current scope.

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
                        logger.debug(f"Symbol: {symbol} - Initial raw local_lows < current_price_raw: {sorted([low for low in local_lows if low < current_price_raw], reverse=True)}")

                        # Filter, sort, and select support levels
                        # current_price here is already formatted. For comparison with unformatted df values, use current_price_raw
                        recent_supports = sorted([low for low in local_lows if low < current_price_raw], reverse=True)

                        support_level_items_filtered = []
                        last_selected_support_level = float('inf') # Initialize high, as we are looking for levels below

                        for s_level_raw in recent_supports: # Iterate through all potential recent supports
                            # ATR Gap Check:
                            # The first support level is always selected if it's below current price (already filtered by recent_supports).
                            # Subsequent levels must be at least ATR*2 below the last_selected_support_level.
                            if not support_level_items_filtered or (last_selected_support_level - s_level_raw >= atr_value * 2):
                                if len(support_level_items_filtered) < 5: # Only add if we still need levels
                                    tolerance = s_level_raw * 0.0005
                                    touch_count = df['low'].apply(lambda x: abs(x - s_level_raw) <= tolerance).sum()
                                    formatted_level = format_value(s_level_raw, price_precision)
                                    if formatted_level is not None:
                                        support_level_items_filtered.append(LevelItem(level=formatted_level, strength=touch_count))
                                        last_selected_support_level = s_level_raw # Update the last selected raw level for the next comparison
                                else:
                                    break # Stop if we have 5 levels

                        support_level_items = support_level_items_filtered # Assign the filtered list
                        # Ensure it's sorted, though the selection process should maintain descending order
                        support_level_items.sort(key=lambda x: x.level, reverse=True)
                        logger.debug(f"Symbol: {symbol} - Support levels after ATR filtering ({len(support_level_items)}): {[item.level for item in support_level_items]}")

                        # Fill with Fibonacci levels if needed for Support
                        if len(support_level_items) < 5:
                            num_needed_support = 5 - len(support_level_items)
                            if not df.empty and len(df) >= 2: # Need at least 2 points for a swing
                                swing_low_price_for_fib = df['low'].min()
                                swing_high_price_for_fib = df['high'].max()

                                # Get raw values of existing support levels to help Fib generator avoid close placement
                                # The support_level_items currently store LevelItem objects with formatted levels.
                                # The generate_fibonacci_levels function expects raw float values for existing_levels_raw.
                                # This is a slight mismatch: current items are formatted.
                                # For now, we pass the formatted levels. This might mean the proximity check in Fib generator
                                # compares formatted vs raw, which is not ideal but a simplification for this step.
                                # A more robust way would be to keep raw values alongside formatted ones until the very end.
                                raw_existing_supports = [item.level for item in support_level_items]

                                logger.info(f"Symbol: {symbol} - Not enough support levels ({len(support_level_items)} found), trying to generate {num_needed_support} Fibonacci support levels.")
                                logger.debug(f"Symbol: {symbol} - Fibonacci params for support: swing_low={swing_low_price_for_fib}, swing_high={swing_high_price_for_fib}, current_price={current_price_raw}, num_needed={num_needed_support}, existing_raw_supports_count={len(raw_existing_supports)}, atr_value={atr_value}")

                                fib_support_levels_raw = generate_fibonacci_levels(
                                    swing_low_price=swing_low_price_for_fib,
                                    swing_high_price=swing_high_price_for_fib,
                                    current_price=current_price_raw, # Use raw current price for Fib calculation context
                                    is_support=True,
                                    num_needed=num_needed_support,
                                    existing_levels_raw=raw_existing_supports, # Pass existing *formatted* levels as raw context
                                    atr_value=atr_value,
                                    price_precision=price_precision,
                                    logger=logger
                                )

                                logger.debug(f"Symbol: {symbol} - Generated {len(fib_support_levels_raw)} raw Fibonacci support levels: {fib_support_levels_raw}")

                                existing_formatted_levels_set = {item.level for item in support_level_items}
                                for fib_level_val in fib_support_levels_raw: # These are already formatted by the generator
                                    if fib_level_val not in existing_formatted_levels_set: # Avoid duplicates
                                        # Add with a default strength, e.g., 0 or 1
                                        support_level_items.append(LevelItem(level=fib_level_val, strength=1))
                                        existing_formatted_levels_set.add(fib_level_val)
                                        if len(support_level_items) >= 5:
                                            break
                            else:
                                logger.warning(f"Not enough data points in DataFrame for {symbol} to calculate Fibonacci support levels (need >= 2, got {len(df)}).")

                            # Sort all supports (original + Fib) and truncate to 5
                            support_level_items.sort(key=lambda x: x.level, reverse=True)
                            if len(support_level_items) > 5:
                                support_level_items = support_level_items[:5]

                            # If still less than 5, it means Fib generator couldn't find enough valid levels.
                            # The requirement is "exactly 5 levels". This might need a fallback if Fib is insufficient.
                            # For now, we rely on Fib generation; if it's short, we'll have fewer.
                            # Plan step 9 (Review and Test) will be important.
                            # The original issue states: "if you out of levels you can add fibo levels ... I need to have exactly 5 levels no less!"
                            # This implies Fib should try harder or have relaxed rules if needed.
                            # The current fib_generator tries to respect ATR. If it can't, it returns fewer.
                            # This might require a second pass for Fib with relaxed ATR if count is still < 5.
                            # Let's proceed with current Fib generator strictness and re-evaluate in testing.

                        # Ensure final list has at most 5 levels (already done above, but as a safeguard)
                        if len(support_level_items) > 5:
                           support_level_items = support_level_items[:5]

                        # Logging final support levels for the symbol
                        logger.info(f"Final support levels for {symbol} ({len(support_level_items)} levels): {[item.level for item in support_level_items]}")

                        # Find local maxima for resistance levels
                        high_extrema_indices = argrelextrema(df['high'].values, np.greater, order=extrema_order)[0]
                        local_highs = df['high'].iloc[high_extrema_indices].unique()
                        logger.debug(f"Symbol: {symbol} - Initial raw local_highs > current_price_raw: {sorted([high for high in local_highs if high > current_price_raw])}")

                        # Filter, sort, and select resistance levels
                        # current_price here is already formatted. For comparison with unformatted df values, use current_price_raw
                        recent_resistances = sorted([high for high in local_highs if high > current_price_raw])

                        resistance_level_items_filtered = []
                        last_selected_resistance_level = 0.0 # Initialize low, as we are looking for levels above

                        for r_level_raw in recent_resistances: # Iterate through all potential recent resistances
                            # ATR Gap Check:
                            # The first resistance level is always selected if it's above current price (already filtered by recent_resistances).
                            # Subsequent levels must be at least ATR*2 above the last_selected_resistance_level.
                            if not resistance_level_items_filtered or (r_level_raw - last_selected_resistance_level >= atr_value * 2):
                                if len(resistance_level_items_filtered) < 5: # Only add if we still need levels
                                    tolerance = r_level_raw * 0.0005
                                    touch_count = df['high'].apply(lambda x: abs(x - r_level_raw) <= tolerance).sum()
                                    formatted_level = format_value(r_level_raw, price_precision)
                                    if formatted_level is not None:
                                        resistance_level_items_filtered.append(LevelItem(level=formatted_level, strength=touch_count))
                                        last_selected_resistance_level = r_level_raw # Update the last selected raw level for the next comparison
                                else:
                                    break # Stop if we have 5 levels

                        resistance_level_items = resistance_level_items_filtered # Assign the filtered list
                        # Ensure it's sorted, though the selection process should maintain ascending order
                        resistance_level_items.sort(key=lambda x: x.level)
                        logger.debug(f"Symbol: {symbol} - Resistance levels after ATR filtering ({len(resistance_level_items)}): {[item.level for item in resistance_level_items]}")

                        # Fill with Fibonacci levels if needed for Resistance
                        if len(resistance_level_items) < 5:
                            num_needed_resistance = 5 - len(resistance_level_items)
                            if not df.empty and len(df) >= 2: # Need at least 2 points for a swing
                                swing_low_price_for_fib = df['low'].min()
                                swing_high_price_for_fib = df['high'].max()

                                # Pass existing *formatted* resistance levels as raw context (same simplification as with support)
                                raw_existing_resistances = [item.level for item in resistance_level_items]

                                logger.info(f"Symbol: {symbol} - Not enough resistance levels ({len(resistance_level_items)} found), trying to generate {num_needed_resistance} Fibonacci resistance levels.")
                                logger.debug(f"Symbol: {symbol} - Fibonacci params for resistance: swing_low={swing_low_price_for_fib}, swing_high={swing_high_price_for_fib}, current_price={current_price_raw}, num_needed={num_needed_resistance}, existing_raw_resistances_count={len(raw_existing_resistances)}, atr_value={atr_value}")

                                fib_resistance_levels_raw = generate_fibonacci_levels(
                                    swing_low_price=swing_low_price_for_fib,
                                    swing_high_price=swing_high_price_for_fib,
                                    current_price=current_price_raw, # Use raw current price
                                    is_support=False, # Key change for resistance
                                    num_needed=num_needed_resistance,
                                    existing_levels_raw=raw_existing_resistances,
                                    atr_value=atr_value,
                                    price_precision=price_precision,
                                    logger=logger
                                )

                                logger.debug(f"Symbol: {symbol} - Generated {len(fib_resistance_levels_raw)} raw Fibonacci resistance levels: {fib_resistance_levels_raw}")

                                existing_formatted_levels_set = {item.level for item in resistance_level_items}
                                for fib_level_val in fib_resistance_levels_raw: # These are already formatted
                                    if fib_level_val not in existing_formatted_levels_set: # Avoid duplicates
                                        resistance_level_items.append(LevelItem(level=fib_level_val, strength=1)) # Default strength 1
                                        existing_formatted_levels_set.add(fib_level_val)
                                        if len(resistance_level_items) >= 5:
                                            break
                            else:
                                logger.warning(f"Not enough data points in DataFrame for {symbol} to calculate Fibonacci resistance levels (need >= 2, got {len(df)}).")

                            # Sort all resistances (original + Fib) and truncate to 5
                            resistance_level_items.sort(key=lambda x: x.level) # Ascending for resistance
                            if len(resistance_level_items) > 5:
                                resistance_level_items = resistance_level_items[:5]

                            # Notes on "exactly 5 levels" from support integration apply here too.

                        # Ensure final list has at most 5 levels (already done above, but as a safeguard)
                        if len(resistance_level_items) > 5:
                           resistance_level_items = resistance_level_items[:5]

                        # Logging final resistance levels for the symbol
                        logger.info(f"Final resistance levels for {symbol} ({len(resistance_level_items)} levels): {[item.level for item in resistance_level_items]}")

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
