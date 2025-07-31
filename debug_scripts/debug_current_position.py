#!/usr/bin/env python3
"""
Debug script to calculate actual current position.
"""

import os
from dotenv import load_dotenv
from bitunix import BitunixClient
from datetime import datetime

load_dotenv()

def debug_current_position():
    """Calculate actual current position by tracking recent activity."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    try:
        client = BitunixClient(api_key, api_secret)
        
        print("🔍 Calculating actual current position for HBAR...")
        symbol = "HBARUSDT"
        
        # Get current balance
        balance_response = client.get_account_balance()
        if balance_response and 'data' in balance_response:
            hbar_balance = 0
            for asset in balance_response['data']:
                if asset.get('coin') == 'HBAR':
                    hbar_balance = float(asset.get('balance', 0)) + float(asset.get('balanceLocked', 0))
                    break
            
            print(f"📊 Current HBAR balance: {hbar_balance}")
        
        # Get recent trades to understand position changes
        trades_response = client.query_order_history(
            symbol=symbol,
            page=1,
            page_size=50
        )
        
        if trades_response and 'data' in trades_response:
            trades_data = trades_response['data'].get('data', [])
            
            # Filter only HBAR trades and completed trades
            hbar_trades = [
                trade for trade in trades_data 
                if (trade.get('symbol') == symbol and 
                    trade.get('status') == 2)  # Only completed trades
            ]
            
            print(f"\n📋 Recent HBAR trades (completed only):")
            print("=" * 80)
            print(f"{'Time':<25} {'Side':<8} {'Price':<12} {'Quantity':<12} {'Running Qty':<12}")
            print("=" * 80)
            
            running_quantity = 0
            buy_trades = []
            
            # Sort by time (newest first)
            hbar_trades.sort(key=lambda x: x.get('utime', ''), reverse=True)
            
            for trade in hbar_trades:
                timestamp = trade.get('utime', '')
                side = trade.get('side')  # 1 = BUY, 2 = SELL
                price = float(trade.get('avgPrice', 0))
                quantity = float(trade.get('dealVolume', 0))
                
                # Convert timestamp
                try:
                    if timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        time_str = "NO_TIME"
                except:
                    time_str = timestamp
                
                # Track position
                if side == 1:  # BUY
                    running_quantity += quantity
                    buy_trades.append({
                        'time': time_str,
                        'price': price,
                        'quantity': quantity
                    })
                    side_text = "BUY"
                elif side == 2:  # SELL
                    running_quantity -= quantity
                    side_text = "SELL"
                
                print(f"{time_str:<25} {side_text:<8} {price:<12} {quantity:<12} {running_quantity:<12}")
                
                # Stop when we reach current balance
                if running_quantity <= hbar_balance:
                    print(f"\n🎯 Found current position! Running quantity ({running_quantity}) matches balance ({hbar_balance})")
                    break
            
            print(f"\n📈 Summary:")
            print(f"Current balance: {hbar_balance}")
            print(f"Calculated running quantity: {running_quantity}")
            print(f"Number of buy trades found: {len(buy_trades)}")
            
            if buy_trades:
                print(f"\n🟢 Buy trades that contribute to current position:")
                for buy in buy_trades:
                    print(f"  - {buy['time']}: {buy['quantity']} @ {buy['price']}")
                
                # Calculate average from buy trades
                total_quantity = sum(buy['quantity'] for buy in buy_trades)
                total_value = sum(buy['quantity'] * buy['price'] for buy in buy_trades)
                
                if total_quantity > 0:
                    avg_price = total_value / total_quantity
                    print(f"\n💰 Calculated average entry price: {avg_price}")
                    print(f"   Total quantity: {total_quantity}")
                    print(f"   Total value: {total_value}")
            
        else:
            print("❌ No trades found!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_current_position() 