from sqlalchemy import Column, Integer, String, DateTime, Numeric, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship # Added in case it's uncommented later
import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exchange_id = Column(String, index=True, nullable=False)
    symbol = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    price = Column(Numeric(precision=20, scale=10), nullable=False) # Using Numeric for precision
    amount = Column(Numeric(precision=20, scale=10), nullable=False) # Using Numeric for precision
    side = Column(String, nullable=False)  # 'buy' or 'sell'
    type = Column(String, nullable=False)  # 'market' or 'limit'
    fee = Column(Numeric(precision=20, scale=10), default=0.0)
    fee_currency = Column(String, nullable=True)
    pnl = Column(Numeric(precision=20, scale=10), default=0.0, nullable=True)
    is_spot = Column(Boolean, default=True, nullable=False)
    order_id = Column(String, nullable=True, index=True) # Stores the exchange_order_id from the 'orders' table (Order.exchange_order_id)
    # If order_id refers to the id of the Order model below, it should be:
    # internal_order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exchange_order_id = Column(String, unique=True, index=True, nullable=False) # ID from the exchange
    exchange_id = Column(String, index=True, nullable=False)
    symbol = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    price = Column(Numeric(precision=20, scale=10), nullable=False) # Price of the order
    amount = Column(Numeric(precision=20, scale=10), nullable=False) # Quantity ordered
    side = Column(String, nullable=False) # 'buy' or 'sell'
    type = Column(String, nullable=False) # 'market', 'limit', etc.
    status = Column(String, nullable=False, index=True) # 'open', 'filled', 'canceled', 'partially_filled'
    filled_amount = Column(Numeric(precision=20, scale=10), default=0.0)
    remaining_amount = Column(Numeric(precision=20, scale=10), default=0.0)

    # Optional: Relationship to trades filled by this order
    # trades = relationship("Trade", backref="order_fills") # This would require 'order_fills' backref in Trade model
