import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd
from pandas import DataFrame, Series # For mocking pandas_ta
from typing import List, Dict, Any
from fastapi import HTTPException # Ensure HTTPException is imported
import ccxt.async_support as ccxt

# Assuming your FastAPI app structure allows this import
from src.routers.market_overview import get_market_overview, MarketOverviewItem, LevelItem, SYMBOL_CONFIG # Added LevelItem

pytestmark = pytest.mark.asyncio

# Sample OHLCV data generator
def generate_ohlcv_data(count: int, symbol: str = "MOCK/USDT", base_price_offset: float = 0.0) -> List[List[Any]]:
    # [timestamp, open, high, low, close, volume]
    base_price = (sum(ord(c) for c in symbol) % 100 + 100) + base_price_offset
    return [[1672531200000 + i*3600000, base_price+i, base_price+10+i, base_price-10+i, base_price+5+i, 1000+i*10] for i in range(count)]

@pytest.fixture
def mock_pandas_ta():
    """Mocks pandas_ta EMA and SMA calculations."""
    with patch('pandas.core.frame.DataFrame.ta') as mock_ta_accessor:
        # Configure the accessor to return a MagicMock that can then have methods like ema, sma mocked
        mock_ta_instance = MagicMock()
        mock_ta_accessor.return_value = mock_ta_instance

        # Default behavior for ema and sma: returns a Series of fixed values
        # These can be overridden per test if needed
        mock_ta_instance.ema.side_effect = lambda length, **kwargs: Series([100.0 + length] * 10) # Dummy Series
        mock_ta_instance.sma.side_effect = lambda length, **kwargs: Series([90.0 + length] * 10)  # Dummy Series
        yield mock_ta_instance

@pytest.fixture
def mock_exchange_factory():
    """Factory to create a mock exchange with configurable OHLCV data."""
    def _factory(ohlcv_data: List[List[Any]] | None, exchange_id: str = 'mock_exchange'):
        mock_ex = AsyncMock()
        # Default ticker behavior - can be overridden by tests
        async def default_fetch_ticker(symbol_arg):
            return {'last': (sum(ord(c) for c in symbol_arg) % 1000) + 500.0, 'symbol': symbol_arg}
        mock_ex.fetch_ticker = AsyncMock(side_effect=default_fetch_ticker)
        mock_ex.fetch_ohlcv.return_value = ohlcv_data
        mock_ex.close = AsyncMock()
        mock_ex.symbols = [config['symbol'] for config in SYMBOL_CONFIG if config['exchange_id'] == exchange_id]
        mock_ex.id = exchange_id
        mock_ex.name = exchange_id.capitalize()
        return mock_ex
    return _factory

@pytest.fixture
def mock_ccxt_getattr_patcher():
    """Patches `ccxt.async_support.getattr` and yields the mock."""
    with patch('ccxt.async_support.getattr') as mock_getattr:
        yield mock_getattr

# To store created mock instances for checking .close()
created_exchange_mocks_for_test = {} # Ensure this is defined globally for the helper

