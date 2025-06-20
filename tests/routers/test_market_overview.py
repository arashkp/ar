import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd
# import pandas_ta as ta # Not strictly necessary for these tests as calculations are in the router
from typing import List, Dict, Any
from fastapi import HTTPException # Ensure HTTPException is imported

# Assuming your FastAPI app structure allows this import
from src.routers.market_overview import get_market_overview, MarketOverviewItem, SYMBOL_CONFIG
# If router object itself is needed for TestClient approach (not used here):
# from src.routers.market_overview import router

pytestmark = pytest.mark.asyncio

# Sample OHLCV data generator
def generate_ohlcv_data(count: int, symbol: str = "MOCK/USDT") -> List[List[Any]]:
    # [timestamp, open, high, low, close, volume]
    # Generate somewhat unique data based on symbol to avoid identical TA results if not desired
    base_price = sum(ord(c) for c in symbol) % 100 + 100 # Simple hash for price variation
    return [[1672531200000 + i*3600000, base_price+i, base_price+10+i, base_price-10+i, base_price+5+i, 1000+i*10] for i in range(count)]

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
created_exchange_mocks_for_test = {}

def configure_mock_getattr(patcher, factory, ohlcv_config: Dict[str, List[List[Any]] | Exception | str]):
    """
    Helper to configure the mock_getattr side_effect.
    ohlcv_config maps exchange_id or symbol to data, Exception, or "insufficient".
    """
    created_exchange_mocks_for_test.clear()

    def side_effect_for_getattr(exchange_id_str: str):
        mock_class = MagicMock() # This mock represents the exchange class (e.g., ccxt.binance)

        # Determine behavior for this exchange_id
        # Default to sufficient data if not specified for the exchange_id directly
        exchange_specific_ohlcv_setting = ohlcv_config.get(exchange_id_str, generate_ohlcv_data(100, f"DEFAULT/{exchange_id_str}"))

        mock_instance = factory(None, exchange_id_str) # OHLCV set by customized fetch_ohlcv

        async def custom_fetch_ohlcv(symbol, timeframe, limit):
            symbol_specific_setting = ohlcv_config.get(symbol, exchange_specific_ohlcv_setting)
            if isinstance(symbol_specific_setting, Exception):
                raise symbol_specific_setting
            if symbol_specific_setting == "insufficient":
                return generate_ohlcv_data(40, symbol) # Less than 50
            if isinstance(symbol_specific_setting, str) and symbol_specific_setting == "empty":
                return []
            if isinstance(symbol_specific_setting, list): # It's data
                return symbol_specific_setting
            # Fallback for exchange_id wide setting if symbol not specifically defined
            if isinstance(exchange_specific_ohlcv_setting, Exception):
                raise exchange_specific_ohlcv_setting
            if exchange_specific_ohlcv_setting == "insufficient":
                return generate_ohlcv_data(40, symbol)
            if exchange_specific_ohlcv_setting == "empty":
                return []
            return exchange_specific_ohlcv_setting # Should be list of lists

        async def custom_fetch_ticker(symbol):
            ticker_setting = ohlcv_config.get(f"ticker_{symbol}", ohlcv_config.get(f"ticker_{exchange_id_str}"))
            if isinstance(ticker_setting, Exception):
                raise ticker_setting
            price = (sum(ord(c) for c in symbol) % 1000) + 500.0 # Default price
            if isinstance(ticker_setting, (int, float)):
                price = float(ticker_setting)
            return {'last': price, 'symbol': symbol}

        init_setting = ohlcv_config.get(f"init_{exchange_id_str}")
        if isinstance(init_setting, Exception):
            mock_class.side_effect = init_setting # Error on instantiation
            # No instance stored if init fails
        else:
            mock_instance.fetch_ohlcv = AsyncMock(side_effect=custom_fetch_ohlcv)
            mock_instance.fetch_ticker = AsyncMock(side_effect=custom_fetch_ticker)
            created_exchange_mocks_for_test[exchange_id_str] = mock_instance
            mock_class.return_value = mock_instance

        return mock_class

    patcher.side_effect = side_effect_for_getattr


async def assert_successful_item(item: MarketOverviewItem, symbol: str):
    assert item.symbol == symbol
    assert isinstance(item.current_price, float) and item.current_price > 0
    assert isinstance(item.ema_20, float) and item.ema_20 is not None
    assert isinstance(item.sma_50, float) and item.sma_50 is not None
    assert isinstance(item.support_levels, list) and len(item.support_levels) > 0
    assert isinstance(item.resistance_levels, list) and len(item.resistance_levels) > 0

