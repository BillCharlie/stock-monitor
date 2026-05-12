#!/usr/bin/env python3
"""Debug TWSE API responses"""

import requests
import json
from datetime import datetime, timedelta
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Test with common Taiwan stock codes
test_codes = ['2330', '2412', '2884', '2379']  # Try different codes

for code in test_codes:
    print(f"\n=== Testing stock code: {code} ===")
    
    current_date = datetime.now()
    found = False
    
    for i in range(20):  # Try last 20 days to find a trading day
        date_str = current_date.strftime("%Y%m%d")
        
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
        params = {
            "response": "json",
            "date": date_str,
            "stockNo": code
        }
        
        try:
            resp = requests.get(url, params=params, timeout=5, verify=False)
            print(f"Date: {date_str}, Status: {resp.status_code}", end="")
            
            if resp.status_code == 200:
                data = resp.json()
                stat = data.get('stat', 'unknown')
                has_data = 'data' in data and data['data']
                
                print(f", Stat: {stat}, Has data: {has_data}")
                
                if has_data:
                    print(f"  ✓ Got {len(data['data'])} records for date {date_str}")
                    latest = data['data'][-1]
                    print(f"    Latest record: {latest[0]}, Close: {latest[4]}, Volume: {latest[5]}")
                    found = True
                    break
            else:
                print(f", Error")
        
        except Exception as e:
            print(f"Date: {date_str}, Exception: {e}")
        
        current_date -= timedelta(days=1)
    
    if not found:
        print(f"  ✗ No data found for {code}")

print("\n\n=== Testing current 2330 for debugging ===")
code = '2330'
date_str = datetime.now().strftime("%Y%m%d")
url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
params = {
    "response": "json",
    "date": date_str,
    "stockNo": code
}

try:
    resp = requests.get(url, params=params, timeout=5, verify=False)
    print(f"Full URL: {url}?{params}")
    print(f"Status: {resp.status_code}")
    print(f"Response text (first 500 chars): {resp.text[:500]}")
    data = resp.json()
    print(f"Response JSON keys: {data.keys()}")
    print(f"Stat: {data.get('stat')}")
    if data.get('data'):
        print(f"Data count: {len(data['data'])}")
except Exception as e:
    print(f"Error: {e}")