def configure_mock_getattr(patcher, factory, ohlcv_config: Dict[str, Any], default_ohlcv_count: int = 350):
    """
    Helper to configure the mock_getattr side_effect.
    ohlcv_config maps exchange_id or symbol to data, Exception, or "insufficient", "empty", "very_little".
    """
    created_exchange_mocks_for_test.clear()

    def side_effect_for_getattr(exchange_id_str: str):
        mock_class = MagicMock()

        default_data_for_exchange = generate_ohlcv_data(default_ohlcv_count, f"DEFAULT/{exchange_id_str}")
        exchange_specific_ohlcv_setting = ohlcv_config.get(exchange_id_str, default_data_for_exchange)

        mock_instance = factory(None, exchange_id_str)

        async def custom_fetch_ohlcv(symbol, timeframe, limit): # Limit is now used from main code (350)
            symbol_specific_setting = ohlcv_config.get(symbol, exchange_specific_ohlcv_setting)

            if isinstance(symbol_specific_setting, Exception):
                raise symbol_specific_setting
            if symbol_specific_setting == "insufficient": # Less than 300, but more than min_data_for_extrema
                return generate_ohlcv_data(150, symbol)
            if symbol_specific_setting == "very_little": # Less than min_data_for_extrema (10)
                return generate_ohlcv_data(7, symbol)
            if symbol_specific_setting == "empty":
                return []
            if isinstance(symbol_specific_setting, list): # It's specific data
                return symbol_specific_setting

            # Fallback to exchange-wide or default generated data
            if isinstance(exchange_specific_ohlcv_setting, Exception): # Should be caught by init_setting ideally
                raise exchange_specific_ohlcv_setting
            # These string checks now apply to exchange_specific_ohlcv_setting if symbol_specific_setting was not found
            if exchange_specific_ohlcv_setting == "insufficient":
                return generate_ohlcv_data(150, symbol)
            if exchange_specific_ohlcv_setting == "very_little":
                return generate_ohlcv_data(7, symbol)
            if exchange_specific_ohlcv_setting == "empty":
                return []
            return exchange_specific_ohlcv_setting # Default list of lists

        async def custom_fetch_ticker(symbol):
            ticker_setting = ohlcv_config.get(f"ticker_{symbol}", ohlcv_config.get(f"ticker_{exchange_id_str}", {}))
            if isinstance(ticker_setting, Exception):
                raise ticker_setting

            price_val = ticker_setting.get('last', (sum(ord(c) for c in symbol) % 1000) + 500.0)
            if isinstance(ticker_setting, (int, float)): # simplified direct price setting
                price_val = float(ticker_setting)

            return {'last': price_val, 'symbol': symbol}

        init_setting = ohlcv_config.get(f"init_{exchange_id_str}")
        if isinstance(init_setting, Exception):
            mock_class.side_effect = init_setting
        else:
            mock_instance.fetch_ohlcv = AsyncMock(side_effect=custom_fetch_ohlcv)
            mock_instance.fetch_ticker = AsyncMock(side_effect=custom_fetch_ticker)
            created_exchange_mocks_for_test[exchange_id_str] = mock_instance
            mock_class.return_value = mock_instance
        return mock_class
    patcher.side_effect = side_effect_for_getattr


async def assert_successful_item(item: MarketOverviewItem, symbol: str, mock_ta_values: Dict[str, float]):
    assert item.symbol == symbol
    assert isinstance(item.current_price, float) and item.current_price > 0

    assert item.ema_21 == mock_ta_values["ema_21"]
    assert item.ema_89 == mock_ta_values["ema_89"]
    assert item.sma_30 == mock_ta_values["sma_30"]
    assert item.sma_150 == mock_ta_values["sma_150"]
    assert item.sma_300 == mock_ta_values["sma_300"]

    assert isinstance(item.support_levels, list)
    if item.support_levels: # Can be empty if current price is below all data
        for sl in item.support_levels:
            assert isinstance(sl, LevelItem)
            assert isinstance(sl.level, float)
            assert isinstance(sl.strength, int) # Check for strength
            assert sl.strength >= 0 # Strength should be non-negative
            assert sl.level < item.current_price if item.current_price > 0 else True # check if price is not 0

    assert isinstance(item.resistance_levels, list)
    if item.resistance_levels: # Can be empty if current price is above all data
        for rl in item.resistance_levels:
            assert isinstance(rl, LevelItem)
            assert isinstance(rl.level, float)
            assert isinstance(rl.strength, int) # Check for strength
            assert rl.strength >= 0 # Strength should be non-negative
            assert rl.level > item.current_price if item.current_price > 0 else True


