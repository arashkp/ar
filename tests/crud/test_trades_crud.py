import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession # Renamed to avoid pycharm/lint confusion with pytest 'Session'
from decimal import Decimal
import datetime

from src.database.base import Base # To create tables
from src.database import models # Actual models: Trade, Order, User
from src.schemas import trade_schema # Pydantic schemas for validation
from src.crud import trades as trades_crud # CRUD functions

# Setup for an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Create all tables and yield a session, then drop all tables."""
    Base.metadata.create_all(bind=engine) # Create tables
    db: SQLAlchemySession = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine) # Drop tables after test

def test_trade_model_creation():
    """Test basic instantiation of the Trade SQLAlchemy model."""
    now = datetime.datetime.utcnow()
    trade = models.Trade(
        exchange_id="test_exchange",
        symbol="BTC/USDT",
        timestamp=now,
        price=Decimal("50000.0"),
        amount=Decimal("1.0"),
        side="buy",
        type="market",
        fee=Decimal("5.0"),
        fee_currency="USDT",
        pnl=Decimal("0.0"),
        is_spot=True,
        order_id="test_order_123"
    )
    assert trade.symbol == "BTC/USDT"
    assert trade.price == Decimal("50000.0")
    assert trade.timestamp == now

def test_order_model_creation():
    """Test basic instantiation of the Order SQLAlchemy model."""
    now = datetime.datetime.utcnow()
    order = models.Order(
        exchange_order_id="ex_ord_789",
        exchange_id="test_exchange",
        symbol="ETH/USDT",
        timestamp=now,
        price=Decimal("4000.0"),
        amount=Decimal("10.0"),
        side="sell",
        type="limit",
        status="open",
        filled_amount=Decimal("0.0"),
        remaining_amount=Decimal("10.0")
    )
    assert order.symbol == "ETH/USDT"
    assert order.status == "open"
    assert order.price == Decimal("4000.0")

def test_save_trade_crud(db_session: SQLAlchemySession): # Use renamed Session
    """Test the save_trade CRUD function."""
    trade_data = trade_schema.TradeCreate(
        exchange_id="bitget",
        symbol="BTC/USDT",
        timestamp=datetime.datetime.utcnow(),
        price=Decimal("50000.00"),
        amount=Decimal("0.01"),
        side="buy",
        type="market",
        fee=Decimal("0.00001"),
        fee_currency="BTC",
        is_spot=True,
        order_id="order123"
    )

    created_trade = trades_crud.save_trade(db=db_session, trade=trade_data)

    assert created_trade.id is not None
    assert created_trade.exchange_id == "bitget"
    assert created_trade.symbol == "BTC/USDT"
    assert created_trade.price == Decimal("50000.00")
    assert created_trade.amount == Decimal("0.01")
    assert created_trade.side == "buy"

    retrieved_trade = db_session.query(models.Trade).filter(models.Trade.id == created_trade.id).first()
    assert retrieved_trade is not None
    assert retrieved_trade.symbol == "BTC/USDT"

def test_save_trade_crud_numeric_precision(db_session: SQLAlchemySession): # Use renamed Session
    """Test that Numeric fields handle precision correctly via CRUD."""
    trade_data_precise = trade_schema.TradeCreate(
        exchange_id="mexc",
        symbol="ETH/BTC",
        timestamp=datetime.datetime.utcnow(),
        price=Decimal("0.0712345678"),
        amount=Decimal("0.1234567890"),
        side="sell",
        type="limit",
        fee=Decimal("0.00012345"),
        fee_currency="ETH",
        is_spot=True
    )
    created_trade = trades_crud.save_trade(db=db_session, trade=trade_data_precise)

    assert created_trade.price == Decimal("0.0712345678")
    assert created_trade.amount == Decimal("0.1234567890")
    assert created_trade.fee == Decimal("0.00012345")
