from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.sql import func
from src.database.base import BaseModel
from datetime import datetime

class Order(BaseModel):
    __tablename__ = "orders"

    exchange_order_id = Column(String)
    user_id = Column(Integer, default=1)  # Placeholder default
    exchange_id = Column(String)
    symbol = Column(String)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    price = Column(Float)
    amount = Column(Float)
    side = Column(String)
    type = Column(String)
    status = Column(String)
    filled_amount = Column(Float, default=0.0)
    remaining_amount = Column(Float) # Should default to amount, handled in __init__ or by application logic
    cost = Column(Float) # price * amount, handled in __init__ or by application logic
    fee = Column(Float, nullable=True, default=0.0)
    fee_currency = Column(String, nullable=True)
    is_spot = Column(Boolean)
    client_order_id = Column(String, nullable=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.amount is not None:
            self.remaining_amount = self.amount
        if self.price is not None and self.amount is not None:
            self.cost = self.price * self.amount

    def __repr__(self):
        return f"<Order(id={self.id}, symbol='{self.symbol}', side='{self.side}', type='{self.type}', status='{self.status}')>"

class Trade(BaseModel):
    __tablename__ = "trades"

    exchange_id = Column(String)
    symbol = Column(String)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    price = Column(Float)
    amount = Column(Float)
    side = Column(String)  # 'buy' or 'sell'
    type = Column(String)  # 'market' or 'limit'
    fee = Column(Float, nullable=True, default=0.0)
    fee_currency = Column(String, nullable=True)
    pnl = Column(Float, nullable=True)  # Profit/Loss for the trade
    is_spot = Column(Boolean, default=True)
    order_id = Column(Integer, nullable=True)  # Reference to the order that created this trade

    def __repr__(self):
        return f"<Trade(id={self.id}, symbol='{self.symbol}', side='{self.side}', amount={self.amount}, price={self.price})>"
