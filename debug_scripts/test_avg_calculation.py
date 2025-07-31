#!/usr/bin/env python3
"""
Test script to debug average price calculation.
"""

import os
from dotenv import load_dotenv
from bitunix import BitunixClient

load_dotenv()

def test_avg_calculation():
    """Test average price calculation for HBAR."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    try:
        client = BitunixClient(api_key, api_secret)
        
        # Test HBAR
        symbol = "HBARUSDT"
        current_quantity = 2825.0211
        
        print(f"🔍 Testing {symbol} with current quantity: {current_quantity}")
        
        # Get trade history
        all_trades = []
        page = 1
        
        while True:
            trades_response = client.query_order_history(
                symbol=symbol,
                page=page,
                page_size=100
            )
            
            if not trades_response or 'data' not in trades_response:
                break
                
            trades_data = trades_response['data'].get('data', [])
            if not trades_data:
                break
                
            all_trades.extend(trades_data)
            page += 1
            
            if page > 5:  # Limit for testing
                break
        
        print(f"📊 Total trades found: {len(all_trades)}")
        
        if all_trades:
            # Sort by timestamp (newest first)
            all_trades.sort(key=lambda x: x.get('utime', ''), reverse=True)
            
            # Track position changes
            running_quantity = 0
            buy_trades_for_current_position = []
            
            print(f"\n🔄 Processing trades (newest first):")
            
            for i, trade in enumerate(all_trades[:20]):  # Show first 20
                side = trade.get('side')
                quantity = float(trade.get('dealVolume', 0))
                price = float(trade.get('avgPrice', 0))
                timestamp = trade.get('utime', '')
                
                print(f"  {i+1}. Side: {side}, Quantity: {quantity}, Price: {price}, Time: {timestamp}")
                
                if quantity <= 0 or price <= 0:
                    continue
                
                if side == 1:  # BUY trade
                    running_quantity += quantity
                    buy_trades_for_current_position.append({
                        'quantity': quantity,
                        'price': price,
                        'timestamp': timestamp
                    })
                    print(f"     ✅ BUY: Running quantity now {running_quantity}")
                    
                elif side == 2:  # SELL trade
                    running_quantity -= quantity
                    print(f"     ❌ SELL: Running quantity now {running_quantity}")
                    
                    # If this sell completely or significantly reduces position, reset
                    if running_quantity <= 0 or running_quantity < current_quantity * 0.1:
                        print(f"     🔄 Position reset detected!")
                        running_quantity = 0
                        buy_trades_for_current_position = []
            
            print(f"\n📈 Buy trades for current position: {len(buy_trades_for_current_position)}")
            
            # Calculate weighted average from current position's buy trades
            if buy_trades_for_current_position:
                total_buy_quantity = sum(trade['quantity'] for trade in buy_trades_for_current_position)
                total_buy_value = sum(trade['quantity'] * trade['price'] for trade in buy_trades_for_current_position)
                
                if total_buy_quantity > 0:
                    avg_price = total_buy_value / total_buy_quantity
                    print(f"📊 Calculated avg entry price: {avg_price}")
                    print(f"📊 Total buy quantity: {total_buy_quantity}")
                    print(f"📊 Total buy value: {total_buy_value}")
                    
                    # Show individual buy trades
                    print(f"\n📋 Buy trades used:")
                    for i, trade in enumerate(buy_trades_for_current_position):
                        print(f"  {i+1}. Quantity: {trade['quantity']}, Price: {trade['price']}, Value: {trade['quantity'] * trade['price']}")
                else:
                    print("⚠️  No valid buy trades found!")
            else:
                print("⚠️  No buy trades found for current position!")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_avg_calculation() 