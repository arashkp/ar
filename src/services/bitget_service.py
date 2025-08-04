import ccxt.async_support as ccxt
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from fastapi import HTTPException, status
import asyncio

logger = logging.getLogger(__name__)

class BitgetService:
    """Service for interacting with Bitget exchange."""
    
    def __init__(self):
        """Initialize Bitget service."""
        self.exchange = None
        self.api_key = None
        self.api_secret = None
        self.passphrase = None  # Bitget requires passphrase
        
    async def initialize(self, api_key: str, api_secret: str, passphrase: str):
        """Initialize Bitget exchange connection."""
        try:
            self.api_key = api_key
            self.api_secret = api_secret
            self.passphrase = passphrase
            
            self.exchange = ccxt.bitget({
                'apiKey': api_key,
                'secret': api_secret,
                'password': passphrase,  # Bitget uses 'password' for passphrase
                'enableRateLimit': True,
                'sandbox': False  # Set to True for testing
            })
            
            logger.info("Bitget service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Bitget service: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize Bitget service: {str(e)}"
            )
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance from Bitget."""
        try:
            if not self.exchange:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bitget service not initialized"
                )
            
            balance = await self.exchange.fetch_balance()
            logger.info("Successfully fetched Bitget balance")
            return balance
        except Exception as e:
            logger.error(f"Failed to fetch Bitget balance: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch Bitget balance: {str(e)}"
            )
    
    async def get_spot_positions(self) -> List[Dict[str, Any]]:
        """Get current spot positions from Bitget."""
        try:
            if not self.exchange:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bitget service not initialized"
                )
            
            # Get account balance which includes spot holdings
            balance = await self.exchange.fetch_balance()
            
            positions = []
            for currency, amount in balance['total'].items():
                if amount > 0 and currency != 'USDT':
                    # Get current price for the asset
                    try:
                        symbol = f"{currency}/USDT"
                        ticker = await self.exchange.fetch_ticker(symbol)
                        current_price = ticker['last']
                    except:
                        current_price = 0
                    
                    positions.append({
                        'symbol': currency,
                        'balance': amount,
                        'current_price': current_price,
                        'value_usdt': amount * current_price
                    })
            
            logger.info(f"Successfully fetched {len(positions)} Bitget spot positions")
            return positions
        except Exception as e:
            logger.error(f"Failed to fetch Bitget spot positions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch Bitget spot positions: {str(e)}"
            )
    
    async def get_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get open orders from Bitget."""
        try:
            if not self.exchange:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bitget service not initialized"
                )
            
            orders = await self.exchange.fetch_open_orders(symbol)
            
            # Transform to match our expected format
            transformed_orders = []
            for order in orders:
                transformed_orders.append({
                    'id': order['id'],
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'type': order['type'],
                    'amount': order['amount'],
                    'price': order['price'],
                    'status': order['status'],
                    'timestamp': order['timestamp']
                })
            
            logger.info(f"Successfully fetched {len(transformed_orders)} Bitget orders")
            return transformed_orders
        except Exception as e:
            logger.error(f"Failed to fetch Bitget orders: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch Bitget orders: {str(e)}"
            )
    
    async def get_trade_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trade history from Bitget."""
        try:
            if not self.exchange:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bitget service not initialized"
                )
            
            trades = await self.exchange.fetch_my_trades(symbol, limit=limit)
            
            # Transform to match our expected format
            transformed_trades = []
            for trade in trades:
                transformed_trades.append({
                    'id': trade['id'],
                    'symbol': trade['symbol'],
                    'side': trade['side'],
                    'amount': trade['amount'],
                    'price': trade['price'],
                    'cost': trade['cost'],
                    'fee': trade['fee'],
                    'timestamp': trade['timestamp']
                })
            
            logger.info(f"Successfully fetched {len(transformed_trades)} Bitget trades")
            return transformed_trades
        except Exception as e:
            logger.error(f"Failed to fetch Bitget trade history: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch Bitget trade history: {str(e)}"
            )
    
    async def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol from Bitget."""
        try:
            if not self.exchange:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bitget service not initialized"
                )
            
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"Failed to get Bitget price for {symbol}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get Bitget price for {symbol}: {str(e)}"
            )
    
    async def get_backward_analysis(self, symbol: str = "HYPE/USDT") -> Dict[str, Any]:
        """Get backward analysis for a specific symbol (default: HYPE)."""
        try:
            if not self.exchange:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bitget service not initialized"
                )
            
            # Get current balance and price
            balance = await self.get_balance()
            current_price = await self.get_current_price(symbol)
            
            # Get trade history for the symbol
            trades = await self.get_trade_history(symbol, limit=1000)
            
            # Filter buy trades only
            buy_trades = [trade for trade in trades if trade['side'] == 'buy']
            
            # Calculate metrics
            total_buy_amount = sum(trade['amount'] for trade in buy_trades)
            total_buy_cost = sum(trade['cost'] for trade in buy_trades)
            average_entry_price = total_buy_cost / total_buy_amount if total_buy_amount > 0 else 0
            
            # Get current balance for the symbol
            symbol_balance = balance['total'].get(symbol.split('/')[0], 0)
            current_value = symbol_balance * current_price
            
            # Calculate P&L
            unrealized_pnl = current_value - total_buy_cost
            unrealized_pnl_percentage = (unrealized_pnl / total_buy_cost * 100) if total_buy_cost > 0 else 0
            
            analysis = {
                'symbol': symbol,
                'current_balance': symbol_balance,
                'current_price': current_price,
                'average_entry_price': average_entry_price,
                'total_buy_amount': total_buy_amount,
                'total_buy_cost': total_buy_cost,
                'current_value': current_value,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_percentage': unrealized_pnl_percentage,
                'number_of_orders': len(buy_trades),
                'relevant_orders': buy_trades,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Successfully generated Bitget backward analysis for {symbol}")
            return analysis
        except Exception as e:
            logger.error(f"Failed to generate Bitget backward analysis: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate Bitget backward analysis: {str(e)}"
            )
    
    async def close(self):
        """Close Bitget exchange connection."""
        if self.exchange:
            await self.exchange.close()
            logger.info("Bitget service connection closed") 