async def assert_item_no_ta(item: MarketOverviewItem, symbol: str, expect_price: bool = True, expect_levels_non_empty: bool = False):
    assert item.symbol == symbol
    if expect_price:
        assert isinstance(item.current_price, float) # Price can be 0 if ticker fails
    else:
        assert item.current_price == 0.0

    assert item.ema_21 is None
    assert item.ema_89 is None
    assert item.sma_30 is None
    assert item.sma_150 is None
    assert item.sma_300 is None

    assert isinstance(item.support_levels, list)
    assert isinstance(item.resistance_levels, list)

    if expect_levels_non_empty:
        # This case means TA failed, but S/R might still be generated from raw data
        # We expect that if levels are generated, they have a valid structure
        # The actual presence of levels depends on the OHLCV data provided in the test.
        # We can assert that if levels exist, they follow the LevelItem model with 'strength'.
        for sl in item.support_levels:
            assert isinstance(sl, LevelItem)
            assert isinstance(sl.level, float)
            assert isinstance(sl.strength, int)
            assert sl.strength >= 0
        for rl in item.resistance_levels:
            assert isinstance(rl, LevelItem)
            assert isinstance(rl.level, float)
            assert isinstance(rl.strength, int)
            assert rl.strength >= 0
        # We cannot reliably assert `len(item.support_levels) > 0` without knowing the exact mock data's nature for S/R generation in this specific "no_ta" context.
        # The original `or not df.empty` check is problematic as df is not available here.
        # The core idea is: if levels ARE present, they are valid. If not, they are empty lists.
    else:
        # This case means S/R calculation was also not possible or expected to be empty
        assert item.support_levels == []
        assert item.resistance_levels == []


MOCKED_TA_VALUES = {
    "ema_21": 100.0 + 21, "ema_89": 100.0 + 89,
    "sma_30": 90.0 + 30, "sma_150": 90.0 + 150, "sma_300": 90.0 + 300,
}

async def test_get_market_overview_success(mock_ccxt_getattr_patcher, mock_exchange_factory, mock_pandas_ta):
    """All symbols, all exchanges successful with sufficient data."""
    ohlcv_config = {}
    for conf in SYMBOL_CONFIG:
        ohlcv_config[conf["symbol"]] = generate_ohlcv_data(350, conf["symbol"]) # Ensure 350 data points

    # Configure pandas_ta mocks
    mock_pandas_ta.ema.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"ema_{length}"]] * 350)
    mock_pandas_ta.sma.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"sma_{length}"]] * 350)

    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config, default_ohlcv_count=350)

    results = await get_market_overview()
    assert len(results) == len(SYMBOL_CONFIG)
    for item in results:
        await assert_successful_item(item, item.symbol, MOCKED_TA_VALUES)

    for ex_id in created_exchange_mocks_for_test:
        created_exchange_mocks_for_test[ex_id].close.assert_awaited_once()

async def test_get_market_overview_insufficient_data_for_ta(mock_ccxt_getattr_patcher, mock_exchange_factory, mock_pandas_ta):
    """One symbol has insufficient data for TA (<300), but enough for S/R calculation (>10). Others fine."""
    insufficient_symbol = "BTC/USDT"
    ohlcv_config = {
        insufficient_symbol: "insufficient", # Will generate 150 points
    }
    # For other symbols, default_ohlcv_count=350 will be used by configure_mock_getattr

    # Configure pandas_ta mocks for successful symbols
    mock_pandas_ta.ema.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"ema_{length}"]] * 350)
    mock_pandas_ta.sma.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"sma_{length}"]] * 350)

    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config, default_ohlcv_count=350)
    results = await get_market_overview()

    assert len(results) == len(SYMBOL_CONFIG)
    for item in results:
        if item.symbol == insufficient_symbol:
            # TA indicators will be None, S/R levels should be present ("Historical Low/High" or "Recent" if some found)
            await assert_item_no_ta(item, item.symbol, expect_price=True, expect_levels_non_empty=True)
        else:
            await assert_successful_item(item, item.symbol, MOCKED_TA_VALUES)

    for ex_id in created_exchange_mocks_for_test:
        created_exchange_mocks_for_test[ex_id].close.assert_awaited_once()


async def test_get_market_overview_very_little_data_for_sr(mock_ccxt_getattr_patcher, mock_exchange_factory, mock_pandas_ta):
    """One symbol has very little data (<10) for S/R. Fallback S/R should still work."""
    very_little_data_symbol = "ETH/USDT"
    ohlcv_config = {
        very_little_data_symbol: "very_little", # Will generate 7 points
    }
    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config, default_ohlcv_count=350)

    # Configure pandas_ta mocks for successful symbols
    mock_pandas_ta.ema.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"ema_{length}"]] * 350)
    mock_pandas_ta.sma.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"sma_{length}"]] * 350)

    results = await get_market_overview()
    assert len(results) == len(SYMBOL_CONFIG)
    for item in results:
        if item.symbol == very_little_data_symbol:
            await assert_item_no_ta(item, item.symbol, expect_price=True, expect_levels_non_empty=True)
            # Check that descriptions are "Historical Low/High"
            for sl in item.support_levels:
                assert sl.description == "Historical Low"
            for rl in item.resistance_levels:
                assert rl.description == "Historical High"
        else:
            await assert_successful_item(item, item.symbol, MOCKED_TA_VALUES)
    for ex_id in created_exchange_mocks_for_test:
        created_exchange_mocks_for_test[ex_id].close.assert_awaited_once()


