import ccxt
import os
import logging
from sqlalchemy.orm import Session
from src.schemas.order_schema import OrderRequest, OrderCreate
from src.crud import orders as crud_orders
from src.database.models import Order # Required for the return type hint, and for CRUD to work with
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def place_order(order_data: OrderRequest, db: Session) -> Order:
    """
    Places an order on the specified exchange and records it in the database.
    """
    logger.info(f"Attempting to place order: {order_data.symbol} {order_data.side} {order_data.amount} @ {order_data.price or 'market'}")

    api_key_name = f"{order_data.exchange_id.upper()}_API_KEY"
    api_secret_name = f"{order_data.exchange_id.upper()}_API_SECRET"

    api_key = os.getenv(api_key_name)
    api_secret = os.getenv(api_secret_name)

    if not api_key or not api_secret:
        logger.error(f"API keys for {order_data.exchange_id} not found in environment variables.")
        # Create an OrderCreate schema with 'rejected' status
        order_to_save = OrderCreate(
            **order_data.model_dump(),
            status='rejected',
            # exchange_order_id will be None by default
        )
        # Persist this rejected order to the database
        db_order = crud_orders.create_order(db=db, order=order_to_save)
        return db_order

    try:
        exchange_class = getattr(ccxt, order_data.exchange_id)
        exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
        })
        if order_data.is_spot:
            exchange.options['defaultType'] = 'spot'
        else:
            # Note: For futures, ccxt might require 'future' or 'swap' or specific market types.
            # This might need adjustment based on the exchange and ccxt's handling.
            # Some exchanges also need `exchange.set_market_type_to_future()` or similar.
            exchange.options['defaultType'] = 'future'
            # Example: exchange.options['defaultMarket'] = 'future' # or 'swap'
            # Some exchanges like Binance need `{'type': 'future'}` in params for create_order
            # or specific methods like `create_future_order`.
            # For simplicity, using defaultType. Test thoroughly.

    except AttributeError:
        logger.error(f"Invalid exchange ID: {order_data.exchange_id}")
        order_to_save = OrderCreate(**order_data.model_dump(), status='rejected')
        db_order = crud_orders.create_order(db=db, order=order_to_save)
        return db_order
    except Exception as e: # Catch other ccxt initialization errors
        logger.error(f"Failed to initialize exchange {order_data.exchange_id}: {e}")
        order_to_save = OrderCreate(**order_data.model_dump(), status='rejected')
        db_order = crud_orders.create_order(db=db, order=order_to_save)
        return db_order

    params = {}
    if order_data.client_order_id:
        params['clientOrderId'] = order_data.client_order_id

    # For futures with Binance, you might need to specify {'type': 'future'} in params
    # if not using a specific futures method or if defaultType isn't enough.
    # if not order_data.is_spot and order_data.exchange_id == 'binance':
    #     params['type'] = 'future' # Or 'linear'/'inverse' based on symbol type

    ccxt_order_response = None
    try:
        logger.info(f"Sending order to {order_data.exchange_id}: {order_data.symbol} {order_data.type} {order_data.side} {order_data.amount} price: {order_data.price}")
        ccxt_order_response = await exchange.create_order(
            symbol=order_data.symbol,
            type=order_data.type,
            side=order_data.side,
            amount=order_data.amount,
            price=order_data.price, # Pass price; ccxt handles None for market orders
            params=params
        )
        logger.info(f"Order placed successfully on {order_data.exchange_id}. Response: {ccxt_order_response}")

        # Ensure timestamp is timezone-aware (UTC)
        order_timestamp = datetime.fromtimestamp(ccxt_order_response['timestamp'] / 1000, tz=timezone.utc) if ccxt_order_response.get('timestamp') else datetime.now(timezone.utc)

        # Prepare data for OrderCreate to avoid duplicate keyword arguments
        order_create_data = order_data.model_dump()
        order_create_data.update({
            'exchange_order_id': str(ccxt_order_response['id']),
            'symbol': ccxt_order_response.get('symbol', order_data.symbol), # Override symbol from exchange if available
            'timestamp': order_timestamp,
            'status': ccxt_order_response.get('status', 'open'),
            'filled_amount': ccxt_order_response.get('filled', 0.0),
            'remaining_amount': ccxt_order_response.get('remaining', order_data.amount - ccxt_order_response.get('filled', 0.0)),
            'cost': ccxt_order_response.get('cost', 0.0),
            'fee': ccxt_order_response.get('fee', {}).get('cost'),
            'fee_currency': ccxt_order_response.get('fee', {}).get('currency'),
        })
        # Fields from order_data like price, amount, side, type, user_id, is_spot are already in order_create_data
        # We need to ensure that the fields expected by OrderCreate are correctly populated.
        # OrderCreate schema: exchange_id, symbol, amount, side, type, price, user_id, is_spot, client_order_id
        # + exchange_order_id, status
        # The model_dump from OrderRequest (order_data) covers most base fields.
        # The update adds/overrides fields from the exchange response.

        order_to_save = OrderCreate(**order_create_data)

    except ccxt.InsufficientFunds as e:
        logger.error(f"Insufficient funds on {order_data.exchange_id} for order: {e}")
        order_to_save = OrderCreate(**order_data.model_dump(), status='rejected_insufficient_funds')
    except ccxt.NetworkError as e:
        logger.error(f"Network error communicating with {order_data.exchange_id}: {e}")
        order_to_save = OrderCreate(**order_data.model_dump(), status='rejected_network_error')
    except ccxt.ExchangeError as e: # More generic exchange error
        logger.error(f"Exchange error on {order_data.exchange_id}: {e}")
        order_to_save = OrderCreate(**order_data.model_dump(), status='rejected_exchange_error')
    except Exception as e: # Catch-all for other ccxt issues or unexpected errors
        logger.error(f"An unexpected error occurred while placing order on {order_data.exchange_id}: {e}", exc_info=True) # Added exc_info
        # Ensure order_to_save is defined for generic errors too
        order_data_dump = order_data.model_dump()
        # Remove fields not expected by OrderCreate if they are causing issues, though model_dump should be fine.
        # Relevant fields for OrderCreate are: exchange_id, symbol, amount, side, type, price, etc.
        # All should be in order_data.model_dump().
        order_to_save = OrderCreate(**order_data_dump, status='rejected_unknown_error')
    finally:
        # Close the exchange connection if possible/needed (ccxt handles this automatically for REST)
        # For async, it's good practice if the exchange object has an explicit close method.
        if hasattr(exchange, 'close'):
            await exchange.close()


    # Persist the order (successful or failed attempt) to the database
    db_order = crud_orders.create_order(db=db, order=order_to_save)
    logger.info(f"Order saved to DB with ID: {db_order.id} and status: {db_order.status}")

    return db_order

async def list_orders(
    db: Session,
    exchange_id: str | None = None,
    symbol: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0 # Renamed from skip to match common API parameter naming
) -> list[Order]:
    """
    Retrieves a list of orders based on specified filters and pagination.
    """
    logger.info(f"Listing orders with filters: exchange_id={exchange_id}, symbol={symbol}, status={status}, limit={limit}, offset={offset}")
    # Note: The CRUD function is synchronous, so we call it directly.
    # If it were async, we would 'await' it.
    orders = crud_orders.get_orders_with_filters(
        db=db,
        exchange_id=exchange_id,
        symbol=symbol,
        status=status,
        skip=offset, # Pass offset as skip to the CRUD function
        limit=limit
    )
    return orders
