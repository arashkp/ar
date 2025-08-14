"""
Funding Rates Router for the AR trading application.

This module provides API endpoints for fetching funding rates
from multiple exchanges.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.services.funding_rate_service import FundingRateService
from src.schemas.funding_rate_schema import (
    FundingRateResponse,
    FundingRatesSummaryResponse,
    ExchangeFundingRatesRequest,
    FundingRateItem
)
from src.utils.error_handlers import exchange_error_handler

router = APIRouter()

# Initialize funding rate service
funding_rate_service = FundingRateService()

@router.get("/funding-rates/", response_model=FundingRatesSummaryResponse)
@exchange_error_handler("funding_rates", "funding rates fetching")
async def get_all_funding_rates(
    symbols: Optional[List[str]] = Query(None, description="Specific symbols to fetch"),
    exchanges: Optional[List[str]] = Query(None, description="Specific exchanges to fetch from")
):
    """
    Get funding rates for all supported symbols across all supported exchanges.
    
    Args:
            symbols: Optional list of specific symbols (e.g., ['BTC', 'ETH'])
    exchanges: Optional list of specific exchanges (e.g., ['kucoin', 'bitunix'])
        
    Returns:
        Complete funding rates summary for all symbols and exchanges
    """
    try:
        rates = await funding_rate_service.get_all_funding_rates(
            symbols=symbols,
            exchanges=exchanges
        )
        return rates
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch funding rates: {str(e)}"
        )

@router.get("/funding-rates/{symbol}", response_model=FundingRateResponse)
@exchange_error_handler("funding_rates", "symbol funding rates fetching")
async def get_symbol_funding_rates(
    symbol: str,
    exchanges: Optional[List[str]] = Query(None, description="Specific exchanges to fetch from")
):
    """
    Get funding rates for a specific symbol across all supported exchanges.
    
    Args:
        symbol: Base symbol (e.g., 'BTC', 'ETH')
        exchanges: Optional list of specific exchanges
        
    Returns:
        Funding rates for the specified symbol across exchanges
    """
    try:
        rates = await funding_rate_service.get_symbol_funding_rates(
            symbol=symbol.upper(),
            exchanges=exchanges
        )
        return rates
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch funding rates for {symbol}: {str(e)}"
        )

@router.get("/funding-rates/exchange/{exchange_id}", response_model=List[FundingRateItem])
@exchange_error_handler("funding_rates", "exchange funding rates fetching")
async def get_exchange_funding_rates(
    exchange_id: str,
    symbols: Optional[List[str]] = Query(None, description="Specific symbols to fetch")
):
    """
    Get funding rates for all symbols from a specific exchange.
    
    Args:
        exchange_id: Exchange identifier (e.g., 'kucoin', 'bitunix')
        symbols: Optional list of specific symbols
        
    Returns:
        List of funding rates for the specified exchange
    """
    try:
        rates = await funding_rate_service.get_exchange_funding_rates(
            exchange_id=exchange_id.lower(),
            symbols=symbols
        )
        return rates
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch funding rates from {exchange_id}: {str(e)}"
        )

@router.post("/funding-rates/custom", response_model=FundingRatesSummaryResponse)
@exchange_error_handler("funding_rates", "custom funding rates fetching")
async def get_custom_funding_rates(
    request: ExchangeFundingRatesRequest
):
    """
    Get funding rates with custom parameters.
    
    Args:
        request: Custom funding rates request with exchanges and symbols
        
    Returns:
        Funding rates summary based on custom parameters
    """
    try:
        rates = await funding_rate_service.get_all_funding_rates(
            symbols=request.symbols,
            exchanges=request.exchanges
        )
        return rates
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch custom funding rates: {str(e)}"
        )

@router.get("/funding-rates/supported/exchanges")
async def get_supported_exchanges():
    """
    Get list of supported exchanges for funding rates.
    
    Returns:
        List of supported exchange identifiers
    """
    from src.services.funding_rate_service import SUPPORTED_EXCHANGES
    return {
        "exchanges": SUPPORTED_EXCHANGES,
        "message": "Supported exchanges for funding rates"
    }

@router.get("/funding-rates/supported/symbols")
async def get_supported_symbols():
    """
    Get list of supported symbols for funding rates.
    
    Returns:
        List of supported symbols and their trading pairs
    """
    from src.services.funding_rate_service import SUPPORTED_SYMBOLS, SYMBOL_TO_PAIR
    return {
        "symbols": SUPPORTED_SYMBOLS,
        "trading_pairs": SYMBOL_TO_PAIR,
        "message": "Supported symbols and trading pairs for funding rates"
    }

@router.on_event("shutdown")
async def shutdown_event():
    """Clean up funding rate service on shutdown."""
    await funding_rate_service.cleanup()
