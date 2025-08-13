import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from src.main import app # Import your FastAPI app
from config.config import Settings, get_settings

# Using pytest-asyncio for async tests
pytestmark = pytest.mark.asyncio


@patch('src.routers.exchange.fetch_ohlcv_service', new_callable=AsyncMock)
async def test_get_ohlcv_success(mock_fetch_ohlcv_service, client):
    test_client, test_settings = client
    mock_fetch_ohlcv_service.return_value = [[1672531200000, 20000, 20100, 19900, 20050, 100]]
    response = test_client.get("/api/v1/exchange/ohlcv?exchange_id=binance&symbol=BTC/USDT&timeframe=1h&limit=1")
    assert response.status_code == 200
    assert response.json() == [[1672531200000, 20000, 20100, 19900, 20050, 100]]
    mock_fetch_ohlcv_service.assert_called_once_with(
        exchange_id='binance',
        symbol='BTC/USDT',
        timeframe='1h',
        limit=1,
        api_key=test_settings.BINANCE_API_KEY,
        api_secret=test_settings.BINANCE_API_SECRET
    )

@patch('src.routers.exchange.fetch_ohlcv_service', new_callable=AsyncMock)
async def test_get_ohlcv_with_explicit_keys(mock_fetch_ohlcv_service, client):
    test_client, _ = client
    mock_fetch_ohlcv_service.return_value = [[1672531200000, 1, 2, 0.5, 1.5, 10]]
    response = test_client.get("/api/v1/exchange/ohlcv?exchange_id=custom_exchange&symbol=ETH/BTC&api_key=explicit_key&api_secret=explicit_secret")
    assert response.status_code == 200
    mock_fetch_ohlcv_service.assert_called_once_with(
        exchange_id='custom_exchange',
        symbol='ETH/BTC',
        timeframe='4h',
        limit=100,
        api_key='explicit_key',
        api_secret='explicit_secret'
    )

@patch('src.routers.exchange.fetch_ohlcv_service', new_callable=AsyncMock)
async def test_get_ohlcv_service_http_exception(mock_fetch_ohlcv_service, client):
    test_client, _ = client
    from fastapi import HTTPException
    mock_fetch_ohlcv_service.side_effect = HTTPException(status_code=404, detail="Symbol not found on exchange")
    response = test_client.get("/api/v1/exchange/ohlcv?exchange_id=binance&symbol=NONEXISTENT/USDT")
    assert response.status_code == 404
    assert response.json() == {"detail": "Symbol not found on exchange"}

@patch('src.routers.exchange.fetch_balance_service', new_callable=AsyncMock)
async def test_get_balance_success_with_explicit_keys(mock_fetch_balance_service, client):
    test_client, _ = client
    mock_fetch_balance_service.return_value = {'total': {'USD': 1000}}
    response = test_client.get("/api/v1/exchange/balance?exchange_id=binance&api_key=key_from_query&api_secret=secret_from_query")
    assert response.status_code == 200
    mock_fetch_balance_service.assert_called_once_with(
        exchange_id='binance',
        api_key='key_from_query',
        api_secret='secret_from_query'
    )

@patch('src.routers.exchange.fetch_balance_service', new_callable=AsyncMock)
async def test_get_balance_success_with_settings_keys(mock_fetch_balance_service, client):
    test_client, test_settings = client
    mock_fetch_balance_service.return_value = {'total': {'USD': 5000}}
    response = test_client.get("/api/v1/exchange/balance?exchange_id=binance")
    assert response.status_code == 200
    mock_fetch_balance_service.assert_called_once_with(
        exchange_id='binance',
        api_key=test_settings.BINANCE_API_KEY,
        api_secret=test_settings.BINANCE_API_SECRET
    )

@patch('src.routers.exchange.fetch_balance_service', new_callable=AsyncMock)
async def test_get_balance_missing_keys(mock_fetch_balance_service, client):
    test_client, _ = client
    response = test_client.get("/api/v1/exchange/balance?exchange_id=no_keys_exchange")
    assert response.status_code == 400
    assert "API key and secret are required" in response.json()["detail"]
    mock_fetch_balance_service.assert_not_called()

# The health endpoint is async
async def test_health_endpoint(client):
    test_client, _ = client
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "AR Trading API is running"}