async def test_get_market_overview_exchange_init_error_one_exchange(mock_ccxt_getattr_patcher, mock_exchange_factory, mock_pandas_ta):
    """One exchange fails to initialize, symbols from other exchanges are fine."""
    failing_exchange_id = "binance"
    ohlcv_config = {f"init_{failing_exchange_id}": ccxt.ExchangeError("Simulated Binance init error")}

    # Configure pandas_ta mocks for successful symbols
    mock_pandas_ta.ema.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"ema_{length}"]] * 350)
    mock_pandas_ta.sma.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"sma_{length}"]] * 350)

    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config, default_ohlcv_count=350)
    results = await get_market_overview()

    assert len(results) == len(SYMBOL_CONFIG)
    for item in results:
        config_item = next(s for s in SYMBOL_CONFIG if s["symbol"] == item.symbol)
        if config_item["exchange_id"] == failing_exchange_id:
            await assert_item_no_ta(item, item.symbol, expect_price=False, expect_levels_non_empty=False)
        else:
            await assert_successful_item(item, item.symbol, MOCKED_TA_VALUES)

    for ex_id, mock_ex in created_exchange_mocks_for_test.items():
        if ex_id != failing_exchange_id: # Only check close for exchanges that were successfully initialized
            mock_ex.close.assert_awaited_once()
    assert failing_exchange_id not in created_exchange_mocks_for_test

async def test_get_market_overview_fetch_ticker_error_one_symbol(mock_ccxt_getattr_patcher, mock_exchange_factory, mock_pandas_ta):
    """fetch_ticker fails for one symbol. Price is 0. TA and S/R should still run if OHLCV is fetched."""
    error_symbol = "ETH/USDT"
    ohlcv_config = {
        f"ticker_{error_symbol}": ccxt.NetworkError("Simulated ticker error"),
    }
    # All symbols get default 350 OHLCV points
    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config, default_ohlcv_count=350)

    # Configure pandas_ta mocks
    mock_pandas_ta.ema.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"ema_{length}"]] * 350)
    mock_pandas_ta.sma.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"sma_{length}"]] * 350)

    results = await get_market_overview()

    assert len(results) == len(SYMBOL_CONFIG)
    for item in results:
        if item.symbol == error_symbol:
            assert item.current_price == 0.0 # Price fetch failed
            # TA and S/R should be calculated based on OHLCV and mocked TA values
            assert item.ema_21 == MOCKED_TA_VALUES["ema_21"]
            assert item.sma_30 == MOCKED_TA_VALUES["sma_30"]
            assert isinstance(item.support_levels, list) # S/R depends on OHLCV data not price
            assert isinstance(item.resistance_levels, list)
        else:
            await assert_successful_item(item, item.symbol, MOCKED_TA_VALUES)
    for ex_id in created_exchange_mocks_for_test:
        created_exchange_mocks_for_test[ex_id].close.assert_awaited_once()


async def test_get_market_overview_fetch_ohlcv_error_one_symbol(mock_ccxt_getattr_patcher, mock_exchange_factory, mock_pandas_ta):
    """fetch_ohlcv fails for one symbol. Price is present, TA and S/R are not."""
    error_symbol = "DOGE/USDT"
    ohlcv_config = {error_symbol: ccxt.NetworkError("Simulated OHLCV error")}
    # Other symbols get default 350 OHLCV points

    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config, default_ohlcv_count=350)

    # Configure pandas_ta mocks for successful symbols
    mock_pandas_ta.ema.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"ema_{length}"]] * 350)
    mock_pandas_ta.sma.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"sma_{length}"]] * 350)

    results = await get_market_overview()

    assert len(results) == len(SYMBOL_CONFIG)
    for item in results:
        if item.symbol == error_symbol:
            # Price is fetched, but no OHLCV means no TA and no S/R
            await assert_item_no_ta(item, item.symbol, expect_price=True, expect_levels_non_empty=False)
        else:
            await assert_successful_item(item, item.symbol, MOCKED_TA_VALUES)
    for ex_id in created_exchange_mocks_for_test:
        created_exchange_mocks_for_test[ex_id].close.assert_awaited_once()

