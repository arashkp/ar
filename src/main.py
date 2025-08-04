from dotenv import load_dotenv
import warnings
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import exchange, trades, market_overview, orders, investment, \
    historical_performance, spot_trades, bitget_trades, telegram  # Added bitget_trades router
from src.database.session import create_db_and_tables  # For DB initialization
from src.utils.auth import require_api_key

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)

app = FastAPI(
    title="AR Trading API",
    description="API for trading analysis and management",
    version="1.0.0"
)

# Add CORS middleware - allow all origins for deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for deployment
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.on_event("startup")
async def on_startup():
    create_db_and_tables()  # Creates tables if they don't exist
    # Log the port for debugging
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Application starting on port {port}")


# Include the exchange router with API key protection
app.include_router(exchange.router, dependencies=[require_api_key()])
app.include_router(trades.router, dependencies=[require_api_key()])  # Added trades router
app.include_router(market_overview.router, prefix="/market", tags=["market"], dependencies=[require_api_key()])
app.include_router(orders.router, dependencies=[require_api_key()])  # Added orders router, prefix is in orders.py
app.include_router(investment.router, dependencies=[require_api_key()])  # Added investment router, prefix is in investment.py
app.include_router(historical_performance.router, dependencies=[require_api_key()])  # Added historical_performance router
app.include_router(spot_trades.router, dependencies=[require_api_key()])  # Added spot_trades router
app.include_router(bitget_trades.router, dependencies=[require_api_key()])
app.include_router(telegram.router, dependencies=[require_api_key()])  # Added bitget_trades router


@app.get("/health", dependencies=[require_api_key()])
async def health_check():
    return {"status": "ok", "message": "AR Trading API is running"}

@app.get("/health/public")
async def public_health_check():
    return {"status": "ok", "message": "AR Trading API is running"}


# For local development
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# For Render deployment - ensure port is properly set
import os
port = int(os.getenv("PORT", 8000))
