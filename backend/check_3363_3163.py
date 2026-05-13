#!/usr/bin/env python3
"""Check if 3363 and 3163 exist in TWSE"""

import requests
import json
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

codes = ['3363', '3163']

for code in codes:
    print(f"\nChecking {code}:")
    current_date = datetime.now()
    
    for i in range(30):  # Try last 30 days
        date_str = current_date.strftime("%Y%m%d")
        
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
        params = {
            "response": "json",
            "date": date_str,
            "stockNo": code
        }
        
        try:
            resp = requests.get(url, params=params, timeout=5, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                stat = data.get('stat', 'unknown')
                has_data = 'data' in data and data['data']
                
                if has_data:
                    print(f"  ✓ Found data for {code} on {date_str}")
                    latest = data['data'][-1]
                    print(f"    Latest: {latest[0]}, Close: {latest[6]}")
                    break
                elif stat == "OK":
                    print(f"  Date {date_str}: OK but no data")
                else:
                    print(f"  Date {date_str}: Stat = {stat}")
        except Exception as e:
            print(f"  Error on {date_str}: {e}")
        
        current_date -= timedelta(days=1)
    else:
        print(f"  ✗ No data found for {code} in last 30 days")
