#!/usr/bin/env python3
"""
Test script to explore all available methods in the Bitunix SDK.
"""

import os
from dotenv import load_dotenv
from bitunix import BitunixClient

load_dotenv()

def explore_bitunix_methods():
    """Explore all available methods in the Bitunix SDK."""
    
    api_key = os.getenv('BITUNIX_API_KEY')
    api_secret = os.getenv('BITUNIX_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ BITUNIX_API_KEY and BITUNIX_API_SECRET not found in .env")
        return
    
    try:
        client = BitunixClient(api_key, api_secret)
        
        print("🔍 Exploring Bitunix SDK methods...")
        print(f"Client type: {type(client)}")
        print(f"Available methods: {[method for method in dir(client) if not method.startswith('_')]}")
        
        # Test different methods that might provide average entry price
        print("\n📊 Testing potential methods for average entry price:")
        
        # Test get_account_balance
        print("\n1. Testing get_account_balance:")
        try:
            balance = client.get_account_balance()
            print(f"   Response: {balance}")
            if balance and 'data' in balance:
                print(f"   Data structure: {list(balance['data'][0].keys()) if balance['data'] else 'No data'}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test if there are any position-related methods
        print("\n2. Looking for position-related methods:")
        position_methods = [method for method in dir(client) if 'position' in method.lower() or 'cost' in method.lower() or 'avg' in method.lower()]
        print(f"   Found: {position_methods}")
        
        # Test if there are any account-related methods
        print("\n3. Looking for account-related methods:")
        account_methods = [method for method in dir(client) if 'account' in method.lower() or 'user' in method.lower()]
        print(f"   Found: {account_methods}")
        
        # Test any method that might give us cost basis
        print("\n4. Testing potential cost basis methods:")
        for method in dir(client):
            if not method.startswith('_') and any(keyword in method.lower() for keyword in ['cost', 'avg', 'basis', 'entry']):
                print(f"   Testing {method}:")
                try:
                    result = getattr(client, method)()
                    print(f"     Result: {result}")
                except Exception as e:
                    print(f"     Error: {e}")
        
        # Test get_latest_price to see the structure
        print("\n5. Testing get_latest_price for HBARUSDT:")
        try:
            price = client.get_latest_price("HBARUSDT")
            print(f"   Price: {price}")
        except Exception as e:
            print(f"   Error: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    explore_bitunix_methods() 