#!/usr/bin/env python3
"""
Comprehensive debug script to show BACKWARD calculation for ALL assets.
Shows detailed breakdown for HBAR, SUI, BONK, and ONDO.
"""
import os
from dotenv import load_dotenv
from bitunix import BitunixClient
from datetime import datetime

load_dotenv()

def debug_all_assets_backward():
    """Show backward calculation for ALL assets."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    try:
        client = BitunixClient(api_key, api_secret)
        
        print("🔍 BACKWARD CALCULATION FOR ALL ASSETS")
        print("=" * 80)
        
        # Get current balances
        balance_response = client.get_account_balance()
        balances = {}
        
        if balance_response and 'data' in balance_response:
            for asset in balance_response['data']:
                coin = asset.get('coin')
                balance = float(asset.get('balance', 0)) + float(asset.get('balanceLocked', 0))
                if balance > 0 and coin != 'USDT':
                    balances[coin] = balance
        
        print(f"📊 Current balances: {balances}")
        print()
        
        # Assets to analyze
        assets = ['HBAR', 'SUI', 'BONK', 'ONDO']
        
        for coin in assets:
            if coin not in balances:
                print(f"⚠️ {coin}: No balance found, skipping...")
                continue
                
            current_balance = balances[coin]
            print(f"\n{'='*80}")
            print(f"🔍 ANALYZING {coin} (Balance: {current_balance})")
            print(f"{'='*80}")
            
            # Get ALL orders for this coin
            symbol = f"{coin}USDT"
            all_orders = []
            page = 1
            
            print(f"📋 Fetching {coin} orders...")
            
            while page <= 5:  # Limit to 5 pages for performance
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
                    
                    all_orders.extend(symbol_orders)
                    page += 1
                    
                except Exception as e:
                    print(f"   Error fetching page {page} for {coin}: {e}")
                    break
            
            print(f"📊 Total {coin} orders found: {len(all_orders)}")
            
            if all_orders:
                # Sort orders by time (newest first) for backward calculation
                all_orders.sort(key=lambda x: x.get('ctime', ''), reverse=True)
                
                print(f"\n🔄 BACKWARD CALCULATION PROCESS for {coin}:")
                print("-" * 100)
                print(f"{'Date':<25} {'Side':<8} {'Status':<8} {'Price':<15} {'Quantity':<15} {'Accumulated':<15} {'Status':<20}")
                print("-" * 100)
                
                relevant_orders = []
                accumulated_quantity = 0.0
                tolerance = 0.01  # 1% tolerance
                target_balance = current_balance
                
                for order in all_orders:
                    timestamp = order.get('ctime', '')
                    side = order.get('side')  # 1 = SELL, 2 = BUY
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
                                print(f"{date_str:<25} {side_text:<8} {status_text:<8} {price:<15.8f} {quantity:<15.8f} {accumulated_quantity:<15.8f} {status_msg:<20}")
                                break
                            elif accumulated_quantity > target_balance * (1 + tolerance):
                                status_msg = f"⚠️ EXCEEDS TARGET"
                                print(f"{date_str:<25} {side_text:<8} {status_text:<8} {price:<15.8f} {quantity:<15.8f} {accumulated_quantity:<15.8f} {status_msg:<20}")
                                break
                            else:
                                status_msg = f"📈 ACCUMULATING"
                                print(f"{date_str:<25} {side_text:<8} {status_text:<8} {price:<15.8f} {quantity:<15.8f} {accumulated_quantity:<15.8f} {status_msg:<20}")
                                
                        elif side == 1:  # SELL - reduces position
                            # For sells, we need to "undo" them to find the original position
                            accumulated_quantity -= quantity
                            
                            # If this sell would make our accumulated quantity negative, skip it
                            if accumulated_quantity < 0:
                                accumulated_quantity = 0
                                status_msg = f"🔄 RESET TO 0"
                            else:
                                status_msg = f"📉 REDUCING"
                            
                            print(f"{date_str:<25} {side_text:<8} {status_text:<8} {price:<15.8f} {quantity:<15.8f} {accumulated_quantity:<15.8f} {status_msg:<20}")
                
                print("-" * 100)
                
                print(f"\n📈 {coin} BACKWARD CALCULATION RESULTS:")
                print(f"Target balance: {target_balance}")
                print(f"Final accumulated quantity: {accumulated_quantity}")
                print(f"Difference: {abs(accumulated_quantity - target_balance)}")
                print(f"Tolerance (1%): {target_balance * tolerance}")
                
                if abs(accumulated_quantity - target_balance) <= (target_balance * tolerance):
                    print(f"✅ {coin} VALIDATION PASSED!")
                else:
                    print(f"❌ {coin} VALIDATION FAILED!")
                
                if relevant_orders:
                    print(f"\n🟢 {coin} RELEVANT BUY ORDERS (used for calculation):")
                    print("-" * 80)
                    print(f"{'Date':<25} {'Price':<15} {'Quantity':<15} {'Value':<15}")
                    print("-" * 80)
                    
                    total_buy_quantity = 0
                    total_buy_value = 0
                    
                    for order in relevant_orders:
                        print(f"{order['date']:<25} {order['price']:<15.8f} {order['quantity']:<15.8f} {order['value']:<15.8f}")
                        total_buy_quantity += order['quantity']
                        total_buy_value += order['value']
                    
                    print("-" * 80)
                    
                    if total_buy_quantity > 0:
                        calculated_avg_price = total_buy_value / total_buy_quantity
                        print(f"\n💰 {coin} CALCULATED AVERAGE ENTRY PRICE: {calculated_avg_price}")
                        print(f"   Total buy quantity: {total_buy_quantity}")
                        print(f"   Total buy value: {total_buy_value}")
                        print(f"   Number of buy orders: {len(relevant_orders)}")
                        
                        # Get current price for PnL calculation
                        try:
                            price_response = client.get_latest_price(symbol)
                            if price_response and isinstance(price_response, dict) and price_response.get('success') and price_response.get('data'):
                                current_price = float(price_response['data'])
                                unrealized_pnl = (current_price - calculated_avg_price) * current_balance
                                unrealized_pnl_percentage = ((current_price - calculated_avg_price) / calculated_avg_price * 100) if calculated_avg_price > 0 else 0
                                
                                print(f"   Current price: {current_price}")
                                print(f"   Unrealized PnL: {unrealized_pnl:.2f} USDT ({unrealized_pnl_percentage:.2f}%)")
                                
                                if unrealized_pnl > 0:
                                    print(f"   📈 PROFIT!")
                                else:
                                    print(f"   📉 LOSS!")
                            else:
                                print(f"   ⚠️ Could not fetch current price")
                        except Exception as e:
                            print(f"   ⚠️ Error fetching current price: {e}")
                    else:
                        print(f"\n❌ {coin}: No valid buy orders found!")
                else:
                    print(f"\n❌ {coin}: No relevant buy orders found!")
            else:
                print(f"❌ {coin}: No orders found!")
        
        print(f"\n{'='*80}")
        print("🎉 BACKWARD CALCULATION COMPLETE FOR ALL ASSETS!")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_all_assets_backward() 