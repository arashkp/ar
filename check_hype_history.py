#!/usr/bin/env python3
"""
Quick diagnostic to check HYPE/USDT weekly data availability on MEXC.
"""

import asyncio
import ccxt.async_support as ccxt
from datetime import datetime

async def check_hype_weekly_data():
    exchange = ccxt.mexc({'enableRateLimit': True})
    
    try:
        print("Fetching HYPE/USDT weekly data from MEXC...")
        print("=" * 60)
        
        # Fetch maximum weekly candles
        ohlcv = await exchange.fetch_ohlcv('HYPE/USDT', timeframe='1w', limit=500)
        
        print(f"\n✅ Successfully fetched {len(ohlcv)} weekly candles")
        print(f"\n📊 Data Range:")
        print(f"   First candle: {datetime.fromtimestamp(ohlcv[0][0]/1000).strftime('%Y-%m-%d')}")
        print(f"   Last candle:  {datetime.fromtimestamp(ohlcv[-1][0]/1000).strftime('%Y-%m-%d')}")
        
        print(f"\n📈 Moving Average Availability:")
        print(f"   20W SMA: {'✅ Available' if len(ohlcv) >= 20 else '❌ Not enough data'} (need 20, have {len(ohlcv)})")
        print(f"   21W EMA: {'✅ Available' if len(ohlcv) >= 21 else '❌ Not enough data'} (need 21, have {len(ohlcv)})")
        print(f"   50W SMA: {'✅ Available' if len(ohlcv) >= 50 else '❌ Not enough data'} (need 50, have {len(ohlcv)})")
        
        if len(ohlcv) < 50:
            weeks_needed = 50 - len(ohlcv)
            print(f"\n⏳ HYPE needs {weeks_needed} more weeks of data for 50W SMA")
            print(f"   Estimated availability: ~{weeks_needed} weeks from now")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(check_hype_weekly_data())
