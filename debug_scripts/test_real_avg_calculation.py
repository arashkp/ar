#!/usr/bin/env python3
"""
Test script to calculate real average entry price from actual buy trades.
"""

import os
from dotenv import load_dotenv
from bitunix import BitunixClient

load_dotenv()

def calculate_real_avg_price():
    """Calculate real average entry price from buy trades."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    try:
        client = BitunixClient(api_key, api_secret)
        
        # Get current balances
        balance_response = client.get_account_balance()
        if not balance_response or 'data' not in balance_response:
            print("❌ Failed to get balance")
            return
            
        balance_data = balance_response['data']
        
        # Calculate average entry price for each asset with balance
        for asset_data in balance_data:
            coin = asset_data.get('coin')
            balance = float(asset_data.get('balance', 0))
            balance_locked = float(asset_data.get('balanceLocked', 0))
            total_balance = balance + balance_locked
            
            if total_balance > 0 and coin != 'USDT':
                print(f"\n🔍 Calculating average entry price for {coin} (balance: {total_balance})")
                
                # Get all buy trades for this coin
                symbol = f"{coin}USDT"
                all_buy_trades = []
                page = 1
                
                while True:
                    try:
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
                        
                        # Filter for BUY trades only (side == 1)
                        buy_trades = [trade for trade in trades_data if trade.get('side') == 1]
                        all_buy_trades.extend(buy_trades)
                        
                        page += 1
                        if page > 10:  # Limit to prevent infinite loops
                            break
                            
                    except Exception as e:
                        print(f"   Error fetching page {page}: {e}")
                        break
                
                print(f"   Found {len(all_buy_trades)} buy trades")
                
                if all_buy_trades:
                    # Sort by timestamp (newest first)
                    all_buy_trades.sort(key=lambda x: x.get('utime', ''), reverse=True)
                    
                    # Calculate weighted average from recent buy trades
                    total_buy_quantity = 0
                    total_buy_value = 0
                    
                    for trade in all_buy_trades:
                        quantity = float(trade.get('dealVolume', 0))
                        price = float(trade.get('avgPrice', 0))
                        
                        if quantity > 0 and price > 0:
                            total_buy_quantity += quantity
                            total_buy_value += quantity * price
                            
                            # If we have enough buy quantity to cover current balance, stop
                            if total_buy_quantity >= total_balance:
                                break
                    
                    if total_buy_quantity > 0:
                        avg_entry_price = total_buy_value / total_buy_quantity
                        print(f"   ✅ Calculated avg entry price: {avg_entry_price}")
                        print(f"   📊 Total buy quantity: {total_buy_quantity}")
                        print(f"   📊 Total buy value: {total_buy_value}")
                        
                        # Show recent buy trades used
                        print(f"   📋 Recent buy trades used:")
                        for i, trade in enumerate(all_buy_trades[:5]):
                            quantity = float(trade.get('dealVolume', 0))
                            price = float(trade.get('avgPrice', 0))
                            timestamp = trade.get('utime', '')
                            print(f"     {i+1}. Quantity: {quantity}, Price: {price}, Time: {timestamp}")
                    else:
                        print(f"   ⚠️  No valid buy trades found")
                else:
                    print(f"   ⚠️  No buy trades found")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    calculate_real_avg_price() 