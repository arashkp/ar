from fastapi import FastAPI
from src.routers import exchange, trades, market_overview, orders, investment # Added investment router
from src.database.session import create_db_and_tables  # For DB initialization

app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()  # Creates tables if they don't exist


# Include the exchange router
app.include_router(exchange.router)
app.include_router(trades.router)  # Added trades router
app.include_router(market_overview.router, prefix="/market", tags=["market"])
app.include_router(orders.router)  # Added orders router, prefix is in orders.py
app.include_router(investment.router) # Added investment router, prefix is in investment.py


@app.get("/health")
async def health_check():
    return {"status": "ok"}
