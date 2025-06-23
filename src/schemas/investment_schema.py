from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import date, datetime

class InvestmentSummaryRequest(BaseModel):
    timeframe: Optional[str] = 'total'  # e.g., 'daily', 'weekly', 'total'
    currency: Optional[str] = 'USD'    # e.g., 'USD', 'BTC'

class InvestmentDataPoint(BaseModel):
    period: str  # Could be a date for daily, week_number for weekly, or 'total'
    total_invested: float
    currency: str

class InvestmentSummaryResponse(BaseModel):
    requested_timeframe: str
    requested_currency: str
    summary: List[InvestmentDataPoint]
    # Optional: Add more fields like overall_total_invested if needed
    overall_total_invested: Optional[float] = None
    calculation_timestamp: datetime

    class Config:
        orm_mode = True # For Pydantic V1
        # from_attributes = True # For Pydantic V2
        pass
