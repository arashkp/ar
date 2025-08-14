#!/usr/bin/env python3
"""
Debug script to test different PEPE symbol formats with Bitunix API.
This will help identify the correct symbol format for PEPE on Bitunix.
"""

import asyncio
import aiohttp
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bitunix API configuration
BITUNIX_BASE_URL = "https://fapi.bitunix.com/api/v1/futures/market"
FUNDING_RATE_ENDPOINT = "/funding_rate"

# Different PEPE symbol formats to test
PEPE_SYMBOLS_TO_TEST = [
    "PEPEUSDT",
    "1000PEPEUSDT", 
    "PEPE/USDT",
    "PEPE_USDT",
    "PEPE",
    "1000PEPE"
]

async def test_pepe_symbol(symbol: str) -> bool:
    """Test if a PEPE symbol format works with Bitunix API."""
    try:
        url = f"{BITUNIX_BASE_URL}{FUNDING_RATE_ENDPOINT}?symbol={symbol}"
        logger.info(f"Testing symbol: {symbol}")
        logger.info(f"URL: {url}")
        
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ SUCCESS for {symbol}: {data}")
                    
                    if data.get('code') == 0 and 'data' in data:
                        funding_data = data['data']
                        funding_rate = funding_data.get('fundingRate', 'N/A')
                        mark_price = funding_data.get('markPrice', 'N/A')
                        last_price = funding_data.get('lastPrice', 'N/A')
                        
                        logger.info(f"   Funding Rate: {funding_rate}")
                        logger.info(f"   Mark Price: {mark_price}")
                        logger.info(f"   Last Price: {last_price}")
                        return True
                    else:
                        logger.warning(f"   API returned error: {data}")
                        return False
                else:
                    logger.error(f"   HTTP Error {response.status}")
                    return False
                    
    except Exception as e:
        logger.error(f"   Exception: {e}")
        return False

async def test_all_pepe_symbols():
    """Test all PEPE symbol formats."""
    logger.info("🔍 Testing different PEPE symbol formats with Bitunix API")
    logger.info("=" * 60)
    
    working_symbols = []
    
    for symbol in PEPE_SYMBOLS_TO_TEST:
        success = await test_pepe_symbol(symbol)
        if success:
            working_symbols.append(symbol)
        logger.info("-" * 40)
        await asyncio.sleep(1)  # Rate limiting
    
    logger.info("=" * 60)
    if working_symbols:
        logger.info(f"✅ Working PEPE symbols: {working_symbols}")
        logger.info(f"🎯 Recommended symbol: {working_symbols[0]}")
    else:
        logger.error("❌ No working PEPE symbols found!")
        logger.info("💡 You may need to check Bitunix documentation or contact support")

if __name__ == "__main__":
    asyncio.run(test_all_pepe_symbols())

