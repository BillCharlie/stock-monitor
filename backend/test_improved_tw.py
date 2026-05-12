#!/usr/bin/env python3
"""Test improved Taiwan stock data fetching"""

import sys
sys.path.insert(0, '.')
from stock_data import get_ohlcv, get_quote

# Test with real Taiwan stocks
test_stocks = ['2330.TW', '2412.TW', '2884.TW', '2379.TW']

print("=" * 60)
print("Testing Taiwan Stock Data Fetching (OHLCV)")
print("=" * 60)

for symbol in test_stocks:
    print(f"\nFetching {symbol}...")
    try:
        df = get_ohlcv(symbol, force_refresh=True)
        if not df.empty:
            print(f"✓ {symbol}: {len(df)} records")
            print(f"  Date range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
            print(f"  Latest Close: {df['Close'].iloc[-1]:.2f}")
            print(f"  Volume: {df['Volume'].iloc[-1]:,}")
        else:
            print(f"✗ {symbol}: No data")
    except Exception as e:
        print(f"✗ {symbol}: Error - {e}")

print("\n" + "=" * 60)
print("Testing Taiwan Stock Quotes")
print("=" * 60)

for symbol in test_stocks:
    print(f"\nFetching quote for {symbol}...")
    try:
        quote = get_quote(symbol)
        if quote:
            print(f"✓ {symbol}:")
            print(f"  Price: {quote.get('price', 'N/A')}")
            print(f"  Change: {quote.get('change', 'N/A')} ({quote.get('change_pct', 'N/A')}%)")
            print(f"  Volume: {quote.get('volume', 'N/A'):,}")
        else:
            print(f"✗ {symbol}: No quote data")
    except Exception as e:
        print(f"✗ {symbol}: Error - {e}")

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)