async def assert_item_no_ta(item: MarketOverviewItem, symbol: str, expect_price: bool = True, expect_levels: bool = False):
    assert item.symbol == symbol
    if expect_price:
        assert isinstance(item.current_price, float) and item.current_price > 0
    else:
        assert item.current_price == 0.0
    assert item.ema_20 is None
    assert item.sma_50 is None
    if expect_levels:
        assert isinstance(item.support_levels, list) and len(item.support_levels) > 0
        assert isinstance(item.resistance_levels, list) and len(item.resistance_levels) > 0
    else:
        assert item.support_levels == []
        assert item.resistance_levels == []

async def test_get_market_overview_success(mock_ccxt_getattr_patcher, mock_exchange_factory):
    """All symbols, all exchanges successful with sufficient data."""
    ohlcv_config = {} # Default: all exchanges get 100 data points per symbol
    for conf in SYMBOL_CONFIG:
        ohlcv_config[conf["symbol"]] = generate_ohlcv_data(100, conf["symbol"])

    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config)

    results = await get_market_overview()
    assert len(results) == len(SYMBOL_CONFIG)
    for item in results:
        await assert_successful_item(item, item.symbol)

    for ex_id in created_exchange_mocks_for_test:
        created_exchange_mocks_for_test[ex_id].close.assert_awaited_once()

async def test_get_market_overview_insufficient_data_one_symbol(mock_ccxt_getattr_patcher, mock_exchange_factory):
    """One symbol has insufficient data, others are fine."""
    insufficient_symbol = "BTC/USDT" # Must be in SYMBOL_CONFIG
    ohlcv_config = {insufficient_symbol: "insufficient"}
    # Other symbols will get default sufficient data from configure_mock_getattr helper

    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config)
    results = await get_market_overview()

    assert len(results) == len(SYMBOL_CONFIG)
    for item in results:
        if item.symbol == insufficient_symbol:
            # Price and levels might be there if some data (even if insufficient for TA) exists
            await assert_item_no_ta(item, item.symbol, expect_price=True, expect_levels=True)
        else:
            await assert_successful_item(item, item.symbol)

    for ex_id in created_exchange_mocks_for_test:
        created_exchange_mocks_for_test[ex_id].close.assert_awaited_once()

async def test_get_market_overview_exchange_init_error_one_exchange(mock_ccxt_getattr_patcher, mock_exchange_factory):
    """One exchange fails to initialize, symbols from other exchanges are fine."""
    failing_exchange_id = "binance" # All symbols from this exchange will fail
    ohlcv_config = {f"init_{failing_exchange_id}": ccxt.ExchangeError("Simulated Binance init error")}

    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config)
    results = await get_market_overview()

    assert len(results) == len(SYMBOL_CONFIG)
    for item in results:
        config_item = next(s for s in SYMBOL_CONFIG if s["symbol"] == item.symbol)
        if config_item["exchange_id"] == failing_exchange_id:
            await assert_item_no_ta(item, item.symbol, expect_price=False, expect_levels=False)
        else: # Symbols from other exchanges (e.g. bitget)
            await assert_successful_item(item, item.symbol)

    for ex_id, mock_ex in created_exchange_mocks_for_test.items():
        if ex_id != failing_exchange_id:
            mock_ex.close.assert_awaited_once()
    assert failing_exchange_id not in created_exchange_mocks_for_test # Because init failed

async def test_get_market_overview_fetch_ticker_error_one_symbol(mock_ccxt_getattr_patcher, mock_exchange_factory):
    """fetch_ticker fails for one symbol. Price is 0, but TA might still run if OHLCV is fetched."""
    error_symbol = "ETH/USDT" # Must be in SYMBOL_CONFIG
    ohlcv_config = {
        f"ticker_{error_symbol}": ccxt.NetworkError("Simulated ticker error"),
        # All symbols (including error_symbol) get sufficient OHLCV by default for TA part
    }
    for conf in SYMBOL_CONFIG: # Ensure all symbols get data for OHLCV
        if conf["symbol"] not in ohlcv_config : # if not the erroring ticker
             ohlcv_config[conf["symbol"]] = generate_ohlcv_data(100, conf["symbol"])


    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config)
    results = await get_market_overview()

    assert len(results) == len(SYMBOL_CONFIG)
    for item in results:
        if item.symbol == error_symbol:
            assert item.current_price == 0.0
            # OHLCV was fetched successfully, so TA and levels should be there
            assert item.ema_20 is not None and isinstance(item.ema_20, float)
            assert item.sma_50 is not None and isinstance(item.sma_50, float)
            assert isinstance(item.support_levels, list) and len(item.support_levels) > 0
            assert isinstance(item.resistance_levels, list) and len(item.resistance_levels) > 0
        else:
            await assert_successful_item(item, item.symbol)

    for ex_id in created_exchange_mocks_for_test:
        created_exchange_mocks_for_test[ex_id].close.assert_awaited_once()