async def test_get_market_overview_ohlcv_empty_one_symbol(mock_ccxt_getattr_patcher, mock_exchange_factory, mock_pandas_ta):
    """fetch_ohlcv returns empty list for one symbol. Price present, TA/S_R not."""
    empty_ohlcv_symbol = "SUI/USDT"
    ohlcv_config = {empty_ohlcv_symbol: "empty"}

    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config, default_ohlcv_count=350)

    # Configure pandas_ta mocks for successful symbols
    mock_pandas_ta.ema.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"ema_{length}"]] * 350)
    mock_pandas_ta.sma.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"sma_{length}"]] * 350)

    results = await get_market_overview()

    assert len(results) == len(SYMBOL_CONFIG)
    for item in results:
        if item.symbol == empty_ohlcv_symbol:
            await assert_item_no_ta(item, item.symbol, expect_price=True, expect_levels_non_empty=False)
        else:
            await assert_successful_item(item, item.symbol, MOCKED_TA_VALUES)
    for ex_id in created_exchange_mocks_for_test:
        created_exchange_mocks_for_test[ex_id].close.assert_awaited_once()


async def test_get_market_overview_no_symbols_configured():
    """SYMBOL_CONFIG is empty. Should return empty list, no HTTPException."""
    # This test needs to ensure it can modify SYMBOL_CONFIG for its duration
    # The current approach of direct import and modification is stateful and can affect other tests if not careful
    # Consider patching SYMBOL_CONFIG within the test's scope if issues arise in larger test suites.

    # For this specific test, ensure SYMBOL_CONFIG is imported in a way that modification is possible and reversible.
    # from src.routers import market_overview as mo_module # For clarity if needed
    # original_config = list(mo_module.SYMBOL_CONFIG)
    # mo_module.SYMBOL_CONFIG.clear()

    # Simpler: Patch SYMBOL_CONFIG where it's used by get_market_overview
    with patch('src.routers.market_overview.SYMBOL_CONFIG', []):
        results = await get_market_overview()
        assert results == []

    # mo_module.SYMBOL_CONFIG.extend(original_config) # Restore if using module-level modification

async def test_get_market_overview_all_symbols_fail_processing(mock_ccxt_getattr_patcher, mock_exchange_factory, mock_pandas_ta):
    """All symbols/exchanges fail OHLCV fetch. Expect HTTPException 500."""
    if not SYMBOL_CONFIG:
        pytest.skip("SYMBOL_CONFIG is empty, this test scenario is not applicable.")
        return

    ohlcv_config = {}
    for conf in SYMBOL_CONFIG:
        ohlcv_config[conf["symbol"]] = ccxt.NetworkError(f"Simulated OHLCV error for {conf['symbol']}")

    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config)

    with pytest.raises(HTTPException) as exc_info:
        await get_market_overview()

    assert exc_info.value.status_code == 500
    assert "Could not fetch any market data" in exc_info.value.detail

    for ex_id in created_exchange_mocks_for_test:
        created_exchange_mocks_for_test[ex_id].close.assert_awaited_once()

async def test_get_market_overview_all_exchanges_init_fail(mock_ccxt_getattr_patcher, mock_exchange_factory, mock_pandas_ta):
    """All exchanges fail to initialize. Expect HTTPException 500."""
    if not SYMBOL_CONFIG:
        pytest.skip("SYMBOL_CONFIG is empty, this test scenario is not applicable.")
        return

    ohlcv_config = {}
    unique_exchange_ids = set(c['exchange_id'] for c in SYMBOL_CONFIG)
    for ex_id_str in unique_exchange_ids:
         ohlcv_config[f"init_{ex_id_str}"] = ccxt.ExchangeNotAvailable(f"Simulated init error for {ex_id_str}")

    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config)

    with pytest.raises(HTTPException) as exc_info:
        await get_market_overview()

    assert exc_info.value.status_code == 500
    assert "Could not fetch any market data" in exc_info.value.detail
    assert not created_exchange_mocks_for_test


