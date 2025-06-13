import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from src.main import app
from src.routers.market_overview import MarketOverviewItem
import ccxt.base.errors as ccxt_errors # For ccxt.ExchangeError

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# Mock Data (Module Level)
# BTC (Binance)
mock_btc_ticker = {'last': 50000.0, 'symbol': 'BTC/USDT'}
mock_btc_ohlcv = [[1672531200000 + i*3600000, 50000 + i*10, 50100 + i*10, 49900 + i*10, 50050 + i*10, 100+i] for i in range(55)]

# ETH (Binance)
mock_eth_ticker = {'last': 4000.0, 'symbol': 'ETH/USDT'}
mock_eth_ohlcv = [[1672531200000 + i*3600000, 4000 + i*5, 4010 + i*5, 3990 + i*5, 4005 + i*5, 150+i] for i in range(55)]

# DOGE (Binance - less data)
mock_doge_ticker = {'last': 0.15, 'symbol': 'DOGE/USDT'}
mock_doge_ohlcv = [[1672531200000 + i*3600000, 0.15 + i*0.001, 0.151+i*0.001, 0.149+i*0.001, 0.1505+i*0.001, 10000+i*100] for i in range(10)]

# POPCAT (Bitget)
mock_popcat_ticker = {'last': 0.005, 'symbol': 'POPCAT/USDT'}
mock_popcat_ohlcv = [[1672531200000 + i*3600000, 0.005 + i*0.0001, 0.0051+i*0.0001, 0.0049+i*0.0001, 0.00505+i*0.0001, 100000+i*1000] for i in range(55)]

# HYPE (Bitget)
mock_hype_ticker = {'last': 0.1, 'symbol': 'HYPE/USDT'}
mock_hype_ohlcv = [[1672531200000 + i*3600000, 0.1 + i*0.001, 0.101+i*0.001, 0.099+i*0.001, 0.1005+i*0.001, 50000+i*500] for i in range(55)]


