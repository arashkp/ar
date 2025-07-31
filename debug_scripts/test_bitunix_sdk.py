#!/usr/bin/env python3
"""
Test script for the official Bitunix SDK.
"""

import os
from dotenv import load_dotenv
from bitunix import BitunixClient

load_dotenv()

def test_bitunix_sdk():
    """Test the official Bitunix SDK."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    print(f"🔑 API Key: {api_key[:10]}...")
    print(f"🔐 API Secret: {api_secret[:10]}...")
    
    try:
        # Initialize the client
        print("\n🚀 Initializing Bitunix client...")
        client = BitunixClient(api_key, api_secret)
        
        # Test public endpoints first (no auth required)
        print("\n📊 Testing public endpoints...")
        
        try:
            # Get latest price for BTC/USDT
            latest_price = client.get_latest_price("BTCUSDT")
            print(f"✅ BTC/USDT Price: {latest_price}")
        except Exception as e:
            print(f"❌ Failed to get BTC price: {e}")
        
        try:
            # Get all trading pairs
            trading_pairs = client.get_trading_pairs()
            print(f"✅ Trading pairs count: {len(trading_pairs) if trading_pairs else 0}")
        except Exception as e:
            print(f"❌ Failed to get trading pairs: {e}")
        
        try:
            # Get rate data
            rate_data = client.get_rate_data()
            print(f"✅ Rate data: {rate_data}")
        except Exception as e:
            print(f"❌ Failed to get rate data: {e}")
        
        try:
            # Get token data
            token_data = client.get_token_data()
            print(f"✅ Token data: {token_data}")
        except Exception as e:
            print(f"❌ Failed to get token data: {e}")
        
        # Test authenticated endpoints
        print("\n🔐 Testing authenticated endpoints...")
        
        try:
            # Get account balance
            account_balance = client.get_account_balance()
            print(f"✅ Account balance: {account_balance}")
            
            if account_balance:
                print("\n💰 Your Real Balance:")
                for asset, amount in account_balance.items():
                    if float(amount) > 0:
                        print(f"   {asset}: {amount}")
        except Exception as e:
            print(f"❌ Failed to get account balance: {e}")
        
        try:
            # Query current orders
            current_orders = client.query_current_orders(symbol="BTCUSDT")
            print(f"✅ Current orders: {current_orders}")
        except Exception as e:
            print(f"❌ Failed to get current orders: {e}")
        
        try:
            # Query order history
            order_history = client.query_order_history(symbol="BTCUSDT", page=1, page_size=5)
            print(f"✅ Order history: {order_history}")
        except Exception as e:
            print(f"❌ Failed to get order history: {e}")
        
        print("\n✅ Bitunix SDK test completed!")
        
    except Exception as e:
        print(f"❌ Failed to initialize Bitunix client: {e}")

if __name__ == "__main__":
    test_bitunix_sdk() 