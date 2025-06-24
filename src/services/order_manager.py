import ccxt
import os
import logging
from sqlalchemy.orm import Session
from src.schemas.order_schema import OrderRequest, OrderCreate
from src.crud import orders as crud_orders
from src.database.models import Order # Required for the return type hint, and for CRUD to work with
from datetime import datetime, timezone
from src.utils.api_key_manager import get_api_keys_from_env
from src.utils.exchange_helpers import (
    initialize_exchange,
    format_order_params,
    parse_exchange_response,
    safe_exchange_operation
)
from src.utils.error_handlers import handle_ccxt_exception, handle_generic_exception

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def place_order(order_data: OrderRequest, db: Session) -> Order:
    """
    Places an order on the specified exchange and records it in the database.
    """
    logger.info(f"Attempting to place order: {order_data.symbol} {order_data.side} {order_data.amount} @ {order_data.price or 'market'}")

    # Get API keys using helper
    api_key, api_secret = get_api_keys_from_env(order_data.exchange_id)

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
        # Initialize exchange using helper
        exchange = await initialize_exchange(
            exchange_id=order_data.exchange_id,
            api_key=api_key,
            api_secret=api_secret,
            is_spot=order_data.is_spot
        )

        # Format order parameters using helper
        order_params = format_order_params(
            order_type=order_data.type,
            side=order_data.side,
            amount=order_data.amount,
            symbol=order_data.symbol,
            price=order_data.price,
            client_order_id=order_data.client_order_id
        )

        # Use safe exchange operation with automatic cleanup
        async with safe_exchange_operation(exchange, "order placement", order_data.exchange_id, cleanup=False):
            logger.info(f"Sending order to {order_data.exchange_id}: {order_data.symbol} {order_data.type} {order_data.side} {order_data.amount} price: {order_data.price}")
            ccxt_order_response = await exchange.create_order(**order_params)
            logger.info(f"Order placed successfully on {order_data.exchange_id}. Response: {ccxt_order_response}")

            # Parse exchange response using helper
            parsed_data = parse_exchange_response(ccxt_order_response, order_data.model_dump())
            order_to_save = OrderCreate(**parsed_data)

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
