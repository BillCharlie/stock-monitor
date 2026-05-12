#!/usr/bin/env python3
"""Debug TWSE API calls"""

import requests
import json
from datetime import datetime, timedelta

# Test with a known working Taiwan stock code
test_codes = ['2330', '3363', '3163', '1519', '0050']

for code in test_codes:
    print(f"\nTesting stock code: {code}")
    
    # Try today's date
    current_date = datetime.now()
    for i in range(5):  # Try last 5 days
        date_str = current_date.strftime("%Y%m%d")
        
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
        params = {
            "response": "json",
            "date": date_str,
            "stockNo": code
        }
        
        try:
            resp = requests.get(url, params=params, timeout=5, verify=False)
            print(f"  Date: {date_str}, Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data and data["data"]:
                    print(f"    ✓ Got {len(data['data'])} records")
                    if data['data']:
                        latest = data['data'][-1]
                        print(f"    Latest: {latest[0]}, Close: {latest[4]}")
                    break
                elif "stat" in data:
                    print(f"    Status: {data.get('stat', 'unknown')}")
            else:
                print(f"    Error: {resp.status_code}")
        
        except Exception as e:
            print(f"  Exception: {e}")
        
        current_date -= timedelta(days=1)
