import asyncio
import logging
import sys
import os

# Add src to Python path to allow direct import of modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Ensure the logger is configured
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting market overview test script (final run)...")
    try:
        # Dynamically import get_market_overview to ensure src path is set
        from routers.market_overview import get_market_overview
        results = await get_market_overview()
        logger.info("Market overview results (final run):")
        for item in results:
            logger.info(item)
        if not results:
            logger.warning("Received empty results from get_market_overview (final run).")
        # Log summary of what to expect
        logger.info("Expected outcomes for this run:")
        logger.info("- Binance symbols (BTC, ETH, DOGE, SUI): Likely geoblocking errors (e.g., 451), returning default data.")
        logger.info("- Bitget HYPE/USDT: Should fetch price and OHLCV, support/resistance. EMA/SMA will be None due to TA-Lib absence (logged warning).")
        logger.info("- POPCAT/USDT: Should no longer be processed or cause errors.")
        logger.info("- TA-Lib: Warning about its absence should be logged.")

    except Exception as e:
        logger.error(f"An error occurred during the test (final run): {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
