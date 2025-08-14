from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class FundingRateItem(BaseModel):
    """Individual funding rate data for a symbol on an exchange."""
    exchange: str = Field(..., description="Exchange name")
    symbol: str = Field(..., description="Trading symbol (e.g., BTC/USDT)")
    funding_rate: float = Field(..., description="Current funding rate as percentage")
    mark_price: Optional[float] = Field(None, description="Mark price of the asset")
    last_price: Optional[float] = Field(None, description="Last traded price")
    next_funding_time: Optional[datetime] = Field(None, description="Next funding time")
    previous_funding_rate: Optional[float] = Field(None, description="Previous funding rate")
    estimated_rate: Optional[float] = Field(None, description="Estimated next funding rate")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

class FundingRateResponse(BaseModel):
    """Response model for funding rate data."""
    symbol: str = Field(..., description="Trading symbol")
    rates: List[FundingRateItem] = Field(..., description="List of funding rates from different exchanges")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Overall last update timestamp")

class FundingRatesSummaryResponse(BaseModel):
    """Summary response for all symbols and exchanges."""
    symbols: List[str] = Field(..., description="List of supported symbols")
    exchanges: List[str] = Field(..., description="List of supported exchanges")
    rates: List[FundingRateResponse] = Field(..., description="Funding rates for all symbols")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Overall last update timestamp")

class ExchangeFundingRatesRequest(BaseModel):
    """Request model for fetching funding rates from specific exchanges."""
    exchanges: Optional[List[str]] = Field(None, description="Specific exchanges to fetch from")
    symbols: Optional[List[str]] = Field(None, description="Specific symbols to fetch")
    include_estimated: bool = Field(default=True, description="Include estimated funding rates")
