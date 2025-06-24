"""
Centralized error handling utilities for the AR trading application.

This module provides decorators and helper functions to standardize error handling
across routers and services, reducing code duplication and ensuring consistent
error responses.
"""

import logging
import functools
from typing import Callable, Any, Optional, Type
from fastapi import HTTPException, status
import ccxt

logger = logging.getLogger(__name__)

# Common error mappings for CCXT exceptions
CCXT_ERROR_MAPPINGS = {
    ccxt.AuthenticationError: (status.HTTP_401_UNAUTHORIZED, "Authentication failed"),
    ccxt.InsufficientFunds: (status.HTTP_400_BAD_REQUEST, "Insufficient funds"),
    ccxt.NetworkError: (status.HTTP_502_BAD_GATEWAY, "Network error"),
    ccxt.RateLimitExceeded: (status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded"),
    ccxt.BadSymbol: (status.HTTP_400_BAD_REQUEST, "Invalid symbol"),
    ccxt.ExchangeError: (status.HTTP_500_INTERNAL_SERVER_ERROR, "Exchange error"),
    ccxt.InvalidOrder: (status.HTTP_400_BAD_REQUEST, "Invalid order"),
    ccxt.OrderNotFound: (status.HTTP_404_NOT_FOUND, "Order not found"),
}

def handle_ccxt_exception(exchange_id: str, operation: str, exception: Exception) -> HTTPException:
    """
    Handle CCXT exceptions and return appropriate HTTPException.
    
    Args:
        exchange_id: The exchange identifier
        operation: Description of the operation being performed
        exception: The CCXT exception that was raised
        
    Returns:
        HTTPException with appropriate status code and detail
    """
    exception_type = type(exception)
    
    if exception_type in CCXT_ERROR_MAPPINGS:
        status_code, base_message = CCXT_ERROR_MAPPINGS[exception_type]
        detail = f"{base_message} for {exchange_id} during {operation}: {str(exception)}"
        return HTTPException(status_code=status_code, detail=detail)
    
    # Default handling for unknown CCXT exceptions
    logger.error(f"Unhandled CCXT exception for {exchange_id} during {operation}: {exception}", exc_info=True)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unexpected exchange error for {exchange_id} during {operation}: {str(exception)}"
    )

def handle_generic_exception(operation: str, exception: Exception, log_error: bool = True) -> HTTPException:
    """
    Handle generic exceptions and return appropriate HTTPException.
    
    Args:
        operation: Description of the operation being performed
        exception: The exception that was raised
        log_error: Whether to log the error (default: True)
        
    Returns:
        HTTPException with appropriate status code and detail
    """
    if isinstance(exception, HTTPException):
        return exception
    
    if log_error:
        logger.error(f"Error during {operation}: {exception}", exc_info=True)
    
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"An unexpected error occurred during {operation}: {str(exception)}"
    )

def api_error_handler(operation: str, log_error: bool = True):
    """
    Decorator for handling API errors in router endpoints.
    
    Args:
        operation: Description of the operation being performed
        log_error: Whether to log errors (default: True)
        
    Returns:
        Decorated function with error handling
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTPExceptions directly
                raise
            except Exception as e:
                # Handle all other exceptions
                raise handle_generic_exception(operation, e, log_error)
        return wrapper
    return decorator

def exchange_error_handler(exchange_id_param: str = "exchange_id", operation: str = "exchange operation"):
    """
    Decorator for handling exchange-related errors in router endpoints.
    
    Args:
        exchange_id_param: Name of the parameter containing exchange_id
        operation: Description of the operation being performed
        
    Returns:
        Decorated function with exchange error handling
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTPExceptions directly
                raise
            except Exception as e:
                # Get exchange_id from kwargs or function signature
                exchange_id = kwargs.get(exchange_id_param, "unknown")
                
                # Check if it's a CCXT exception
                if any(isinstance(e, ccxt_exc) for ccxt_exc in CCXT_ERROR_MAPPINGS.keys()):
                    raise handle_ccxt_exception(exchange_id, operation, e)
                else:
                    # Handle generic exceptions
                    raise handle_generic_exception(operation, e)
        return wrapper
    return decorator

def validate_required_fields(data: dict, required_fields: list, operation: str) -> None:
    """
    Validate that required fields are present in the data.
    
    Args:
        data: Dictionary containing the data to validate
        required_fields: List of required field names
        operation: Description of the operation for error messages
        
    Raises:
        HTTPException: If any required field is missing
    """
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields for {operation}: {', '.join(missing_fields)}"
        )

def validate_positive_number(value: Any, field_name: str, operation: str) -> None:
    """
    Validate that a value is a positive number.
    
    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        operation: Description of the operation for error messages
        
    Raises:
        HTTPException: If the value is not a positive number
    """
    try:
        num_value = float(value)
        if num_value <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} must be a positive number for {operation}"
            )
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a valid number for {operation}"
        ) 