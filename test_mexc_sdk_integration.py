#!/usr/bin/env python3
"""
Test script for MEXC API integration using the mexc-api package.

This script tests the basic functionality of the MEXC API integration
without placing actual orders.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append('src')

from src.services.mexc_service import MEXCService
from mexc_api.common.enums import Side, OrderType

# Load environment variables
load_dotenv()

async def test_mexc_sdk_integration():
    """Test MEXC API integration."""
    print("Testing MEXC API Integration...")
    
    # Get API keys from environment
    api_key = os.getenv('MEXC_API_KEY')
    api_secret = os.getenv('MEXC_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ MEXC API keys not found in environment variables")
        print("Please set MEXC_API_KEY and MEXC_API_SECRET")
        return False
    
    try:
        # Test MEXC service initialization
        print("1. Testing MEXC service initialization...")
        mexc_service = MEXCService(api_key=api_key, api_secret=api_secret)
        print("✅ MEXC service initialized successfully")
        
        # Test symbol formatting
        print("2. Testing symbol formatting...")
        formatted_symbol = mexc_service.format_symbol("BTC/USDT")
        expected_symbol = "BTCUSDT"
        if formatted_symbol == expected_symbol:
            print(f"✅ Symbol formatting works: {formatted_symbol}")
        else:
            print(f"❌ Symbol formatting failed: expected {expected_symbol}, got {formatted_symbol}")
            return False
        
        # Test order parameter formatting
        print("3. Testing order parameter formatting...")
        params = mexc_service.format_order_params(
            symbol="BTC/USDT",
            side="BUY",
            order_type="LIMIT",
            quantity=0.001,
            price=50000.0,
            client_order_id="test_order_123"
        )
        expected_keys = ['symbol', 'side', 'order_type', 'quantity', 'price', 'newClientOrderId']
        if all(key in params for key in expected_keys):
            print(f"✅ Order parameter formatting works: {params}")
        else:
            print(f"❌ Order parameter formatting failed: missing keys")
            return False
        
        # Test status mapping
        print("4. Testing status mapping...")
        status_mappings = [
            ('NEW', 'open'),
            ('FILLED', 'filled'),
            ('CANCELED', 'canceled'),
            ('REJECTED', 'rejected')
        ]
        for mexc_status, expected_status in status_mappings:
            mapped_status = mexc_service._map_mexc_status(mexc_status)
            if mapped_status == expected_status:
                print(f"✅ Status mapping works: {mexc_status} -> {mapped_status}")
            else:
                print(f"❌ Status mapping failed: {mexc_status} -> {mapped_status} (expected {expected_status})")
                return False
        
        # Test response parsing (with mock data)
        print("5. Testing response parsing...")
        mock_response = {
            'orderId': '12345',
            'symbol': 'BTCUSDT',
            'status': 'NEW',
            'executedQty': '0.0',
            'origQty': '0.001',
            'cummulativeQuoteQty': '0.0',
            'time': 1640995200000  # Unix timestamp in milliseconds
        }
        original_data = {
            'symbol': 'BTC/USDT',
            'amount': 0.001,
            'side': 'buy',
            'type': 'limit'
        }
        parsed_data = mexc_service.parse_order_response({'data': mock_response}, original_data)
        if parsed_data.get('exchange_order_id') == '12345':
            print(f"✅ Response parsing works: {parsed_data}")
        else:
            print(f"❌ Response parsing failed")
            return False
        
        print("\n🎉 All MEXC API integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

async def test_mexc_account_info():
    """Test getting account information from MEXC."""
    print("\nTesting MEXC Account Info...")
    
    api_key = os.getenv('MEXC_API_KEY')
    api_secret = os.getenv('MEXC_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ MEXC API keys not found")
        return False
    
    try:
        mexc_service = MEXCService(api_key=api_key, api_secret=api_secret)
        account_info = await mexc_service.get_account_info()
        
        if account_info and 'balances' in account_info:
            print("✅ Account info retrieved successfully")
            print(f"Account type: {account_info.get('accountType', 'Unknown')}")
            print(f"Number of balances: {len(account_info.get('balances', []))}")
            return True
        else:
            print("❌ Failed to get account info")
            return False
            
    except Exception as e:
        print(f"❌ Account info test failed: {e}")
        return False

async def main():
    """Main test function."""
    print("=" * 50)
    print("MEXC API Integration Test")
    print("=" * 50)
    
    # Test basic integration
    integration_success = await test_mexc_sdk_integration()
    
    if integration_success:
        # Test account info (requires valid API keys)
        await test_mexc_account_info()
    
    print("\n" + "=" * 50)
    if integration_success:
        print("✅ MEXC API integration is ready!")
    else:
        print("❌ MEXC API integration has issues")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main()) 