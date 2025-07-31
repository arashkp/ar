#!/usr/bin/env python3
"""
Debug script to test the validation logic for quantity matching.
"""
import os
from dotenv import load_dotenv
from bitunix import BitunixClient
from datetime import datetime

load_dotenv()

def debug_validation():
    """Test the validation logic for all assets."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    try:
        client = BitunixClient(api_key, api_secret)
        
        # Get current balances
        balance_response = client.get_account_balance()
        balances = {}
        
        if balance_response and 'data' in balance_response:
            for asset in balance_response['data']:
                coin = asset.get('coin')
                balance = float(asset.get('balance', 0)) + float(asset.get('balanceLocked', 0))
                if balance > 0:
                    balances[coin] = balance
        
        print("📊 Current Account Balances:")
        for coin, balance in balances.items():
            print(f"   {coin}: {balance}")
        
        # Test validation for each asset
        assets_to_test = ['HBAR', 'SUI', 'BONK', 'ONDO']
        
        for coin in assets_to_test:
            if coin not in balances:
                print(f"\n❌ {coin}: No balance found")
                continue
                
            print(f"\n🔍 Testing validation for {coin}:")
            current_balance = balances[coin]
            print(f"   Current balance: {current_balance}")
            
            # Get trade history
            symbol = f"{coin}USDT"
            all_buy_trades = []
            page = 1
            
            while page <= 3:  # Limit pages for testing
                try:
                    orders_response = client.query_order_history(
                        symbol=symbol,
                        page=page,
                        page_size=100
                    )
                    
                    if not orders_response or 'data' not in orders_response:
                        break
                        
                    orders_data = orders_response['data'].get('data', [])
                    if not orders_data:
                        break
                    
                    # Filter only orders for this specific symbol
                    symbol_orders = [
                        order for order in orders_data 
                        if order.get('symbol') == symbol
                    ]
                    
                    # Process orders to find position resets and calculate average
                    for order in symbol_orders:
                        side = order.get('side')  # 1 = SELL, 2 = BUY
                        status = order.get('status')  # 2 = FILLED
                        price = float(order.get('avgPrice', 0))
                        quantity = float(order.get('dealVolume', 0))
                        
                        if status == 2:  # Only completed orders
                            if side == 1:  # SELL - potential position reset
                                # Check if this sell is significant (more than 80% of current balance)
                                if quantity > current_balance * 0.8:
                                    # This is a position reset - clear previous buys
                                    all_buy_trades.clear()
                                    print(f"   🎯 Position reset detected: SELL {quantity} at {price}")
                            elif side == 2:  # BUY
                                all_buy_trades.append({
                                    'price': price,
                                    'quantity': quantity,
                                    'value': price * quantity
                                })
                    
                    page += 1
                    
                except Exception as e:
                    print(f"   Error fetching page {page}: {e}")
                    break
            
            if not all_buy_trades:
                print(f"   ❌ No buy trades found")
                continue
            
            # Calculate weighted average
            total_buy_quantity = sum(trade['quantity'] for trade in all_buy_trades)
            total_buy_value = sum(trade['value'] for trade in all_buy_trades)
            calculated_avg_price = total_buy_value / total_buy_quantity
            
            # Validation
            tolerance = 0.01  # 1% tolerance
            balance_difference = abs(total_buy_quantity - current_balance)
            balance_tolerance = current_balance * tolerance
            
            print(f"   📊 Calculation Results:")
            print(f"      Total buy quantity: {total_buy_quantity}")
            print(f"      Total buy value: {total_buy_value}")
            print(f"      Calculated avg price: {calculated_avg_price}")
            print(f"      Current balance: {current_balance}")
            print(f"      Difference: {balance_difference}")
            print(f"      Tolerance: {balance_tolerance}")
            
            if balance_difference <= balance_tolerance:
                print(f"   ✅ VALIDATION PASSED")
            else:
                print(f"   ❌ VALIDATION FAILED")
                print(f"      Difference ({balance_difference}) > Tolerance ({balance_tolerance})")
            
            print(f"   📋 Buy trades used ({len(all_buy_trades)} orders):")
            for i, trade in enumerate(all_buy_trades[-5:], 1):  # Show last 5 trades
                print(f"      {i}. Qty: {trade['quantity']}, Price: {trade['price']}, Value: {trade['value']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_validation() 