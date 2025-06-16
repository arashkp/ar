import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import ccxt
from src.schemas.order_schema import OrderRequest, OrderCreate
from src.services.order_manager import place_order
from src.database.models import Order
from src.crud import orders as crud_orders # So we can mock its create_order method

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def sample_order_request():
    return OrderRequest(
        exchange_id="binance",
        symbol="BTC/USDT",
        amount=1.0,
        side="buy",
        type="limit",
        price=30000.0,
        user_id=1,
        is_spot=True,
        client_order_id="test_client_order_id_123"
    )

@pytest.fixture
def mock_db_session():
    return MagicMock()

@patch('src.services.order_manager.os.getenv')
@patch('src.services.order_manager.crud_orders.create_order')
@patch('src.services.order_manager.ccxt')
async def test_place_order_success(mock_ccxt, mock_crud_create_order, mock_os_getenv, sample_order_request, mock_db_session):
    mock_os_getenv.side_effect = lambda key: "dummy_key" if "API_KEY" in key or "API_SECRET" in key else None

    mock_exchange_instance = AsyncMock()
    mock_ccxt_order_response = {
        'id': 'exchange_order_123',
        'clientOrderId': sample_order_request.client_order_id,
        'timestamp': datetime.now(timezone.utc).timestamp() * 1000, # ccxt usually provides ms
        'datetime': datetime.now(timezone.utc).isoformat(),
        'status': 'open',
        'symbol': sample_order_request.symbol,
        'type': sample_order_request.type,
        'side': sample_order_request.side,
        'price': sample_order_request.price,
        'amount': sample_order_request.amount,
        'filled': 0.0,
        'remaining': sample_order_request.amount,
        'cost': 0.0,
        'fee': {'cost': 0.0, 'currency': 'USDT'},
        'info': {} # Actual exchange info
    }
    mock_exchange_instance.create_order.return_value = mock_ccxt_order_response
    mock_exchange_instance.close = AsyncMock() # Ensure close is an async mock if called with await

    # Setup getattr(ccxt, exchange_id) to return a mock class, which when called, returns our instance
    mock_exchange_class = MagicMock(return_value=mock_exchange_instance)
    mock_ccxt.binance = mock_exchange_class # Assuming exchange_id is 'binance'
    # More generic way if exchange_id can vary:
    setattr(mock_ccxt, sample_order_request.exchange_id, mock_exchange_class)


    mock_db_order = Order(
        id=1, exchange_order_id='exchange_order_123', status='open', **sample_order_request.model_dump()
    )
    mock_crud_create_order.return_value = mock_db_order

    result_order = await place_order(order_data=sample_order_request, db=mock_db_session)

    mock_exchange_class.assert_called_once_with({
        'apiKey': 'dummy_key',
        'secret': 'dummy_key',
    })
    mock_exchange_instance.create_order.assert_called_once_with(
        symbol=sample_order_request.symbol,
        type=sample_order_request.type,
        side=sample_order_request.side,
        amount=sample_order_request.amount,
        price=sample_order_request.price,
        params={'clientOrderId': sample_order_request.client_order_id}
    )

    # Check that crud_orders.create_order was called with an OrderCreate object
    # that has the correct attributes derived from the ccxt response
    call_args = mock_crud_create_order.call_args[0] # Get positional arguments
    assert len(call_args) == 2 # db, order
    order_create_arg = call_args[1]
    assert isinstance(order_create_arg, OrderCreate)
    assert order_create_arg.exchange_order_id == 'exchange_order_123'
    assert order_create_arg.status == 'open'
    assert order_create_arg.filled_amount == 0.0
    assert order_create_arg.cost == 0.0

    assert result_order == mock_db_order
    assert result_order.status == 'open'

