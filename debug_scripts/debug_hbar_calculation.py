#!/usr/bin/env python3
"""
Debug script to show EXACTLY which HBAR orders are used for average entry price calculation.
FIXED: Only use buy orders AFTER the position close on July 26th!
"""
import os
from dotenv import load_dotenv
from bitunix import BitunixClient
from datetime import datetime

load_dotenv()

def debug_hbar_calculation():
    """Show exactly which HBAR orders are used for average calculation."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    try:
        client = BitunixClient(api_key, api_secret)
        
        print("🔍 Debugging HBAR average entry price calculation...")
        symbol = "HBARUSDT"
        
        # Get current balance first
        balance_response = client.get_account_balance()
        current_hbar_balance = 0.0
        if balance_response and 'data' in balance_response:
            for asset in balance_response['data']:
                if asset.get('coin') == 'HBAR':
                    current_hbar_balance = float(asset.get('balance', 0)) + float(asset.get('balanceLocked', 0))
                    break
        
        print(f"📊 Current HBAR balance: {current_hbar_balance}")
        
        # Get ALL HBAR orders from API
        all_hbar_orders = []
        page = 1
        page_size = 100
        
        print(f"\n📋 Fetching ALL HBAR orders from API...")
        
        while page <= 10:  # Safety limit
            try:
                print(f"  Fetching page {page}...")
                orders_response = client.query_order_history(
                    symbol=symbol,
                    page=page,
                    page_size=page_size
                )
                
                if not orders_response or 'data' not in orders_response:
                    print(f"    No more data after page {page-1}")
                    break
                    
                orders_data = orders_response['data'].get('data', [])
                if not orders_data:
                    print(f"    No orders on page {page}")
                    break
                
                # Filter only HBAR orders (as API returns all symbols)
                hbar_orders = [
                    order for order in orders_data 
                    if order.get('symbol') == symbol
                ]
                
                all_hbar_orders.extend(hbar_orders)
                print(f"    Found {len(hbar_orders)} HBAR orders on page {page}")
                
                page += 1
                
            except Exception as e:
                print(f"    Error fetching page {page}: {e}")
                break
        
        print(f"\n📊 Total HBAR orders found: {len(all_hbar_orders)}")
        
        if all_hbar_orders:
            # Sort by timestamp (oldest first)
            all_hbar_orders.sort(key=lambda x: x.get('ctime', ''))
            
            print(f"\n📋 ALL HBAR orders from API (sorted by date):")
            print("=" * 120)
            print(f"{'Date':<25} {'Side':<8} {'Status':<8} {'Price':<15} {'Quantity':<20} {'Value':<15} {'Order ID':<20}")
            print("=" * 120)
            
            # Find the position close date (July 26th, 2025-07-26 15:41:40)
            position_close_date = "2025-07-26T15:41:40.193254Z"
            position_close_timestamp = datetime.fromisoformat(position_close_date.replace('Z', '+00:00'))
            
            print(f"\n🎯 POSITION CLOSE DATE: {position_close_date}")
            print(f"   Only using buy orders AFTER this date!")
            
            buy_orders_used = []
            total_buy_quantity = 0
            total_buy_value = 0
            
            for order in all_hbar_orders:
                timestamp = order.get('ctime', '')
                side = order.get('side')  # 1 = SELL, 2 = BUY (from official docs)
                status = order.get('status')
                price = float(order.get('avgPrice', 0))
                quantity = float(order.get('dealVolume', 0))
                value = price * quantity
                order_id = order.get('orderId', 'N/A')
                
                # Convert timestamp
                try:
                    if timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        date_str = "NO_TIME"
                        dt = None
                except:
                    date_str = timestamp
                    dt = None
                
                # Convert side to readable format
                side_text = "SELL" if side == 1 else "BUY" if side == 2 else f"UNK({side})"
                
                # Convert status to readable format
                status_text = "FILLED" if status == 2 else "PENDING" if status == 1 else "CANCELED" if status == 3 else f"UNK({status})"
                
                # Mark if this is the position close
                is_position_close = " 🎯 POSITION CLOSE!" if timestamp == position_close_date else ""
                
                print(f"{date_str:<25} {side_text:<8} {status_text:<8} {price:<15} {quantity:<20} {value:<15} {order_id:<20}{is_position_close}")
                
                # Track BUY orders that would be used in calculation (ONLY AFTER POSITION CLOSE)
                if (status == 2 and  # Completed orders only
                    side == 2 and  # BUY orders only
                    dt and  # Valid timestamp
                    dt > position_close_timestamp):  # AFTER position close
                    
                    buy_orders_used.append({
                        'date': date_str,
                        'price': price,
                        'quantity': quantity,
                        'value': value,
                        'order_id': order_id
                    })
                    
                    total_buy_quantity += quantity
                    total_buy_value += value
            
            print("=" * 120)
            
            # Show calculation details
            print(f"\n💰 AVERAGE ENTRY PRICE CALCULATION (AFTER POSITION CLOSE):")
            print(f"   Total BUY orders used: {len(buy_orders_used)}")
            print(f"   Total buy quantity: {total_buy_quantity}")
            print(f"   Total buy value: {total_buy_value}")
            
            if total_buy_quantity > 0:
                calculated_avg_price = total_buy_value / total_buy_quantity
                print(f"   Calculated average: {calculated_avg_price}")
                print(f"   Current balance: {current_hbar_balance}")
                
                # Show what the API is returning
                print(f"\n🔍 What the API endpoint returns:")
                print(f"   API average entry price: 0.2565473739466777")
                print(f"   Difference: {abs(calculated_avg_price - 0.2565473739466777)}")
                
                if buy_orders_used:
                    print(f"\n📋 BUY orders used in calculation (AFTER position close):")
                    print("=" * 80)
                    print(f"{'Date':<25} {'Price':<15} {'Quantity':<20} {'Value':<15}")
                    print("=" * 80)
                    for buy in buy_orders_used:
                        print(f"{buy['date']:<25} {buy['price']:<15} {buy['quantity']:<20} {buy['value']:<15}")
                else:
                    print("❌ No buy orders found after position close!")
            else:
                print("❌ No valid BUY orders found after position close!")
        
        else:
            print("❌ No HBAR orders found!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_hbar_calculation() 