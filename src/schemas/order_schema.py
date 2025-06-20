from __future__ import annotations

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, validator

class OrderBase(BaseModel):
    exchange_id: str
    symbol: str
    amount: float
    side: str  # 'buy' or 'sell'
    type: str  # 'market' or 'limit'
    price: Optional[float] = None
    user_id: Optional[int] = 1 # Default to placeholder
    is_spot: bool = True
    client_order_id: Optional[str] = None

class OrderRequest(OrderBase):
    @validator('price', always=True)
    def price_required_for_limit_orders(cls, v, values):
        if values.get('type') == 'limit' and v is None:
            raise ValueError('Price must be provided for limit orders')
        return v

class OrderCreate(OrderBase):
    exchange_order_id: Optional[str] = None # Should be provided if the order already exists on an exchange
    status: str = 'pending' # Initial status, e.g., 'pending' if new, or actual status if known
    # Fields that will be calculated or set based on other fields or logic
    # before saving to DB, not directly from request.
    # For example, cost and remaining_amount might be set by the service layer.
    # However, the DB model's __init__ already handles remaining_amount and cost
    # if price and amount are available.
    # For OrderCreate, we might not need to explicitly define them if they are
    # derived from OrderBase fields.

class OrderResponse(OrderBase):
    id: int
    exchange_order_id: Optional[str] = None
    timestamp: datetime
    status: str
    filled_amount: float
    remaining_amount: float
    cost: float
    fee: Optional[float] = None
    fee_currency: Optional[str] = None

    class Config:
        orm_mode = True # Pydantic V1 way for ORM compatibility
        # from_attributes = True # Pydantic V2 way for ORM compatibility
        # Pydantic V2 is preferred, but sticking to orm_mode for broader compatibility for now
        # unless specified. Assuming Pydantic V1 for orm_mode. If V2 is used,
        # this should be from_attributes = True.
        # Given the problem context usually implies recent versions,
        # let's assume from_attributes is the modern way if orm_mode causes issues.
        # For now, let's stick to orm_mode as it's more common in existing codebases.
        # If this were Pydantic V2, it would be:
        # model_config = {"from_attributes": True}

        # Re-checking common practice for FastAPI/SQLAlchemy, orm_mode is standard for Pydantic v1.x
        # If the environment uses Pydantic v2.x, this should be `from_attributes = True`.
        # Without knowing the Pydantic version, `orm_mode = True` is a safe bet for compatibility.
        # Let's assume Pydantic v1.x for now.
        pass
