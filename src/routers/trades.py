from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database.database import get_db # For database session dependency
from src.schemas import trade_schema # Pydantic schemas for trades
from src.crud import trades as trades_crud # CRUD operations for trades

router = APIRouter(
    prefix="/api/v1/trades",
    tags=["Trades"], # Tag for API documentation
)

@router.post("/", response_model=trade_schema.TradeRead)
async def create_trade(
    trade: trade_schema.TradeCreate,
    db: Session = Depends(get_db)
):
    """
    Creates a new trade record in the database.
    Accepts trade data and saves it.
    """
    try:
        created_trade = trades_crud.save_trade(db=db, trade=trade)
        return created_trade
    except Exception as e:
        # Generic error handling, specific exceptions should be caught in CRUD or service layer if needed
        raise HTTPException(status_code=500, detail=f"An error occurred while saving the trade: {str(e)}")

# Optional: Endpoint to read trades (example)
# @router.get("/{trade_id}", response_model=trade_schema.TradeRead)
# async def read_trade(trade_id: int, db: Session = Depends(get_db)):
#     db_trade = trades_crud.get_trade(db, trade_id=trade_id) # Assuming get_trade exists in crud
#     if db_trade is None:
#         raise HTTPException(status_code=404, detail="Trade not found")
#     return db_trade
