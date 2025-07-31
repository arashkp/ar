"""
Spot trades router for the AR trading application.

This module provides read-only endpoints for fetching spot positions,
orders, and trade history from various exchanges.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from services.bitunix_service import BitunixService
from services.exchange_interface import SpotPosition, SpotOrder, SpotTrade
from utils.api_key_manager import get_api_keys_from_env

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/spot-trades",
    tags=["spot-trades"],
    responses={404: {"description": "Not found"}},
)


# Pydantic models for API responses
class SpotPositionResponse(BaseModel):
    """Response model for spot position data."""
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


class SpotOrderResponse(BaseModel):
    """Response model for spot order data."""
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float]
    filled_quantity: float
    remaining_quantity: float
    status: str
    created_at: datetime
    updated_at: datetime
    client_order_id: Optional[str] = None


class SpotTradeResponse(BaseModel):
    """Response model for spot trade data."""
    trade_id: str
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float
    fee_asset: str
    timestamp: datetime
    taker: bool


class SpotTradesSummaryResponse(BaseModel):
    """Response model for spot trades summary."""
    positions: List[SpotPositionResponse]
    open_orders: List[SpotOrderResponse]
    total_positions_value: float
    total_unrealized_pnl: float
    last_updated: datetime


class ConnectionTestResponse(BaseModel):
    """Response model for exchange connection test."""
    exchange: str
    status: str
    message: str
    account_info: Dict[str, Any]
    test_timestamp: datetime
    is_mock_data: bool


class BackwardAnalysisOrder(BaseModel):
    date: str
    price: float
    quantity: float
    value: float
    side: str
    status: str

class BackwardAnalysisAsset(BaseModel):
    symbol: str
    current_balance: float
    average_entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percentage: float
    total_buy_quantity: float
    total_buy_value: float
    number_of_orders: int
    relevant_orders: List[BackwardAnalysisOrder]
    validation_passed: bool

class BackwardAnalysisResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    assets: List[BackwardAnalysisAsset]


def get_bitunix_service() -> BitunixService:
    """
    Get Bitunix service instance with API credentials.
    
    Returns:
        Initialized BitunixService instance
        
    Raises:
        HTTPException: If API credentials are not available
    """
    api_key, api_secret = get_api_keys_from_env("BITUNIX")
    
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bitunix API credentials not configured"
        )
    
    return BitunixService(api_key, api_secret)


@router.get("/test-connection", response_model=ConnectionTestResponse)
async def test_exchange_connection(
    exchange: str = "bitunix",
    service: BitunixService = Depends(get_bitunix_service)
):
    """
    Test exchange connection and verify API credentials.
    """
    try:
        if exchange.lower() != "bitunix":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exchange '{exchange}' not supported. Currently only 'bitunix' is supported."
            )
        
        # Try to get real balance data
        try:
            balance = await service.get_account_balance()
            
            # Check if we got real data or mock data
            is_mock_data = False
            if balance == service._mock_data['balances']:
                is_mock_data = True
                logger.warning("Using mock data - real Bitunix API connection failed")
            
            account_info = {
                "total_assets": len(balance),
                "total_balance_usdt": sum(amount for asset, amount in balance.items() if asset != "USDT"),
                "usdt_balance": balance.get("USDT", 0),
                "assets_with_balance": [
                    {"asset": asset, "amount": amount}
                    for asset, amount in balance.items()
                    if amount > 0
                ],
                "is_mock_data": is_mock_data
            }
            
            status_msg = "success"
            message = "Successfully connected to Bitunix API" if not is_mock_data else "Connected to Bitunix API (using mock data - real API endpoints not available)"
            
            return ConnectionTestResponse(
                exchange=exchange,
                status=status_msg,
                message=message,
                account_info=account_info,
                test_timestamp=datetime.now(timezone.utc),
                is_mock_data=is_mock_data
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch account balance: {e}")
            return ConnectionTestResponse(
                exchange=exchange,
                status="error",
                message=f"Connection test failed: {str(e)}",
                account_info={},
                test_timestamp=datetime.now(timezone.utc),
                is_mock_data=False
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Connection test failed for {exchange}: {e}")
        return ConnectionTestResponse(
            exchange=exchange,
            status="error",
            message=f"Connection test failed: {str(e)}",
            account_info={},
            test_timestamp=datetime.now(timezone.utc),
            is_mock_data=False
        )


@router.get("/backward-analysis", response_model=BackwardAnalysisResponse)
async def get_backward_analysis(bitunix_service: BitunixService = Depends(get_bitunix_service)):
    """Get backward calculation analysis for all assets."""
    try:
        # Initialize the client if needed
        if not bitunix_service._client:
            await bitunix_service.initialize()
            
        # Get current balances
        balance_response = bitunix_service._client.get_account_balance()
        balances = {}
        
        if balance_response and 'data' in balance_response:
            for asset in balance_response['data']:
                coin = asset.get('coin')
                balance = float(asset.get('balance', 0)) + float(asset.get('balanceLocked', 0))
                if balance > 0:  # Include all assets with balance > 0, including USDT
                    balances[coin] = balance
        
        assets = ['HBAR', 'SUI', 'BONK', 'ONDO', 'USDT']
        analysis_assets = []
        
        for coin in assets:
            if coin not in balances:
                continue
                
            current_balance = balances[coin]
            
            # Special handling for USDT - no trading pair needed
            if coin == 'USDT':
                analysis_asset = BackwardAnalysisAsset(
                    symbol="USDT",
                    current_balance=round(current_balance, 8),
                    average_entry_price=1.0,  # USDT is always 1:1
                    current_price=1.0,
                    unrealized_pnl=0.0,
                    unrealized_pnl_percentage=0.0,
                    total_buy_quantity=current_balance,
                    total_buy_value=current_balance,
                    number_of_orders=0,
                    relevant_orders=[],
                    validation_passed=True
                )
                analysis_assets.append(analysis_asset)
                continue
            
            symbol = f"{coin}USDT"
            
            # Get orders for this coin
            all_orders = []
            page = 1
            
            while page <= 5:  # Limit to 5 pages for performance
                try:
                    orders_response = bitunix_service._client.query_order_history(
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
                    logger.warning(f"Error fetching page {page} for {coin}: {e}")
                    break
            
            if all_orders:
                # Sort orders by time (newest first) for backward calculation
                all_orders.sort(key=lambda x: x.get('ctime', ''), reverse=True)
                
                relevant_orders = []
                accumulated_quantity = 0.0
                tolerance = 0.01  # 1% tolerance
                target_balance = current_balance
                
                for order in all_orders:
                    side = order.get('side')  # 1 = SELL, 2 = BUY
                    status = order.get('status')
                    price = float(order.get('avgPrice', 0))
                    quantity = float(order.get('dealVolume', 0))
                    
                    if status == 2:  # Only completed orders
                        if side == 2:  # BUY - adds to position
                            relevant_orders.append({
                                'date': order.get('ctime', ''),
                                'price': round(price, 8),
                                'quantity': round(quantity, 8),
                                'value': round(price * quantity, 8),
                                'side': 'BUY',
                                'status': 'FILLED'
                            })
                            accumulated_quantity += quantity
                            
                            # Check if we've reached the target balance
                            if abs(accumulated_quantity - target_balance) <= (target_balance * tolerance):
                                break
                            elif accumulated_quantity > target_balance * (1 + tolerance):
                                break
                                
                        elif side == 1:  # SELL - reduces position
                            # For sells, we need to "undo" them to find the original position
                            accumulated_quantity -= quantity
                            
                            # If this sell would make our accumulated quantity negative, skip it
                            if accumulated_quantity < 0:
                                accumulated_quantity = 0
                
                if relevant_orders:
                    # Calculate totals
                    total_buy_quantity = sum(order['quantity'] for order in relevant_orders)
                    total_buy_value = sum(order['value'] for order in relevant_orders)
                    
                    if total_buy_quantity > 0:
                        calculated_avg_price = total_buy_value / total_buy_quantity
                        
                        # Get current price
                        try:
                            price_response = bitunix_service._client.get_latest_price(symbol)
                            if price_response and isinstance(price_response, dict) and price_response.get('success') and price_response.get('data'):
                                current_price = float(price_response['data'])
                            else:
                                current_price = calculated_avg_price  # Fallback
                        except:
                            current_price = calculated_avg_price  # Fallback
                        
                        # Calculate PnL
                        unrealized_pnl = (current_price - calculated_avg_price) * current_balance
                        unrealized_pnl_percentage = ((current_price - calculated_avg_price) / calculated_avg_price * 100) if calculated_avg_price > 0 else 0
                        
                        # Validation
                        validation_passed = abs(total_buy_quantity - current_balance) <= (current_balance * tolerance)
                        
                        # Create response with proper rounding
                        analysis_asset = BackwardAnalysisAsset(
                            symbol=f"{coin}/USDT",
                            current_balance=round(current_balance, 8),
                            average_entry_price=round(calculated_avg_price, 8),
                            current_price=round(current_price, 8),
                            unrealized_pnl=round(unrealized_pnl, 2),
                            unrealized_pnl_percentage=round(unrealized_pnl_percentage, 2),
                            total_buy_quantity=round(total_buy_quantity, 8),
                            total_buy_value=round(total_buy_value, 2),
                            number_of_orders=len(relevant_orders),
                            relevant_orders=[
                                BackwardAnalysisOrder(
                                    date=order['date'],
                                    price=order['price'],
                                    quantity=order['quantity'],
                                    value=order['value'],
                                    side=order['side'],
                                    status=order['status']
                                ) for order in relevant_orders
                            ],
                            validation_passed=validation_passed
                        )
                        
                        analysis_assets.append(analysis_asset)
        
        return BackwardAnalysisResponse(
            success=True,
            message="Backward analysis completed successfully",
            timestamp=datetime.now(timezone.utc).isoformat(),
            assets=analysis_assets
        )
        
    except Exception as e:
        logger.error(f"Backward analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform backward analysis: {str(e)}"
        )


@router.get("/positions", response_model=List[SpotPositionResponse])
async def get_spot_positions(
    exchange: str = "bitunix",
    service: BitunixService = Depends(get_bitunix_service)
):
    """
    Get current spot positions.
    
    Args:
        exchange: Exchange name (currently only supports 'bitunix')
        service: Exchange service instance
        
    Returns:
        List of current spot positions with PnL calculations
    """
    try:
        if exchange.lower() != "bitunix":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exchange '{exchange}' not supported. Currently only 'bitunix' is supported."
            )
        
        positions = await service.get_spot_positions()
        
        # Convert to response models
        response_positions = []
        for position in positions:
            response_positions.append(SpotPositionResponse(
                symbol=position.symbol,
                base_asset=position.base_asset,
                quote_asset=position.quote_asset,
                quantity=position.quantity,
                average_entry_price=position.average_entry_price,
                current_price=position.current_price,
                unrealized_pnl=position.unrealized_pnl,
                unrealized_pnl_percentage=position.unrealized_pnl_percentage,
                total_value=position.total_value,
                last_updated=position.last_updated
            ))
        
        return response_positions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch spot positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch spot positions: {str(e)}"
        )


@router.get("/orders", response_model=List[SpotOrderResponse])
async def get_open_orders(
    symbol: Optional[str] = None,
    exchange: str = "bitunix",
    service: BitunixService = Depends(get_bitunix_service)
):
    """
    Get open spot orders.
    
    Args:
        symbol: Optional symbol filter (e.g., 'BTC/USDT')
        exchange: Exchange name (currently only supports 'bitunix')
        service: Exchange service instance
        
    Returns:
        List of open spot orders
    """
    try:
        if exchange.lower() != "bitunix":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exchange '{exchange}' not supported. Currently only 'bitunix' is supported."
            )
        
        orders = await service.get_open_orders(symbol=symbol)
        
        # Convert to response models
        response_orders = []
        for order in orders:
            response_orders.append(SpotOrderResponse(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side.value,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
                filled_quantity=order.filled_quantity,
                remaining_quantity=order.remaining_quantity,
                status=order.status.value,
                created_at=order.created_at,
                updated_at=order.updated_at,
                client_order_id=order.client_order_id
            ))
        
        return response_orders
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch open orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch open orders: {str(e)}"
        )


@router.get("/trades", response_model=List[SpotTradeResponse])
async def get_trade_history(
    symbol: Optional[str] = None,
    limit: int = 25,
    exchange: str = "bitunix",
    service: BitunixService = Depends(get_bitunix_service)
):
    """
    Get historical spot trades.
    
    Args:
        symbol: Optional symbol filter (e.g., 'BTC/USDT')
        limit: Maximum number of trades to return (max 100)
        exchange: Exchange name (currently only supports 'bitunix')
        service: Exchange service instance
        
    Returns:
        List of historical spot trades
    """
    try:
        if exchange.lower() != "bitunix":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exchange '{exchange}' not supported. Currently only 'bitunix' is supported."
            )
        
        # Limit the maximum number of trades to prevent abuse
        if limit > 100:
            limit = 100
        
        trades = await service.get_trade_history(symbol=symbol, limit=limit)
        
        # Convert to response models
        response_trades = []
        for trade in trades:
            response_trades.append(SpotTradeResponse(
                trade_id=trade.trade_id,
                order_id=trade.order_id,
                symbol=trade.symbol,
                side=trade.side.value,
                quantity=trade.quantity,
                price=trade.price,
                fee=trade.fee,
                fee_asset=trade.fee_asset,
                timestamp=trade.timestamp,
                taker=trade.taker
            ))
        
        return response_trades
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch trade history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch trade history: {str(e)}"
        )


@router.get("/summary", response_model=SpotTradesSummaryResponse)
async def get_spot_trades_summary(
    exchange: str = "bitunix",
    service: BitunixService = Depends(get_bitunix_service)
):
    """
    Get comprehensive spot trades summary including positions, orders, and totals.
    
    Args:
        exchange: Exchange name (currently only supports 'bitunix')
        service: Exchange service instance
        
    Returns:
        Summary of spot trades data including positions, orders, and calculated totals
    """
    try:
        if exchange.lower() != "bitunix":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exchange '{exchange}' not supported. Currently only 'bitunix' is supported."
            )
        
        # Fetch all data concurrently
        positions, open_orders = await asyncio.gather(
            service.get_spot_positions(),
            service.get_open_orders(),
            return_exceptions=True
        )
        
        # Handle exceptions from concurrent calls
        if isinstance(positions, Exception):
            raise positions
        if isinstance(open_orders, Exception):
            raise open_orders
        
        # Calculate totals
        total_positions_value = sum(pos.total_value for pos in positions)
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)
        
        # Convert to response models
        response_positions = [
            SpotPositionResponse(
                symbol=pos.symbol,
                base_asset=pos.base_asset,
                quote_asset=pos.quote_asset,
                quantity=pos.quantity,
                average_entry_price=pos.average_entry_price,
                current_price=pos.current_price,
                unrealized_pnl=pos.unrealized_pnl,
                unrealized_pnl_percentage=pos.unrealized_pnl_percentage,
                total_value=pos.total_value,
                last_updated=pos.last_updated
            ) for pos in positions
        ]
        
        response_orders = [
            SpotOrderResponse(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side.value,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
                filled_quantity=order.filled_quantity,
                remaining_quantity=order.remaining_quantity,
                status=order.status.value,
                created_at=order.created_at,
                updated_at=order.updated_at,
                client_order_id=order.client_order_id
            ) for order in open_orders
        ]
        
        return SpotTradesSummaryResponse(
            positions=response_positions,
            open_orders=response_orders,
            total_positions_value=total_positions_value,
            total_unrealized_pnl=total_unrealized_pnl,
            last_updated=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch spot trades summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch spot trades summary: {str(e)}"
        )


@router.get("/balance", response_model=Dict[str, float])
async def get_account_balance(
    exchange: str = "bitunix",
    service: BitunixService = Depends(get_bitunix_service)
):
    """
    Get account balance.
    
    Args:
        exchange: Exchange name (currently only supports 'bitunix')
        service: Exchange service instance
        
    Returns:
        Dictionary mapping asset symbols to balances
    """
    try:
        if exchange.lower() != "bitunix":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exchange '{exchange}' not supported. Currently only 'bitunix' is supported."
            )
        
        balance = await service.get_account_balance()
        return balance
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch account balance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch account balance: {str(e)}"
        ) 