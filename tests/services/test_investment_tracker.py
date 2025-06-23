import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

from src.services.investment_tracker import calculate_investment_summary
from src.schemas.investment_schema import InvestmentSummaryResponse, InvestmentDataPoint
from src.database.models import Order # Assuming Order model is used for cost calculation

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_db_session():
    return MagicMock()

# Sample order data for mocking CRUD responses
def create_mock_order(id: int, cost: float, timestamp: datetime, side: str = 'buy', status: str = 'filled'):
    return Order(
        id=id,
        exchange_id="test_exchange",
        symbol="BTC/USDT",
        timestamp=timestamp,
        price=cost, # Assuming price is effectively cost for simplicity here if amount is 1
        amount=1.0, # Assuming amount is 1 for simplicity in cost calculation
        side=side,
        type='limit',
        status=status,
        filled_amount=1.0,
        remaining_amount=0.0,
        cost=cost, # This is the key field for investment summary
        fee=cost * 0.001,
        fee_currency='USDT',
        is_spot=True
    )

@patch('src.services.investment_tracker.crud_orders.get_filled_buy_orders_for_summary')
async def test_calculate_investment_summary_total_usd(mock_get_filled_orders, mock_db_session):
    now = datetime.now(timezone.utc)
    mock_orders_data = [
        create_mock_order(id=1, cost=100.0, timestamp=now - timedelta(days=10)),
        create_mock_order(id=2, cost=150.0, timestamp=now - timedelta(days=5)),
    ]
    mock_get_filled_orders.return_value = mock_orders_data

    summary_response = await calculate_investment_summary(db=mock_db_session, timeframe='total', currency='USD')

    assert summary_response.requested_timeframe == 'total'
    assert summary_response.requested_currency == 'USD'
    assert len(summary_response.summary) == 1

    data_point = summary_response.summary[0]
    assert data_point.period == 'total'
    assert data_point.total_invested == 250.0 # 100.0 + 150.0
    assert data_point.currency == 'USD'

    assert summary_response.overall_total_invested is None # Not set for 'total' timeframe
    assert summary_response.calculation_timestamp is not None

    mock_get_filled_orders.assert_called_once_with(db=mock_db_session)


@patch('src.services.investment_tracker.crud_orders.get_filled_buy_orders_for_summary')
async def test_calculate_investment_summary_daily_usd(mock_get_filled_orders, mock_db_session):
    now = datetime.now(timezone.utc)
    # Orders from today, yesterday, and two days ago
    mock_orders_data = [
        create_mock_order(id=1, cost=50.0, timestamp=now - timedelta(microseconds=10)), # Today
        create_mock_order(id=2, cost=60.0, timestamp=now - timedelta(microseconds=20)), # Today
        create_mock_order(id=3, cost=100.0, timestamp=now - timedelta(days=1)), # Yesterday
        create_mock_order(id=4, cost=200.0, timestamp=now - timedelta(days=2)), # Two days ago
        create_mock_order(id=5, cost=10.0, timestamp=now - timedelta(days=35)), # Outside 30 day default range for daily
    ]
    # The service function filters by date range *before* grouping.
    # So, mock_get_filled_orders should be called with start_date and end_date for 'daily'.
    # We will simulate that the CRUD function returns only relevant orders for the last 30 days.

    # Let's refine this: the service calls CRUD with a date range.
    # So, the mock should reflect what CRUD returns for that range.
    # The service expects orders within the last 30 days for 'daily'.
    relevant_orders = [o for o in mock_orders_data if o.timestamp >= (now - timedelta(days=30))]
    mock_get_filled_orders.return_value = relevant_orders


    summary_response = await calculate_investment_summary(db=mock_db_session, timeframe='daily', currency='USD')

    assert summary_response.requested_timeframe == 'daily'
    assert summary_response.requested_currency == 'USD'

    # Expected daily summary:
    # Today: 50 + 60 = 110
    # Yesterday: 100
    # Two days ago: 200
    # The order from 35 days ago should be excluded by the date range passed to CRUD.

    expected_daily_totals = {
        (now - timedelta(days=2)).strftime('%Y-%m-%d'): 200.0,
        (now - timedelta(days=1)).strftime('%Y-%m-%d'): 100.0,
        now.strftime('%Y-%m-%d'): 110.0,
    }

    assert len(summary_response.summary) == 3
    total_invested_from_summary = 0
    for point in summary_response.summary:
        assert point.currency == 'USD'
        assert point.period in expected_daily_totals
        assert point.total_invested == expected_daily_totals[point.period]
        total_invested_from_summary += point.total_invested

    assert summary_response.overall_total_invested == total_invested_from_summary # 110 + 100 + 200 = 410

    # Check that CRUD was called with a date range
    mock_get_filled_orders.assert_called_once()
    call_args = mock_get_filled_orders.call_args[1] # keyword arguments
    assert 'start_date' in call_args and call_args['start_date'] is not None
    assert 'end_date' in call_args and call_args['end_date'] is not None