@pytest.mark.asyncio
async def test_get_market_overview_success(client):
    mock_binance_exchange_instance = AsyncMock(name='mock_binance_exchange')
    mock_bitget_exchange_instance = AsyncMock(name='mock_bitget_exchange')

    async def mock_binance_fetch_ticker(symbol, **kwargs):
        if symbol == "BTC/USDT": return mock_btc_ticker
        if symbol == "ETH/USDT": return mock_eth_ticker
        if symbol == "DOGE/USDT": return mock_doge_ticker
        if symbol == "SUI/USDT": raise ccxt_errors.ExchangeError(f"Mock: {symbol} not found on Binance")
        return {}

    async def mock_binance_fetch_ohlcv(symbol, timeframe, limit, **kwargs):
        if symbol == "BTC/USDT": return mock_btc_ohlcv
        if symbol == "ETH/USDT": return mock_eth_ohlcv
        if symbol == "DOGE/USDT": return mock_doge_ohlcv
        if symbol == "SUI/USDT": return []
        return []

    mock_binance_exchange_instance.fetch_ticker = AsyncMock(side_effect=mock_binance_fetch_ticker)
    mock_binance_exchange_instance.fetch_ohlcv = AsyncMock(side_effect=mock_binance_fetch_ohlcv)
    mock_binance_exchange_instance.close = AsyncMock()
    # Add id attribute for logging in the endpoint
    mock_binance_exchange_instance.id = 'binance'


    async def mock_bitget_fetch_ticker(symbol, **kwargs):
        if symbol == "POPCAT/USDT": return mock_popcat_ticker
        if symbol == "HYPE/USDT": return mock_hype_ticker
        raise ccxt_errors.ExchangeError(f"Mock: {symbol} not found on Bitget")

    async def mock_bitget_fetch_ohlcv(symbol, timeframe, limit, **kwargs):
        if symbol == "POPCAT/USDT": return mock_popcat_ohlcv
        if symbol == "HYPE/USDT": return mock_hype_ohlcv
        return []

    mock_bitget_exchange_instance.fetch_ticker = AsyncMock(side_effect=mock_bitget_fetch_ticker)
    mock_bitget_exchange_instance.fetch_ohlcv = AsyncMock(side_effect=mock_bitget_fetch_ohlcv)
    mock_bitget_exchange_instance.close = AsyncMock()
    # Add id attribute for logging in the endpoint
    mock_bitget_exchange_instance.id = 'bitget'

    # Patch target assumes 'import ccxt.async_support as ccxt' in market_overview.py
    # and then calls ccxt.binance() and ccxt.bitget()
    with patch('src.routers.market_overview.ccxt.binance', return_value=mock_binance_exchange_instance) as mock_binance_init, \
         patch('src.routers.market_overview.ccxt.bitget', return_value=mock_bitget_exchange_instance) as mock_bitget_init:

        response = client.get("/market/market-overview/")

        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 6

        symbols_processed = {item['symbol']: item for item in response_data}
        for item_symbol in symbols_processed:
            MarketOverviewItem(**symbols_processed[item_symbol]) # Validate Pydantic

        # BTC (Binance)
        assert symbols_processed["BTC/USDT"]["current_price"] == mock_btc_ticker['last']
        assert symbols_processed["BTC/USDT"]["ema_20"] is not None
        assert symbols_processed["BTC/USDT"]["sma_50"] is not None

        # ETH (Binance)
        assert symbols_processed["ETH/USDT"]["current_price"] == mock_eth_ticker['last']
        assert symbols_processed["ETH/USDT"]["ema_20"] is not None
        assert symbols_processed["ETH/USDT"]["sma_50"] is not None

        # DOGE (Binance - less data)
        assert symbols_processed["DOGE/USDT"]["current_price"] == mock_doge_ticker['last']
        assert symbols_processed["DOGE/USDT"]["ema_20"] is None
        assert symbols_processed["DOGE/USDT"]["sma_50"] is None

        # SUI (Binance - simulated error/no data)
        assert symbols_processed["SUI/USDT"]["current_price"] == 0.0
        assert symbols_processed["SUI/USDT"]["ema_20"] is None
        assert symbols_processed["SUI/USDT"]["sma_50"] is None
        assert symbols_processed["SUI/USDT"]["support_levels"] == []
        assert symbols_processed["SUI/USDT"]["resistance_levels"] == []

        # POPCAT (Bitget)
        assert symbols_processed["POPCAT/USDT"]["current_price"] == mock_popcat_ticker['last']
        assert symbols_processed["POPCAT/USDT"]["ema_20"] is not None
        assert symbols_processed["POPCAT/USDT"]["sma_50"] is not None

        # HYPE (Bitget)
        assert symbols_processed["HYPE/USDT"]["current_price"] == mock_hype_ticker['last']
        assert symbols_processed["HYPE/USDT"]["ema_20"] is not None
        assert symbols_processed["HYPE/USDT"]["sma_50"] is not None

        mock_binance_exchange_instance.close.assert_awaited_once()
        mock_bitget_exchange_instance.close.assert_awaited_once()

        mock_binance_init.assert_called_once()
        mock_bitget_init.assert_called_once()

@pytest.mark.asyncio
async def test_get_market_overview_all_symbols_fail(client):
    mock_error_binance_exchange = AsyncMock(name='mock_error_binance')
    mock_error_binance_exchange.fetch_ticker = AsyncMock(side_effect=ccxt_errors.ExchangeError("Binance mock ticker error"))
    mock_error_binance_exchange.fetch_ohlcv = AsyncMock(side_effect=ccxt_errors.ExchangeError("Binance mock ohlcv error"))
    mock_error_binance_exchange.close = AsyncMock()
    mock_error_binance_exchange.id = 'binance'


    mock_error_bitget_exchange = AsyncMock(name='mock_error_bitget')
    mock_error_bitget_exchange.fetch_ticker = AsyncMock(side_effect=ccxt_errors.ExchangeError("Bitget mock ticker error"))
    mock_error_bitget_exchange.fetch_ohlcv = AsyncMock(side_effect=ccxt_errors.ExchangeError("Bitget mock ohlcv error"))
    mock_error_bitget_exchange.close = AsyncMock()
    mock_error_bitget_exchange.id = 'bitget'

    with patch('src.routers.market_overview.ccxt.binance', return_value=mock_error_binance_exchange) as mock_binance_init, \
         patch('src.routers.market_overview.ccxt.bitget', return_value=mock_error_bitget_exchange) as mock_bitget_init:

        response = client.get("/market/market-overview/")
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 6
        for item in response_data:
            MarketOverviewItem(**item) # Validate Pydantic
            assert item['current_price'] == 0.0
            assert item['ema_20'] is None
            assert item['sma_50'] is None
            assert item['support_levels'] == []
            assert item['resistance_levels'] == []

        mock_error_binance_exchange.close.assert_awaited_once()
        mock_error_bitget_exchange.close.assert_awaited_once()

        mock_binance_init.assert_called_once()
        mock_bitget_init.assert_called_once()
