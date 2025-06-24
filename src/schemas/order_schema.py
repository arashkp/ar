from __future__ import annotations

from typing import Optional
from datetime import datetime, timezone # Added timezone
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
    exchange_order_id: Optional[str] = None
    status: str = 'pending'

    # Fields from exchange response or pre-calculated, needed for DB storage
    timestamp: Optional[datetime] = None
    filled_amount: Optional[float] = None
    remaining_amount: Optional[float] = None
    cost: Optional[float] = None
    fee: Optional[float] = None
    fee_currency: Optional[str] = None

    @validator('timestamp', pre=True, always=True)
    def default_timestamp(cls, v):
        return v or datetime.now(timezone.utc)

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
        from_attributes = True  # Pydantic V2 way for ORM compatibility
