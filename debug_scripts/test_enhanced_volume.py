#!/usr/bin/env python3
"""
Test script for enhanced volume analysis implementation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def test_enhanced_volume_analysis():
    """Test the enhanced volume analysis calculations"""
    
    print("🧪 Testing Enhanced Volume Analysis")
    print("=" * 50)
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    
    # Generate realistic price and volume data
    base_price = 50000
    base_volume = 1000000
    
    prices = []
    volumes = []
    
    for i in range(100):
        # Price with some trend and noise
        if i < 50:
            price = base_price + i * 10 + np.random.normal(0, 100)
        else:
            price = base_price + 500 - (i-50) * 8 + np.random.normal(0, 100)
        
        # Volume with some patterns
        if i == 30:  # Volume spike
            volume = base_volume * 3 + np.random.normal(0, 100000)
        elif i == 70:  # Volume drop
            volume = base_volume * 0.3 + np.random.normal(0, 50000)
        else:
            volume = base_volume + np.random.normal(0, 200000)
        
        prices.append(max(price, 1000))  # Ensure positive price
        volumes.append(max(volume, 10000))  # Ensure positive volume
    
    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': volumes
    })
    
    print(f"📊 Sample data created: {len(df)} records")
    print(f"   Price range: ${df['close'].min():,.0f} - ${df['close'].max():,.0f}")
    print(f"   Volume range: {df['volume'].min():,.0f} - {df['volume'].max():,.0f}")
    
    # Test enhanced volume analysis
    print("\n🔧 Testing Enhanced Volume Calculations:")
    
    # 1. Volume EMA
    df['volume_ema_20'] = df['volume'].ewm(span=20, adjust=False).mean()
    print(f"   ✅ Volume EMA (20): {df['volume_ema_20'].iloc[-1]:,.0f}")
    
    # 2. Volume Ratio
    df['volume_ratio'] = df['volume'] / df['volume_ema_20']
    current_volume_ratio = df['volume_ratio'].iloc[-1]
    print(f"   ✅ Volume Ratio: {current_volume_ratio:.2f}x")
    
    # 3. Volume Ratio Average
    df['volume_ratio_avg'] = df['volume_ratio'].rolling(window=5).mean()
    current_volume_ratio_avg = df['volume_ratio_avg'].iloc[-1]
    print(f"   ✅ Volume Ratio Avg: {current_volume_ratio_avg:.2f}x")
    
    # 4. Volume-Price Ratio
    df['price_change'] = df['close'].pct_change()
    df['vol_price_ratio'] = df['volume_ratio'] * df['price_change'].abs()
    current_vol_price_ratio = df['vol_price_ratio'].iloc[-1]
    print(f"   ✅ Volume-Price Ratio: {current_vol_price_ratio:.3f}")
    
    # 5. Volume Status
    def volume_level(vr):
        if vr > 2:
            return "very_high"
        elif vr > 1.2:
            return "high"
        elif vr < 0.5:
            return "low"
        else:
            return "normal"
    
    df['volume_status'] = df['volume_ratio'].apply(volume_level)
    current_volume_status = df['volume_status'].iloc[-1]
    print(f"   ✅ Volume Status: {current_volume_status}")
    
    # Test DCA analysis logic
    print("\n🎯 Testing DCA Analysis Logic:")
    
    # Simulate DCA analysis
    current_price = df['close'].iloc[-1]
    rsi_14 = 45.0  # Simulated RSI
    volume_ratio = current_volume_ratio
    volume_ratio_avg = current_volume_ratio_avg
    vol_price_ratio = current_vol_price_ratio
    volume_status = current_volume_status
    
    reasoning = []
    confidence = 50.0
    signal = "hold"
    amount_multiplier = 1.0
    
    # Enhanced Volume Analysis
    if volume_status == "very_high":
        reasoning.append("Very high volume - potential breakout/breakdown")
        confidence += 15
        if vol_price_ratio > 1.5:
            reasoning.append("Volume confirms strong price movement")
            confidence += 10
            amount_multiplier = 1.4
    elif volume_status == "high":
        reasoning.append("High volume activity")
        confidence += 10
        if vol_price_ratio > 1.0:
            reasoning.append("Volume supports price movement")
            confidence += 5
    elif volume_status == "low":
        reasoning.append("Low volume - weak momentum")
        confidence -= 10
        amount_multiplier *= 0.8
        if vol_price_ratio < 0.5:
            reasoning.append("Price moving without volume support")
            confidence -= 5
    
    # Volume trend analysis
    if volume_ratio_avg > 1.3:
        reasoning.append("Volume trend is increasing")
        confidence += 5
    elif volume_ratio_avg < 0.7:
        reasoning.append("Volume trend is decreasing")
        confidence -= 5
    
    # Volume-price divergence detection
    if vol_price_ratio < 0.3 and abs(df['price_change'].iloc[-1]) > 0.02:
        reasoning.append("Price moving without volume confirmation")
        confidence -= 10
        signal = "wait"
    
    # Determine final signal
    if confidence >= 80:
        signal = "strong_buy"
    elif confidence >= 60:
        signal = "buy"
    elif confidence >= 40:
        signal = "hold"
    elif confidence >= 20:
        signal = "wait"
    else:
        signal = "avoid"
    
    # Clamp values
    confidence = max(0, min(100, confidence))
    amount_multiplier = max(0.5, min(2.0, amount_multiplier))
    
    print(f"   📈 Current Price: ${current_price:,.2f}")
    print(f"   📊 RSI (14): {rsi_14:.1f}")
    print(f"   📊 Volume Status: {volume_status} ({volume_ratio:.2f}x)")
    print(f"   📊 Volume Trend: {volume_ratio_avg:.2f}x")
    print(f"   📊 Volume-Price Ratio: {vol_price_ratio:.3f}")
    print(f"   🎯 DCA Signal: {signal.upper()}")
    print(f"   🎯 Confidence: {confidence:.1f}%")
    print(f"   🎯 Amount Multiplier: {amount_multiplier:.2f}x")
    
    print("\n💡 Reasoning:")
    for reason in reasoning:
        print(f"   • {reason}")
    
    # Test different scenarios
    print("\n🧪 Testing Different Scenarios:")
    
    scenarios = [
        {
            'name': 'High Volume Breakout',
            'volume_ratio': 2.5,
            'volume_status': 'very_high',
            'vol_price_ratio': 1.8,
            'volume_ratio_avg': 1.6
        },
        {
            'name': 'Low Volume Weakness',
            'volume_ratio': 0.3,
            'volume_status': 'low',
            'vol_price_ratio': 0.1,
            'volume_ratio_avg': 0.5
        },
        {
            'name': 'Normal Volume',
            'volume_ratio': 1.0,
            'volume_status': 'normal',
            'vol_price_ratio': 0.8,
            'volume_ratio_avg': 0.9
        }
    ]
    
    for scenario in scenarios:
        print(f"\n   📋 {scenario['name']}:")
        print(f"      Volume: {scenario['volume_ratio']:.2f}x ({scenario['volume_status']})")
        print(f"      Trend: {scenario['volume_ratio_avg']:.2f}x")
        print(f"      Vol-Price: {scenario['vol_price_ratio']:.3f}")
        
        # Simulate analysis
        if scenario['volume_status'] == 'very_high':
            print(f"      → Strong signal potential")
        elif scenario['volume_status'] == 'low':
            print(f"      → Weak signal potential")
        else:
            print(f"      → Neutral signal potential")
    
    print("\n✅ Enhanced Volume Analysis Test Complete!")
    print("\n📚 Key Benefits:")
    print("   • EMA-based volume ratio for faster reaction")
    print("   • Volume trend detection for momentum analysis")
    print("   • Volume-price correlation for signal validation")
    print("   • Categorical status for simplified decision making")
    print("   • Enhanced DCA signals with volume-based reasoning")

if __name__ == "__main__":
    test_enhanced_volume_analysis() 