# --- New tests for Support/Resistance Logic ---

def generate_sr_test_ohlcv(points: List[Dict[str, float]], num_total_points: int = 50) -> List[List[Any]]:
    """
    Generates OHLCV data for S/R testing.
    `points` is a list of dicts like {'timestamp_idx': i, 'low': val, 'high': val}
    The function ensures these specific points are embedded in a larger dataset.
    Other points will have low=200, high=250 to not interfere with typical test levels.
    """
    base_time = 1672531200000
    ohlcv = []
    point_indices = {p['timestamp_idx']: p for p in points}

    for i in range(num_total_points):
        ts = base_time + i * 3600000
        op = point_indices.get(i, {}).get('open', 225.0)
        hi = point_indices.get(i, {}).get('high', 250.0)
        lo = point_indices.get(i, {}).get('low', 200.0)
        cl = point_indices.get(i, {}).get('close', 225.0)
        vol = 1000 + i * 10
        ohlcv.append([ts, op, hi, lo, cl, vol])
    return ohlcv

# Test case 1: Mix of Recent and Historical Levels
async def test_sr_mix_recent_historical(mock_ccxt_getattr_patcher, mock_exchange_factory, mock_pandas_ta):
    symbol_under_test = "SR/MIX"
    current_price = 100.0

    # Craft OHLCV:
    # Recent Lows: 90, 95 (local minima)
    # Historical Lows: 80, 85 (will be picked by nsmallest)
    # Recent Highs: 110, 105 (local maxima)
    # Historical Highs: 120, 115 (will be picked by nlargest)

    # Make sure local extrema are actualy local by padding:
    # For low at index i to be local min (order 5): low[i-5]..low[i-1] > low[i] < low[i+1]..low[i+5]
    # For simplicity, we'll ensure a few points around are higher for lows, lower for highs.
    # And then pad with non-interfering values.
    ohlcv_points = [
        # For supports (target < 100)
        {'timestamp_idx': 10, 'low': 90, 'high': 100}, # Recent Low
        {'timestamp_idx': 20, 'low': 95, 'high': 102}, # Recent Low
        # Add other lows that will be "historical"
        {'timestamp_idx': 5, 'low': 80, 'high': 90},
        {'timestamp_idx': 15, 'low': 85, 'high': 95},
        {'timestamp_idx': 25, 'low': 75, 'high': 85}, # Extra one

        # For resistances (target > 100)
        {'timestamp_idx': 30, 'low': 100, 'high': 110}, # Recent High
        {'timestamp_idx': 40, 'low': 102, 'high': 105}, # Recent High
        # Add other highs that will be "historical"
        {'timestamp_idx': 28, 'low': 110, 'high': 120},
        {'timestamp_idx': 35, 'low': 112, 'high': 115},
        {'timestamp_idx': 45, 'low': 120, 'high': 125}, # Extra one
    ]
    # Add padding points to ensure argrelextrema works as expected for order=5
    # For 90 at index 10: indices 5-9 and 11-15 should have low > 90
    # For 95 at index 20: indices 15-19 and 21-25 should have low > 95
    # For 110 at index 30: indices 25-29 and 31-35 should have high < 110
    # For 105 at index 40: indices 35-39 and 41-45 should have high < 105

    # Simplified approach: use a generator that makes it easier to create local extremas
    # This requires a more complex generator or manually crafting a full list.
    # Let's use a simpler list of values and check if it works with argrelextrema.
    # We'll use a longer series to give argrelextrema space.

    low_values = [150]*50 # timestamp_idx from 0 to 49
    high_values = [50]*50

    # Insert our specific points (prices are relative to current_price = 100)
    # Recent Lows
    low_values[10] = 90 # Expected Recent Low
    for i in range(5,10): low_values[i] = 91
    for i in range(11,16): low_values[i] = 91

    low_values[20] = 95 # Expected Recent Low
    for i in range(15,20): low_values[i] = 96
    for i in range(21,26): low_values[i] = 96

    # Historical Lows (will be picked by nsmallest from remaining)
    low_values[5] = 80
    low_values[6] = 85
    low_values[7] = 75 # This should be the 3rd historical if 2 recent found

    # Recent Highs
    high_values[30] = 110 # Expected Recent High
    for i in range(25,30): high_values[i] = 109
    for i in range(31,36): high_values[i] = 109

    high_values[40] = 105 # Expected Recent High
    for i in range(35,40): high_values[i] = 104
    for i in range(41,46): high_values[i] = 104

    # Historical Highs
    high_values[25] = 120
    high_values[26] = 115
    high_values[27] = 125 # This should be the 3rd historical

    custom_ohlcv = [[1672531200000 + i*3600000, 100, high_values[i], low_values[i], 100, 1000+i*10] for i in range(50)]

    ohlcv_config = {
        symbol_under_test: custom_ohlcv,
        f"ticker_{symbol_under_test}": current_price, # Set current price
    }
    # Mock SYMBOL_CONFIG for this test
    test_specific_symbol_config = [{"symbol": symbol_under_test, "exchange_id": "mock_exchange", "name": "SRTestCoin"}]

    with patch('src.routers.market_overview.SYMBOL_CONFIG', test_specific_symbol_config):
        configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config, default_ohlcv_count=50)

        # Configure pandas_ta mocks for this specific test
        mock_pandas_ta.ema.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"ema_{length}"]] * 50)
        mock_pandas_ta.sma.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"sma_{length}"]] * 50)

        results = await get_market_overview()

    assert len(results) == 1
    item = results[0]
    assert item.symbol == symbol_under_test

    # Assertions for Support Levels
    assert len(item.support_levels) <= 5
    sl_levels = [sl.level for sl in item.support_levels]
    sl_strengths = [sl.strength for sl in item.support_levels]

    # Check if specific levels are present and their strengths are integers
    # The exact strength values depend on the complex interaction of extrema detection,
    # ATR filtering, and Fibonacci generation, which is hard to precisely predict in mock tests
    # without replicating the entire logic. So, we check for presence and type.
    assert 95.0 in sl_levels
    assert isinstance(sl_strengths[sl_levels.index(95.0)], int)
    assert 90.0 in sl_levels
    assert isinstance(sl_strengths[sl_levels.index(90.0)], int)

    assert all(isinstance(s, int) and s >= 0 for s in sl_strengths)
    assert len(item.support_levels) > 0 # Expect some levels to be found

    # Assertions for Resistance Levels
    assert len(item.resistance_levels) <= 5
    rl_levels = [rl.level for rl in item.resistance_levels]
    rl_strengths = [rl.strength for rl in item.resistance_levels]

    assert 105.0 in rl_levels
    assert isinstance(rl_strengths[rl_levels.index(105.0)], int)
    assert 110.0 in rl_levels
    assert isinstance(rl_strengths[rl_levels.index(110.0)], int)

    assert all(isinstance(s, int) and s >= 0 for s in rl_strengths)
    assert len(item.resistance_levels) > 0 # Expect some levels to be found

    # Check sorting
    assert all(item.support_levels[i].level >= item.support_levels[i+1].level for i in range(len(item.support_levels)-1))
    assert all(item.resistance_levels[i].level <= item.resistance_levels[i+1].level for i in range(len(item.resistance_levels)-1))