@patch('src.services.order_manager.os.getenv')
@patch('src.services.order_manager.crud_orders.create_order')
@patch('src.services.order_manager.ccxt')
async def test_place_order_insufficient_funds(mock_ccxt, mock_crud_create_order, mock_os_getenv, sample_order_request, mock_db_session):
    mock_os_getenv.side_effect = lambda key: "dummy_key" if "API_KEY" in key or "API_SECRET" in key else None

    mock_exchange_instance = AsyncMock()
    mock_exchange_instance.create_order.side_effect = ccxt.InsufficientFunds("Not enough balance")
    mock_exchange_instance.close = AsyncMock()

    mock_exchange_class = MagicMock(return_value=mock_exchange_instance)
    setattr(mock_ccxt, sample_order_request.exchange_id, mock_exchange_class)

    # crud_orders.create_order should still be called, but with a rejected status
    # The Order model's __init__ will calculate cost and remaining_amount
    # from price and amount if they are present in the OrderCreate schema.
    # For a rejected order, these might be 0 or based on original request.
    # The OrderCreate passed to crud will have status='rejected_insufficient_funds'.
    # The Order model returned by crud will reflect this.

    # Simulate the Order object that crud_orders.create_order would return
    # based on an OrderCreate schema with status 'rejected_insufficient_funds'
    rejected_order_create_data = sample_order_request.model_dump()
    rejected_order_create_data.update({
        'status': 'rejected_insufficient_funds',
        'exchange_order_id': None, # No exchange ID for rejected order
        # timestamp will be set by OrderCreate or the DB model
    })
    # cost and remaining_amount are calculated by Order model's __init__
    # For OrderCreate, they are not explicitly set unless they are part of the schema.
    # Our OrderCreate does not have them, so Order model's defaults/calculations apply.
    mock_db_order_rejected = Order(id=2, **rejected_order_create_data, price=sample_order_request.price, amount=sample_order_request.amount)

    mock_crud_create_order.return_value = mock_db_order_rejected

    result_order = await place_order(order_data=sample_order_request, db=mock_db_session)

    mock_exchange_instance.create_order.assert_called_once()

    call_args = mock_crud_create_order.call_args[0]
    order_create_arg = call_args[1]
    assert isinstance(order_create_arg, OrderCreate)
    assert order_create_arg.status == 'rejected_insufficient_funds'

    assert result_order.status == 'rejected_insufficient_funds'

@patch('src.services.order_manager.os.getenv')
@patch('src.services.order_manager.crud_orders.create_order')
async def test_place_order_no_api_keys(mock_crud_create_order, mock_os_getenv, sample_order_request, mock_db_session):
    mock_os_getenv.return_value = None # Simulate no API keys found

    # Prepare data for the Order object that crud_orders.create_order would return
    # This simulates the OrderCreate object being converted to an Order model
    rejected_order_data = sample_order_request.model_dump()
    rejected_order_data.update({
        'status': 'rejected', # Default rejection status when keys are missing
        'exchange_order_id': None,
        # cost and remaining_amount will be calculated by Order model's __init__
    })
    mock_db_order_no_keys = Order(id=3, **rejected_order_data, price=sample_order_request.price, amount=sample_order_request.amount)
    mock_crud_create_order.return_value = mock_db_order_no_keys

    result_order = await place_order(order_data=sample_order_request, db=mock_db_session)

    call_args = mock_crud_create_order.call_args[0]
    order_create_arg = call_args[1]
    assert isinstance(order_create_arg, OrderCreate)
    assert order_create_arg.status == 'rejected'

    assert result_order.status == 'rejected'
    assert mock_os_getenv.call_count >= 2 # Checked for KEY and SECRET

# TODO: Add tests for NetworkError, ExchangeError, invalid exchange ID, etc.
# For example, test_place_order_network_error:
# mock_exchange_instance.create_order.side_effect = ccxt.NetworkError("Connection timeout")
# ... assert status 'rejected_network_error'

