import ccxt
import os
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException
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
from src.services.mexc_service import MEXCService

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

    # Route MEXC orders to dedicated service
    if order_data.exchange_id.lower() == 'mexc':
        return await _place_mexc_order(order_data, api_key, api_secret, db)
    else:
        return await _place_ccxt_order(order_data, api_key, api_secret, db)


async def _place_mexc_order(order_data: OrderRequest, api_key: str, api_secret: str, db: Session) -> Order:
    """
    Place order using MEXC SDK.
    """
    try:
        logger.info(f"Using MEXC SDK for order placement")
        
        # Initialize MEXC service
        mexc_service = MEXCService(api_key=api_key, api_secret=api_secret)
        
        # Place order using MEXC SDK
        mexc_response = await mexc_service.place_order(
            symbol=order_data.symbol,
            side=order_data.side,
            order_type=order_data.type,
            quantity=order_data.amount,
            price=order_data.price,
            client_order_id=order_data.client_order_id
        )
        
        logger.info(f"MEXC order placed successfully: {mexc_response}")
        
        # Parse MEXC response
        parsed_data = mexc_service.parse_order_response(mexc_response, order_data.model_dump())
        order_to_save = OrderCreate(**parsed_data)
        
        # Save to database
        db_order = crud_orders.create_order(db=db, order=order_to_save)
        logger.info(f"MEXC order saved to database with ID: {db_order.id}")
        
        return db_order
        
    except HTTPException:
        # Re-raise HTTPException directly
        raise
    except Exception as e:
        logger.error(f"Unexpected error placing MEXC order: {e}")
        # Create rejected order
        order_to_save = OrderCreate(
            **order_data.model_dump(),
            status='rejected',
        )
        db_order = crud_orders.create_order(db=db, order=order_to_save)
        return db_order


async def _place_ccxt_order(order_data: OrderRequest, api_key: str, api_secret: str, db: Session) -> Order:
    """
    Place order using CCXT (for non-MEXC exchanges).
    """
    try:
        # Initialize exchange using helper
        logger.info(f"About to initialize exchange for {order_data.exchange_id}...")
        exchange = await initialize_exchange(
            exchange_id=order_data.exchange_id,
            api_key=api_key,
            api_secret=api_secret,
            is_spot=order_data.is_spot
        )
        logger.info(f"Exchange initialized successfully for {order_data.exchange_id}")
        logger.info(f"Exchange API key configured: {bool(exchange.apiKey)}")
        logger.info(f"Exchange secret configured: {bool(exchange.secret)}")
        logger.info(f"Exchange options: {getattr(exchange, 'options', {})}")

        # Format order parameters using helper
        logger.info(f"About to format order parameters...")
        order_params = format_order_params(
            order_type=order_data.type,
            side=order_data.side,
            amount=order_data.amount,
            symbol=order_data.symbol,
            price=order_data.price,
            client_order_id=order_data.client_order_id
        )
        logger.info(f"Order parameters formatted successfully")

        # Use safe exchange operation with automatic cleanup
        logger.info(f"About to enter safe_exchange_operation context...")
        async with safe_exchange_operation(exchange, "order placement", order_data.exchange_id, cleanup=False):
            logger.info(f"Inside safe_exchange_operation context")
            logger.info(f"Sending order to {order_data.exchange_id}: {order_data.symbol} {order_data.type} {order_data.side} {order_data.amount} price: {order_data.price}")
            logger.info(f"Full order parameters: {order_params}")
            logger.info(f"About to call exchange.create_order()...")
            
            try:
                logger.info(f"Calling exchange.create_order() with timeout...")
                import asyncio
                
                # Add timeout to prevent hanging
                ccxt_order_response = await asyncio.wait_for(
                    exchange.create_order(**order_params),
                    timeout=30.0  # 30 second timeout
                )
                logger.info(f"Order placed successfully on {order_data.exchange_id}. Response: {ccxt_order_response}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout error: exchange.create_order() took longer than 30 seconds")
                raise Exception("Order placement timed out - request took longer than 30 seconds")
            except Exception as e:
                logger.error(f"Error during exchange.create_order() call: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error details: {str(e)}")
                raise
            
            # Parse exchange response using helper
            parsed_data = parse_exchange_response(ccxt_order_response, order_data.model_dump())
            order_to_save = OrderCreate(**parsed_data)

            # Save to database
            db_order = crud_orders.create_order(db=db, order=order_to_save)
            logger.info(f"Order saved to database with ID: {db_order.id}")

            return db_order

    except ccxt.InsufficientFunds as e:
        logger.error(f"Insufficient funds on {order_data.exchange_id}: {e}")
        # Create an OrderCreate schema with 'rejected_insufficient_funds' status
        order_to_save = OrderCreate(
            **order_data.model_dump(),
            status='rejected_insufficient_funds',
        )
        # Persist this rejected order to the database
        db_order = crud_orders.create_order(db=db, order=order_to_save)
        return db_order
    except ccxt.NetworkError as e:
        logger.error(f"Network error with {order_data.exchange_id}: {e}")
        # Create an OrderCreate schema with 'rejected_network_error' status
        order_to_save = OrderCreate(
            **order_data.model_dump(),
            status='rejected_network_error',
        )
        # Persist this rejected order to the database
        db_order = crud_orders.create_order(db=db, order=order_to_save)
        return db_order
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error with {order_data.exchange_id}: {e}")
        # Create an OrderCreate schema with 'rejected_exchange_error' status
        order_to_save = OrderCreate(
            **order_data.model_dump(),
            status='rejected_exchange_error',
        )
        # Persist this rejected order to the database
        db_order = crud_orders.create_order(db=db, order=order_to_save)
        return db_order
    except Exception as e:
        logger.error(f"Unexpected error placing order on {order_data.exchange_id}: {e}")
        # Create an OrderCreate schema with 'rejected' status
        order_to_save = OrderCreate(
            **order_data.model_dump(),
            status='rejected',
        )
        # Persist this rejected order to the database
        db_order = crud_orders.create_order(db=db, order=order_to_save)
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
