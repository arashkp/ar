#!/usr/bin/env python3
"""
Debug script to show ALL HBAR trades sorted by time.
"""

import os
from dotenv import load_dotenv
from bitunix import BitunixClient
from datetime import datetime

load_dotenv()

def debug_hbar_trades():
    """Show ALL HBAR trades sorted by time."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    try:
        client = BitunixClient(api_key, api_secret)
        
        print("🔍 Fetching ALL HBAR trades...")
        symbol = "HBARUSDT"
        all_trades = []
        page = 1
        
        # Fetch ALL pages
        while True:
            try:
                print(f"Fetching page {page}...")
                trades_response = client.query_order_history(
                    symbol=symbol,
                    page=page,
                    page_size=100
                )
                
                if not trades_response or 'data' not in trades_response:
                    print(f"No more data after page {page-1}")
                    break
                    
                trades_data = trades_response['data'].get('data', [])
                if not trades_data:
                    print(f"No trades on page {page}")
                    break
                
                print(f"Found {len(trades_data)} trades on page {page}")
                all_trades.extend(trades_data)
                
                page += 1
                if page > 20:  # Safety limit
                    print("Reached safety limit of 20 pages")
                    break
                    
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                break
        
        print(f"\n📊 Total HBAR trades found: {len(all_trades)}")
        
        if all_trades:
            # Sort by timestamp (newest first)
            all_trades.sort(key=lambda x: x.get('utime', ''), reverse=True)
            
            print(f"\n📋 ALL HBAR trades sorted by time (newest first):")
            print("=" * 80)
            print(f"{'Time':<25} {'Side':<8} {'Price':<12} {'Quantity':<12} {'Status':<8}")
            print("=" * 80)
            
            for i, trade in enumerate(all_trades):
                timestamp = trade.get('utime', '')
                side = trade.get('side')
                price = trade.get('avgPrice', 0)
                quantity = trade.get('dealVolume', 0)
                status = trade.get('status')
                
                # Convert side to readable format
                side_text = "BUY" if side == 1 else "SELL" if side == 2 else f"UNK({side})"
                
                # Convert timestamp to readable format
                try:
                    if timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        time_str = "NO_TIME"
                except:
                    time_str = timestamp
                
                print(f"{time_str:<25} {side_text:<8} {price:<12} {quantity:<12} {status:<8}")
                
                # Show first 20 and last 20 trades
                if i == 19 and len(all_trades) > 40:
                    print("..." + " " * 50 + "...")
                    print(f"Showing {len(all_trades) - 40} more trades...")
                    print("..." + " " * 50 + "...")
                    # Skip to last 20
                    for j in range(len(all_trades) - 20, len(all_trades)):
                        trade = all_trades[j]
                        timestamp = trade.get('utime', '')
                        side = trade.get('side')
                        price = trade.get('avgPrice', 0)
                        quantity = trade.get('dealVolume', 0)
                        status = trade.get('status')
                        
                        side_text = "BUY" if side == 1 else "SELL" if side == 2 else f"UNK({side})"
                        
                        try:
                            if timestamp:
                                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                time_str = "NO_TIME"
                        except:
                            time_str = timestamp
                        
                        print(f"{time_str:<25} {side_text:<8} {price:<12} {quantity:<12} {status:<8}")
                    break
                elif i >= 19 and len(all_trades) <= 40:
                    break
            
            # Summary statistics
            print(f"\n📈 Summary:")
            buy_trades = [t for t in all_trades if t.get('side') == 1]
            sell_trades = [t for t in all_trades if t.get('side') == 2]
            completed_trades = [t for t in all_trades if t.get('status') == 2]
            
            print(f"Total trades: {len(all_trades)}")
            print(f"Buy trades: {len(buy_trades)}")
            print(f"Sell trades: {len(sell_trades)}")
            print(f"Completed trades: {len(completed_trades)}")
            
            # Show recent buy trades only
            recent_buys = [t for t in all_trades if t.get('side') == 1 and t.get('status') == 2][:10]
            if recent_buys:
                print(f"\n🟢 Recent BUY trades (completed):")
                print("=" * 60)
                print(f"{'Time':<25} {'Price':<12} {'Quantity':<12}")
                print("=" * 60)
                for trade in recent_buys:
                    timestamp = trade.get('utime', '')
                    price = trade.get('avgPrice', 0)
                    quantity = trade.get('dealVolume', 0)
                    
                    try:
                        if timestamp:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            time_str = "NO_TIME"
                    except:
                        time_str = timestamp
                    
                    print(f"{time_str:<25} {price:<12} {quantity:<12}")
        else:
            print("❌ No HBAR trades found!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_hbar_trades() 