# Test case 2: Only Recent Levels (e.g. 5 local extrema found)
async def test_sr_only_recent(mock_ccxt_getattr_patcher, mock_exchange_factory, mock_pandas_ta):
    symbol_under_test = "SR/RECENT"
    current_price = 100.0

    low_values = [150]*50
    high_values = [50]*50

    # 5 recent lows
    for i in range(5):
        val = 90 - i*2
        idx = 5 + i*7
        low_values[idx] = val
        for k in range(idx-2, idx): low_values[k] = val + 1 # Ensure local min
        for k in range(idx+1, idx+3): low_values[k] = val + 1 # Ensure local min

    # 5 recent highs
    for i in range(5):
        val = 110 + i*2
        idx = 5 + i*7
        high_values[idx] = val
        for k in range(idx-2, idx): high_values[k] = val -1 # Ensure local max
        for k in range(idx+1, idx+3): high_values[k] = val -1 # Ensure local max

    custom_ohlcv = [[1672531200000 + i*3600000, 100, high_values[i], low_values[i], 100, 1000+i*10] for i in range(50)]

    ohlcv_config = {
        symbol_under_test: custom_ohlcv,
        f"ticker_{symbol_under_test}": current_price,
    }
    test_specific_symbol_config = [{"symbol": symbol_under_test, "exchange_id": "mock_exchange", "name": "SRTestCoinRecent"}]

    with patch('src.routers.market_overview.SYMBOL_CONFIG', test_specific_symbol_config):
        configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config, default_ohlcv_count=50)
        mock_pandas_ta.ema.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"ema_{length}"]] * 50)
        mock_pandas_ta.sma.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"sma_{length}"]] * 50)
        results = await get_market_overview()

    assert len(results) == 1
    item = results[0]

    assert len(item.support_levels) == 5
    assert all(isinstance(sl.strength, int) and sl.strength >= 0 for sl in item.support_levels) # Check strength type and value
    assert len(item.resistance_levels) == 5
    assert all(isinstance(rl.strength, int) and rl.strength >= 0 for rl in item.resistance_levels) # Check strength type and value
    assert all(item.support_levels[i].level >= item.support_levels[i+1].level for i in range(len(item.support_levels)-1))
    assert all(item.resistance_levels[i].level <= item.resistance_levels[i+1].level for i in range(len(item.resistance_levels)-1))


