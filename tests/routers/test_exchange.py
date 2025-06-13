import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from src.main import app # Import your FastAPI app
from config.config import Settings, get_settings

# Using pytest-asyncio for async tests
pytestmark = pytest.mark.asyncio

@pytest.fixture
def test_settings_fixture():
    # This fixture provides a consistent Settings object for tests
    return Settings(
        DATABASE_URL="sqlite:///:memory:", # Example: Use in-memory db for tests
        EXCHANGE_API_KEY="global_test_key",
        EXCHANGE_API_SECRET="global_test_secret",
        BINANCE_API_KEY="binance_test_key_from_settings",
        BINANCE_API_SECRET="binance_test_secret_from_settings",
        COINBASEPRO_API_KEY=None,
        COINBASEPRO_API_SECRET=None,
        COINBASEPRO_PASSWORD=None
    )

@pytest.fixture
def client(test_settings_fixture):
    # Override the get_settings dependency for tests
    app.dependency_overrides[get_settings] = lambda: test_settings_fixture
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {} # Clean up

@patch('src.services.trading_api.fetch_ohlcv', new_callable=AsyncMock)
async def test_get_ohlcv_success(mock_fetch_ohlcv, client, test_settings_fixture):
    mock_fetch_ohlcv.return_value = [[1672531200000, 20000, 20100, 19900, 20050, 100]]
    response = client.get("/api/v1/exchange/ohlcv?exchange_id=binance&symbol=BTC/USDT&timeframe=1h&limit=1")
    assert response.status_code == 200
    assert response.json() == [[1672531200000, 20000, 20100, 19900, 20050, 100]]
    mock_fetch_ohlcv.assert_called_once_with(
        exchange_id='binance',
        symbol='BTC/USDT',
        timeframe='1h',
        limit=1,
        api_key=test_settings_fixture.BINANCE_API_KEY,
        api_secret=test_settings_fixture.BINANCE_API_SECRET
    )

@patch('src.services.trading_api.fetch_ohlcv', new_callable=AsyncMock)
async def test_get_ohlcv_with_explicit_keys(mock_fetch_ohlcv, client):
    mock_fetch_ohlcv.return_value = [[1672531200000, 1, 2, 0.5, 1.5, 10]]
    response = client.get("/api/v1/exchange/ohlcv?exchange_id=custom_exchange&symbol=ETH/BTC&api_key=explicit_key&api_secret=explicit_secret")
    assert response.status_code == 200
    mock_fetch_ohlcv.assert_called_once_with(
        exchange_id='custom_exchange',
        symbol='ETH/BTC',
        timeframe='1h',
        limit=100,
        api_key='explicit_key',
        api_secret='explicit_secret'
    )

@patch('src.services.trading_api.fetch_ohlcv', new_callable=AsyncMock)
async def test_get_ohlcv_service_http_exception(mock_fetch_ohlcv, client):
    from fastapi import HTTPException
    mock_fetch_ohlcv.side_effect = HTTPException(status_code=404, detail="Symbol not found on exchange")
    response = client.get("/api/v1/exchange/ohlcv?exchange_id=binance&symbol=NONEXISTENT/USDT")
    assert response.status_code == 404
    assert response.json() == {"detail": "Symbol not found on exchange"}

@patch('src.services.trading_api.fetch_balance', new_callable=AsyncMock)
async def test_get_balance_success_with_explicit_keys(mock_fetch_balance, client):
    mock_fetch_balance.return_value = {'total': {'USD': 1000}}
    response = client.get("/api/v1/exchange/balance?exchange_id=binance&api_key=key_from_query&api_secret=secret_from_query")
    assert response.status_code == 200
    mock_fetch_balance.assert_called_once_with(
        exchange_id='binance',
        api_key='key_from_query',
        api_secret='secret_from_query'
    )

@patch('src.services.trading_api.fetch_balance', new_callable=AsyncMock)
async def test_get_balance_success_with_settings_keys(mock_fetch_balance, client, test_settings_fixture):
    mock_fetch_balance.return_value = {'total': {'USD': 5000}}
    response = client.get("/api/v1/exchange/balance?exchange_id=binance")
    assert response.status_code == 200
    mock_fetch_balance.assert_called_once_with(
        exchange_id='binance',
        api_key=test_settings_fixture.BINANCE_API_KEY,
        api_secret=test_settings_fixture.BINANCE_API_SECRET
    )

@patch('src.services.trading_api.fetch_balance', new_callable=AsyncMock)
async def test_get_balance_missing_keys(mock_fetch_balance, client):
    # This test assumes 'no_keys_exchange' does not have keys in test_settings_fixture
    response = client.get("/api/v1/exchange/balance?exchange_id=no_keys_exchange")
    assert response.status_code == 400
    assert "API key and secret are required" in response.json()["detail"]
    mock_fetch_balance.assert_not_called()

# Synchronous test for a synchronous endpoint
def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
