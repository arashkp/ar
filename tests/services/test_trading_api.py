import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from src.services.trading_api import initialize_exchange, fetch_ohlcv, fetch_balance
import ccxt.async_support as ccxt

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_ccxt_exchange_class():
    mock_exchange_instance = AsyncMock()
    mock_exchange_instance.has = {'fetchOHLCV': True, 'fetchBalance': True}
    mock_exchange_instance.load_markets = AsyncMock(return_value={'BTC/USDT': {}})
    mock_exchange_instance.fetch_ohlcv = AsyncMock(return_value=[[1672531200000, 100, 110, 90, 105, 1000]])
    mock_exchange_instance.fetch_balance = AsyncMock(return_value={'free': {'USDT': 1000}})
    mock_exchange_instance.close = AsyncMock()

    mock_class = MagicMock(return_value=mock_exchange_instance)
    return mock_class, mock_exchange_instance

async def test_initialize_exchange_success(mock_ccxt_exchange_class):
    mock_class, _ = mock_ccxt_exchange_class
    with patch.object(ccxt, 'binance', mock_class): # Patching 'binance' as an example
        exchange = await initialize_exchange('binance', 'key', 'secret')
        assert exchange is not None
        mock_class.assert_called_once_with({'apiKey': 'key', 'secret': 'secret', 'enableRateLimit': True})
        await exchange.close() # Ensure close is called if successful init

async def test_initialize_exchange_not_found():
    with pytest.raises(HTTPException) as exc_info:
        await initialize_exchange('unknownexchange')
    assert exc_info.value.status_code == 400
    assert "Exchange unknownexchange not found" in exc_info.value.detail

async def test_initialize_exchange_auth_error(mock_ccxt_exchange_class):
    mock_class, mock_instance = mock_ccxt_exchange_class
    # To trigger load_markets or similar call that ccxt might do internally on init,
    # or if initialize_exchange itself calls it:
    # For this test, let's assume the error happens during the ccxt.exchange_class() call
    mock_class.side_effect = ccxt.AuthenticationError("auth failed")
    with patch.object(ccxt, 'binance', mock_class):
        with pytest.raises(HTTPException) as exc_info:
            await initialize_exchange('binance', 'key', 'secret')
    assert exc_info.value.status_code == 401
    assert "Authentication failed for binance" in exc_info.value.detail

async def test_fetch_ohlcv_success(mock_ccxt_exchange_class):
    mock_class, mock_instance = mock_ccxt_exchange_class
    with patch.object(ccxt, 'binance', mock_class):
        ohlcv = await fetch_ohlcv('binance', 'BTC/USDT', '1h', 1)
        assert ohlcv == [[1672531200000, 100, 110, 90, 105, 1000]]
        mock_instance.load_markets.assert_called_once()
        mock_instance.fetch_ohlcv.assert_called_once_with('BTC/USDT', timeframe='1h', limit=1)
        mock_instance.close.assert_called_once()

async def test_fetch_ohlcv_exchange_does_not_support(mock_ccxt_exchange_class):
    mock_class, mock_instance = mock_ccxt_exchange_class
    mock_instance.has['fetchOHLCV'] = False
    with patch.object(ccxt, 'binance', mock_class):
        with pytest.raises(HTTPException) as exc_info:
            await fetch_ohlcv('binance', 'BTC/USDT')
    assert exc_info.value.status_code == 501
    assert "does not support fetching OHLCV data" in exc_info.value.detail
    mock_instance.close.assert_called_once()

async def test_fetch_ohlcv_symbol_not_available(mock_ccxt_exchange_class):
    mock_class, mock_instance = mock_ccxt_exchange_class
    mock_instance.load_markets = AsyncMock(return_value={'ETH/USDT': {}}) # BTC/USDT not in markets
    with patch.object(ccxt, 'binance', mock_class):
        with pytest.raises(HTTPException) as exc_info:
            await fetch_ohlcv('binance', 'BTC/USDT')
    assert exc_info.value.status_code == 400
    assert "Symbol BTC/USDT not available" in exc_info.value.detail
    mock_instance.close.assert_called_once()

async def test_fetch_balance_success(mock_ccxt_exchange_class):
    mock_class, mock_instance = mock_ccxt_exchange_class
    with patch.object(ccxt, 'binance', mock_class):
        balance = await fetch_balance('binance', 'key', 'secret')
        assert balance == {'free': {'USDT': 1000}}
        mock_instance.fetch_balance.assert_called_once()
        mock_instance.close.assert_called_once()

async def test_fetch_balance_no_keys():
    with pytest.raises(HTTPException) as exc_info:
        await fetch_balance('binance', None, None)
    assert exc_info.value.status_code == 400
    assert "API key and secret are required" in exc_info.value.detail

async def test_fetch_balance_auth_error(mock_ccxt_exchange_class):
    mock_class, mock_instance = mock_ccxt_exchange_class
    mock_instance.fetch_balance = AsyncMock(side_effect=ccxt.AuthenticationError("auth failed"))
    with patch.object(ccxt, 'binance', mock_class):
        with pytest.raises(HTTPException) as exc_info:
            await fetch_balance('binance', 'key', 'secret')
    assert exc_info.value.status_code == 401
    assert "Authentication failed for binance when fetching balance" in exc_info.value.detail
    mock_instance.close.assert_called_once()
