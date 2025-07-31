"""
Abstract exchange interface for the AR trading application.

This module provides a common interface for all exchange operations,
allowing easy integration of new exchanges while maintaining consistent
API patterns across the application.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class OrderStatus(Enum):
    """Enumeration for order statuses."""
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PENDING = "pending"


class OrderSide(Enum):
    """Enumeration for order sides."""
    BUY = "buy"
    SELL = "sell"


@dataclass
class SpotPosition:
    """Data class for spot position information."""
    symbol: str
    base_asset: str
    quote_asset: str
    quantity: float
    average_entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percentage: float
    total_value: float
    last_updated: datetime


@dataclass
class SpotOrder:
    """Data class for spot order information."""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: str
    quantity: float
    price: Optional[float]
    filled_quantity: float
    remaining_quantity: float
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    client_order_id: Optional[str] = None


@dataclass
class SpotTrade:
    """Data class for spot trade information."""
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    fee: float
    fee_asset: str
    timestamp: datetime
    taker: bool


class ExchangeInterface(ABC):
    """
    Abstract base class for exchange operations.
    
    This interface defines the common methods that all exchange implementations
    must provide, ensuring consistency across different exchanges.
    """
    
    def __init__(self, api_key: str, api_secret: str, **kwargs):
        """
        Initialize the exchange interface.
        
        Args:
            api_key: API key for authentication
            api_secret: API secret for authentication
            **kwargs: Additional exchange-specific configuration
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.exchange_name = self.__class__.__name__.replace('Service', '')
        self._client = None
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the exchange client.
        
        This method should set up the exchange-specific client
        and perform any necessary authentication.
        """
        pass
    
    @abstractmethod
    async def get_spot_positions(self) -> List[SpotPosition]:
        """
        Fetch current spot positions.
        
        Returns:
            List of current spot positions with PnL calculations
        """
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[SpotOrder]:
        """
        Fetch open spot orders.
        
        Args:
            symbol: Optional symbol filter (e.g., 'BTC/USDT')
            
        Returns:
            List of open spot orders
        """
        pass
    
    @abstractmethod
    async def get_trade_history(
        self, 
        symbol: Optional[str] = None, 
        limit: int = 25,
        since: Optional[datetime] = None
    ) -> List[SpotTrade]:
        """
        Fetch historical spot trades.
        
        Args:
            symbol: Optional symbol filter (e.g., 'BTC/USDT')
            limit: Maximum number of trades to return
            since: Optional start time for filtering
            
        Returns:
            List of historical spot trades
        """
        pass
    
    @abstractmethod
    async def get_account_balance(self) -> Dict[str, float]:
        """
        Fetch account balance.
        
        Returns:
            Dictionary mapping asset symbols to balances
        """
        pass
    
    @abstractmethod
    async def get_ticker_price(self, symbol: str) -> float:
        """
        Get current price for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            
        Returns:
            Current price as float
        """
        pass
    
    async def calculate_position_pnl(self, position: SpotPosition) -> SpotPosition:
        """
        Calculate PnL for a position using current market price.
        
        Args:
            position: Position to calculate PnL for
            
        Returns:
            Updated position with PnL calculations
        """
        try:
            current_price = await self.get_ticker_price(position.symbol)
            total_value = position.quantity * current_price
            unrealized_pnl = (current_price - position.average_entry_price) * position.quantity
            unrealized_pnl_percentage = (
                (current_price - position.average_entry_price) / position.average_entry_price * 100
            ) if position.average_entry_price > 0 else 0
            
            return SpotPosition(
                symbol=position.symbol,
                base_asset=position.base_asset,
                quote_asset=position.quote_asset,
                quantity=position.quantity,
                average_entry_price=position.average_entry_price,
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percentage=unrealized_pnl_percentage,
                total_value=total_value,
                last_updated=datetime.utcnow()
            )
        except Exception as e:
            # Return position with existing PnL if calculation fails
            return position
    
    async def close(self) -> None:
        """
        Close the exchange connection.
        
        This method should clean up any open connections
        or resources used by the exchange client.
        """
        if self._client:
            if hasattr(self._client, 'close'):
                await self._client.close()
            self._client = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule cleanup for later if we're in an async context
                loop.create_task(self.close())
            else:
                loop.run_until_complete(self.close())
        except RuntimeError:
            # No event loop, skip cleanup
            pass 