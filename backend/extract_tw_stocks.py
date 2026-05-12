#!/usr/bin/env python3
"""Extract all Taiwan stocks from watchlist.py"""

import re
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

if __name__ == "__main__":
    tw_stocks = extract_tw_stocks()
    print(f"Total Taiwan stocks: {len(tw_stocks)}\n")
    for stock in tw_stocks:
        print(f"{stock['symbol']:12} {stock['name']:15} {stock['name_en']}")
    
    # Save to file for testing
    with open("tw_stocks.txt", "w", encoding="utf-8") as f:
        for stock in tw_stocks:
            f.write(f"{stock['symbol']}\n")
    print(f"\nSaved {len(tw_stocks)} symbols to tw_stocks.txt")
