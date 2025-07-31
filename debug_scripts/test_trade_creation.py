import os
import sys

# 1. Set environment variable for DATABASE_URL
# This MUST be done before any imports that might initialize SQLAlchemy engine,
# particularly before 'database.database' or 'config.config' are imported indirectly.
TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/testdb_trades"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
print(f"Using DATABASE_URL: {TEST_DATABASE_URL} (set before imports)")

import datetime
from decimal import Decimal

# Add src and database directories to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
sys.path.insert(0, project_root)
# print(f"Updated sys.path: {sys.path}")


try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.exc import OperationalError, ProgrammingError

    from src.schemas import trade_schema
    from src.crud import trades as trades_crud
    from database import models
    from database.database import Base
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure all dependencies (SQLAlchemy, Pydantic, psycopg2-binary) are installed and script is run from project root.")
    sys.exit(1)


def main():
    engine = None
    try:
        # Attempt to connect to the default 'postgres' database to check/create 'testdb_trades'
        # This uses the TEST_DATABASE_URL set globally now.
        default_db_url = TEST_DATABASE_URL.replace('/testdb_trades', '/postgres')
        temp_engine = create_engine(default_db_url) # Uses the globally set DATABASE_URL

        with temp_engine.connect() as conn:
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = 'testdb_trades'"))
            db_exists = result.scalar_one_or_none()

            if not db_exists:
                print(f"Database 'testdb_trades' does not exist.")
                print("This script expects the database to be pre-created.")
                print("Please create it manually: CREATE DATABASE testdb_trades OWNER postgres;")
                print("Exiting as database does not exist.")
                # For CI/automated tests, ensure the DB is created by an external script or service.
                temp_engine.dispose()
                sys.exit(1) # Exit if DB doesn't exist, as per simplified logic.
            else:
                print("Database 'testdb_trades' already exists.")
        temp_engine.dispose()

        # 2. Initialize the database schema
        engine = create_engine(TEST_DATABASE_URL) # Uses the globally set DATABASE_URL
        print("Attempting to create tables in 'testdb_trades'...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully (if they didn't exist).")

    except OperationalError as e:
        print(f"DB OperationalError: {e}")
        if "does not exist" in str(e).lower() and 'testdb_trades' in str(e).lower():
            print(f"The database 'testdb_trades' likely does not exist. Please create it first.")
        elif "password authentication failed" in str(e).lower():
            print(f"Password authentication failed for user 'postgres'. Check credentials.")
        elif "connection refused" in str(e).lower():
            print(f"Connection refused. Ensure PostgreSQL server is running at localhost:5432.")
        else:
            print("Ensure PostgreSQL is running, accessible, 'testdb_trades' exists, and credentials are correct.")
        if engine:
            engine.dispose()
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during DB setup: {e}")
        if engine:
            engine.dispose()
        sys.exit(1)

    SessionLocalTest = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session: Session = SessionLocalTest()
    print("Database session obtained.")

    try:
        trade_time = datetime.datetime.now(datetime.timezone.utc)
        trade_data_in = trade_schema.TradeCreate(
            exchange_id='test_exchange',
            symbol='BTC/USD',
            timestamp=trade_time,
            price=Decimal('50000.0000000000'),
            amount=Decimal('1.0000000000'),
            side='buy',
            type='market',
            fee=Decimal('50.0000000000'),
            fee_currency='USD',
            pnl=Decimal('0.0'),
            is_spot=True,
            order_id='test_order_123'
        )
        print(f"TradeCreate instance created: {trade_data_in.model_dump()}")

        print("Saving trade to database...")
        created_trade_model = trades_crud.save_trade(db=db_session, trade=trade_data_in)
        print(f"Trade saved. Returned object type: {type(created_trade_model)}")

        assert isinstance(created_trade_model, models.Trade), \
            f"Returned object is not a models.Trade instance, got {type(created_trade_model)}"
        print("Returned object is an instance of models.Trade - Check PASSED.")

        assert created_trade_model.id is not None, "Returned trade ID is None."
        print(f"Returned trade ID: {created_trade_model.id} - Check PASSED.")

        assert created_trade_model.symbol == trade_data_in.symbol, \
            f"Symbol mismatch: expected {trade_data_in.symbol}, got {created_trade_model.symbol}"
        print("Symbol matches input - Check PASSED.")

        assert created_trade_model.price == trade_data_in.price, \
            f"Price mismatch: expected {trade_data_in.price}, got {created_trade_model.price}"
        print("Price matches input - Check PASSED.")

        assert created_trade_model.amount == trade_data_in.amount, \
            f"Amount mismatch: expected {trade_data_in.amount}, got {created_trade_model.amount}"
        print("Amount matches input - Check PASSED.")

        time_difference = abs((created_trade_model.timestamp.replace(tzinfo=None) - trade_data_in.timestamp.replace(tzinfo=None)).total_seconds())
        assert time_difference < 1, f"Timestamp difference too large: {time_difference}s"
        print("Timestamp is valid and matches input closely - Check PASSED.")

        print(f"Querying database for trade ID: {created_trade_model.id}...")
        queried_trade = db_session.query(models.Trade).filter(models.Trade.id == created_trade_model.id).first()

        assert queried_trade is not None, "Trade not found in database after querying."
        print("Trade found in database by ID - Check PASSED.")

        assert queried_trade.symbol == trade_data_in.symbol, \
            f"Queried trade symbol mismatch: expected {trade_data_in.symbol}, got {queried_trade.symbol}"
        print("Queried trade symbol matches - Check PASSED.")

        assert queried_trade.price == trade_data_in.price, \
            f"Queried trade price mismatch: expected {trade_data_in.price}, got {queried_trade.price}"
        print("Queried trade price matches - Check PASSED.")

        print("\nAll checks PASSED! Trade creation and verification successful.")

    except AssertionError as e:
        print(f"\nAssertionError: {e}")
        print("A check FAILED during trade verification.")
    except OperationalError as e:
        print(f"\nDB OperationalError during trade operations: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if db_session:
            db_session.close()
            print("Database session closed.")
        if engine:
            engine.dispose()
            print("Database engine disposed.")

if __name__ == "__main__":
    main()
