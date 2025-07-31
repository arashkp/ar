#!/usr/bin/env python3
"""
Debug script to analyze BONK orders and show calculation details.
"""

import os
from dotenv import load_dotenv
from bitunix import BitunixClient
from datetime import datetime

load_dotenv()

def debug_bonk_orders():
    """Analyze BONK orders to identify calculation issues."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    try:
        client = BitunixClient(api_key, api_secret)
        
        print("🔍 Analyzing BONK orders for calculation verification...")
        symbol = "BONKUSDT"
        
        # Get current balance
        balance_response = client.get_account_balance()
        if balance_response and 'data' in balance_response:
            bonk_balance = 0
            for asset in balance_response['data']:
                if asset.get('coin') == 'BONK':
                    bonk_balance = float(asset.get('balance', 0)) + float(asset.get('balanceLocked', 0))
                    break
            
            print(f"📊 Current BONK balance: {bonk_balance}")
        
        # Get all BONK orders
        all_orders = []
        page = 1
        page_size = 100
        
        while True:
            try:
                print(f"Fetching page {page}...")
                orders_response = client.query_order_history(
                    symbol=symbol,
                    page=page,
                    page_size=page_size
                )
                
                if not orders_response or 'data' not in orders_response:
                    print(f"No more data after page {page-1}")
                    break
                    
                orders_data = orders_response['data'].get('data', [])
                if not orders_data:
                    print(f"No orders on page {page}")
                    break
                
                # Filter only BONK orders
                bonk_orders = [
                    order for order in orders_data 
                    if order.get('symbol') == symbol
                ]
                all_orders.extend(bonk_orders)
                
                print(f"Found {len(bonk_orders)} BONK orders on page {page}")
                
                page += 1
                if page > 10:  # Safety limit
                    print("Reached safety limit of 10 pages")
                    break
                    
            except Exception as e:
                print(f"Error fetching page {page}: {e}")
                break
        
        print(f"\n📊 Total BONK orders found: {len(all_orders)}")
        
        if all_orders:
            # Sort by timestamp (oldest first for chronological analysis)
            all_orders.sort(key=lambda x: x.get('ctime', ''))
            
            print(f"\n📋 ALL BONK orders sorted by date (oldest first):")
            print("=" * 120)
            print(f"{'Date':<25} {'Side':<8} {'Status':<8} {'Price':<15} {'Quantity':<20} {'Value':<15} {'Running Qty':<15} {'Running Value':<15}")
            print("=" * 120)
            
            running_quantity = 0
            running_value = 0
            buy_orders = []
            sell_orders = []
            
            for order in all_orders:
                timestamp = order.get('ctime', '')
                side = order.get('side')  # 1 = SELL, 2 = BUY (from official docs)
                status = order.get('status')
                price = float(order.get('avgPrice', 0))
                quantity = float(order.get('dealVolume', 0))
                value = price * quantity
                
                # Convert timestamp
                try:
                    if timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        date_str = "NO_TIME"
                except:
                    date_str = timestamp
                
                # Convert side to readable format
                side_text = "SELL" if side == 1 else "BUY" if side == 2 else f"UNK({side})"
                
                # Convert status to readable format
                status_text = "FILLED" if status == 2 else "PENDING" if status == 1 else "CANCELED" if status == 3 else f"UNK({status})"
                
                # Track running position (only for completed orders)
                if status == 2:  # Only completed orders
                    if side == 2:  # BUY
                        running_quantity += quantity
                        running_value += value
                        buy_orders.append({
                            'date': date_str,
                            'price': price,
                            'quantity': quantity,
                            'value': value
                        })
                    elif side == 1:  # SELL
                        running_quantity -= quantity
                        running_value -= value
                        sell_orders.append({
                            'date': date_str,
                            'price': price,
                            'quantity': quantity,
                            'value': value
                        })
                
                print(f"{date_str:<25} {side_text:<8} {status_text:<8} {price:<15} {quantity:<20} {value:<15} {running_quantity:<15} {running_value:<15}")
            
            print("=" * 120)
            
            # Summary analysis
            print(f"\n📈 Summary Analysis:")
            print(f"Current balance: {bonk_balance}")
            print(f"Final running quantity: {running_quantity}")
            print(f"Final running value: {running_value}")
            print(f"Number of BUY orders: {len(buy_orders)}")
            print(f"Number of SELL orders: {len(sell_orders)}")
            
            if buy_orders:
                print(f"\n🟢 BUY orders (completed):")
                print("=" * 80)
                print(f"{'Date':<25} {'Price':<15} {'Quantity':<20} {'Value':<15}")
                print("=" * 80)
                for buy in buy_orders:
                    print(f"{buy['date']:<25} {buy['price']:<15} {buy['quantity']:<20} {buy['value']:<15}")
                
                # Calculate average from buy orders
                total_buy_quantity = sum(buy['quantity'] for buy in buy_orders)
                total_buy_value = sum(buy['value'] for buy in buy_orders)
                
                if total_buy_quantity > 0:
                    calculated_avg_price = total_buy_value / total_buy_quantity
                    print(f"\n💰 Calculated average entry price: {calculated_avg_price}")
                    print(f"   Total buy quantity: {total_buy_quantity}")
                    print(f"   Total buy value: {total_buy_value}")
                    print(f"   My hardcoded value: 0.00002565")
                    print(f"   Difference: {abs(calculated_avg_price - 0.00002565)}")
            
            if sell_orders:
                print(f"\n🔴 SELL orders (completed):")
                print("=" * 80)
                print(f"{'Date':<25} {'Price':<15} {'Quantity':<20} {'Value':<15}")
                print("=" * 80)
                for sell in sell_orders:
                    print(f"{sell['date']:<25} {sell['price']:<15} {sell['quantity']:<20} {sell['value']:<15}")
            
        else:
            print("❌ No BONK orders found!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_bonk_orders() 