import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from src.main import app # app is needed for TestClient, but not used directly in patch
from src.schemas.order_schema import OrderRequest, OrderResponse # For type hints and validation
from src.database.models import Order # For mock service return types

# Use the test_client fixture defined in conftest.py
# Use the db_session fixture if direct DB manipulation is needed in a test,
# but for API tests, we mostly mock the service layer.

# Mark all tests in this file as asyncio if they directly use async features (not common for TestClient usage)
# However, the underlying service calls are async, so pytest-asyncio might be relevant if not using @patch for services.
# For these tests, we are patching the service, so direct asyncio marking per test is not strictly needed.

@patch('src.services.order_manager.place_order', new_callable=AsyncMock)
def test_place_order_api_success(mock_place_order_service, test_client: TestClient):
    # Prepare mock service response
    # The service returns a SQLAlchemy Order model instance
    mock_order_db = Order(
        id=1,
        exchange_id="binance",
        symbol="BTC/USDT",
        amount=1.0,
        side="buy",
        type="limit",
        price=30000.0,
        user_id=1,
        is_spot=True,
        client_order_id="test_client_id_001",
        exchange_order_id="exchange_order_id_001",
        timestamp=datetime.now(timezone.utc),
        status="open", # Successful status
        filled_amount=0.0,
        remaining_amount=1.0,
        cost=0.0, # (price * filled_amount)
        fee=0.0,
        fee_currency="USDT"
    )
    mock_place_order_service.return_value = mock_order_db

    # Prepare request payload
    order_payload = {
        "exchange_id": "binance",
        "symbol": "BTC/USDT",
        "amount": 1.0,
        "side": "buy",
        "type": "limit",
        "price": 30000.0,
        "user_id": 1,
        "is_spot": True,
        "client_order_id": "test_client_id_001"
    }

    response = test_client.post("/api/v1/orders/place", json=order_payload)

    assert response.status_code == 201
    response_data = response.json()

    # Validate some key fields in the response
    assert response_data["id"] == mock_order_db.id
    assert response_data["exchange_id"] == mock_order_db.exchange_id
    assert response_data["symbol"] == mock_order_db.symbol
    assert response_data["status"] == "open"
    assert response_data["exchange_order_id"] == "exchange_order_id_001"

    # Ensure the service was called with correct data (OrderRequest schema)
    # The first argument to the mock is 'order_data', the second is 'db'
    # call_args[0] is a tuple of positional args, call_args[1] is a dict of kwargs
    # In our case, place_order is called with order_data=order_request, db=db_session
    # So, order_data is a keyword argument.
    service_call_args = mock_place_order_service.call_args
    assert service_call_args is not None
    called_with_order_request = service_call_args.kwargs['order_data'] # or args[0] if positional

    assert isinstance(called_with_order_request, OrderRequest)
    assert called_with_order_request.symbol == order_payload["symbol"]
    assert called_with_order_request.price == order_payload["price"]


def test_place_order_api_validation_error(test_client: TestClient):
    # Limit order missing price
    order_payload = {
        "exchange_id": "binance",
        "symbol": "BTC/USDT",
        "amount": 1.0,
        "side": "buy",
        "type": "limit", # Price is required for limit order
        # "price": 30000.0, # Missing price
        "user_id": 1,
        "is_spot": True
    }
    response = test_client.post("/api/v1/orders/place", json=order_payload)
    assert response.status_code == 422 # FastAPI validation error
    # Optionally, check the detail of the error
    # response_data = response.json()
    # assert "price" in response_data["detail"][0]["loc"] # Example check

@patch('src.services.order_manager.place_order', new_callable=AsyncMock)
def test_place_order_api_insufficient_funds(mock_place_order_service, test_client: TestClient):
    # Mock service to return an order with 'rejected_insufficient_funds' status
    mock_order_db_rejected = Order(
        id=2,
        exchange_id="binance",
        symbol="BTC/USDT",
        amount=1.0,
        side="buy",
        type="limit",
        price=30000.0,
        user_id=1,
        is_spot=True,
        timestamp=datetime.now(timezone.utc),
        status="rejected_insufficient_funds", # Critical for this test
        # Other fields as necessary...
        filled_amount=0.0,
        remaining_amount=1.0, # Or amount, as per model logic for rejections
        cost=0.0
    )
    mock_place_order_service.return_value = mock_order_db_rejected

    order_payload = {
        "exchange_id": "binance",
        "symbol": "BTC/USDT",
        "amount": 1.0,
        "side": "buy",
        "type": "limit",
        "price": 30000.0,
        "user_id": 1,
        "is_spot": True
    }
    response = test_client.post("/api/v1/orders/place", json=order_payload)

    # As per the router's error handling for 'rejected_insufficient_funds' status:
    assert response.status_code == 400
    response_data = response.json()
    assert "Order rejected due to insufficient funds" in response_data["detail"]


@patch('src.services.order_manager.place_order', new_callable=AsyncMock)
def test_place_order_api_generic_rejection(mock_place_order_service, test_client: TestClient):
    # Mock service to return an order with a generic 'rejected' status
    mock_order_db_rejected = Order(
        id=3,
        exchange_id="binance",
        symbol="BTC/USDT",
        amount=1.0,
        side="buy",
        type="market", # Market order
        user_id=1,
        is_spot=True,
        timestamp=datetime.now(timezone.utc),
        status="rejected_some_other_reason", # Generic rejection
        filled_amount=0.0,
        remaining_amount=1.0,
        cost=0.0
    )
    mock_place_order_service.return_value = mock_order_db_rejected

    order_payload = {
        "exchange_id": "binance",
        "symbol": "BTC/USDT",
        "amount": 1.0,
        "side": "buy",
        "type": "market",
        "user_id": 1,
        "is_spot": True
    }
    response = test_client.post("/api/v1/orders/place", json=order_payload)

    assert response.status_code == 400 # As per router's handling of "rejected" in status
    response_data = response.json()
    assert "Order placement failed or was rejected" in response_data["detail"]
    assert "Status: rejected_some_other_reason" in response_data["detail"]

# Example of testing ccxt exception handling if the service re-raises it
# and the router catches it.
@patch('src.services.order_manager.place_order', new_callable=AsyncMock)
def test_place_order_api_ccxt_exchange_error(mock_place_order_service, test_client: TestClient):
    # Mock service to raise a ccxt.ExchangeError
    # This simulates the service not catching the error, or re-raising it.
    # The API router has try-except blocks for these.
    mock_place_order_service.side_effect = ccxt.ExchangeError("Exchange specific error message")

    order_payload = {
        "exchange_id": "binance",
        "symbol": "BTC/USDT",
        "amount": 1.0,
        "side": "buy",
        "type": "market",
        "user_id": 1,
        "is_spot": True
    }
    response = test_client.post("/api/v1/orders/place", json=order_payload)

    assert response.status_code == 400 # Or 502, depending on router's mapping
    response_data = response.json()
    assert "Exchange error with binance: Exchange specific error message" in response_data["detail"]
