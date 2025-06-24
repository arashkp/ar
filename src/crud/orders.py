from sqlalchemy.orm import Session
from datetime import datetime # Added import
from src.database.models import Order
from src.schemas.order_schema import OrderCreate
from src.utils.crud_helpers import BaseCRUDHelper, validate_pagination_params

# Create base CRUD helper for Order model
order_crud = BaseCRUDHelper(Order)

def create_order(db: Session, order: OrderCreate) -> Order:
    """
    Creates a new order in the database.
    The OrderCreate schema should provide all necessary fields for the Order model.
    The Order model's __init__ handles calculation of 'cost' and 'remaining_amount'
    if 'price' and 'amount' are provided.
    """
    # Create a dictionary from the Pydantic model, excluding unset fields if necessary
    # or ensuring all required fields for Order model are present.
    order_data = order.model_dump()

    # Use base CRUD helper for creation
    return order_crud.create(db, order_data)

def get_order_by_id(db: Session, order_id: int) -> Order | None:
    """
    Retrieves an order from the database by its ID.
    """
    return order_crud.get_by_id(db, order_id)

def update_order_status(db: Session, order_id: int, status: str) -> Order | None:
    """
    Updates the status of an existing order.
    """
    return order_crud.update(db, order_id, {"status": status})

def get_orders_by_user_id(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> list[Order]:
    """
    Retrieves all orders for a specific user_id with pagination.
    (Optional, but good for listing orders)
    """
    # Validate pagination parameters
    validate_pagination_params(skip, limit)
    
    return order_crud.get_multi_with_filters(
        db=db,
        filters={"user_id": user_id},
        skip=skip,
        limit=limit,
        order_by="timestamp",
        order_desc=True
    )

def get_orders(db: Session, skip: int = 0, limit: int = 100) -> list[Order]:
    """
    Retrieves all orders with pagination.
    (Optional, for admin or general listing)
    """
    # Validate pagination parameters
    validate_pagination_params(skip, limit)
    
    return order_crud.get_multi(
        db=db,
        skip=skip,
        limit=limit,
        order_by="timestamp",
        order_desc=True
    )

def get_orders_with_filters(
    db: Session,
    exchange_id: str | None = None,
    symbol: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100
) -> list[Order]:
    """
    Retrieves orders from the database with optional filters and pagination.
    """
    # Validate pagination parameters
    validate_pagination_params(skip, limit)
    
    # Build filters dictionary
    filters = {}
    if exchange_id:
        filters["exchange_id"] = exchange_id
    if symbol:
        filters["symbol"] = symbol
    if status:
        filters["status"] = status

    return order_crud.get_multi_with_filters(
        db=db,
        filters=filters,
        skip=skip,
        limit=limit,
        order_by="timestamp",
        order_desc=True
    )

def get_filled_buy_orders_for_summary(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> list[Order]:
    """
    Retrieves 'buy' orders with status 'filled', optionally within a date range.
    These orders are used for calculating investment summaries.
    """
    # Build base filters
    filters = {"side": "buy", "status": "filled"}
    
    # Get orders with filters
    orders = order_crud.get_multi_with_filters(
        db=db,
        filters=filters,
        limit=1000,  # Higher limit for summary calculations
        order_by="timestamp",
        order_desc=False  # Ascending order for chronological analysis
    )
    
    # Apply date range filtering if provided
    if start_date or end_date:
        filtered_orders = []
        for order in orders:
            if start_date and order.timestamp < start_date:
                continue
            if end_date and order.timestamp > end_date:
                continue
            filtered_orders.append(order)
        return filtered_orders
    
    return orders
