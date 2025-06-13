from fastapi import FastAPI
from src.routers import exchange, trades, market_overview # Added trades and market_overview

app = FastAPI()

# Include the exchange router
app.include_router(exchange.router)
app.include_router(trades.router) # Added trades router
app.include_router(market_overview.router, prefix="/market", tags=["market"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
