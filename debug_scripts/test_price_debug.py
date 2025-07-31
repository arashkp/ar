#!/usr/bin/env python3
"""
Debug script to test price fetching from Bitunix API.
"""
import os
from dotenv import load_dotenv
from bitunix import BitunixClient

load_dotenv()

def test_price_fetching():
    """Test price fetching for all your assets."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    try:
        client = BitunixClient(api_key, api_secret)
        
        # Your actual assets from the balance
        assets = ['HBAR', 'SUI', 'BONK', 'ONDO']
        
        print("🔍 Testing price fetching for your assets...")
        
        for asset in assets:
            symbol = f"{asset}USDT"
            print(f"\n📊 Testing {symbol}:")
            
            try:
                price = client.get_latest_price(symbol)
                print(f"  ✅ Price: {price}")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_price_fetching() 