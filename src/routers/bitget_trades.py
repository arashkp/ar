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
    try:
        # Get API keys from environment
        api_key, api_secret, passphrase = get_bitget_api_keys()
        
        # Initialize service if not already done
        if not bitget_service.exchange:
            await bitget_service.initialize(api_key, api_secret, passphrase)
        
        balance = await bitget_service.get_balance()
        return balance
    except Exception as e:
        logger.error(f"Error fetching Bitget balance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Bitget balance: {str(e)}"
        )

@router.get("/positions")
@api_error_handler("Bitget positions fetching")
async def get_bitget_positions():
    """Get Bitget spot positions."""
    try:
        # Get API keys from environment
        api_key, api_secret, passphrase = get_bitget_api_keys()
        
        # Initialize service if not already done
        if not bitget_service.exchange:
            await bitget_service.initialize(api_key, api_secret, passphrase)
        
        positions = await bitget_service.get_spot_positions()
        return positions
    except Exception as e:
        logger.error(f"Error fetching Bitget positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Bitget positions: {str(e)}"
        )

@router.get("/orders")
@api_error_handler("Bitget orders fetching")
async def get_bitget_orders(symbol: Optional[str] = None):
    """Get Bitget open orders."""
    try:
        # Get API keys from environment
        api_key, api_secret, passphrase = get_bitget_api_keys()
        
        # Initialize service if not already done
        if not bitget_service.exchange:
            await bitget_service.initialize(api_key, api_secret, passphrase)
        
        orders = await bitget_service.get_orders(symbol)
        return orders
    except Exception as e:
        logger.error(f"Error fetching Bitget orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Bitget orders: {str(e)}"
        )

@router.get("/trades")
@api_error_handler("Bitget trades fetching")
async def get_bitget_trades(symbol: Optional[str] = None, limit: int = 100):
    """Get Bitget trade history."""
    try:
        # Get API keys from environment
        api_key, api_secret, passphrase = get_bitget_api_keys()
        
        # Initialize service if not already done
        if not bitget_service.exchange:
            await bitget_service.initialize(api_key, api_secret, passphrase)
        
        trades = await bitget_service.get_trade_history(symbol, limit)
        return trades
    except Exception as e:
        logger.error(f"Error fetching Bitget trades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Bitget trades: {str(e)}"
        )

@router.get("/backward-analysis")
@api_error_handler("Bitget backward analysis")
async def get_bitget_backward_analysis(symbol: str = "HYPE/USDT"):
    """Get Bitget backward analysis for a specific symbol (default: HYPE)."""
    try:
        # Get API keys from environment
        api_key, api_secret, passphrase = get_bitget_api_keys()
        
        # Initialize service if not already done
        if not bitget_service.exchange:
            await bitget_service.initialize(api_key, api_secret, passphrase)
        
        analysis = await bitget_service.get_backward_analysis(symbol)
        return analysis
    except Exception as e:
        logger.error(f"Error generating Bitget backward analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Bitget backward analysis: {str(e)}"
        )

@router.get("/price/{symbol}")
@api_error_handler("Bitget price fetching")
async def get_bitget_price(symbol: str):
    """Get current price for a symbol from Bitget."""
    try:
        # Get API keys from environment
        api_key, api_secret, passphrase = get_bitget_api_keys()
        
        # Initialize service if not already done
        if not bitget_service.exchange:
            await bitget_service.initialize(api_key, api_secret, passphrase)
        
        price = await bitget_service.get_current_price(symbol)
        return {"symbol": symbol, "price": price}
    except Exception as e:
        logger.error(f"Error fetching Bitget price for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Bitget price for {symbol}: {str(e)}"
        )

def get_bitget_api_keys():
    """Get Bitget API keys from environment variables."""
    try:
        api_key = get_api_keys_from_env("BITGET", "API_KEY")
        api_secret = get_api_keys_from_env("BITGET", "API_SECRET")
        passphrase = get_api_keys_from_env("BITGET", "PASSPHRASE")
        
        if not api_key or not api_secret or not passphrase:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bitget API keys not configured. Please set BITGET_API_KEY, BITGET_API_SECRET, and BITGET_PASSPHRASE environment variables."
            )
        
        return api_key, api_secret, passphrase
    except Exception as e:
        logger.error(f"Error getting Bitget API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Bitget API keys: {str(e)}"
        ) 