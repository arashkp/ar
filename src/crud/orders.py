from sqlalchemy.orm import Session
from src.database.models import Order
from src.schemas.order_schema import OrderCreate

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

    # The Order model's __init__ is expected to handle:
    # - remaining_amount (defaults to amount)
    # - cost (price * amount)
    # It also expects all other fields defined in OrderCreate to be passed.
    db_order = Order(**order_data)

    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

def get_order_by_id(db: Session, order_id: int) -> Order | None:
    """
    Retrieves an order from the database by its ID.
    """
    return db.query(Order).filter(Order.id == order_id).first()

def update_order_status(db: Session, order_id: int, status: str) -> Order | None:
    """
    Updates the status of an existing order.
    """
    db_order = get_order_by_id(db=db, order_id=order_id)
    if db_order:
        db_order.status = status
        # Potentially update other fields based on status, e.g., if 'filled' or 'cancelled'
        # For example, if status is 'filled', filled_amount might become equal to amount,
        # and remaining_amount might become 0. This logic could be more complex
        # and might be better suited for a service layer function that calls this.
        # For now, just updating status.
        db.commit()
        db.refresh(db_order)
        return db_order
    return None

def get_orders_by_user_id(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> list[Order]:
    """
    Retrieves all orders for a specific user_id with pagination.
    (Optional, but good for listing orders)
    """
    return db.query(Order).filter(Order.user_id == user_id).offset(skip).limit(limit).all()

def get_orders(db: Session, skip: int = 0, limit: int = 100) -> list[Order]:
    """
    Retrieves all orders with pagination.
    (Optional, for admin or general listing)
    """
    return db.query(Order).offset(skip).limit(limit).all()
