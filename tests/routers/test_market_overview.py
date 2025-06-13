import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from src.main import app # Assuming your FastAPI app instance is here
from src.routers.market_overview import MarketOverviewItem # Pydantic model
import ccxt.async_support as ccxt # Import for ccxt.ExchangeError

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# Mock Data
mock_btc_ticker = {'last': 50000.0, 'symbol': 'BTC/USDT'}
mock_btc_ohlcv = [
    [1672531200000, 48000, 52000, 47000, 50000, 1000], # timestamp, open, high, low, close, volume
] + [[1672531200000 + i*3600000, 50000 + i*10, 50100 + i*10, 49900 + i*10, 50050 + i*10, 100+i] for i in range(55)]

mock_eth_ticker = {'last': 4000.0, 'symbol': 'ETH/USDT'}
mock_eth_ohlcv = [
    [1672531200000, 3800, 4200, 3700, 4000, 2000],
] + [[1672531200000 + i*3600000, 4000 + i*5, 4010 + i*5, 3990 + i*5, 4005 + i*5, 150+i] for i in range(55)]

mock_doge_ticker = {'last': 0.15, 'symbol': 'DOGE/USDT'}
mock_doge_ohlcv = [[1672531200000 + i*3600000, 0.15 + i*0.001, 0.151+i*0.001, 0.149+i*0.001, 0.1505+i*0.001, 10000+i*100] for i in range(10)] # Only 10 data points


@pytest_asyncio.fixture
async def mock_ccxt_exchange():
    mock_exchange_instance = AsyncMock()

    async def mock_fetch_ticker(symbol, **kwargs):
        if symbol == "BTC/USDT":
            return mock_btc_ticker
        elif symbol == "ETH/USDT":
            return mock_eth_ticker
        elif symbol == "DOGE/USDT":
            return mock_doge_ticker
        elif symbol in ["SUI/USDT", "POPCAT/USDT", "HYPE/USDT"]:
            raise ccxt.ExchangeError(f"Symbol {symbol} not found or data unavailable")
        return {}

    async def mock_fetch_ohlcv(symbol, timeframe, limit, **kwargs):
        if symbol == "BTC/USDT":
            return mock_btc_ohlcv
        elif symbol == "ETH/USDT":
            return mock_eth_ohlcv
        elif symbol == "DOGE/USDT":
            return mock_doge_ohlcv
        elif symbol in ["SUI/USDT", "POPCAT/USDT", "HYPE/USDT"]:
            return []
        return []

    mock_exchange_instance.fetch_ticker = AsyncMock(side_effect=mock_fetch_ticker)
    mock_exchange_instance.fetch_ohlcv = AsyncMock(side_effect=mock_fetch_ohlcv)
    mock_exchange_instance.close = AsyncMock()

    # Patching getattr(ccxt, 'binance') implicitly
    # The router uses: exchange_class = getattr(ccxt, exchange_id) where exchange_id = 'binance'
    # So we patch 'ccxt.async_support.binance' which is what getattr will retrieve.
    with patch('ccxt.async_support.binance', return_value=mock_exchange_instance) as mock_constructor:
        # Ensure the constructor returns our mocked instance
        mock_constructor.return_value = mock_exchange_instance
        yield mock_exchange_instance


@pytest.mark.asyncio
async def test_get_market_overview_success(client, mock_ccxt_exchange):
    response = client.get("/market/market-overview/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 6

    symbols_processed = [item['symbol'] for item in response_data]
    assert "BTC/USDT" in symbols_processed
    assert "ETH/USDT" in symbols_processed
    assert "DOGE/USDT" in symbols_processed
    assert "SUI/USDT" in symbols_processed
    assert "POPCAT/USDT" in symbols_processed
    assert "HYPE/USDT" in symbols_processed

    for item_data in response_data:
        MarketOverviewItem(**item_data) # Validate Pydantic model compliance

        assert "symbol" in item_data
        assert "current_price" in item_data
        assert "ema_20" in item_data
        assert "sma_50" in item_data
        assert "support_levels" in item_data
        assert "resistance_levels" in item_data
        assert isinstance(item_data["support_levels"], list)
        assert isinstance(item_data["resistance_levels"], list)

        if item_data["symbol"] == "BTC/USDT":
            assert item_data["current_price"] == 50000.0
            assert item_data["ema_20"] is not None
            assert item_data["sma_50"] is not None
            assert len(item_data["support_levels"]) <= 5
            assert len(item_data["resistance_levels"]) <= 5
            if item_data["support_levels"]:
                assert item_data["support_levels"] == sorted(item_data["support_levels"])
            if item_data["resistance_levels"]:
                assert item_data["resistance_levels"] == sorted(item_data["resistance_levels"])

        if item_data["symbol"] == "DOGE/USDT":
            assert item_data["current_price"] == 0.15
            assert item_data["ema_20"] is None
            assert item_data["sma_50"] is None
            assert len(item_data["support_levels"]) <= 5
            assert len(item_data["resistance_levels"]) <= 5
            if mock_doge_ohlcv:
                all_lows = sorted([d[3] for d in mock_doge_ohlcv])
                all_highs = sorted([d[2] for d in mock_doge_ohlcv], reverse=True) # nlargest means descending
                assert item_data["support_levels"] == all_lows[:5]
                # nlargest(5) means the 5 biggest values, then sorted by the endpoint
                # The endpoint sorts them: sorted(df['high'].nlargest(5).tolist())
                # So, we mimic that:
                expected_resistance = sorted(all_highs[:5]) if len(all_highs) >=5 else sorted(all_highs)
                assert item_data["resistance_levels"] == expected_resistance


        if item_data["symbol"] in ["SUI/USDT", "POPCAT/USDT", "HYPE/USDT"]:
            assert item_data["current_price"] == 0.0
            assert item_data["ema_20"] is None
            assert item_data["sma_50"] is None
            assert item_data["support_levels"] == []
            assert item_data["resistance_levels"] == []

    mock_ccxt_exchange.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_market_overview_all_symbols_fail(client):
    mock_exchange_instance = AsyncMock()
    # Simulate ccxt.ExchangeError for fetch_ticker for all symbols
    mock_exchange_instance.fetch_ticker = AsyncMock(side_effect=ccxt.ExchangeError("Simulated exchange error for all tickers"))
    # fetch_ohlcv can also raise an error or return empty, error is more direct for this test
    mock_exchange_instance.fetch_ohlcv = AsyncMock(side_effect=ccxt.ExchangeError("Simulated exchange error for all OHLCV"))
    mock_exchange_instance.close = AsyncMock()

    with patch('ccxt.async_support.binance', return_value=mock_exchange_instance) as mock_constructor:
        mock_constructor.return_value = mock_exchange_instance
        response = client.get("/market/market-overview/")

        assert response.status_code == 200 # Endpoint handles errors gracefully per symbol
        response_data = response.json()
        assert len(response_data) == 6 # SYMBOLS has 6 items

        for item in response_data:
            MarketOverviewItem(**item) # Validate Pydantic model compliance
            assert item['current_price'] == 0.0 # Default error value
            assert item['ema_20'] is None
            assert item['sma_50'] is None
            assert item['support_levels'] == []
            assert item['resistance_levels'] == []

        mock_exchange_instance.close.assert_awaited_once()
