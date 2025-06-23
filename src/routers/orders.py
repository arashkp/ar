from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import ccxt # Import ccxt for its specific exceptions

from src.database.session import get_db
from src.schemas.order_schema import OrderRequest, OrderResponse, OrderCreate # Added OrderCreate
from src.services import order_manager # Assuming order_manager has the place_order function
from src.crud import orders as crud_orders # Added import for crud_orders
from src.database.models import Order # For type hinting if needed, though response_model handles conversion

router = APIRouter(
    prefix="/api/v1/orders",
    tags=["orders"],
    responses={404: {"description": "Not found"}},
)

# New endpoint for directly creating an order
@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_new_order_entry(
    order: OrderCreate, # Use OrderCreate schema
    db: Session = Depends(get_db)
):
    """
    Create a new order entry directly in the database.
    This endpoint is for scenarios where an order is recorded without
    initiating it through the system's exchange placement logic (e.g., importing existing orders).
    """
    try:
        # The OrderCreate schema should contain all necessary fields,
        # including exchange_order_id and status, if known.
        created_order_db = crud_orders.create_order(db=db, order=order)
        return created_order_db
    except Exception as e:
        # Perform basic error logging if possible, or ensure CRUD layer handles it
        # logger.error(f"Error creating order entry: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the order entry: {str(e)}"
        )

@router.post("/place", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_new_order(
    order_request: OrderRequest,
    db: Session = Depends(get_db)
):
    """
    Place a new order on an exchange and record it.
    """
    try:
        # The order_manager.place_order function is expected to be async
        created_order_db = await order_manager.place_order(order_data=order_request, db=db)

        # The place_order service should ideally always return a persisted order object,
        # even if the exchange placement failed (status='rejected').
        # If it could return None for some reason (e.g., DB error before creation),
        # that would be an internal server error.

        if created_order_db is None:
            # This case should ideally not be reached if place_order always persists an attempt.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create order entry in database after attempting placement."
            )

        # If the order was rejected by the exchange or due to internal logic (e.g. no API keys),
        # the status in created_order_db will reflect this (e.g., 'rejected', 'rejected_insufficient_funds').
        # We can check the status if we want to return different HTTP status codes based on it.
        # For example, if status indicates a client-side error (like insufficient funds based on a specific status string).
        if created_order_db.status == 'rejected_insufficient_funds':
            # This is an example. The service layer sets specific statuses.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order rejected due to insufficient funds on {order_request.exchange_id}."
            )
        elif created_order_db.status and 'rejected' in created_order_db.status:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, # Or 502 if it's an upstream exchange issue
                detail=f"Order placement failed or was rejected. Status: {created_order_db.status}"
            )

        # If successful (status is 'open', 'filled', or similar positive status from exchange)
        # FastAPI will automatically convert the SQLAlchemy model (created_order_db)
        # to an OrderResponse Pydantic model.
        return created_order_db

    except ccxt.InsufficientFunds as e:
        # This might be redundant if the service layer catches this and sets status to 'rejected_insufficient_funds'
        # and we handle that status above. However, if the service re-raises, this is a fallback.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient funds on {order_request.exchange_id}: {str(e)}"
        )
    except ccxt.NetworkError as e:
        # Error communicating with the exchange
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, # 504 or 502
            detail=f"Network error with {order_request.exchange_id}: {str(e)}"
        )
    except ccxt.ExchangeError as e:
        # General error from the exchange (e.g. invalid symbol, bad request to exchange)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # Could be 502 if it's an exchange server-side issue
            detail=f"Exchange error with {order_request.exchange_id}: {str(e)}"
        )
    except HTTPException:
        # Re-raise HTTPException directly if it's one we've already processed (e.g. from status checks)
        raise
    except Exception as e:
        # Catch-all for other unexpected errors from the service layer or this router
        # Log the error for debugging
        # logger.error(f"Unexpected error placing order: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/", response_model=list[OrderResponse])
async def list_orders_api(
    exchange_id: str | None = None,
    symbol: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of orders based on optional filters and pagination.
    - **exchange_id**: Filter by exchange ID (e.g., 'binance').
    - **symbol**: Filter by trading symbol (e.g., 'BTC/USDT').
    - **status**: Filter by order status (e.g., 'open', 'filled', 'cancelled').
    - **limit**: Maximum number of orders to return.
    - **offset**: Number of orders to skip for pagination.
    """
    try:
        orders_list = await order_manager.list_orders(
            db=db,
            exchange_id=exchange_id,
            symbol=symbol,
            status=status,
            limit=limit,
            offset=offset
        )
        # FastAPI will automatically convert the list of Order SQLAlchemy models
        # to a list of OrderResponse Pydantic models.
        return orders_list
    except Exception as e:
        # Consider more specific error handling if needed, e.g., for validation errors
        # logger.error(f"Error listing orders: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while listing orders: {str(e)}"
        )
