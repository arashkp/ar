from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging

from src.database.session import get_db
from src.services.bitget_service import BitgetService
from src.utils.api_key_manager import get_api_keys_from_env
from src.utils.error_handlers import api_error_handler

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/bitget",
    tags=["bitget"],
    responses={404: {"description": "Not found"}},
)

# Global Bitget service instance
bitget_service = BitgetService()

@router.get("/balance")
@api_error_handler("Bitget balance fetching")
async def get_bitget_balance():
    """Get Bitget account balance."""
    # Get API keys from environment
    api_key, api_secret, passphrase = get_bitget_api_keys()

    # Initialize service if not already done
    if not bitget_service.exchange:
        await bitget_service.initialize(api_key, api_secret, passphrase)

    balance = await bitget_service.get_balance()
    return balance

@router.get("/positions")
@api_error_handler("Bitget positions fetching")
async def get_bitget_positions():
    """Get Bitget spot positions."""
    # Get API keys from environment
    api_key, api_secret, passphrase = get_bitget_api_keys()

    # Initialize service if not already done
    if not bitget_service.exchange:
        await bitget_service.initialize(api_key, api_secret, passphrase)

    positions = await bitget_service.get_spot_positions()
    return positions

@router.get("/orders")
@api_error_handler("Bitget orders fetching")
async def get_bitget_orders(symbol: Optional[str] = None):
    """Get Bitget open orders."""
    # Get API keys from environment
    api_key, api_secret, passphrase = get_bitget_api_keys()

    # Initialize service if not already done
    if not bitget_service.exchange:
        await bitget_service.initialize(api_key, api_secret, passphrase)

    orders = await bitget_service.get_orders(symbol)
    return orders

@router.get("/trades")
@api_error_handler("Bitget trades fetching")
async def get_bitget_trades(symbol: Optional[str] = None, limit: int = 100):
    """Get Bitget trade history."""
    # Get API keys from environment
    api_key, api_secret, passphrase = get_bitget_api_keys()

    # Initialize service if not already done
    if not bitget_service.exchange:
        await bitget_service.initialize(api_key, api_secret, passphrase)

    trades = await bitget_service.get_trade_history(symbol, limit)
    return trades

@router.get("/backward-analysis")
@api_error_handler("Bitget backward analysis")
async def get_bitget_backward_analysis(symbol: str = "HYPE/USDT"):
    """Get Bitget backward analysis for a specific symbol (default: HYPE)."""
    # Get API keys from environment
    api_key, api_secret, passphrase = get_bitget_api_keys()

    # Initialize service if not already done
    if not bitget_service.exchange:
        await bitget_service.initialize(api_key, api_secret, passphrase)

    analysis = await bitget_service.get_backward_analysis(symbol)
    return analysis

@router.get("/price/{symbol}")
@api_error_handler("Bitget price fetching")
async def get_bitget_price(symbol: str):
    """Get current price for a symbol from Bitget."""
    # Get API keys from environment
    api_key, api_secret, passphrase = get_bitget_api_keys()

    # Initialize service if not already done
    if not bitget_service.exchange:
        await bitget_service.initialize(api_key, api_secret, passphrase)

    price = await bitget_service.get_current_price(symbol)
    return {"symbol": symbol, "price": price}

def get_bitget_api_keys():
    """Get Bitget API keys from environment variables."""
    try:
        api_key = get_api_keys_from_env("BITGET", "API_KEY")
        api_secret = get_api_keys_from_env("BITGET", "API_SECRET")
        passphrase = get_api_keys_from_env("BITGET", "PASSPHRASE")
        
        if not api_key or not api_secret or not passphrase:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Bitget API not configured. Please set BITGET_API_KEY, BITGET_API_SECRET, and BITGET_PASSPHRASE environment variables."
            )
        
        return api_key, api_secret, passphrase
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error getting Bitget API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Bitget API keys: {str(e)}"
        ) 