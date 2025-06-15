import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import ExitStack
import ccxt.base.errors as ccxt_errors

from src.main import app
from src.routers.market_overview import MarketOverviewItem, SYMBOL_CONFIG # Import SYMBOL_CONFIG

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# Mock Data (Module Level - ensure these cover symbols in SYMBOL_CONFIG)
mock_btc_ticker = {'last': 50000.0, 'symbol': 'BTC/USDT'}
mock_btc_ohlcv = [[1672531200000 + i*3600000, 50000 + i*10, 50100 + i*10, 49900 + i*10, 50050 + i*10, 100+i] for i in range(55)]

mock_eth_ticker = {'last': 4000.0, 'symbol': 'ETH/USDT'}
mock_eth_ohlcv = [[1672531200000 + i*3600000, 4000 + i*5, 4010 + i*5, 3990 + i*5, 4005 + i*5, 150+i] for i in range(55)]

mock_doge_ticker = {'last': 0.15, 'symbol': 'DOGE/USDT'}
mock_doge_ohlcv = [[1672531200000 + i*3600000, 0.15 + i*0.001, 0.151+i*0.001, 0.149+i*0.001, 0.1505+i*0.001, 10000+i*100] for i in range(10)] # Less data

mock_sui_ticker = {'last': 1.0, 'symbol': 'SUI/USDT'} # Example for SUI if it were to succeed
mock_sui_ohlcv = [[1672531200000 + i*3600000, 1.0 + i*0.01, 1.01+i*0.01, 0.99+i*0.01, 1.005+i*0.01, 10000+i*100] for i in range(55)]


mock_popcat_ticker = {'last': 0.005, 'symbol': 'POPCAT/USDT'}
mock_popcat_ohlcv = [[1672531200000 + i*3600000, 0.005 + i*0.0001, 0.0051+i*0.0001, 0.0049+i*0.0001, 0.00505+i*0.0001, 100000+i*1000] for i in range(55)]

mock_hype_ticker = {'last': 0.1, 'symbol': 'HYPE/USDT'}
mock_hype_ohlcv = [[1672531200000 + i*3600000, 0.1 + i*0.001, 0.101+i*0.001, 0.099+i*0.001, 0.1005+i*0.001, 50000+i*500] for i in range(55)]


