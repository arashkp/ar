#!/usr/bin/env python3
"""
Debug script to demonstrate BACKWARD calculation approach.
Shows how we process orders in reverse chronological order to reach target balance.
"""
import os
from dotenv import load_dotenv
from bitunix import BitunixClient
from datetime import datetime

load_dotenv()

def debug_backward_calculation():
    """Demonstrate backward calculation for SUI."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    try:
        client = BitunixClient(api_key, api_secret)
        
        print("🔍 Demonstrating BACKWARD calculation for SUI...")
        
        # Get current SUI balance
        balance_response = client.get_account_balance()
        current_sui_balance = 0.0
        
        if balance_response and 'data' in balance_response:
            for asset in balance_response['data']:
                if asset.get('coin') == 'SUI':
                    current_sui_balance = float(asset.get('balance', 0)) + float(asset.get('balanceLocked', 0))
                    break
        
        print(f"📊 Target SUI balance: {current_sui_balance}")
        
        # Get ALL SUI orders
        symbol = "SUIUSDT"
        all_orders = []
        page = 1
        page_size = 100
        
        print(f"\n📋 Fetching ALL SUI orders...")
        
        while True:
            try:
                print(f"   Fetching page {page}...")
                orders_response = client.query_order_history(
                    symbol=symbol,
                    page=page,
                    page_size=page_size
                )
                
                if not orders_response or 'data' not in orders_response:
                    print(f"   No more data after page {page-1}")
                    break
                    
                orders_data = orders_response['data'].get('data', [])
                if not orders_data:
                    print(f"   No orders on page {page}")
                    break
                
                # Filter only SUI orders (as API returns all symbols)
                sui_orders = [
                    order for order in orders_data
                    if order.get('symbol') == symbol
                ]
                
                all_orders.extend(sui_orders)
                print(f"   Found {len(sui_orders)} SUI orders on page {page}")
                
                page += 1
                if page > 10:  # Safety limit
                    print("   Reached safety limit of 10 pages")
                    break
                    
            except Exception as e:
                print(f"   Error fetching page {page}: {e}")
                break
        
        print(f"\n📊 Total SUI orders found: {len(all_orders)}")
        
        if all_orders:
            # Sort orders by time (newest first) for backward calculation
            all_orders.sort(key=lambda x: x.get('ctime', ''), reverse=True)
            
            print(f"\n🔄 BACKWARD CALCULATION PROCESS:")
            print("=" * 120)
            print(f"{'Date':<25} {'Side':<8} {'Status':<8} {'Price':<15} {'Quantity':<20} {'Accumulated':<15} {'Status':<20}")
            print("=" * 120)
            
            relevant_orders = []
            accumulated_quantity = 0.0
            tolerance = 0.01  # 1% tolerance
            target_balance = current_sui_balance
            
            for order in all_orders:
                timestamp = order.get('ctime', '')
                side = order.get('side')  # 1 = SELL, 2 = BUY (from official docs)
                status = order.get('status')
                price = float(order.get('avgPrice', 0))
                quantity = float(order.get('dealVolume', 0))
                
                try:
                    if timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        date_str = "NO_TIME"
                except:
                    date_str = timestamp
                
                side_text = "SELL" if side == 1 else "BUY" if side == 2 else f"UNK({side})"
                status_text = "FILLED" if status == 2 else "PENDING" if status == 1 else "CANCELED" if status == 3 else f"UNK({status})"
                
                if status == 2:  # Only completed orders
                    if side == 2:  # BUY - adds to position
                        relevant_orders.append({
                            'date': date_str,
                            'price': price,
                            'quantity': quantity,
                            'value': price * quantity
                        })
                        accumulated_quantity += quantity
                        
                        # Check if we've reached the target balance
                        if abs(accumulated_quantity - target_balance) <= (target_balance * tolerance):
                            status_msg = f"✅ TARGET REACHED!"
                            print(f"{date_str:<25} {side_text:<8} {status_text:<8} {price:<15} {quantity:<20} {accumulated_quantity:<15} {status_msg:<20}")
                            break
                        elif accumulated_quantity > target_balance * (1 + tolerance):
                            status_msg = f"⚠️ EXCEEDS TARGET"
                            print(f"{date_str:<25} {side_text:<8} {status_text:<8} {price:<15} {quantity:<20} {accumulated_quantity:<15} {status_msg:<20}")
                            break
                        else:
                            status_msg = f"📈 ACCUMULATING"
                            print(f"{date_str:<25} {side_text:<8} {status_text:<8} {price:<15} {quantity:<20} {accumulated_quantity:<15} {status_msg:<20}")
                            
                    elif side == 1:  # SELL - reduces position
                        # For sells, we need to "undo" them to find the original position
                        accumulated_quantity -= quantity
                        
                        # If this sell would make our accumulated quantity negative, skip it
                        if accumulated_quantity < 0:
                            accumulated_quantity = 0
                            status_msg = f"🔄 RESET TO 0"
                        else:
                            status_msg = f"📉 REDUCING"
                        
                        print(f"{date_str:<25} {side_text:<8} {status_text:<8} {price:<15} {quantity:<20} {accumulated_quantity:<15} {status_msg:<20}")
            
            print("=" * 120)
            
            print(f"\n📈 BACKWARD CALCULATION RESULTS:")
            print(f"Target balance: {target_balance}")
            print(f"Final accumulated quantity: {accumulated_quantity}")
            print(f"Difference: {abs(accumulated_quantity - target_balance)}")
            print(f"Tolerance (1%): {target_balance * tolerance}")
            
            if abs(accumulated_quantity - target_balance) <= (target_balance * tolerance):
                print(f"✅ VALIDATION PASSED!")
            else:
                print(f"❌ VALIDATION FAILED!")
            
            if relevant_orders:
                print(f"\n🟢 RELEVANT BUY ORDERS (used for calculation):")
                print("=" * 80)
                print(f"{'Date':<25} {'Price':<15} {'Quantity':<20} {'Value':<15}")
                print("=" * 80)
                
                total_buy_quantity = 0
                total_buy_value = 0
                
                for order in relevant_orders:
                    print(f"{order['date']:<25} {order['price']:<15} {order['quantity']:<20} {order['value']:<15}")
                    total_buy_quantity += order['quantity']
                    total_buy_value += order['value']
                
                print("=" * 80)
                
                if total_buy_quantity > 0:
                    calculated_avg_price = total_buy_value / total_buy_quantity
                    print(f"\n💰 CALCULATED AVERAGE ENTRY PRICE: {calculated_avg_price}")
                    print(f"   Total buy quantity: {total_buy_quantity}")
                    print(f"   Total buy value: {total_buy_value}")
                    print(f"   Number of buy orders: {len(relevant_orders)}")
                else:
                    print(f"\n❌ No valid buy orders found!")
            else:
                print(f"\n❌ No relevant buy orders found!")
        else:
            print("❌ No SUI orders found!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_backward_calculation() 