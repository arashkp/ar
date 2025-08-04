from fastapi import HTTPException, status, Depends, Header
from typing import Optional
import os

def get_api_key():
    """Get API key from environment variable dynamically."""
    return os.getenv("API_KEY", "your-secret-api-key-here")

async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """
    Verify API key from request header.
    Usage: Add this as a dependency to your endpoints.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Get API key dynamically
    api_key = get_api_key()
    
    if x_api_key != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return True

# Dependency for protected endpoints
def require_api_key():
    return Depends(verify_api_key) 