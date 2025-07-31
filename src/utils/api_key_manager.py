"""
API Key Management utilities for the AR trading application.

This module provides centralized functions for retrieving and validating API keys
from various sources (environment variables, query parameters, settings) to reduce
code duplication across routers and services.
"""

import os
from typing import Optional, Tuple
from fastapi import HTTPException, status
from core.config import Settings, settings

def get_api_keys_from_env(exchange_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Get API keys for an exchange from environment variables.
    
    Args:
        exchange_id: The exchange identifier (e.g., 'binance', 'coinbasepro')
        
    Returns:
        Tuple of (api_key, api_secret) - both may be None if not found
    """
    exchange_upper = exchange_id.upper()
    api_key_name = f"{exchange_upper}_API_KEY"
    api_secret_name = f"{exchange_upper}_API_SECRET"
    
    api_key = os.getenv(api_key_name)
    api_secret = os.getenv(api_secret_name)
    
    return api_key, api_secret

def get_api_keys_from_settings(exchange_id: str, settings: Settings) -> Tuple[Optional[str], Optional[str]]:
    """
    Get API keys for an exchange from settings object.
    
    Args:
        exchange_id: The exchange identifier
        settings: Settings object containing API keys
        
    Returns:
        Tuple of (api_key, api_secret) - both may be None if not found
    """
    exchange_upper = exchange_id.upper()
    api_key = getattr(settings, f"{exchange_upper}_API_KEY", None)
    api_secret = getattr(settings, f"{exchange_upper}_API_SECRET", None)
    
    return api_key, api_secret

def get_effective_api_keys(
    exchange_id: str,
    query_api_key: Optional[str] = None,
    query_api_secret: Optional[str] = None,
    settings: Optional[Settings] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get effective API keys with fallback priority: query params > settings > env vars.
    
    Args:
        exchange_id: The exchange identifier
        query_api_key: API key from query parameters (highest priority)
        query_api_secret: API secret from query parameters (highest priority)
        settings: Settings object (medium priority)
        
    Returns:
        Tuple of (api_key, api_secret) - both may be None if not found
    """
    # Priority 1: Query parameters
    if query_api_key and query_api_secret:
        return query_api_key, query_api_secret
    
    # Priority 2: Settings object
    if settings:
        settings_key, settings_secret = get_api_keys_from_settings(exchange_id, settings)
        if settings_key and settings_secret:
            return settings_key, settings_secret
    
    # Priority 3: Environment variables
    env_key, env_secret = get_api_keys_from_env(exchange_id)
    if env_key and env_secret:
        return env_key, env_secret
    
    # If we have partial keys, return what we have (for debugging)
    if query_api_key or query_api_secret:
        return query_api_key, query_api_secret
    
    return None, None

def validate_api_keys_required(
    exchange_id: str,
    api_key: Optional[str],
    api_secret: Optional[str],
    operation: str = "API operation"
) -> None:
    """
    Validate that API keys are provided for operations that require them.
    
    Args:
        exchange_id: The exchange identifier
        api_key: The API key
        api_secret: The API secret
        operation: Description of the operation for error messages
        
    Raises:
        HTTPException: If API keys are missing
    """
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API key and secret are required for {exchange_id} to {operation}. "
                   f"Provide them as query parameters or set them as environment variables "
                   f"(e.g., {exchange_id.upper()}_API_KEY, {exchange_id.upper()}_API_SECRET)."
        )

def get_api_keys_for_public_data(
    exchange_id: str,
    query_api_key: Optional[str] = None,
    query_api_secret: Optional[str] = None,
    settings: Optional[Settings] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get API keys for public data operations (like OHLCV) where keys are optional.
    
    Args:
        exchange_id: The exchange identifier
        query_api_key: API key from query parameters
        query_api_secret: API secret from query parameters
        settings: Settings object
        
    Returns:
        Tuple of (api_key, api_secret) - both may be None for public data
    """
    return get_effective_api_keys(
        exchange_id=exchange_id,
        query_api_key=query_api_key,
        query_api_secret=query_api_secret,
        settings=settings
    )

def get_api_keys_for_private_data(
    exchange_id: str,
    query_api_key: Optional[str] = None,
    query_api_secret: Optional[str] = None,
    settings: Optional[Settings] = None,
    operation: str = "private data access"
) -> Tuple[str, str]:
    """
    Get API keys for private data operations (like balance, orders) where keys are required.
    
    Args:
        exchange_id: The exchange identifier
        query_api_key: API key from query parameters
        query_api_secret: API secret from query parameters
        settings: Settings object
        operation: Description of the operation for error messages
        
    Returns:
        Tuple of (api_key, api_secret) - guaranteed to be non-None
        
    Raises:
        HTTPException: If API keys are missing
    """
    api_key, api_secret = get_effective_api_keys(
        exchange_id=exchange_id,
        query_api_key=query_api_key,
        query_api_secret=query_api_secret,
        settings=settings
    )
    
    validate_api_keys_required(exchange_id, api_key, api_secret, operation)
    
    return api_key, api_secret

def format_exchange_key_name(exchange_id: str, key_type: str = "API_KEY") -> str:
    """
    Format the environment variable name for an exchange API key.
    
    Args:
        exchange_id: The exchange identifier
        key_type: The type of key ("API_KEY" or "API_SECRET")
        
    Returns:
        Formatted environment variable name
    """
    return f"{exchange_id.upper()}_{key_type}"

def log_api_key_usage(exchange_id: str, operation: str, has_keys: bool) -> None:
    """
    Log API key usage for debugging and monitoring.
    
    Args:
        exchange_id: The exchange identifier
        operation: The operation being performed
        has_keys: Whether API keys are available
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if has_keys:
        logger.debug(f"Using API keys for {exchange_id} during {operation}")
    else:
        logger.warning(f"No API keys available for {exchange_id} during {operation}") 