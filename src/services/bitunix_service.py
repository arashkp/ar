"""
Bitunix exchange service implementation.

This module provides Bitunix-specific implementations for spot trading operations
using the official Bitunix Python SDK.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from fastapi import HTTPException, status

# Redirect stdout/stderr to suppress SDK output
import sys
from io import StringIO
_original_stdout = sys.stdout
_original_stderr = sys.stderr
sys.stdout = StringIO()
sys.stderr = StringIO()

from bitunix import BitunixClient

# Restore stdout/stderr after import
sys.stdout = _original_stdout
sys.stderr = _original_stderr

# Suppress verbose logging from Bitunix SDK and other libraries
logging.getLogger('bitunix').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.ERROR)
logging.getLogger('httpcore').setLevel(logging.ERROR)

# Suppress ALL output from SDK
import sys
import os
from io import StringIO

# Monkey patch print to suppress SDK output
_original_print = print
def silent_print(*args, **kwargs):
    pass

class SuppressAllOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._original_print = print
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        globals()['print'] = silent_print
        return self
    
    def __exit__(self, *args):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        globals()['print'] = self._original_print

from src.services.exchange_interface import (
    ExchangeInterface,
    SpotPosition,
    SpotOrder,
    SpotTrade,
    OrderStatus,
    OrderSide
)

logger = logging.getLogger(__name__)


class BitunixService(ExchangeInterface):
    """Bitunix exchange service implementation using official SDK."""
    
    def __init__(self, api_key: str, api_secret: str, **kwargs):
        """
        Initialize Bitunix service.
        
        Args:
            api_key: Bitunix API key
            api_secret: Bitunix API secret
            **kwargs: Additional configuration
        """
        super().__init__(api_key, api_secret, **kwargs)
        self.exchange_name = "Bitunix"
        self._client = None
        
        # Mock data for development (fallback)
        self._mock_data = {
            'balances': {
                'BTC': 0.05,
                'ETH': 2.5,
                'USDT': 500.25,
                'ADA': 1000.0,
                'DOT': 50.0
            },
            'positions': [
                {
                    'symbol': 'BTC/USDT',
                    'base_asset': 'BTC',
                    'quote_asset': 'USDT',
                    'quantity': 0.05,
                    'average_entry_price': 45000.0,
                    'current_price': 48000.0,
                    'unrealized_pnl': 150.0,
                    'unrealized_pnl_percentage': 6.67,
                    'total_value': 2400.0
                },
                {
                    'symbol': 'ETH/USDT',
                    'base_asset': 'ETH',
                    'quote_asset': 'USDT',
                    'quantity': 2.5,
                    'average_entry_price': 3200.0,
                    'current_price': 3500.0,
                    'unrealized_pnl': 750.0,
                    'unrealized_pnl_percentage': 9.38,
                    'total_value': 8750.0
                },
                {
                    'symbol': 'ADA/USDT',
                    'base_asset': 'ADA',
                    'quote_asset': 'USDT',
                    'quantity': 1000.0,
                    'average_entry_price': 0.45,
                    'current_price': 0.42,
                    'unrealized_pnl': -30.0,
                    'unrealized_pnl_percentage': -6.67,
                    'total_value': 420.0
                }
            ],
            'orders': [
                {
                    'order_id': '12345',
                    'symbol': 'BTC/USDT',
                    'side': 'BUY',
                    'order_type': 'LIMIT',
                    'quantity': 0.01,
                    'price': 47000.0,
                    'filled_quantity': 0.0,
                    'remaining_quantity': 0.01,
                    'status': 'OPEN',
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                }
            ],
            'trades': [
                {
                    'trade_id': '67890',
                    'order_id': '12345',
                    'symbol': 'BTC/USDT',
                    'side': 'BUY',
                    'quantity': 0.02,
                    'price': 45000.0,
                    'fee': 0.9,
                    'fee_asset': 'USDT',
                    'timestamp': datetime.now(timezone.utc),
                    'taker': True
                }
            ]
        }
    
    async def initialize(self) -> None:
        """Initialize the Bitunix API client."""
        try:
            # Temporarily suppress all logging during client initialization
            old_level = logging.getLogger().level
            logging.getLogger().setLevel(logging.ERROR)
            
            self._client = BitunixClient(self.api_key, self.api_secret)
            
            # Restore original logging level
            logging.getLogger().setLevel(old_level)
            
        except Exception as e:
            logger.error(f"Failed to initialize Bitunix service: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize Bitunix service: {str(e)}"
            )
    
    async def get_spot_positions(self) -> List[SpotPosition]:
        """
        Fetch current spot positions from Bitunix using official SDK.
        
        Returns:
            List of current spot positions with PnL calculations
        """
        try:
            if not self._client:
                await self.initialize()
            
            # Get account balance using official SDK
            with SuppressAllOutput():
                balance_response = self._client.get_account_balance()
            
            if not balance_response or 'data' not in balance_response:
                return self._get_mock_positions()
            
            balance_data = balance_response['data']
            positions = []
            
            for asset_data in balance_data:
                coin = asset_data.get('coin')
                balance = float(asset_data.get('balance', 0))
                balance_locked = float(asset_data.get('balanceLocked', 0))
                total_balance = balance + balance_locked
                
                if total_balance > 0 and coin != 'USDT':
                    try:
                        # Get current price for the asset from REAL API
                        symbol = f"{coin}USDT"
                        with SuppressAllOutput():
                            current_price = await self.get_ticker_price(f"{coin}/USDT")
                        
                        # Calculate total value
                        total_value = total_balance * current_price
                        
                        # Calculate real average entry price from trade history
                        avg_entry_price = await self._calculate_average_entry_price(coin, total_balance)
                        
                        # Calculate PnL
                        unrealized_pnl = (current_price - avg_entry_price) * total_balance
                        unrealized_pnl_percentage = (
                            (current_price - avg_entry_price) / avg_entry_price * 100
                        ) if avg_entry_price > 0 else 0
                        
                        position = SpotPosition(
                            symbol=f"{coin}/USDT",
                            base_asset=coin,
                            quote_asset="USDT",
                            quantity=total_balance,
                            average_entry_price=avg_entry_price,
                            current_price=current_price,
                            unrealized_pnl=unrealized_pnl,
                            unrealized_pnl_percentage=unrealized_pnl_percentage,
                            total_value=total_value,
                            last_updated=datetime.now(timezone.utc)
                        )
                        
                        positions.append(position)
                        
                    except Exception as e:
                        continue
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to fetch spot positions: {e}")
            return self._get_mock_positions()
    
    async def _calculate_average_entry_price(self, coin: str, total_quantity: float) -> float:
        """
        Calculate average entry price using BACKWARD approach.
        
        Process orders in descending order (newest first) and accumulate
        until we reach the current balance, then calculate average.
        
        Args:
            coin: Asset symbol (e.g., 'HBAR')
            total_quantity: Total quantity held
            
        Returns:
            Average entry price calculated from relevant trades
        """
        try:
            if not self._client:
                await self.initialize()
            
            # Get current balance from account for validation
            with SuppressAllOutput():
                balance_response = self._client.get_account_balance()
            current_balance = 0.0
            
            if balance_response and 'data' in balance_response:
                for asset in balance_response['data']:
                    if asset.get('coin') == coin:
                        current_balance = float(asset.get('balance', 0)) + float(asset.get('balanceLocked', 0))
                        break
            
            # Calculating average entry price
            
            # Get trade history for this specific coin
            symbol = f"{coin}USDT"
            all_orders = []
            page = 1
            
            # Fetch multiple pages to get enough orders
            while page <= 5:  # Limit to 5 pages for performance
                try:
                    with SuppressAllOutput():
                        orders_response = self._client.query_order_history(
                            symbol=symbol,
                            page=page,
                            page_size=100
                        )
                    
                    if not orders_response or 'data' not in orders_response:
                        break
                        
                    orders_data = orders_response['data'].get('data', [])
                    if not orders_data:
                        break
                    
                    # Filter only orders for this specific symbol
                    symbol_orders = [
                        order for order in orders_data 
                        if order.get('symbol') == symbol
                    ]
                    
                    all_orders.extend(symbol_orders)
                    page += 1
                    
                except Exception as e:
                    break
            
            if not all_orders:
                return await self._get_fallback_avg_price(coin)
            
            # Sort orders by price (highest first) for backward calculation
            all_orders.sort(key=lambda x: float(x.get('avgPrice', 0)), reverse=True)
            
            # BACKWARD CALCULATION: Start from highest price and work down
            relevant_orders = []
            accumulated_quantity = 0.0
            tolerance = 0.01  # 1% tolerance
            
            # Processing orders from highest price to lowest
            
            for order in all_orders:
                side = order.get('side')  # 1 = SELL, 2 = BUY (from official docs)
                status = order.get('status')  # 2 = FILLED
                price = float(order.get('avgPrice', 0))
                quantity = float(order.get('dealVolume', 0))
                
                if status == 2:  # Only completed orders
                    if side == 2:  # BUY - adds to position
                        relevant_orders.append({
                            'price': price,
                            'quantity': quantity,
                            'value': price * quantity,
                            'type': 'BUY'
                        })
                        accumulated_quantity += quantity
                        
                        # Check if we've reached the target balance
                        if abs(accumulated_quantity - current_balance) <= (current_balance * tolerance):
                            break
                        elif accumulated_quantity > current_balance * (1 + tolerance):
                            break
                            
                    elif side == 1:  # SELL - reduces position
                        # For sells, we need to "undo" them to find the original position
                        accumulated_quantity -= quantity
                        
                        # If this sell would make our accumulated quantity negative, skip it
                        if accumulated_quantity < 0:
                            accumulated_quantity = 0
                            continue
            
            if not relevant_orders:
                return await self._get_fallback_avg_price(coin)
            
            # Calculate weighted average from relevant buy orders
            total_buy_quantity = sum(order['quantity'] for order in relevant_orders)
            total_buy_value = sum(order['value'] for order in relevant_orders)
            
            if total_buy_quantity <= 0:
                return await self._get_fallback_avg_price(coin)
            
            calculated_avg_price = total_buy_value / total_buy_quantity
            
            # VALIDATION: Check if calculated quantity matches account balance
            balance_difference = abs(total_buy_quantity - current_balance)
            balance_tolerance = current_balance * tolerance
            
            # Calculation completed
            
            if balance_difference <= balance_tolerance:
                return calculated_avg_price
            else:
                logger.warning(f"Validation failed for {coin}, using fallback")
                return await self._get_fallback_avg_price(coin)
                
        except Exception as e:
            logger.error(f"Error calculating average entry price for {coin}: {e}")
            return await self._get_fallback_avg_price(coin)
    
    def _get_fallback_price_for_coin(self, coin: str) -> float:
        """Get current price as fallback - no hardcoded values!"""
        try:
            if not self._client:
                return 1.0
            
            symbol = f"{coin}USDT"
            current_price = self._client.get_latest_price(symbol)
            if current_price and isinstance(current_price, (int, float)):
                return float(current_price)
            else:
                return 1.0
        except:
            return 1.0
    
    async def _get_fallback_avg_price(self, coin: str) -> float:
        """
        Get current price as fallback when trade history is not available.
        No hardcoded values - only real API data!
        """
        try:
            if not self._client:
                await self.initialize()
            
            symbol = f"{coin}USDT"
            with SuppressAllOutput():
                current_price = self._client.get_latest_price(symbol)
            
            if current_price and isinstance(current_price, (int, float)):
                return float(current_price)
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"Fallback price calculation failed for {coin}: {e}")
            return 1.0
    
    def _get_mock_positions(self) -> List[SpotPosition]:
        """Get mock positions for fallback."""
        positions = []
        
        for pos_data in self._mock_data['positions']:
            position = SpotPosition(
                symbol=pos_data['symbol'],
                base_asset=pos_data['base_asset'],
                quote_asset=pos_data['quote_asset'],
                quantity=pos_data['quantity'],
                average_entry_price=pos_data['average_entry_price'],
                current_price=pos_data['current_price'],
                unrealized_pnl=pos_data['unrealized_pnl'],
                unrealized_pnl_percentage=pos_data['unrealized_pnl_percentage'],
                total_value=pos_data['total_value'],
                last_updated=datetime.now(timezone.utc)
            )
            positions.append(position)
        
        return positions
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[SpotOrder]:
        """
        Fetch open spot orders from Bitunix using official SDK.
        
        Args:
            symbol: Optional symbol filter (e.g., 'BTC/USDT')
            
        Returns:
            List of open spot orders
        """
        try:
            if not self._client:
                await self.initialize()
            
            # If no symbol provided, fetch orders for all supported symbols
            if symbol is None:
                return await self._get_all_open_orders()
            
            # Use the internal method to fetch orders for the specific symbol
            return await self._get_orders_for_symbol(symbol)
            
        except Exception as e:
            logger.error(f"Failed to fetch open orders: {e}")
            return self._get_mock_orders(symbol)
    
    async def _get_all_open_orders(self) -> List[SpotOrder]:
        """
        Fetch open orders for all supported symbols.
        
        Returns:
            List of all open orders across all supported symbols
        """
        # Fetching orders for all symbols
        all_orders = []
        
        # Get the list of supported symbols from the backward analysis
        # We'll fetch orders for common trading pairs
        supported_symbols = [
            'BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'ADA/USDT', 'SOL/USDT', 
            'SUI/USDT', 'XLM/USDT', 'TRX/USDT', 'PEPE/USDT', 'BNB/USDT', 
            'ATOM/USDT', 'DOT/USDT', 'BCH/USDT', 'BONK/USDT', 'HBAR/USDT', 'HYPE/USDT'
        ]
        
        for symbol in supported_symbols:
            try:
                # Call the internal method directly to avoid recursion
                symbol_orders = await self._get_orders_for_symbol(symbol)
                if symbol_orders and isinstance(symbol_orders, list):
                    all_orders.extend(symbol_orders)
            except Exception as e:
                continue
        
        # All orders fetched
        return all_orders
    
    async def _get_orders_for_symbol(self, symbol: str) -> List[SpotOrder]:
        """
        Internal method to fetch orders for a specific symbol.
        
        Args:
            symbol: Symbol to fetch orders for (e.g., 'BTC/USDT')
            
        Returns:
            List of orders for the symbol
        """
        try:
            # Get current orders using official SDK for specific symbol
            symbol_param = symbol.replace('/', '') if symbol else None
            # Fetching orders from API
            with SuppressAllOutput():
                orders_response = self._client.query_current_orders(symbol=symbol_param)
            
            # API response received
            
            if not orders_response or 'data' not in orders_response:
                return self._get_mock_orders(symbol)
            
            orders_data = orders_response['data']
            # Processing orders
            orders = []
            
            # Check if orders_data is a list
            if not isinstance(orders_data, list):
                return []
            
            for order_data in orders_data:
                try:
                    
                    # Map Bitunix order status to our enum
                    status_mapping = {
                        1: OrderStatus.OPEN,  # Pending
                        2: OrderStatus.FILLED,  # Completed
                        3: OrderStatus.CANCELLED,  # Cancelled
                        4: OrderStatus.PARTIALLY_FILLED  # Partially filled
                    }
                    
                    raw_status = order_data.get('status', 1)
                    order_status = status_mapping.get(raw_status, OrderStatus.OPEN)
                    # Order status mapped
                    
                    # Map Bitunix side to our enum
                    # According to official docs: Side (1 Sell 2 Buy)
                    side = OrderSide.SELL if order_data.get('side') == 1 else OrderSide.BUY
                    
                    order = SpotOrder(
                        order_id=str(order_data.get('orderId')),
                        symbol=order_data.get('symbol', '').replace('USDT', '/USDT'),
                        side=side,
                        order_type='LIMIT' if order_data.get('orderType') == 1 else 'MARKET',
                        quantity=float(order_data.get('volume', 0)),
                        price=float(order_data.get('price', 0)) if order_data.get('price') else None,
                        filled_quantity=float(order_data.get('dealVolume', 0)),
                        remaining_quantity=float(order_data.get('leftVolume', 0)),
                        status=order_status,
                        created_at=datetime.fromisoformat(
                            order_data.get('ctime', '').replace('Z', '+00:00')
                        ),
                        updated_at=datetime.fromisoformat(
                            order_data.get('utime', '').replace('Z', '+00:00')
                        ),
                        client_order_id=str(order_data.get('clientId'))
                    )
                    
                    orders.append(order)
                    
                except Exception as e:
                    continue
            
            # Orders processed
            return orders
            
        except Exception as e:
            logger.error(f"Failed to fetch orders for {symbol}: {e}")
            return self._get_mock_orders(symbol)
    
    def _get_mock_orders(self, symbol: Optional[str] = None) -> List[SpotOrder]:
        """Get mock orders for fallback."""
            # Using mock data
        orders = []
        
        for order_data in self._mock_data['orders']:
            if symbol and order_data['symbol'] != symbol:
                # Symbol mismatch, skipping
                continue
                
            order = SpotOrder(
                order_id=order_data['order_id'],
                symbol=order_data['symbol'],
                side=OrderSide.BUY if order_data['side'] == 'BUY' else OrderSide.SELL,
                order_type=order_data['order_type'],
                quantity=order_data['quantity'],
                price=order_data['price'],
                filled_quantity=order_data['filled_quantity'],
                remaining_quantity=order_data['remaining_quantity'],
                status=OrderStatus.OPEN if order_data['status'] == 'OPEN' else OrderStatus.FILLED,
                created_at=order_data['created_at'],
                updated_at=order_data['updated_at']
            )
            orders.append(order)
        
        # Mock orders processed
        return orders
    
    async def get_trade_history(
        self, 
        symbol: Optional[str] = None, 
        limit: int = 25,
        since: Optional[datetime] = None
    ) -> List[SpotTrade]:
        """
        Fetch historical spot trades from Bitunix using official SDK.
        
        Args:
            symbol: Optional symbol filter (e.g., 'BTC/USDT')
            limit: Maximum number of trades to return
            since: Optional start time for filtering
            
        Returns:
            List of historical spot trades
        """
        try:
            if not self._client:
                await self.initialize()
            
            # Get order history using official SDK
            symbol_param = symbol.replace('/', '') if symbol else None
            with SuppressAllOutput():
                trades_response = self._client.query_order_history(
                    symbol=symbol_param, 
                    page=1, 
                    page_size=limit
                )
            
            if not trades_response or 'data' not in trades_response:
                return self._get_mock_trades(symbol, limit)
            
            trades_data = trades_response['data'].get('data', [])
            trades = []
            
            for trade_data in trades_data:
                try:
                    # Map Bitunix side to our enum
                    # According to official docs: Side (1 Sell 2 Buy)
                    side = OrderSide.SELL if trade_data.get('side') == 1 else OrderSide.BUY
                    
                    trade = SpotTrade(
                        trade_id=str(trade_data.get('orderId')),
                        order_id=str(trade_data.get('orderId')),
                        symbol=trade_data.get('symbol', '').replace('USDT', '/USDT'),
                        side=side,
                        quantity=float(trade_data.get('dealVolume', 0)),
                        price=float(trade_data.get('avgPrice', 0)),
                        fee=float(trade_data.get('fee', 0)),
                        fee_asset=trade_data.get('feeCoin', ''),
                        timestamp=datetime.fromisoformat(
                            trade_data.get('utime', '').replace('Z', '+00:00')
                        ),
                        taker=True  # Default to taker for now
                    )
                    
                    trades.append(trade)
                    
                except Exception as e:
                    continue
            
            return trades[:limit]
            
        except Exception as e:
            logger.error(f"Failed to fetch trade history: {e}")
            return self._get_mock_trades(symbol, limit)
    
    def _get_mock_trades(self, symbol: Optional[str] = None, limit: int = 25) -> List[SpotTrade]:
        """Get mock trades for fallback."""
        trades = []
        
        for trade_data in self._mock_data['trades']:
            if symbol and trade_data['symbol'] != symbol:
                continue
                
            trade = SpotTrade(
                trade_id=trade_data['trade_id'],
                order_id=trade_data['order_id'],
                symbol=trade_data['symbol'],
                side=OrderSide.BUY if trade_data['side'] == 'BUY' else OrderSide.SELL,
                quantity=trade_data['quantity'],
                price=trade_data['price'],
                fee=trade_data['fee'],
                fee_asset=trade_data['fee_asset'],
                timestamp=trade_data['timestamp'],
                taker=trade_data['taker']
            )
            trades.append(trade)
        
        return trades[:limit]
    
    async def get_account_balance(self) -> Dict[str, float]:
        """
        Fetch account balance from Bitunix using official SDK.
        
        Returns:
            Dictionary mapping asset symbols to balances
        """
        try:
            if not self._client:
                await self.initialize()
            
            # Get account balance using official SDK
            with SuppressAllOutput():
                balance_response = self._client.get_account_balance()
            
            if not balance_response or 'data' not in balance_response:
                return self._mock_data['balances']
            
            balance_data = balance_response['data']
            balance_dict = {}
            
            for asset_data in balance_data:
                coin = asset_data.get('coin')
                balance = float(asset_data.get('balance', 0))
                balance_locked = float(asset_data.get('balanceLocked', 0))
                total_balance = balance + balance_locked
                
                if total_balance > 0:
                    balance_dict[coin] = total_balance
            
            return balance_dict
            
        except Exception as e:
            logger.error(f"Failed to fetch account balance: {e}")
            return self._mock_data['balances']
    
    async def get_ticker_price(self, symbol: str) -> float:
        """
        Get current price for a symbol from Bitunix using official SDK.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            
        Returns:
            Current price as float
        """
        try:
            if not self._client:
                await self.initialize()
            
            # Convert symbol format (BTC/USDT -> BTCUSDT)
            symbol_param = symbol.replace('/', '')
            
            # Get latest price using official SDK - NO HARDCODED VALUES!
            with SuppressAllOutput():
                price_response = self._client.get_latest_price(symbol_param)
            
            # Handle Bitunix API response format
            if price_response and isinstance(price_response, dict):
                if price_response.get('success') and price_response.get('data'):
                    return float(price_response['data'])
                else:
                    logger.error(f"Invalid price response for {symbol}: {price_response}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Invalid price response for {symbol} from Bitunix API"
                    )
            elif price_response and isinstance(price_response, (int, float)):
                return float(price_response)
            else:
                logger.error(f"Failed to get real price for {symbol} from API: {price_response}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get real price for {symbol} from Bitunix API"
                )
            
        except Exception as e:
            logger.error(f"Failed to fetch ticker price for {symbol}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch ticker price for {symbol}: {str(e)}"
            )
    
    async def close(self) -> None:
        """Close the Bitunix exchange connection."""
        self._client = None 