async def test_get_market_overview_fetch_ohlcv_error_one_symbol(mock_ccxt_getattr_patcher, mock_exchange_factory):
    """fetch_ohlcv fails for one symbol. Price is present, TA and levels are not."""
    error_symbol = "DOGE/USDT" # Must be in SYMBOL_CONFIG
    ohlcv_config = {error_symbol: ccxt.NetworkError("Simulated OHLCV error")}
    # Other symbols get default sufficient data

    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config)
    results = await get_market_overview()

    assert len(results) == len(SYMBOL_CONFIG)
    for item in results:
        if item.symbol == error_symbol:
            await assert_item_no_ta(item, item.symbol, expect_price=True, expect_levels=False)
        else:
            await assert_successful_item(item, item.symbol)

    for ex_id in created_exchange_mocks_for_test:
        created_exchange_mocks_for_test[ex_id].close.assert_awaited_once()

async def test_get_market_overview_ohlcv_empty_one_symbol(mock_ccxt_getattr_patcher, mock_exchange_factory):
    """fetch_ohlcv returns empty list for one symbol. Price present, TA/levels not."""
    empty_ohlcv_symbol = "SUI/USDT" # Must be in SYMBOL_CONFIG
    ohlcv_config = {empty_ohlcv_symbol: "empty"} # "empty" will make fetch_ohlcv return []
    # Other symbols get default sufficient data

    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config)
    results = await get_market_overview()

    assert len(results) == len(SYMBOL_CONFIG)
    for item in results:
        if item.symbol == empty_ohlcv_symbol:
            await assert_item_no_ta(item, item.symbol, expect_price=True, expect_levels=False)
        else:
            await assert_successful_item(item, item.symbol)

    for ex_id in created_exchange_mocks_for_test:
        created_exchange_mocks_for_test[ex_id].close.assert_awaited_once()


async def test_get_market_overview_no_symbols_configured():
    """SYMBOL_CONFIG is empty. Should return empty list, no HTTPException."""
    from src.routers import market_overview # Access the module to modify its global

    original_symbol_config_content = list(market_overview.SYMBOL_CONFIG)
    market_overview.SYMBOL_CONFIG.clear() # Modify the actual list used by the function

    results = await get_market_overview()
    assert results == []

    market_overview.SYMBOL_CONFIG.extend(original_symbol_config_content) # Restore


async def test_get_market_overview_all_symbols_fail_processing(mock_ccxt_getattr_patcher, mock_exchange_factory):
    """All symbols/exchanges fail at some point (e.g. all OHLCV fetches fail). Expect HTTPException 500."""
    if not SYMBOL_CONFIG: # Guard for this test
        pytest.skip("SYMBOL_CONFIG is empty, this test scenario is not applicable.")
        return

    # Configure all symbols to cause an OHLCV fetch error
    ohlcv_config = {}
    for conf in SYMBOL_CONFIG:
        ohlcv_config[conf["symbol"]] = ccxt.NetworkError(f"Simulated OHLCV error for {conf['symbol']}")

    configure_mock_getattr(mock_ccxt_getattr_patcher, mock_exchange_factory, ohlcv_config)

    with pytest.raises(HTTPException) as exc_info:
        await get_market_overview()

    assert exc_info.value.status_code == 500
    assert "Could not fetch any market data" in exc_info.value.detail

    for ex_id in created_exchange_mocks_for_test: # Close should still be called
        created_exchange_mocks_for_test[ex_id].close.assert_awaited_once()

async def test_get_market_overview_all_exchanges_init_fail(mock_ccxt_getattr_patcher, mock_exchange_factory):
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
    assert not created_exchange_mocks_for_test # No mocks should be created if init fails.
