from sqlalchemy.orm import Session
from database import models # This should correctly refer to database/models.py
from src.schemas import trade_schema # This refers to src/schemas/trade_schema.py

def save_trade(db: Session, trade: trade_schema.TradeCreate) -> models.Trade:
    """
    Saves a new trade to the database.
    Converts Pydantic schema (trade_schema.TradeCreate) to SQLAlchemy model (models.Trade).
    """
    db_trade = models.Trade(
        exchange_id=trade.exchange_id,
        symbol=trade.symbol,
        timestamp=trade.timestamp,
        price=trade.price,
        amount=trade.amount,
        side=trade.side,
        type=trade.type,
        fee=trade.fee,
        fee_currency=trade.fee_currency,
        pnl=trade.pnl,
        is_spot=trade.is_spot,
        order_id=trade.order_id
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade

# Example of a function to retrieve a trade (optional for now)
# def get_trade(db: Session, trade_id: int) -> models.Trade | None:
#     return db.query(models.Trade).filter(models.Trade.id == trade_id).first()
