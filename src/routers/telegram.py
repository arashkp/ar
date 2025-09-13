from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
import logging

from src.utils.auth import require_api_key
from src.services.telegram_service import telegram_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

class TestMessageRequest(BaseModel):
    message: Optional[str] = None

class SchedulerRequest(BaseModel):
    interval_hours: int = 3
    action: str  # "start" or "stop"

@router.post("/test", dependencies=[require_api_key()])
async def send_test_message(request: TestMessageRequest):
    """Send a test message to verify bot configuration."""
    try:
        if request.message:
            success = await telegram_service.send_message(request.message)
        else:
            success = await telegram_service.send_test_message()
        
        if success:
            return {"status": "success", "message": "Test message sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send test message"
            )
    except Exception as e:
        logger.error(f"Error sending test message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending test message: {str(e)}"
        )

@router.post("/report", dependencies=[require_api_key()])
async def send_market_report():
    """Send a market report immediately."""
    try:
        report = await telegram_service.generate_market_report()
        success = await telegram_service.send_message(report)
        
        if success:
            return {"status": "success", "message": "Market report sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send market report"
            )
    except Exception as e:
        logger.error(f"Error sending market report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending market report: {str(e)}"
        )

@router.post("/scheduler", dependencies=[require_api_key()])
async def control_scheduler(request: SchedulerRequest):
    """Start or stop the scheduler for periodic reports."""
    try:
        if request.action.lower() == "start":
            telegram_service.start_scheduler(request.interval_hours)
            return {
                "status": "success", 
                "message": f"Scheduler started - reports every {request.interval_hours} hours"
            }
        elif request.action.lower() == "stop":
            telegram_service.stop_scheduler()
            return {"status": "success", "message": "Scheduler stopped"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action must be 'start' or 'stop'"
            )
    except Exception as e:
        logger.error(f"Error controlling scheduler: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error controlling scheduler: {str(e)}"
        )

@router.post("/test-orders", dependencies=[require_api_key()])
async def test_orders_count():
    """Test the orders count functionality."""
    try:
        success = await telegram_service.send_test_report_with_orders()
        
        if success:
            return {"status": "success", "message": "Orders count test sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send orders count test"
            )
    except Exception as e:
        logger.error(f"Error testing orders count: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing orders count: {str(e)}"
        )

@router.get("/status", dependencies=[require_api_key()])
async def get_telegram_status():
    """Get the current status of the Telegram bot and scheduler."""
    try:
        status_info = {
            "bot_configured": telegram_service.bot is not None,
            "scheduler_running": telegram_service.is_running,
            "chat_id": telegram_service.chat_id if telegram_service.chat_id else None
        }
        
        return {"status": "success", "data": status_info}
    except Exception as e:
        logger.error(f"Error getting telegram status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting telegram status: {str(e)}"
        ) 