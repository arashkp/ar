#!/usr/bin/env python3
"""
Debug script to test symbol filtering for average price calculation.
"""

import os
from dotenv import load_dotenv
from bitunix import BitunixClient

load_dotenv()

def debug_symbol_filter():
    """Debug symbol filtering for each asset."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    try:
        client = BitunixClient(api_key, api_secret)
        
        # Test each asset
        assets = ['HBAR', 'SUI', 'BONK', 'ONDO']
        
        for coin in assets:
            print(f"\n🔍 Testing {coin}:")
            symbol = f"{coin}USDT"
            
            # Get first page of trades
            try:
                trades_response = client.query_order_history(
                    symbol=symbol,
                    page=1,
                    page_size=10
                )
                
                if trades_response and 'data' in trades_response:
                    trades_data = trades_response['data'].get('data', [])
                    print(f"   Found {len(trades_data)} trades for {symbol}")
                    
                    # Show first few trades
                    for i, trade in enumerate(trades_data[:3]):
                        side = trade.get('side')
                        status = trade.get('status')
                        quantity = trade.get('dealVolume')
                        price = trade.get('avgPrice')
                        base = trade.get('base')
                        symbol_trade = trade.get('symbol')
                        
                        print(f"     Trade {i+1}: side={side}, status={status}, quantity={quantity}, price={price}, base={base}, symbol={symbol_trade}")
                        
                        # Check if this is a BUY trade (side == 1) and completed (status == 2)
                        if side == 1 and status == 2:
                            print(f"       ✅ This is a valid BUY trade for {coin}")
                        else:
                            print(f"       ❌ Not a valid BUY trade (side={side}, status={status})")
                else:
                    print(f"   ❌ No trades found for {symbol}")
                    
            except Exception as e:
                print(f"   ❌ Error fetching trades for {symbol}: {e}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_symbol_filter() 