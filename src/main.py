from fastapi import FastAPI
from src.routers import exchange # Import the exchange router

app = FastAPI()

# Include the exchange router
app.include_router(exchange.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
