"""
Exchange utilities for the AR trading application.

This module provides centralized functions for CCXT exchange initialization,
configuration, and management to reduce code duplication across services.
"""

import logging
from typing import Optional, Dict, Any
import ccxt.async_support as ccxt
from fastapi import HTTPException, status
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Common exchange configuration parameters
DEFAULT_EXCHANGE_CONFIG = {
    'enableRateLimit': True,
    'timeout': 30000,  # 30 seconds
    'rateLimit': 1000,  # 1 second between requests
    'options': {
        'defaultType': 'spot',
    }
}

# Exchange-specific configurations
EXCHANGE_SPECIFIC_CONFIG = {
    'binance': {
        'options': {
            'defaultType': 'spot',
            'adjustForTimeDifference': True,
        }
    },
    'coinbasepro': {
        'sandbox': False,  # Set to True for testing
    },
    'kraken': {
        'timeout': 60000,  # Kraken can be slower
    },
    'mexc': {
        'timeout': 60000,  # 60 seconds timeout for MEXC (increased due to reliability issues)
        'options': {
            'defaultType': 'spot',
        }
    }
}


def get_exchange_config(exchange_id: str, is_spot: bool = True, **kwargs) -> Dict[str, Any]:
    """
    Get configuration for a specific exchange.
    
    Args:
        exchange_id: The exchange identifier
        is_spot: Whether this is for spot trading (vs futures)
        **kwargs: Additional configuration parameters
        
    Returns:
        Dictionary containing exchange configuration
    """
    config = DEFAULT_EXCHANGE_CONFIG.copy()

    # Add exchange-specific configuration
    if exchange_id in EXCHANGE_SPECIFIC_CONFIG:
        config.update(EXCHANGE_SPECIFIC_CONFIG[exchange_id])

    # Override with provided kwargs
    config.update(kwargs)

    # Set market type based on is_spot parameter
    if not is_spot:
        config.setdefault('options', {})
        config['options']['defaultType'] = 'future'

    return config


def initialize_mexc_sdk(api_key: str, api_secret: str):
    """
    Initialize MEXC SDK client.
    
    Args:
        api_key: MEXC API key
        api_secret: MEXC API secret
        
    Returns:
        MEXC SDK Spot client instance
        
    Raises:
        HTTPException: If MEXC SDK initialization fails
    """
    try:
        from mexc_sdk import Spot
        client = Spot(api_key=api_key, api_secret=api_secret)
        logger.info("MEXC SDK initialized successfully")
        return client
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MEXC SDK not installed. Please install with: pip install mexc-sdk"
        )
    except Exception as e:
        logger.error(f"Failed to initialize MEXC SDK: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize MEXC SDK: {str(e)}"
        )


async def initialize_exchange(
        exchange_id: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        is_spot: bool = True,
        **kwargs
) -> ccxt.Exchange:
    """
    Initialize and return a CCXT exchange instance.
    
    Args:
        exchange_id: The exchange identifier
        api_key: API key for authentication
        api_secret: API secret for authentication
        is_spot: Whether this is for spot trading
        **kwargs: Additional configuration parameters
        
    Returns:
        Initialized CCXT exchange instance
        
    Raises:
        HTTPException: If exchange initialization fails
    """
    try:
        # Get exchange class
        exchange_class = getattr(ccxt, exchange_id)

        # Prepare configuration
        config = get_exchange_config(exchange_id, is_spot, **kwargs)

        # Add API credentials if provided
        if api_key and api_secret:
            config['apiKey'] = api_key
            config['secret'] = api_secret

        # Create exchange instance
        exchange = exchange_class(config)

        # logger.debug(f"Initialized {exchange_id} exchange instance")
        # logger.info(f"Exchange config: {config}")
        logger.info(f"Exchange has create_order: {hasattr(exchange, 'create_order')}")
        return exchange

    except AttributeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exchange {exchange_id} not found or not supported"
        )
    except Exception as e:
        logger.error(f"Failed to initialize {exchange_id} exchange: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize {exchange_id} exchange: {str(e)}"
        )


