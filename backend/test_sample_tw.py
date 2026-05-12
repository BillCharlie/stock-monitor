#!/usr/bin/env python3
"""Quick test of Taiwan stocks data fetching - Sample version"""

import sys
import time
sys.path.insert(0, '.')

from stock_data import get_ohlcv

# Test a representative sample of Taiwan stocks
test_stocks = [
    # 已知问题的股票
    ("3363.TW", "上诠"),
    ("3163.TW", "波若威"),
    ("1519.TW", "華城"),
    ("5347.TW", "世界先進"),
    ("5247.TW", "(待查)"),  # 用户提到的
    
    # 其他样本
    ("2330.TW", "台積電"),
    ("2454.TW", "聯發科"),
    ("2337.TW", "旺宏"),
    ("3037.TW", "欣興"),
    ("4958.TW", "臻鼎"),
    ("2302.TW", "鴻海"),
    ("1605.TW", "華新"),
    ("2015.TW", "豐興"),
]

print("Testing representative Taiwan stocks with new TWSE API priority...")
print("=" * 85)

success_count = 0
fail_count = 0

for symbol, name in test_stocks:
    try:
        print(f"Fetching {symbol:10} {name:15}...", end=" ", flush=True)
        df = get_ohlcv(symbol, force_refresh=True)
        
        if not df.empty:
            rows = len(df)
            last_date = df.index[-1].strftime('%Y-%m-%d')
            last_close = df['Close'].iloc[-1]
            print(f"✓ [{rows:4d} rows] {last_date} {last_close:8.2f}")
            success_count += 1
        else:
            print(f"✗ NO DATA")
            fail_count += 1
    except Exception as e:
        print(f"✗ ERROR: {str(e)[:40]}")
        fail_count += 1
    
    time.sleep(0.2)

print("=" * 85)
print(f"Results: {success_count} success, {fail_count} failed out of {len(test_stocks)} tested")
print(f"Success rate: {success_count*100//len(test_stocks)}%")
