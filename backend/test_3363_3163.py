#!/usr/bin/env python3
"""Test specific Taiwan stocks"""

import sys
sys.path.insert(0, '.')
from stock_data import get_ohlcv, get_quote

test_stocks = ['3363.TW', '3163.TW']

print("=" * 60)
print("Testing 3363 and 3163")
print("=" * 60)

for symbol in test_stocks:
    print(f"\n{'='*60}")
    print(f"Testing {symbol}")
    print(f"{'='*60}")
    
    # Test OHLCV
    print(f"\n1. Testing OHLCV data...")
    try:
        df = get_ohlcv(symbol, force_refresh=True)
        if not df.empty:
            print(f"✓ {symbol}: {len(df)} records")
            print(f"  Date range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
            print(f"  Latest Close: {df['Close'].iloc[-1]:.2f}")
        else:
            print(f"✗ {symbol}: No OHLCV data")
    except Exception as e:
        print(f"✗ {symbol}: Error - {e}")
    
    # Test Quote
    print(f"\n2. Testing Quote...")
    try:
        quote = get_quote(symbol)
        if quote:
            print(f"✓ {symbol}: {quote}")
        else:
            print(f"✗ {symbol}: No quote")
    except Exception as e:
        print(f"✗ {symbol}: Error - {e}")

print("\n\nNote: These stocks might be delisted or no longer trading")
