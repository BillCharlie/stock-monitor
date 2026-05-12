#!/usr/bin/env python3
"""Test TWSE API fallback for Taiwan stocks"""

import sys
sys.path.insert(0, '.')
from stock_data import get_ohlcv

print("Testing 3363.TW with TWSE fallback (fast mode - 30 days)...")
df = get_ohlcv('3363.TW', force_refresh=True)
print(f"✓ 3363.TW: {len(df)} rows")
if not df.empty:
    print(f"  Latest: {df.index[-1].strftime('%Y-%m-%d')} Close: {df['Close'].iloc[-1]:.2f}")
    print()

print("Testing 3163.TW with TWSE fallback (fast mode - 30 days)...")
df2 = get_ohlcv('3163.TW', force_refresh=True)
print(f"✓ 3163.TW: {len(df2)} rows")
if not df2.empty:
    print(f"  Latest: {df2.index[-1].strftime('%Y-%m-%d')} Close: {df2['Close'].iloc[-1]:.2f}")
    print()

print("Testing 1519.TW with TWSE fallback (fast mode - 30 days)...")
df3 = get_ohlcv('1519.TW', force_refresh=True)
print(f"✓ 1519.TW: {len(df3)} rows")
if not df3.empty:
    print(f"  Latest: {df3.index[-1].strftime('%Y-%m-%d')} Close: {df3['Close'].iloc[-1]:.2f}")
    print()

print("All tests completed!")

