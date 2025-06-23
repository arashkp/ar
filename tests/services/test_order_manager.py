import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import ccxt # Keep this for the ccxt.X exceptions in the service code if not fully mocked
import ccxt as actual_ccxt # Import the real ccxt module for its exception classes
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
    # crud_orders.create_order is called with keyword arguments: create_order(db=db, order=order_to_save)
    assert mock_crud_create_order.call_count == 1
    called_kwargs = mock_crud_create_order.call_args.kwargs
    assert 'db' in called_kwargs
    assert 'order' in called_kwargs
    order_create_arg = called_kwargs['order']
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
    # Fields like price and amount are already in rejected_order_create_data.
    mock_db_order_rejected = Order(id=2, **rejected_order_create_data)

    mock_crud_create_order.return_value = mock_db_order_rejected

    # Configure mock_ccxt to use actual exception classes from ccxt
    # This ensures that `isinstance(e, ccxt.InsufficientFunds)` works as expected in the service code.
    mock_ccxt.InsufficientFunds = actual_ccxt.InsufficientFunds
    mock_ccxt.NetworkError = actual_ccxt.NetworkError
    mock_ccxt.ExchangeError = actual_ccxt.ExchangeError

    result_order = await place_order(order_data=sample_order_request, db=mock_db_session)

    mock_exchange_instance.create_order.assert_called_once()

    # Check call to crud_orders.create_order
    assert mock_crud_create_order.call_count == 1
    called_kwargs = mock_crud_create_order.call_args.kwargs
    assert 'db' in called_kwargs
    assert 'order' in called_kwargs
    order_create_arg = called_kwargs['order']
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
    # Fields like price and amount are already in rejected_order_data.
    mock_db_order_no_keys = Order(id=3, **rejected_order_data)
    mock_crud_create_order.return_value = mock_db_order_no_keys

    result_order = await place_order(order_data=sample_order_request, db=mock_db_session)

    assert mock_crud_create_order.call_count == 1
    called_kwargs = mock_crud_create_order.call_args.kwargs
    assert 'db' in called_kwargs
    assert 'order' in called_kwargs
    order_create_arg = called_kwargs['order']
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
@patch('src.services.order_manager.ccxt', spec=actual_ccxt) # Use spec for mock_ccxt
async def test_place_order_invalid_exchange_id(
    mock_ccxt, mock_crud_create_order, mock_os_getenv, sample_order_request, mock_db_session
):
    mock_os_getenv.side_effect = lambda key: "dummy_key" # API keys are found

    # Modify the exchange_id in a copy of the request for this specific test case
    # to ensure it's an ID that spec'd mock_ccxt won't have.
    test_order_request = sample_order_request.model_copy(deep=True)
    test_order_request.exchange_id = "invalidexchangenamefortest"

    # Because mock_ccxt is spec'd with actual_ccxt, trying to getattr(mock_ccxt, "invalidexchangenamefortest")
    # will raise an AttributeError, which is caught by the service.

    # We might need to ensure that any valid exchanges (like 'binance' if used by other parts of code indirectly)
    # are still available on mock_ccxt if the spec is too strict or if ccxt loads them dynamically.
    # However, for this specific path, the AttributeError should occur first.
    # If 'binance' (original sample_order_request.exchange_id) was needed for other mocks,
    # it should be explicitly set up on mock_ccxt if spec removes it.
    # For this test, we assume 'invalidexchangenamefortest' is what we're testing the failure for.

    rejected_order_data = test_order_request.model_dump() # Use the modified request
    rejected_order_data.update({'status': 'rejected', 'exchange_order_id': None})
    mock_db_order_rejected = Order(id=4, **rejected_order_data)
    mock_crud_create_order.return_value = mock_db_order_rejected

    result_order = await place_order(order_data=test_order_request, db=mock_db_session) # Use test_order_request

    # Check call to crud_orders.create_order
    assert mock_crud_create_order.call_count == 1
    called_kwargs = mock_crud_create_order.call_args.kwargs
    assert 'db' in called_kwargs
    assert 'order' in called_kwargs
    order_create_arg = called_kwargs['order']
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

    # Ensure mock_ccxt uses real ccxt exceptions
    mock_ccxt.InsufficientFunds = actual_ccxt.InsufficientFunds
    mock_ccxt.NetworkError = actual_ccxt.NetworkError
    mock_ccxt.ExchangeError = actual_ccxt.ExchangeError

    mock_exchange_instance = AsyncMock()
    # Use the actual_ccxt for raising the error in the test's side_effect
    mock_exchange_instance.create_order.side_effect = actual_ccxt.NetworkError("Connection failed")
    mock_exchange_instance.close = AsyncMock()

    mock_exchange_class = MagicMock(return_value=mock_exchange_instance)
    setattr(mock_ccxt, sample_order_request.exchange_id, mock_exchange_class)

    rejected_order_data = sample_order_request.model_dump()
    rejected_order_data.update({'status': 'rejected_network_error', 'exchange_order_id': None})
    # Fields like price and amount are already in rejected_order_data.
    mock_db_order_rejected = Order(id=5, **rejected_order_data)
    mock_crud_create_order.return_value = mock_db_order_rejected

    result_order = await place_order(order_data=sample_order_request, db=mock_db_session)

    assert mock_crud_create_order.call_count == 1
    called_kwargs = mock_crud_create_order.call_args.kwargs
    assert 'db' in called_kwargs
    assert 'order' in called_kwargs
    order_create_arg = called_kwargs['order']
    assert isinstance(order_create_arg, OrderCreate)
    assert order_create_arg.status == 'rejected_network_error'
    assert result_order.status == 'rejected_network_error'


