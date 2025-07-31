#!/usr/bin/env python3
"""
Debug script to verify correct trade interpretation.
"""

import os
from dotenv import load_dotenv
from bitunix import BitunixClient
from datetime import datetime

load_dotenv()

def debug_trade_interpretation():
    """Verify correct trade interpretation."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    try:
        client = BitunixClient(api_key, api_secret)
        
        print("🔍 Verifying trade interpretation for HBAR...")
        symbol = "HBARUSDT"
        
        # Get first page of trades
        trades_response = client.query_order_history(
            symbol=symbol,
            page=1,
            page_size=20
        )
        
        if trades_response and 'data' in trades_response:
            trades_data = trades_response['data'].get('data', [])
            
            print(f"\n📋 First 20 HBAR trades with interpretation:")
            print("=" * 100)
            print(f"{'Time':<25} {'Side':<8} {'Status':<8} {'Price':<12} {'Quantity':<12} {'Interpretation':<20}")
            print("=" * 100)
            
            for trade in trades_data[:20]:
                timestamp = trade.get('utime', '')
                side = trade.get('side')
                status = trade.get('status')
                price = trade.get('avgPrice', 0)
                quantity = trade.get('dealVolume', 0)
                
                # Convert side to readable format
                side_text = "BUY" if side == 1 else "SELL" if side == 2 else f"UNK({side})"
                
                # Convert status to readable format
                status_text = "COMPLETED" if status == 2 else "PENDING" if status == 1 else "CANCELED" if status == 3 else f"UNK({status})"
                
                # Convert timestamp to readable format
                try:
                    if timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        time_str = "NO_TIME"
                except:
                    time_str = timestamp
                
                # Interpretation
                if status == 2:  # Completed
                    if side == 1:  # BUY
                        interpretation = "✅ BUY (completed)"
                    elif side == 2:  # SELL
                        interpretation = "🔴 SELL (completed)"
                    else:
                        interpretation = "❓ Unknown side"
                else:
                    interpretation = "⏸️ Not completed"
                
                print(f"{time_str:<25} {side_text:<8} {status_text:<8} {price:<12} {quantity:<12} {interpretation:<20}")
            
            # Summary
            completed_buys = [t for t in trades_data if t.get('side') == 1 and t.get('status') == 2]
            completed_sells = [t for t in trades_data if t.get('side') == 2 and t.get('status') == 2]
            pending_orders = [t for t in trades_data if t.get('status') == 1]
            canceled_orders = [t for t in trades_data if t.get('status') == 3]
            
            print(f"\n📊 Summary:")
            print(f"Completed BUY orders: {len(completed_buys)}")
            print(f"Completed SELL orders: {len(completed_sells)}")
            print(f"Pending orders: {len(pending_orders)}")
            print(f"Canceled orders: {len(canceled_orders)}")
            print(f"Total orders: {len(trades_data)}")
            
        else:
            print("❌ No trades found!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_trade_interpretation() 