# Test for invalid exchange ID
@patch('src.services.order_manager.os.getenv')
@patch('src.services.order_manager.crud_orders.create_order')
@patch('src.services.order_manager.ccxt') # To control how getattr(ccxt, exchange_id) behaves
async def test_place_order_invalid_exchange_id(mock_ccxt, mock_crud_create_order, mock_os_getenv, sample_order_request, mock_db_session):
    mock_os_getenv.side_effect = lambda key: "dummy_key" # API keys are found

    # Simulate ccxt not having the exchange_id attribute
    # Note: sample_order_request.exchange_id is 'binance'
    # To simulate it being invalid, we make getattr(mock_ccxt, 'binance') raise AttributeError
    mock_ccxt.configure_mock(**{sample_order_request.exchange_id: None}) # Remove attribute
    # A more direct way to simulate getattr raising AttributeError:
    # mock_ccxt.getattr.side_effect = AttributeError
    # However, ccxt itself is a module, so we mock the dynamic access:
    # We need to make sure that when `getattr(ccxt, sample_order_request.exchange_id)` is called, it fails.
    # If `sample_order_request.exchange_id` is 'binance', then `mock_ccxt.binance` would be accessed.
    # If `mock_ccxt.binance` itself is a MagicMock, accessing an attribute on it by default returns another MagicMock.
    # To make it act like the attribute doesn't exist on the ccxt module:
    delattr(mock_ccxt, sample_order_request.exchange_id) # This might not work as expected if mock_ccxt is already a MagicMock
                                                        # and sample_order_request.exchange_id is one of its children.
                                                        # A better way for MagicMock:
    # mock_ccxt.attach_mock(MagicMock(side_effect=AttributeError), sample_order_request.exchange_id)
    # For this test, let's make the __getattr__ of mock_ccxt raise an error for the specific exchange
    def mock_getattr(name):
        if name == sample_order_request.exchange_id:
            raise AttributeError(f"Exchange '{name}' not found in ccxt")
        return MagicMock() # Default behavior for other attributes
    mock_ccxt.__getattr__ = mock_getattr


    rejected_order_data = sample_order_request.model_dump()
    rejected_order_data.update({'status': 'rejected', 'exchange_order_id': None})
    mock_db_order_rejected = Order(id=4, **rejected_order_data, price=sample_order_request.price, amount=sample_order_request.amount)
    mock_crud_create_order.return_value = mock_db_order_rejected

    result_order = await place_order(order_data=sample_order_request, db=mock_db_session)

    call_args = mock_crud_create_order.call_args[0]
    order_create_arg = call_args[1]
    assert isinstance(order_create_arg, OrderCreate)
    assert order_create_arg.status == 'rejected'

    assert result_order.status == 'rejected'

    # Ensure ccxt.exchange_class was not called if getattr failed
    # This is implicitly tested by mock_crud_create_order being called with 'rejected' status
    # (as the exchange init block would be skipped).
    # mock_exchange_class.assert_not_called() if mock_exchange_class was defined.
    # In this specific mock setup for getattr, this assertion is harder.
    # The key is that the status is 'rejected' due to early exit.

    # Reset __getattr__ if mock_ccxt is used in other tests to avoid interference
    del mock_ccxt.__getattr__

# Example for NetworkError
@patch('src.services.order_manager.os.getenv')
@patch('src.services.order_manager.crud_orders.create_order')
@patch('src.services.order_manager.ccxt')
async def test_place_order_network_error(mock_ccxt, mock_crud_create_order, mock_os_getenv, sample_order_request, mock_db_session):
    mock_os_getenv.side_effect = lambda key: "dummy_key"

    mock_exchange_instance = AsyncMock()
    mock_exchange_instance.create_order.side_effect = ccxt.NetworkError("Connection failed")
    mock_exchange_instance.close = AsyncMock()

    mock_exchange_class = MagicMock(return_value=mock_exchange_instance)
    setattr(mock_ccxt, sample_order_request.exchange_id, mock_exchange_class)

    rejected_order_data = sample_order_request.model_dump()
    rejected_order_data.update({'status': 'rejected_network_error', 'exchange_order_id': None})
    mock_db_order_rejected = Order(id=5, **rejected_order_data, price=sample_order_request.price, amount=sample_order_request.amount)
    mock_crud_create_order.return_value = mock_db_order_rejected

    result_order = await place_order(order_data=sample_order_request, db=mock_db_session)

    call_args = mock_crud_create_order.call_args[0]
    order_create_arg = call_args[1]
    assert isinstance(order_create_arg, OrderCreate)
    assert order_create_arg.status == 'rejected_network_error'
    assert result_order.status == 'rejected_network_error'
