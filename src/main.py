from fastapi import FastAPI
from src.routers import exchange, trades # Added trades

app = FastAPI()

# Include the exchange router
app.include_router(exchange.router)
app.include_router(trades.router) # Added trades router

@app.get("/health")
async def health_check():
    return {"status": "ok"}