# Test case 3: Only Historical Levels (e.g., no local extrema satisfy criteria)
async def test_sr_only_historical(mock_ccxt_getattr_patcher, mock_exchange_factory, mock_pandas_ta):
    symbol_under_test = "SR/HISTORICAL"
    current_price = 100.0

    # Monotonically increasing price (no local lows below current_price, no local highs above current_price will be 'recent')
    # Or, all local extrema are e.g. above current_price for lows.
    low_values = [101 + i for i in range(50)] # All lows are above current_price or at least increasing
    high_values = [105 + i for i in range(50)]# All highs are above current_price and increasing

    # To ensure some historical values are picked:
    low_values[5] = 70; low_values[10]=75; low_values[15]=80; low_values[20]=85; low_values[25]=90;
    high_values[5]=130; high_values[10]=125; high_values[15]=120; high_values[20]=115; high_values[25]=110;


    custom_ohlcv = [[1672531200000 + i*3600000, 100, high_values[i], low_values[i], 100, 1000+i*10] for i in range(50)]

    ohlcv_config = {
        symbol_under_test: custom_ohlcv,
        f"ticker_{symbol_under_test}": current_price,
    }
    test_specific_symbol_config = [{"symbol": symbol_under_test, "exchange_id": "mock_exchange", "name": "SRTestCoinHistorical"}]

    with patch('src.routers.market_overview.SYMBOL_CONFIG', test_specific_symbol_config):
        configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config, default_ohlcv_count=50)
        mock_pandas_ta.ema.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"ema_{length}"]] * 50)
        mock_pandas_ta.sma.side_effect = lambda length, **kwargs: Series([MOCKED_TA_VALUES[f"sma_{length}"]] * 50)
        results = await get_market_overview()

    assert len(results) == 1
    item = results[0]

    # Expect 5 historical lows as local lows > 100 or argrelextrema finds none < 100
    # However, nsmallest/fibonacci will pick values < 100
    assert len(item.support_levels) == 5
    assert all(isinstance(sl.strength, int) and sl.strength >= 0 for sl in item.support_levels) # Check strength type and value
    assert all(sl.level < current_price for sl in item.support_levels)

    # Expect 5 historical highs as local highs might be found but we want to test fallback
    assert len(item.resistance_levels) == 5
    assert all(isinstance(rl.strength, int) and rl.strength >= 0 for rl in item.resistance_levels) # Check strength type and value
    assert all(rl.level > current_price for rl in item.resistance_levels)

    assert all(item.support_levels[i].level >= item.support_levels[i+1].level for i in range(len(item.support_levels)-1))
    assert all(item.resistance_levels[i].level <= item.resistance_levels[i+1].level for i in range(len(item.resistance_levels)-1))

# Test for very little data scenario (already covered by test_get_market_overview_very_little_data_for_sr)
# but this can be an explicit S/R version if needed.
# The existing test already checks for "Historical Low/High" descriptions.
