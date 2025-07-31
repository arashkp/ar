#!/usr/bin/env python3
"""
Debug script to test trade history fetching from Bitunix API.
"""

import os
import asyncio
from dotenv import load_dotenv
from bitunix import BitunixClient

load_dotenv()

def debug_trade_history():
    """Debug trade history fetching for each coin."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    print(f"🔑 API Key: {api_key[:10]}...")
    print(f"🔐 API Secret: {api_secret[:10]}...")
    
    try:
        # Initialize the client
        print("\n🚀 Initializing Bitunix client...")
        client = BitunixClient(api_key, api_secret)
        
        # Test coins
        coins = ['HBAR', 'SUI', 'BONK', 'ONDO']
        
        for coin in coins:
            print(f"\n{'='*50}")
            print(f"🔍 Analyzing {coin} trade history...")
            print(f"{'='*50}")
            
            symbol = f"{coin}USDT"
            
            # Get current price
            try:
                current_price = client.get_latest_price(symbol)
                print(f"💰 Current {coin} price: {current_price}")
            except Exception as e:
                print(f"❌ Failed to get current price: {e}")
                continue
            
            # Get trade history
            all_trades = []
            page = 1
            
            while True:
                try:
                    trades_response = client.query_order_history(
                        symbol=symbol,
                        page=page,
                        page_size=100
                    )
                    
                    if not trades_response or 'data' not in trades_response:
                        print(f"📄 Page {page}: No data returned")
                        break
                    
                    trades_data = trades_response['data'].get('data', [])
                    if not trades_data:
                        print(f"📄 Page {page}: Empty data")
                        break
                    
                    print(f"📄 Page {page}: Found {len(trades_data)} trades")
                    all_trades.extend(trades_data)
                    page += 1
                    
                    if page > 10:  # Limit to 10 pages for debugging
                        print(f"⚠️  Limited to {page-1} pages for debugging")
                        break
                        
                except Exception as e:
                    print(f"❌ Error fetching page {page}: {e}")
                    break
            
            print(f"\n📊 Total trades found: {len(all_trades)}")
            
            if all_trades:
                # Sort by timestamp (newest first)
                all_trades.sort(key=lambda x: x.get('utime', ''), reverse=True)
                
                # Analyze trades
                buy_trades = []
                sell_trades = []
                
                for trade in all_trades[:20]:  # Show first 20 trades
                    side = trade.get('side')
                    quantity = float(trade.get('dealVolume', 0))
                    price = float(trade.get('avgPrice', 0))
                    timestamp = trade.get('utime', '')
                    
                    if side == 0:  # BUY
                        buy_trades.append({
                            'quantity': quantity,
                            'price': price,
                            'timestamp': timestamp
                        })
                        print(f"🟢 BUY: {quantity} @ {price} ({timestamp})")
                    elif side == 1:  # SELL
                        sell_trades.append({
                            'quantity': quantity,
                            'price': price,
                            'timestamp': timestamp
                        })
                        print(f"🔴 SELL: {quantity} @ {price} ({timestamp})")
                
                print(f"\n📈 Buy trades: {len(buy_trades)}")
                print(f"📉 Sell trades: {len(sell_trades)}")
                
                # Calculate simple average from recent buy trades
                if buy_trades:
                    total_quantity = sum(trade['quantity'] for trade in buy_trades)
                    total_value = sum(trade['quantity'] * trade['price'] for trade in buy_trades)
                    avg_price = total_value / total_quantity if total_quantity > 0 else 0
                    print(f"📊 Simple avg from {len(buy_trades)} buy trades: {avg_price}")
                else:
                    print("⚠️  No buy trades found!")
            else:
                print("❌ No trade history found!")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_trade_history() 