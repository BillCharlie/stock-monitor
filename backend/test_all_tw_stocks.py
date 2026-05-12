#!/usr/bin/env python3
"""Test all Taiwan stocks data fetching"""

import sys
import time
from datetime import datetime
sys.path.insert(0, '.')

from stock_data import get_ohlcv
from watchlist import WATCHLIST

def extract_tw_stocks():
    """递归提取所有.TW股票"""
    stocks = []
    
    def traverse(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                traverse(value)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict) and "symbol" in item:
                    symbol = item["symbol"]
                    if symbol.endswith(".TW"):
                        stocks.append({
                            "symbol": symbol,
                            "name": item.get("name", ""),
                            "name_en": item.get("name_en", "")
                        })
                else:
                    traverse(item)
    
    traverse(WATCHLIST)
    return sorted(list({s["symbol"]: s for s in stocks}.values()), key=lambda x: x["symbol"])

def test_all_taiwan_stocks():
    """Test fetching data for all Taiwan stocks"""
    tw_stocks = extract_tw_stocks()
    print(f"Testing {len(tw_stocks)} Taiwan stocks...")
    print("=" * 80)
    
    success_count = 0
    fail_count = 0
    fail_list = []
    
    start_time = time.time()
    
    for i, stock in enumerate(tw_stocks, 1):
        symbol = stock["symbol"]
        try:
            df = get_ohlcv(symbol, force_refresh=True)
            
            if not df.empty:
                rows = len(df)
                last_date = df.index[-1].strftime('%Y-%m-%d')
                last_close = df['Close'].iloc[-1]
                print(f"✓ {i:3d}. {symbol:10} {stock['name']:15} [{rows:4d} rows] Latest: {last_date} {last_close:8.2f}")
                success_count += 1
            else:
                print(f"✗ {i:3d}. {symbol:10} {stock['name']:15} [NO DATA]")
                fail_count += 1
                fail_list.append(symbol)
        except Exception as e:
            print(f"✗ {i:3d}. {symbol:10} {stock['name']:15} [ERROR: {str(e)[:30]}]")
            fail_count += 1
            fail_list.append(symbol)
        
        # Rate limiting
        if i % 10 == 0:
            print(f"   Progress: {i}/{len(tw_stocks)}... ({success_count} success, {fail_count} failed)")
        time.sleep(0.1)
    
    elapsed = time.time() - start_time
    
    print("=" * 80)
    print(f"\nTest Results:")
    print(f"  Total:   {len(tw_stocks)}")
    print(f"  Success: {success_count} ({success_count*100//len(tw_stocks)}%)")
    print(f"  Failed:  {fail_count} ({fail_count*100//len(tw_stocks)}%)")
    print(f"  Time:    {elapsed:.1f}s")
    
    if fail_list:
        print(f"\nFailed stocks ({len(fail_list)}):")
        for symbol in fail_list:
            print(f"  - {symbol}")
    
    return success_count == len(tw_stocks)

if __name__ == "__main__":
    success = test_all_taiwan_stocks()
    sys.exit(0 if success else 1)