@pytest.mark.asyncio
async def test_get_market_overview_success(client):

    def create_mock_exchange(exchange_id_for_mock):
        mock_exchange = AsyncMock(name=f'mock_{exchange_id_for_mock}_exchange')
        mock_exchange.id = exchange_id_for_mock # For logging in endpoint

        async def _dynamic_fetch_ticker(symbol, **kwargs):
            if symbol == "BTC/USDT": return mock_btc_ticker
            if symbol == "ETH/USDT": return mock_eth_ticker
            if symbol == "DOGE/USDT": return mock_doge_ticker
            if symbol == "POPCAT/USDT": return mock_popcat_ticker
            if symbol == "HYPE/USDT": return mock_hype_ticker
            if symbol == "SUI/USDT": # Simulate SUI failing for ticker on its designated exchange (binance)
                if exchange_id_for_mock == 'binance':
                     raise ccxt_errors.ExchangeError(f"Mock: Ticker for {symbol} not found on {exchange_id_for_mock}")
                else: # If SUI was on another exchange in a different test.
                    return mock_sui_ticker
            print(f"Unhandled symbol in mock_fetch_ticker for {exchange_id_for_mock}: {symbol}")
            raise ccxt_errors.ExchangeError(f"Mock: Unhandled ticker symbol {symbol} for {exchange_id_for_mock}")

        async def _dynamic_fetch_ohlcv(symbol, timeframe, limit, **kwargs):
            if symbol == "BTC/USDT": return mock_btc_ohlcv
            if symbol == "ETH/USDT": return mock_eth_ohlcv
            if symbol == "DOGE/USDT": return mock_doge_ohlcv
            if symbol == "POPCAT/USDT": return mock_popcat_ohlcv
            if symbol == "HYPE/USDT": return mock_hype_ohlcv
            if symbol == "SUI/USDT": # Simulate SUI failing for OHLCV on its designated exchange
                 if exchange_id_for_mock == 'binance':
                    return []
                 else:
                    return mock_sui_ohlcv
            print(f"Unhandled symbol in mock_fetch_ohlcv for {exchange_id_for_mock}: {symbol}")
            return []

        mock_exchange.fetch_ticker = AsyncMock(side_effect=_dynamic_fetch_ticker)
        mock_exchange.fetch_ohlcv = AsyncMock(side_effect=_dynamic_fetch_ohlcv)
        mock_exchange.close = AsyncMock()
        return mock_exchange

    unique_exchange_ids = set(item['exchange_id'] for item in SYMBOL_CONFIG)
    mock_exchange_class_constructors = {}
    active_mock_exchange_instances = {}

    for ex_id in unique_exchange_ids:
        instance = create_mock_exchange(ex_id)
        active_mock_exchange_instances[ex_id] = instance
        # This mock will be returned when `getattr(ccxt, ex_id)` is called,
        # and then `()` is called on it (the constructor).
        mock_exchange_class_constructors[ex_id] = MagicMock(return_value=instance)

    patchers = []
    # The patch target is `src.routers.market_overview.ccxt.{exchange_id}`.
    # This assumes in market_overview.py: `import ccxt.async_support as ccxt`
    # then `exchange_class = getattr(ccxt, exchange_id)` which means `ccxt.binance`, `ccxt.bitget` etc. are accessed.
    for ex_id, constructor_mock in mock_exchange_class_constructors.items():
        patchers.append(patch(f'src.routers.market_overview.ccxt.{ex_id}', constructor_mock))

    with ExitStack() as stack:
        for p in patchers:
            stack.enter_context(p)

        response = client.get("/market/market-overview/")
        assert response.status_code == 200
        response_data = response.json()

        assert len(response_data) == len(SYMBOL_CONFIG)
        response_map = {item['symbol']: item for item in response_data}

        for config_item in SYMBOL_CONFIG:
            symbol = config_item['symbol']
            exchange_id = config_item['exchange_id']
            assert symbol in response_map
            item_data = response_map[symbol]
            MarketOverviewItem(**item_data) # Validate Pydantic

            assert "current_price" in item_data
            assert "ema_20" in item_data
            assert "sma_50" in item_data
            assert "support_levels" in item_data
            assert "resistance_levels" in item_data

            if symbol == "BTC/USDT":
                assert item_data["current_price"] == mock_btc_ticker['last']
                assert item_data["ema_20"] is not None
                assert item_data["sma_50"] is not None
            elif symbol == "POPCAT/USDT":
                assert item_data["current_price"] == mock_popcat_ticker['last']
                assert item_data["ema_20"] is not None
                assert item_data["sma_50"] is not None
            elif symbol == "DOGE/USDT": # Less data
                assert item_data["current_price"] == mock_doge_ticker['last']
                assert item_data["ema_20"] is None
                assert item_data["sma_50"] is None
            elif symbol == "SUI/USDT": # Simulated failure for SUI on Binance
                assert item_data["current_price"] == 0.0
                assert item_data["ema_20"] is None
                assert item_data["sma_50"] is None
                assert item_data["support_levels"] == []

        for ex_id in unique_exchange_ids:
            active_mock_exchange_instances[ex_id].close.assert_awaited()
            mock_exchange_class_constructors[ex_id].assert_called()


@pytest.mark.asyncio
async def test_get_market_overview_all_symbols_fail(client):
    def create_error_mock_exchange(exchange_id_for_mock):
        mock_exchange = AsyncMock(name=f'mock_error_{exchange_id_for_mock}_exchange')
        mock_exchange.id = exchange_id_for_mock
        # Simulate failure at the fetch_ticker level for all symbols on this exchange
        mock_exchange.fetch_ticker = AsyncMock(side_effect=ccxt_errors.ExchangeError(f"Mock E_FAIL Ticker {exchange_id_for_mock}"))
        # fetch_ohlcv might not even be called if fetch_ticker fails hard, but good to define behavior
        mock_exchange.fetch_ohlcv = AsyncMock(side_effect=ccxt_errors.ExchangeError(f"Mock E_FAIL OHLCV {exchange_id_for_mock}"))
        mock_exchange.close = AsyncMock()
        return mock_exchange

    unique_exchange_ids = set(item['exchange_id'] for item in SYMBOL_CONFIG)
    mock_exchange_class_constructors = {}
    active_mock_error_instances = {}

    for ex_id in unique_exchange_ids:
        instance = create_error_mock_exchange(ex_id)
        active_mock_error_instances[ex_id] = instance
        mock_exchange_class_constructors[ex_id] = MagicMock(return_value=instance)

    patchers = []
    for ex_id, constructor_mock in mock_exchange_class_constructors.items():
         patchers.append(patch(f'src.routers.market_overview.ccxt.{ex_id}', constructor_mock))

    with ExitStack() as stack:
        for p in patchers:
            stack.enter_context(p)

        response = client.get("/market/market-overview/")
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == len(SYMBOL_CONFIG)

        for item in response_data:
            MarketOverviewItem(**item) # Validate Pydantic
            assert item['current_price'] == 0.0
            assert item['ema_20'] is None
            assert item['sma_50'] is None
            assert item['support_levels'] == []
            assert item['resistance_levels'] == []

        for ex_id in unique_exchange_ids:
            active_mock_error_instances[ex_id].close.assert_awaited()
            mock_exchange_class_constructors[ex_id].assert_called()