# Test for list_orders service function
@patch('src.services.order_manager.crud_orders.get_orders_with_filters')
async def test_list_orders(mock_get_orders_with_filters, mock_db_session):
    # Import list_orders here to avoid issues with module-level patches if not careful
    from src.services.order_manager import list_orders

    # Sample filter parameters
    exchange_id = "binance"
    symbol = "BTC/USDT"
    status = "filled"
    limit = 50
    offset = 0

    # Mocked return value from the CRUD function
    mock_order_1 = Order(id=1, exchange_id=exchange_id, symbol=symbol, status=status, price=30000, amount=1)
    mock_order_2 = Order(id=2, exchange_id=exchange_id, symbol=symbol, status=status, price=31000, amount=0.5)
    mocked_orders_list = [mock_order_1, mock_order_2]

    mock_get_orders_with_filters.return_value = mocked_orders_list

    # Call the service function
    result = await list_orders(
        db=mock_db_session,
        exchange_id=exchange_id,
        symbol=symbol,
        status=status,
        limit=limit,
        offset=offset
    )

    # Assert that the CRUD function was called with the correct parameters
    mock_get_orders_with_filters.assert_called_once_with(
        db=mock_db_session,
        exchange_id=exchange_id,
        symbol=symbol,
        status=status,
        skip=offset, # Ensure 'offset' is correctly passed as 'skip'
        limit=limit
    )

    # Assert that the service function returned the expected result
    assert result == mocked_orders_list
    assert len(result) == 2
    assert result[0].id == 1
    assert result[1].symbol == symbol

@patch('src.services.order_manager.crud_orders.get_orders_with_filters')
async def test_list_orders_no_filters(mock_get_orders_with_filters, mock_db_session):
    from src.services.order_manager import list_orders
    # Test with no optional filters
    limit = 100
    offset = 0

    mocked_orders_list = [Order(id=i, price=100*i, amount=i) for i in range(3)] # Dummy orders
    mock_get_orders_with_filters.return_value = mocked_orders_list

    result = await list_orders(db=mock_db_session, limit=limit, offset=offset)

    mock_get_orders_with_filters.assert_called_once_with(
        db=mock_db_session,
        exchange_id=None, # Expect None for optional params not provided
        symbol=None,
        status=None,
        skip=offset,
        limit=limit
    )
    assert result == mocked_orders_list
