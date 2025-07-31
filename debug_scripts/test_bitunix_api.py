#!/usr/bin/env python3
"""
Simple test script to check Bitunix API endpoints and response structure.
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_bitunix_api():
    """Test Bitunix API endpoints to understand the structure."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    print(f"🔑 API Key: {api_key[:10]}...")
    print(f"🔐 API Secret: {api_secret[:10]}...")
    
    # Test different base URLs
    base_urls = [
        "https://api.bitunix.com",
        "https://api.bitunix.io",
        "https://api.bitunix.net",
        "https://bitunix.com/api",
        "https://bitunix.io/api",
        "https://bitunix.net/api",
        "https://api.bitunix.com/v1",
        "https://api.bitunix.com/v2",
        "https://api.bitunix.com/api",
        "https://api.bitunix.com/rest"
    ]
    
    # Test endpoints
    endpoints = [
        '/account/balance',
        '/account',
        '/user/balance',
        '/wallet/balance',
        '/market/ticker/BTCUSDT',
        '/order/open',
        '/trade/history',
        '/balance',
        '/ticker/BTCUSDT',
        '/ticker',
        '/public/ticker/BTCUSDT',
        '/public/ticker'
    ]
    
    async with aiohttp.ClientSession() as session:
        for base_url in base_urls:
            print(f"\n🌐 Testing base URL: {base_url}")
            
            for endpoint in endpoints:
                url = f"{base_url}{endpoint}"
                print(f"   🔍 Testing: {endpoint}")
                
                # Try without authentication first
                try:
                    async with session.get(url) as response:
                        print(f"      Status: {response.status}")
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                                print(f"      ✅ Success: {type(data)}")
                                if isinstance(data, dict):
                                    print(f"      Keys: {list(data.keys())}")
                            except:
                                text = await response.text()
                                print(f"      📝 Text: {text[:50]}...")
                        elif response.status == 401:
                            print(f"      🔐 Requires authentication")
                        elif response.status == 404:
                            print(f"      ❌ Not found")
                        else:
                            text = await response.text()
                            print(f"      ❌ Error {response.status}: {text[:50]}...")
                            
                except Exception as e:
                    print(f"      ❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_bitunix_api()) 