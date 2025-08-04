"""
Technical Analysis utilities to replace pandas_ta for better compatibility.
This module provides EMA, SMA, ATR, and RSI calculations using native pandas/numpy.
"""

import pandas as pd
import numpy as np
from typing import Optional


def ema(data: pd.Series, length: int = 14) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).
    
    Args:
        data: Price series (usually close prices)
        length: Period length for EMA calculation
        
    Returns:
        EMA series
    """
    return data.ewm(span=length, adjust=False).mean()


def sma(data: pd.Series, length: int = 14) -> pd.Series:
    """
    Calculate Simple Moving Average (SMA).
    
    Args:
        data: Price series (usually close prices)
        length: Period length for SMA calculation
        
    Returns:
        SMA series
    """
    return data.rolling(window=length).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR).
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        length: Period length for ATR calculation
        
    Returns:
        ATR series
    """
    # Calculate True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate ATR using EMA
    return ema(true_range, length)


def rsi(data: pd.Series, length: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    
    Args:
        data: Price series (usually close prices)
        length: Period length for RSI calculation
        
    Returns:
        RSI series (values between 0 and 100)
    """
    # Calculate price changes
    delta = data.diff()
    
    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    
    # Calculate average gains and losses using EMA
    avg_gains = ema(gains, length)
    avg_losses = ema(losses, length)
    
    # Calculate RS and RSI
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


# Monkey patch pandas DataFrame to add ta methods for compatibility
def _add_ta_methods_to_dataframe():
    """Add ta methods to pandas DataFrame for compatibility with existing code."""
    
    def ta_ema(self, length: int = 14, **kwargs) -> pd.Series:
        """Calculate EMA on the DataFrame's close column."""
        if 'close' in self.columns:
            return ema(self['close'], length)
        elif len(self.columns) == 1:
            return ema(self.iloc[:, 0], length)
        else:
            raise ValueError("Cannot determine which column to use for EMA calculation")
    
    def ta_sma(self, length: int = 14, **kwargs) -> pd.Series:
        """Calculate SMA on the DataFrame's close column."""
        if 'close' in self.columns:
            return sma(self['close'], length)
        elif len(self.columns) == 1:
            return sma(self.iloc[:, 0], length)
        else:
            raise ValueError("Cannot determine which column to use for SMA calculation")
    
    def ta_atr(self, length: int = 14, **kwargs) -> pd.Series:
        """Calculate ATR using high, low, and close columns."""
        required_cols = ['high', 'low', 'close']
        if not all(col in self.columns for col in required_cols):
            raise ValueError(f"ATR calculation requires columns: {required_cols}")
        return atr(self['high'], self['low'], self['close'], length)
    
    def ta_rsi(self, length: int = 14, **kwargs) -> pd.Series:
        """Calculate RSI on the DataFrame's close column."""
        if 'close' in self.columns:
            return rsi(self['close'], length)
        elif len(self.columns) == 1:
            return rsi(self.iloc[:, 0], length)
        else:
            raise ValueError("Cannot determine which column to use for RSI calculation")
    
    # Add methods to pandas DataFrame
    pd.DataFrame.ta = type('TA', (), {})
    pd.DataFrame.ta.ema = ta_ema
    pd.DataFrame.ta.sma = ta_sma
    pd.DataFrame.ta.atr = ta_atr
    pd.DataFrame.ta.rsi = ta_rsi


# Initialize the ta methods
_add_ta_methods_to_dataframe() 