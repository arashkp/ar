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
class _TAAccessor:
    """Lightweight TA accessor compatible with the legacy pandas_ta API used in the app."""

    def __init__(self, df: pd.DataFrame):
        self._df = df

    def _resolve_close_series(self) -> pd.Series:
        if 'close' in self._df.columns:
            return self._df['close']
        if len(self._df.columns) == 1:
            return self._df.iloc[:, 0]
        raise ValueError("Cannot determine which column to use for close price based calculations")

    def ema(self, length: int = 14, **kwargs) -> pd.Series:
        return ema(self._resolve_close_series(), length)

    def sma(self, length: int = 14, **kwargs) -> pd.Series:
        return sma(self._resolve_close_series(), length)

    def atr(self, length: int = 14, **kwargs) -> pd.Series:
        required_cols = ['high', 'low', 'close']
        if not all(col in self._df.columns for col in required_cols):
            raise ValueError(f"ATR calculation requires columns: {required_cols}")
        return atr(self._df['high'], self._df['low'], self._df['close'], length)

    def rsi(self, length: int = 14, **kwargs) -> pd.Series:
        return rsi(self._resolve_close_series(), length)


class _TADescriptor:
    """Descriptor that attaches the TA accessor to pandas DataFrames."""

    def __get__(self, instance: Optional[pd.DataFrame], owner):
        if instance is None:
            return self
        return _TAAccessor(instance)


def _add_ta_methods_to_dataframe():
    """Add .ta accessor to pandas DataFrame if pandas_ta is not available."""
    existing = getattr(pd.DataFrame, 'ta', None)
    if isinstance(existing, _TADescriptor):
        return  # Already patched by this helper
    if existing is not None and not callable(existing):
        # Respect any existing TA accessor (e.g., pandas_ta) to avoid conflicts
        return
    pd.DataFrame.ta = _TADescriptor()


# Initialize the ta methods
_add_ta_methods_to_dataframe()
