"""
Historical Performance Router.

This module provides API endpoints for fetching historical performance
data calculated from OHLCV data.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import logging
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Import services and utilities
from src.services.historical_performance_service import (
    HistoricalPerformanceService, PerformanceMetrics
)
from src.routers.market_overview import SYMBOL_CONFIG
from src.utils.error_handlers import api_error_handler

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/v1/historical/performance", response_model=List[PerformanceMetrics])
@api_error_handler("Historical performance data fetching")
async def get_historical_performance(
    symbols: Optional[List[str]] = Query(None, description="List of symbols to fetch (default: all configured)"),
    timeframes: Optional[List[str]] = Query(None, description="List of timeframes (7d, 14d, 1m, 3m, 6m, 1y, ytd)")
):
    """
    Get historical performance data for crypto symbols.
    
    Args:
        symbols: List of trading symbols (e.g., ['BTC/USDT', 'ETH/USDT'])
        timeframes: List of timeframes to fetch
        
    Returns:
        List of PerformanceMetrics objects with performance data
    """
    try:
        # Initialize service
        service = HistoricalPerformanceService()
        
        # If no symbols specified, get all configured symbols
        if symbols is None:
            symbol_config = SYMBOL_CONFIG
        else:
            # Filter symbol config to requested symbols
            symbol_config = [
                config for config in SYMBOL_CONFIG 
                if config["symbol"] in symbols
            ]
        
        if not symbol_config:
            raise HTTPException(
                status_code=400,
                detail="No valid symbols provided. Check your symbol configuration."
            )
        
        # If no timeframes specified, get all available
        if timeframes is None:
            timeframes = ["7d", "14d", "1m", "3m", "6m", "1y", "ytd"]
        
        logger.info(f"Fetching historical performance for {len(symbol_config)} symbols, timeframes: {timeframes}")
        
        # Fetch historical performance data
        performance_data = await service.get_all_symbols_performance(
            symbol_config=symbol_config,
            timeframes=timeframes
        )
        
        # Clean up
        await service.cleanup()
        
        logger.info(f"Successfully fetched performance data for {len(performance_data)} symbols")
        return performance_data
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in historical performance endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/api/v1/historical/performance/symbol/{symbol}")
@api_error_handler("Single symbol historical performance")
async def get_symbol_performance(
    symbol: str,
    timeframes: Optional[List[str]] = Query(None, description="List of timeframes (7d, 14d, 1m, 3m, 6m, 1y, ytd)")
):
    """
    Get historical performance data for a specific symbol.
    
    Args:
        symbol: Trading symbol (e.g., 'BTC/USDT')
        timeframes: List of timeframes to fetch
        
    Returns:
        PerformanceMetrics object
    """
    try:
        # Find symbol in config
        symbol_config = None
        for config in SYMBOL_CONFIG:
            if config["symbol"] == symbol:
                symbol_config = config
                break
        
        if not symbol_config:
            raise HTTPException(
                status_code=404,
                detail=f"Symbol {symbol} not found in configuration"
            )
        
        # If no timeframes specified, get all available
        if timeframes is None:
            timeframes = ["7d", "14d", "1m", "3m", "6m", "1y", "ytd"]
        
        # Initialize service
        service = HistoricalPerformanceService()
        
        logger.info(f"Fetching historical performance for {symbol}, timeframes: {timeframes}")
        
        # Fetch performance data
        performance_data = await service.get_symbol_performance(
            symbol=symbol,
            exchange_id=symbol_config["exchange_id"],
            timeframes=timeframes
        )
        
        # Clean up
        await service.cleanup()
        
        if not performance_data:
            raise HTTPException(
                status_code=404,
                detail=f"No performance data available for {symbol}"
            )
        
        return performance_data
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in symbol performance endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/api/v1/historical/supported")
async def get_supported_symbols_and_timeframes():
    """
    Get list of supported symbols and timeframes.
    
    Returns:
        Dictionary with supported symbols and timeframes
    """
    try:
        return {
            "supported_symbols": [config["symbol"] for config in SYMBOL_CONFIG],
            "supported_timeframes": ["7d", "14d", "1m", "3m", "6m", "1y", "ytd"],
            "timeframe_descriptions": {
                "7d": "7 days",
                "14d": "14 days", 
                "1m": "1 month",
                "3m": "3 months",
                "6m": "6 months",
                "1y": "1 year",
                "ytd": "Year to date"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting supported symbols and timeframes: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        ) 