@patch('src.services.investment_tracker.crud_orders.get_filled_buy_orders_for_summary')
async def test_calculate_investment_summary_weekly_usd(mock_get_filled_orders, mock_db_session):
    now = datetime.now(timezone.utc)

    # Orders for current week and last week
    # Week 1 (current):
    order1_w1 = create_mock_order(id=1, cost=100, timestamp=now - timedelta(days=1)) # e.g. Friday
    order2_w1 = create_mock_order(id=2, cost=50,  timestamp=now - timedelta(days=2)) # e.g. Thursday
    # Week 2 (last week):
    order3_w2 = create_mock_order(id=3, cost=200, timestamp=now - timedelta(days=7)) # e.g. Last Friday
    order4_w2 = create_mock_order(id=4, cost=25,  timestamp=now - timedelta(days=8)) # e.g. Last Thursday
    # Order from 13 weeks ago (should be excluded by default 12-week range)
    order5_w13 = create_mock_order(id=5, cost=1000, timestamp=now - timedelta(weeks=13))

    relevant_orders = [order1_w1, order2_w1, order3_w2, order4_w2]
    mock_get_filled_orders.return_value = relevant_orders

    summary_response = await calculate_investment_summary(db=mock_db_session, timeframe='weekly', currency='USD')

    assert summary_response.requested_timeframe == 'weekly'
    assert summary_response.requested_currency == 'USD'

    # Expected weekly summary:
    current_week_iso = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    last_week_date = now - timedelta(weeks=1)
    last_week_iso = f"{last_week_date.isocalendar()[0]}-W{last_week_date.isocalendar()[1]:02d}"

    expected_weekly_totals = {
        current_week_iso: 150.0, # 100 + 50
        last_week_iso: 225.0     # 200 + 25
    }

    # The order of summary points matters if sorted by week_str
    # The service sorts them, so we should expect that order.
    # If last_week_iso < current_week_iso, then it comes first.

    assert len(summary_response.summary) == 2
    total_invested_from_summary = 0

    # Check that the periods are correct and totals match
    found_periods = set()
    for point in summary_response.summary:
        assert point.currency == 'USD'
        assert point.period in expected_weekly_totals
        assert point.total_invested == expected_weekly_totals[point.period]
        total_invested_from_summary += point.total_invested
        found_periods.add(point.period)

    assert found_periods == set(expected_weekly_totals.keys())
    assert summary_response.overall_total_invested == total_invested_from_summary # 150 + 225 = 375

    mock_get_filled_orders.assert_called_once()
    call_args = mock_get_filled_orders.call_args[1]
    assert 'start_date' in call_args and call_args['start_date'] is not None
    assert 'end_date' in call_args and call_args['end_date'] is not None


async def test_calculate_investment_summary_unsupported_currency(mock_db_session):
    with pytest.raises(NotImplementedError) as excinfo:
        await calculate_investment_summary(db=mock_db_session, timeframe='total', currency='BTC')
    assert "BTC is not yet supported" in str(excinfo.value)

async def test_calculate_investment_summary_invalid_timeframe(mock_db_session):
    with pytest.raises(ValueError) as excinfo:
        await calculate_investment_summary(db=mock_db_session, timeframe='monthly', currency='USD')
    assert "Unsupported timeframe: monthly" in str(excinfo.value)

@patch('src.services.investment_tracker.crud_orders.get_filled_buy_orders_for_summary')
async def test_calculate_investment_summary_no_orders(mock_get_filled_orders, mock_db_session):
    mock_get_filled_orders.return_value = [] # No orders found

    summary_response_total = await calculate_investment_summary(db=mock_db_session, timeframe='total', currency='USD')
    assert len(summary_response_total.summary) == 1
    assert summary_response_total.summary[0].total_invested == 0
    assert summary_response_total.summary[0].period == 'total'

    summary_response_daily = await calculate_investment_summary(db=mock_db_session, timeframe='daily', currency='USD')
    assert len(summary_response_daily.summary) == 0 # No data points if no orders in range
    assert summary_response_daily.overall_total_invested == 0

    summary_response_weekly = await calculate_investment_summary(db=mock_db_session, timeframe='weekly', currency='USD')
    assert len(summary_response_weekly.summary) == 0 # No data points if no orders in range
    assert summary_response_weekly.overall_total_invested == 0
