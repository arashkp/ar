"""
Historical Performance Service using OHLCV data.

This module calculates historical performance metrics (7d, 14d, 1m, 3m, 6m, 1y, YTD)
from OHLCV data fetched from exchanges using the existing infrastructure.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from pydantic import BaseModel
from src.services.cache_manager import read_ohlcv_from_cache, write_ohlcv_to_cache
from src.core.config import settings
import ccxt.async_support as ccxt
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

# Timeframe mappings for calculations
TIMEFRAME_DAYS = {
    "7d": 7,
    "14d": 14,
    "1m": 30,
    "3m": 90,
    "6m": 180,
    "1y": 365,
    "ytd": None  # Special case - calculated from year start
}


class PerformanceMetrics(BaseModel):
    """Model for performance metrics."""
    symbol: str
    performance: Dict[str, float]
    highs: Dict[str, float]
    lows: Dict[str, float]
    current_prices: Dict[str, float]
    last_updated: datetime


class HistoricalPerformanceService:
    """Service for calculating historical performance from OHLCV data."""
    
    def __init__(self):
        """Initialize the service."""
        self.active_exchanges = {}
        logger.info("Historical Performance Service initialized")
    
    async def _get_exchange(self, exchange_id: str) -> ccxt.Exchange:
        """Get or create exchange instance."""
        if exchange_id not in self.active_exchanges:
            try:
                exchange_class = getattr(ccxt, exchange_id)
                exchange = exchange_class({'enableRateLimit': True})
                self.active_exchanges[exchange_id] = exchange
                logger.info(f"Initialized {exchange_id} for historical data")
            except Exception as e:
                logger.error(f"Error initializing exchange {exchange_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to initialize exchange {exchange_id}"
                )
        return self.active_exchanges[exchange_id]
    
    def _calculate_performance(self, df: pd.DataFrame, days: int) -> Optional[float]:
        """Calculate percentage change for a given number of days."""
        if len(df) < days:
            return None
        
        try:
            current_price = df['close'].iloc[-1]
            past_price = df['close'].iloc[-days]
            
            if past_price == 0:
                return None
            
            percentage_change = ((current_price - past_price) / past_price) * 100
            return round(percentage_change, 2)
        except Exception as e:
            logger.error(f"Error calculating performance for {days} days: {e}")
            return None
    
    def _calculate_ytd_performance(self, df: pd.DataFrame) -> Optional[float]:
        """Calculate year-to-date performance."""
        try:
            current_year = datetime.now().year
            year_start = datetime(current_year, 1, 1)
            
            # Convert timestamp to datetime for filtering
            df_copy = df.copy()
            df_copy['datetime'] = pd.to_datetime(df_copy['timestamp'], unit='ms')
            
            # Filter data from year start
            year_data = df_copy[df_copy['datetime'] >= year_start]
            
            if len(year_data) < 2:
                return None
            
            first_price = year_data['close'].iloc[0]
            current_price = year_data['close'].iloc[-1]
            
            if first_price == 0:
                return None
            
            percentage_change = ((current_price - first_price) / first_price) * 100
            return round(percentage_change, 2)
        except Exception as e:
            logger.error(f"Error calculating YTD performance: {e}")
            return None
    
    def _calculate_highs_lows(self, df: pd.DataFrame, days: int) -> tuple[Optional[float], Optional[float]]:
        """Calculate high and low for a given number of days."""
        if len(df) < days:
            return None, None
        
        try:
            recent_data = df.tail(days)
            high = recent_data['high'].max()
            low = recent_data['low'].min()
            return round(high, 6), round(low, 6)
        except Exception as e:
            logger.error(f"Error calculating highs/lows for {days} days: {e}")
            return None, None
    
    def _calculate_ytd_highs_lows(self, df: pd.DataFrame) -> tuple[Optional[float], Optional[float]]:
        """Calculate year-to-date highs and lows."""
        try:
            current_year = datetime.now().year
            year_start = datetime(current_year, 1, 1)
            
            # Convert timestamp to datetime for filtering
            df_copy = df.copy()
            df_copy['datetime'] = pd.to_datetime(df_copy['timestamp'], unit='ms')
            
            # Filter data from year start
            year_data = df_copy[df_copy['datetime'] >= year_start]
            
            if len(year_data) < 1:
                return None, None
            
            high = year_data['high'].max()
            low = year_data['low'].min()
            return round(high, 6), round(low, 6)
        except Exception as e:
            logger.error(f"Error calculating YTD highs/lows: {e}")
            return None, None
    
    async def get_symbol_performance(
        self, 
        symbol: str, 
        exchange_id: str,
        timeframes: List[str] = None
    ) -> Optional[PerformanceMetrics]:
        """
        Get performance metrics for a single symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            exchange_id: Exchange ID (e.g., 'binance', 'bitunix')
            timeframes: List of timeframes to calculate
            
        Returns:
            PerformanceMetrics object or None if failed
        """
        if timeframes is None:
            timeframes = list(TIMEFRAME_DAYS.keys())
        
        try:
            # Try to get cached data first (using daily timeframe)
            cached_df = read_ohlcv_from_cache(settings.CACHE_DIRECTORY, symbol, timeframe='1d')
            
            if cached_df is None or cached_df.empty:
                logger.info(f"No cached daily data for {symbol}, fetching from exchange...")
                
                # Fetch data from exchange
                exchange = await self._get_exchange(exchange_id)
                
                # Fetch enough data for the longest timeframe (1 year = 365 days)
                max_days = max([days for days in TIMEFRAME_DAYS.values() if days is not None])
                fetch_limit = max_days + 50  # Add buffer
                
                ohlcv_data = await exchange.fetch_ohlcv(
                    symbol, 
                    timeframe='1d', 
                    limit=fetch_limit
                )
                
                if not ohlcv_data:
                    logger.error(f"No OHLCV data returned for {symbol}")
                    return None
                
                # Convert to DataFrame
                df = pd.DataFrame(
                    ohlcv_data,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df['timestamp'] = df['timestamp'].astype('int64')
                df.sort_values(by='timestamp', ascending=True, inplace=True)
                
                # Cache the data with daily timeframe
                write_ohlcv_to_cache(settings.CACHE_DIRECTORY, symbol, df, timeframe='1d')
            else:
                logger.info(f"Using cached daily data for {symbol}")
                df = cached_df
            
            # Calculate performance metrics
            performance = {}
            highs = {}
            lows = {}
            current_prices = {}
            
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize(None)
            today = pd.to_datetime('now').normalize().tz_localize(None)
            for timeframe in timeframes:
                days = TIMEFRAME_DAYS.get(timeframe)
                if timeframe == "ytd":
                    current_year = today.year
                    year_start = pd.to_datetime(f"{current_year}-01-01")
                    period_df = df[(df['datetime'] >= year_start) & (df['datetime'] < today)]
                elif timeframe.endswith('d'):
                    n_days = int(timeframe[:-1])
                    start_date = today - pd.Timedelta(days=n_days)
                    period_df = df[(df['datetime'] >= start_date) & (df['datetime'] < today)]
                elif timeframe.endswith('m'):
                    n_months = int(timeframe[:-1])
                    start_date = today - relativedelta(months=n_months)
                    period_df = df[(df['datetime'] >= start_date) & (df['datetime'] < today)]
                elif timeframe.endswith('y'):
                    n_years = int(timeframe[:-1])
                    start_date = today - relativedelta(years=n_years)
                    period_df = df[(df['datetime'] >= start_date) & (df['datetime'] < today)]
                else:
                    continue
                if len(period_df) >= 2:
                    first_price = period_df['close'].iloc[0]
                    last_price = period_df['close'].iloc[-1]
                    performance[timeframe] = round(((last_price - first_price) / first_price) * 100, 2)
                    highs[timeframe] = round(period_df['high'].max(), 6)
                    lows[timeframe] = round(period_df['low'].min(), 6)
                    current_prices[timeframe] = last_price
            
            return PerformanceMetrics(
                symbol=symbol,
                performance=performance,
                highs=highs,
                lows=lows,
                current_prices=current_prices,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error calculating performance for {symbol}: {e}")
            return None
    
    async def get_all_symbols_performance(
        self, 
        symbol_config: List[Dict],
        timeframes: List[str] = None
    ) -> List[PerformanceMetrics]:
        """
        Get performance metrics for all configured symbols.
        
        Args:
            symbol_config: List of symbol configurations
            timeframes: List of timeframes to calculate
            
        Returns:
            List of PerformanceMetrics objects
        """
        results = []
        
        for config in symbol_config:
            symbol = config["symbol"]
            exchange_id = config["exchange_id"]
            
            try:
                metrics = await self.get_symbol_performance(
                    symbol=symbol,
                    exchange_id=exchange_id,
                    timeframes=timeframes
                )
                
                if metrics:
                    results.append(metrics)
                else:
                    logger.warning(f"Failed to get performance for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue
        
        return results
    
    async def cleanup(self):
        """Clean up exchange connections."""
        for exchange_id, exchange in self.active_exchanges.items():
            try:
                await exchange.close()
                logger.info(f"Closed {exchange_id} exchange")
            except Exception as e:
                logger.error(f"Error closing {exchange_id} exchange: {e}")
        
        self.active_exchanges.clear() 