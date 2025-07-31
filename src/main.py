from dotenv import load_dotenv
import warnings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import exchange, trades, market_overview, orders, investment, \
    historical_performance, spot_trades  # Added spot_trades router
from database.session import create_db_and_tables  # For DB initialization

load_dotenv()

# Suppress the specific UserWarning from pandas_ta regarding pkg_resources
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.",
)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()  # Creates tables if they don't exist


# Include the exchange router
app.include_router(exchange.router)
app.include_router(trades.router)  # Added trades router
app.include_router(market_overview.router, prefix="/market", tags=["market"])
app.include_router(orders.router)  # Added orders router, prefix is in orders.py
app.include_router(investment.router)  # Added investment router, prefix is in investment.py
app.include_router(historical_performance.router)  # Added historical_performance router
app.include_router(spot_trades.router)  # Added spot_trades router


@app.get("/health")
async def health_check():
    return {"status": "ok"}