async def validate_exchange_capability(
        exchange: ccxt.Exchange,
        capability: str,
        exchange_id: str
) -> None:
    """
    Validate that an exchange supports a specific capability.
    
    Args:
        exchange: The CCXT exchange instance
        capability: The capability to check (e.g., 'fetchOHLCV', 'fetchBalance')
        exchange_id: The exchange identifier for error messages
        
    Raises:
        HTTPException: If the capability is not supported
    """
    if not exchange.has.get(capability, False):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Exchange {exchange_id} does not support {capability}"
        )


async def validate_symbol(
        exchange: ccxt.Exchange,
        symbol: str,
        exchange_id: str
) -> None:
    """
    Validate that a symbol is available on the exchange.
    
    Args:
        exchange: The CCXT exchange instance
        symbol: The trading symbol to validate
        exchange_id: The exchange identifier for error messages
        
    Raises:
        HTTPException: If the symbol is not available
    """
    try:
        markets = await exchange.load_markets()
        if symbol not in markets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Symbol {symbol} not available on {exchange_id}"
            )
    except Exception as e:
        logger.error(f"Error validating symbol {symbol} on {exchange_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating symbol {symbol} on {exchange_id}: {str(e)}"
        )


@asynccontextmanager
async def safe_exchange_operation(
        exchange: ccxt.Exchange,
        operation: str,
        exchange_id: str,
        cleanup: bool = True
):
    """
    Context manager for safe exchange operations with proper cleanup.
    
    Args:
        exchange: The CCXT exchange instance
        operation: Description of the operation being performed
        exchange_id: The exchange identifier
        cleanup: Whether to close the exchange connection after operation
        
    Yields:
        The exchange instance
        
    Raises:
        HTTPException: If the operation fails
    """
    try:
        yield exchange
    except Exception as e:
        logger.error(f"Error during {operation} on {exchange_id}: {e}")
        raise
    finally:
        if cleanup and hasattr(exchange, 'close'):
            try:
                await exchange.close()
                logger.debug(f"Closed {exchange_id} exchange connection")
            except Exception as e:
                logger.warning(f"Error closing {exchange_id} exchange connection: {e}")


def format_order_params(
        order_type: str,
        side: str,
        amount: float,
        symbol: str,
        price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        **kwargs
) -> Dict[str, Any]:
    """
    Format order parameters for CCXT create_order call.
    
    Args:
        order_type: The order type ('market', 'limit', etc.)
        side: The order side ('buy', 'sell')
        amount: The order amount
        symbol: The trading symbol
        price: The order price (required for limit orders)
        client_order_id: Optional client order ID
        **kwargs: Additional order parameters
        
    Returns:
        Dictionary containing formatted order parameters
    """
    # Convert symbol format (remove slash for MEXC)
    formatted_symbol = symbol.replace('/', '')

    params = {
        'symbol': formatted_symbol,
        'type': order_type.upper(),
        'side': side.upper(),
        'amount': amount,  # CCXT uses 'amount' as the standardized parameter name
    }

    # Add price for limit orders
    if price is not None:
        params['price'] = price

    # Add client order ID if provided
    if client_order_id:
        params['params'] = {'newClientOrderId': client_order_id}  # Put exchange-specific params in 'params'

    # Add any additional parameters
    if kwargs:
        params.setdefault('params', {}).update(kwargs)

    return params


def parse_exchange_response(
        response: Dict[str, Any],
        order_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Parse and format exchange response for database storage.
    
    Args:
        response: The raw exchange response
        order_data: The original order data
        
    Returns:
        Dictionary containing parsed order data for database storage
    """
    from datetime import datetime, timezone

    parsed_data = order_data.copy()

    # Extract exchange-specific fields
    parsed_data.update({
        'exchange_order_id': str(response.get('id', '')),
        'symbol': response.get('symbol', order_data.get('symbol')),
        'status': response.get('status', 'open'),
        'filled_amount': response.get('filled', 0.0),
        'remaining_amount': response.get('remaining', order_data.get('amount', 0.0)),
        'cost': response.get('cost', 0.0),
    })

    # Handle timestamp
    if response.get('timestamp'):
        parsed_data['timestamp'] = datetime.fromtimestamp(
            response['timestamp'] / 1000, tz=timezone.utc
        )

    # Handle fees
    fee_info = response.get('fee', {})
    if isinstance(fee_info, dict):
        parsed_data['fee'] = fee_info.get('cost')
        parsed_data['fee_currency'] = fee_info.get('currency')
    else:
        parsed_data['fee'] = fee_info

    return parsed_data
