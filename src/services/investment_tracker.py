from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from collections import defaultdict

from src.schemas.investment_schema import InvestmentSummaryResponse, InvestmentDataPoint
from src.crud import orders as crud_orders # Assuming function will be in crud_orders
# from src.crud import trades as crud_trades # If using trades table directly

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def calculate_investment_summary(
    db: Session,
    timeframe: str = 'total',
    currency: str = 'USD'
) -> InvestmentSummaryResponse:
    """
    Calculates the investment summary based on filled 'buy' orders.
    Currently supports USD calculations. BTC conversion is a future enhancement.
    """
    logger.info(f"Calculating investment summary for timeframe: {timeframe}, currency: {currency}")

    if currency.upper() != 'USD':
        # For now, only USD is supported as per issue's guidance to start simple.
        # BTC calculation would require historical price feeds.
        raise NotImplementedError(f"Currency {currency} is not yet supported for investment summary. Please use USD.")

    # Fetch relevant orders/trades. We need 'buy' orders that are 'filled'.
    # The 'cost' field in the Order model (price * amount) should represent the invested amount in the quote currency.
    # We assume the quote currency is USD or a USD-pegged stablecoin (e.g., USDT, USDC).

    # This function will be created in step 4c
    # For now, we define its expected signature:
    # filled_buy_orders = crud_orders.get_filled_buy_orders_for_summary(db=db, start_date=None, end_date=None)
    # The actual implementation of get_filled_buy_orders_for_summary might take date ranges.

    summary_points: List[InvestmentDataPoint] = []
    overall_total_invested = 0.0

    # Determine date range for querying if not 'total'
    end_date = datetime.now(timezone.utc)
    start_date = None

    if timeframe == 'daily':
        # Let's assume 'daily' means last 30 days for now, or it could be grouped by each day.
        # For simplicity in this first pass, let's make 'daily' sum up investments for each of the last 30 days.
        # A more robust implementation might take specific date ranges as parameters.
        start_date = end_date - timedelta(days=30)
        # Fetch all filled buy orders within this broad range
        orders = crud_orders.get_filled_buy_orders_for_summary(db=db, start_date=start_date, end_date=end_date)

        daily_investments: Dict[str, float] = defaultdict(float)
        for order in orders:
            if order.timestamp and order.cost: # Ensure timestamp and cost are not None
                order_date_str = order.timestamp.strftime('%Y-%m-%d')
                daily_investments[order_date_str] += order.cost

        for date_str, total in sorted(daily_investments.items()):
            summary_points.append(InvestmentDataPoint(period=date_str, total_invested=total, currency=currency.upper()))
            overall_total_invested += total

    elif timeframe == 'weekly':
        # Let's assume 'weekly' means last 12 weeks.
        start_date = end_date - timedelta(weeks=12)
        orders = crud_orders.get_filled_buy_orders_for_summary(db=db, start_date=start_date, end_date=end_date)

        weekly_investments: Dict[str, float] = defaultdict(float)
        for order in orders:
            if order.timestamp and order.cost:
                # Group by ISO week number and year
                week_str = f"{order.timestamp.isocalendar()[0]}-W{order.timestamp.isocalendar()[1]:02d}"
                weekly_investments[week_str] += order.cost

        for week_str, total in sorted(weekly_investments.items()):
            summary_points.append(InvestmentDataPoint(period=week_str, total_invested=total, currency=currency.upper()))
            overall_total_invested += total

    elif timeframe == 'total':
        orders = crud_orders.get_filled_buy_orders_for_summary(db=db) # No date filter for total
        current_total = sum(order.cost for order in orders if order.cost is not None)
        summary_points.append(InvestmentDataPoint(period='total', total_invested=current_total, currency=currency.upper()))
        overall_total_invested = current_total
    else:
        raise ValueError(f"Unsupported timeframe: {timeframe}. Supported values are 'daily', 'weekly', 'total'.")

    return InvestmentSummaryResponse(
        requested_timeframe=timeframe,
        requested_currency=currency.upper(),
        summary=summary_points,
        overall_total_invested=overall_total_invested if timeframe not in ['total'] else None, # Only set if not 'total' to avoid redundancy
        calculation_timestamp=datetime.now(timezone.utc)
    )
