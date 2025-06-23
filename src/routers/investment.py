from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.schemas.investment_schema import InvestmentSummaryResponse # Request params will be query params
from src.services import investment_tracker
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/investment_summary", # Changed prefix
    tags=["investment_summary"], # Changed tag
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=InvestmentSummaryResponse) # Changed path to /
async def get_investment_summary_api(
    timeframe: str = Query('total', enum=['daily', 'weekly', 'total'], description="Timeframe for the summary: 'daily', 'weekly', or 'total'."),
    currency: str = Query('USD', enum=['USD', 'BTC'], description="Currency for the summary: 'USD' or 'BTC'. Currently, only 'USD' is fully supported."),
    db: Session = Depends(get_db)
):
    """
    Calculate and return investment summary metrics.
    - **timeframe**: Aggregation period ('daily', 'weekly', 'total'). Default: 'total'.
    - **currency**: Currency for reporting ('USD', 'BTC'). Default: 'USD'.
                     Note: BTC calculation is not yet fully implemented.
    """
    try:
        summary_response = await investment_tracker.calculate_investment_summary(
            db=db,
            timeframe=timeframe,
            currency=currency
        )
        return summary_response
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except ValueError as e: # For invalid timeframe
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating investment summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while calculating the investment summary: {str(e)}"
        )
