"""
MEXC-specific trading service using the mexc-api community SDK.

This module provides MEXC-specific implementations for order placement,
market data, and account operations using the mexc-api package.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status
from mexc_api.spot import Spot
from mexc_api.common.enums import Side, OrderType

logger = logging.getLogger(__name__)


class MEXCService:
    """Service class for MEXC exchange operations using mexc-api SDK."""
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize MEXC service with API credentials.
        
        Args:
            api_key: MEXC API key
            api_secret: MEXC API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = Spot(api_key, api_secret)
        logger.info("MEXC service initialized with mexc-api SDK")
    
    def format_symbol(self, symbol: str) -> str:
        """
        Format symbol for MEXC API (remove slash).
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            
        Returns:
            Formatted symbol for MEXC (e.g., 'BTCUSDT')
        """
        return symbol.replace('/', '')
    
    def format_order_params(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Format order parameters for MEXC SDK.
        
        Args:
            symbol: Trading symbol
            side: Order side ('BUY' or 'SELL')
            order_type: Order type ('MARKET' or 'LIMIT')
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            client_order_id: Optional client order ID
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing formatted order parameters
        """
        formatted_symbol = self.format_symbol(symbol)
        
        params = {
            'symbol': formatted_symbol,
            'side': Side.BUY if side.upper() == 'BUY' else Side.SELL,
            'order_type': OrderType.LIMIT if order_type.upper() == 'LIMIT' else OrderType.MARKET,
            'quantity': str(quantity),
        }
        
        # Add price for LIMIT orders
        if order_type.upper() == 'LIMIT' and price is not None:
            params['price'] = str(price)
        
        # Add client order ID if provided
        if client_order_id:
            params['newClientOrderId'] = client_order_id
        
        # Add any additional parameters
        params.update(kwargs)
        
        logger.debug(f"MEXC order parameters: {params}")
        return params
    
    def parse_order_response(self, response: Dict[str, Any], original_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse MEXC order response to match application format.
        
        Args:
            response: Raw MEXC SDK response
            original_data: Original order data
            
        Returns:
            Parsed order data for database storage
        """
        parsed_data = original_data.copy()
        
        # Extract MEXC-specific fields
        order = response.get('data', response)
        parsed_data.update({
            'exchange_order_id': str(order.get('orderId', '')),
            'symbol': order.get('symbol', original_data.get('symbol')),
            'status': self._map_mexc_status(order.get('status', 'NEW')),
            'filled_amount': float(order.get('executedQty', 0.0)),
            'remaining_amount': float(order.get('origQty', original_data.get('amount', 0.0))),
            'cost': float(order.get('cummulativeQuoteQty', 0.0)),
        })
        
        # Handle timestamp
        if order.get('time'):
            parsed_data['timestamp'] = datetime.fromtimestamp(
                int(order['time']) / 1000, tz=timezone.utc
            )
        
        # Handle fees (MEXC doesn't provide fee info in order response)
        parsed_data['fee'] = 0.0
        parsed_data['fee_currency'] = None
        
        logger.debug(f"Parsed MEXC order response: {parsed_data}")
        return parsed_data
    
    def _map_mexc_status(self, mexc_status: str) -> str:
        """
        Map MEXC order status to application status format.
        
        Args:
            mexc_status: MEXC order status
            
        Returns:
            Application status format
        """
        status_mapping = {
            'NEW': 'open',
            'PARTIALLY_FILLED': 'partially_filled',
            'FILLED': 'filled',
            'CANCELED': 'canceled',
            'PENDING_CANCEL': 'pending_cancel',
            'REJECTED': 'rejected',
            'EXPIRED': 'expired'
        }
        return status_mapping.get(mexc_status, 'unknown')
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Place an order using MEXC SDK.
        
        Args:
            symbol: Trading symbol
            side: Order side ('BUY' or 'SELL')
            order_type: Order type ('MARKET' or 'LIMIT')
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            client_order_id: Optional client order ID
            **kwargs: Additional parameters
            
        Returns:
            Order response from MEXC
            
        Raises:
            HTTPException: If order placement fails
        """
        try:
            logger.info(f"Placing MEXC order: {symbol} {side} {order_type} {quantity} @ {price or 'market'}")
            
            # Format order parameters
            order_params = self.format_order_params(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                client_order_id=client_order_id,
                **kwargs
            )
            
            # Place order using MEXC SDK
            if order_params['order_type'] == OrderType.LIMIT:
                response = self.client.account.new_order(
                    order_params['symbol'],
                    order_params['side'],
                    order_params['order_type'],
                    order_params['quantity'],
                    price=order_params.get('price'),
                    newClientOrderId=order_params.get('newClientOrderId')
                )
            else:
                response = self.client.account.new_order(
                    order_params['symbol'],
                    order_params['side'],
                    order_params['order_type'],
                    order_params['quantity'],
                    newClientOrderId=order_params.get('newClientOrderId')
                )
            logger.info(f"MEXC order placed successfully: {response}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error placing MEXC order: {e}")
            error_msg = str(e)
            
            # Handle specific MEXC errors
            if "insufficient balance" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient funds on MEXC: {error_msg}"
                )
            elif "invalid symbol" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid symbol on MEXC: {error_msg}"
                )
            elif "price" in error_msg.lower() and "precision" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Price precision error on MEXC: {error_msg}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"MEXC order placement failed: {error_msg}"
                )
    
    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Get order status from MEXC.
        
        Args:
            symbol: Trading symbol
            order_id: MEXC order ID
            
        Returns:
            Order status information
        """
        try:
            formatted_symbol = self.format_symbol(symbol)
            response = self.client.account.query_order(formatted_symbol, orderId=order_id)
            return response
        except Exception as e:
            logger.error(f"Error getting MEXC order status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get MEXC order status: {str(e)}"
            )
    
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order on MEXC.
        
        Args:
            symbol: Trading symbol
            order_id: MEXC order ID
            
        Returns:
            Cancellation response
        """
        try:
            formatted_symbol = self.format_symbol(symbol)
            response = self.client.account.cancel_order(formatted_symbol, orderId=order_id)
            return response
        except Exception as e:
            logger.error(f"Error canceling MEXC order: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel MEXC order: {str(e)}"
            )
    
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information from MEXC.
        
        Returns:
            Account information
        """
        try:
            response = self.client.account.account_information()
            return response
        except Exception as e:
            logger.error(f"Error getting MEXC account info: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get MEXC account info: {str(e)}"
            ) 