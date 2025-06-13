from pydantic import BaseModel
from typing import Optional
import datetime
from decimal import Decimal # For precise numeric types

class TradeBase(BaseModel):
    exchange_id: str
    symbol: str
    timestamp: datetime.datetime
    price: Decimal
    amount: Decimal
    side: str # 'buy' or 'sell'
    type: str # 'market' or 'limit'
    fee: Optional[Decimal] = 0.0
    fee_currency: Optional[str] = None
    pnl: Optional[Decimal] = 0.0
    is_spot: bool = True
    order_id: Optional[str] = None

class TradeCreate(TradeBase):
    pass

class TradeRead(TradeBase):
    id: int

    class Config:
        from_attributes = True # For Pydantic v2


# Optional: Schemas for Order model if you plan to create CRUD for it too.
# class OrderBase(BaseModel):
#     exchange_order_id: str
#     exchange_id: str
#     symbol: str
#     timestamp: datetime.datetime
#     price: Decimal
#     amount: Decimal
#     side: str
#     type: str
#     status: str
#     filled_amount: Optional[Decimal] = 0.0
#     remaining_amount: Optional[Decimal] = 0.0

# class OrderCreate(OrderBase):
#     pass

# class OrderRead(OrderBase):
#     id: int
#     class Config:
#         from_attributes = True
