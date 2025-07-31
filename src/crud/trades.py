from sqlalchemy.orm import Session
from database.models import Trade # Fixed import path
from schemas import trade_schema # This refers to src/schemas/trade_schema.py
from utils.crud_helpers import BaseCRUDHelper

# Create base CRUD helper for Trade model
trade_crud = BaseCRUDHelper(Trade)

def save_trade(db: Session, trade: trade_schema.TradeCreate) -> Trade:
    """
    Saves a new trade to the database.
    Converts Pydantic schema (trade_schema.TradeCreate) to SQLAlchemy model (models.Trade).
    """
    # Convert Pydantic model to dictionary
    trade_data = {
        "exchange_id": trade.exchange_id,
        "symbol": trade.symbol,
        "timestamp": trade.timestamp,
        "price": trade.price,
        "amount": trade.amount,
        "side": trade.side,
        "type": trade.type,
        "fee": trade.fee,
        "fee_currency": trade.fee_currency,
        "pnl": trade.pnl,
        "is_spot": trade.is_spot,
        "order_id": trade.order_id
    }
    
    # Use base CRUD helper for creation
    return trade_crud.create(db, trade_data)

def get_trade(db: Session, trade_id: int) -> Trade | None:
    """
    Retrieves a trade from the database by its ID.
    """
    return trade_crud.get_by_id(db, trade_id)

def get_trade_or_404(db: Session, trade_id: int) -> Trade:
    """
    Retrieves a trade from the database by its ID or raises 404 if not found.
    """
    return trade_crud.get_by_id_or_404(db, trade_id)

def get_trades(db: Session, skip: int = 0, limit: int = 100) -> list[Trade]:
    """
    Retrieves all trades with pagination.
    """
    return trade_crud.get_multi(
        db=db,
        skip=skip,
        limit=limit,
        order_by="timestamp",
        order_desc=True
    )

def get_trades_with_filters(
    db: Session,
    exchange_id: str | None = None,
    symbol: str | None = None,
    side: str | None = None,
    skip: int = 0,
    limit: int = 100
) -> list[Trade]:
    """
    Retrieves trades from the database with optional filters and pagination.
    """
    # Build filters dictionary
    filters = {}
    if exchange_id:
        filters["exchange_id"] = exchange_id
    if symbol:
        filters["symbol"] = symbol
    if side:
        filters["side"] = side

    return trade_crud.get_multi_with_filters(
        db=db,
        filters=filters,
        skip=skip,
        limit=limit,
        order_by="timestamp",
        order_desc=True
    )
