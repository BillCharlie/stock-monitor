"""
Real-time data fetcher for intraday K-line updates and chip analysis.
Provides multiple data sources: TWSE, Sina Finance, Tencent Finance, etc.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.getenv("DATA_DIR", os.path.dirname(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Realtime cache TTL (shorter for intraday updates)
REALTIME_CACHE_TTL = 30  # 30 seconds during market hours


def _get_sina_realtime(symbol: str) -> dict | None:
    """
    Get real-time price data from Sina Finance.
    Works for both Taiwan stocks (symbol format: 0000) and US stocks (AAPL, MSFT, etc).
    """
    try:
        # Convert symbol format
        sina_symbol = symbol.upper()
        if sina_symbol.endswith(".TW"):
            # Taiwan stock: convert 2330.TW to tw2330
            code = sina_symbol[:-3]
            sina_symbol = f"tw{code}"
        elif sina_symbol.endswith(".US"):
            # US stock
            sina_symbol = symbol.replace(".US", "").upper()
        
        url = f"https://hq.sinajs.cn/?list={sina_symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        resp = requests.get(url, headers=headers, timeout=5, verify=False)
        resp.encoding = "gb2312"
        
        if resp.status_code == 200:
            # Parse response format: var hq_str_tw2330="2330,13.55,..."
            content = resp.text
            if "=" in content:
                data_str = content.split('="')[1].rstrip('";')
                parts = data_str.split(",")
                
                if len(parts) >= 6:
                    return {
                        "source": "sina",
                        "symbol": symbol,
                        "price": float(parts[3]),
                        "bid": float(parts[1]),
                        "ask": float(parts[2]),
                        "open": float(parts[1]),
                        "high": float(parts[4]),
                        "low": float(parts[5]),
                        "volume": int(float(parts[8])) if len(parts) > 8 else 0,
                        "timestamp": datetime.now().isoformat(),
                    }
    except Exception as e:
        logger.debug(f"Sina realtime fetch failed for {symbol}: {e}")
    
    return None


def _get_tencent_realtime(symbol: str) -> dict | None:
    """
    Get real-time price data from Tencent Finance.
    Support both Taiwan and US stocks.
    """
    try:
        # Convert symbol format for Tencent
        tencent_symbol = symbol.upper()
        if tencent_symbol.endswith(".TW"):
            code = tencent_symbol[:-3]
            tencent_symbol = f"twhk{code}"  # Taiwan: twhk2330
        elif tencent_symbol.endswith(".US"):
            tencent_symbol = f"us{symbol[:-3]}"  # US: usAAPL
        
        url = "https://qt.gtimg.cn/q={}".format(tencent_symbol)
        headers = {"User-Agent": "Mozilla/5.0"}
        
        resp = requests.get(url, headers=headers, timeout=5)
        resp.encoding = "utf-8"
        
        if resp.status_code == 200 and resp.text:
            # Parse: v_twhk2330="2330~台積電~13.55~..."
            parts = resp.text.strip('";~').split("~")
            
            if len(parts) >= 4:
                return {
                    "source": "tencent",
                    "symbol": symbol,
                    "price": float(parts[3]),
                    "bid": float(parts[5]) if len(parts) > 5 else float(parts[3]),
                    "ask": float(parts[6]) if len(parts) > 6 else float(parts[3]),
                    "high": float(parts[8]) if len(parts) > 8 else float(parts[3]),
                    "low": float(parts[9]) if len(parts) > 9 else float(parts[3]),
                    "volume": int(float(parts[12])) if len(parts) > 12 else 0,
                    "timestamp": datetime.now().isoformat(),
                }
    except Exception as e:
        logger.debug(f"Tencent realtime fetch failed for {symbol}: {e}")
    
    return None


def _get_twse_realtime(symbol: str) -> dict | None:
    """
    Get real-time quote from Taiwan Stock Exchange (TWSE).
    Only for Taiwan stocks (.TW format).
    """
    if not symbol.upper().endswith(".TW"):
        return None
    
    try:
        code = symbol.split(".")[0]
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_AVG"
        
        params = {
            "response": "json",
            "date": datetime.now().strftime("%Y%m%d"),
            "stockNo": code
        }
        
        resp = requests.get(url, params=params, timeout=5, verify=False)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("stat") == "OK" and data.get("data"):
                latest = data["data"][-1] if data["data"] else None
                if latest:
                    # TWSE format: [code, date, trade_price, trade_volume]
                    return {
                        "source": "twse",
                        "symbol": symbol,
                        "price": float(latest[2]) if len(latest) > 2 else None,
                        "volume": int(latest[3]) if len(latest) > 3 else 0,
                        "timestamp": datetime.now().isoformat(),
                    }
    except Exception as e:
        logger.debug(f"TWSE realtime fetch failed for {symbol}: {e}")
    
    return None


def get_realtime_quote(symbol: str) -> dict:
    """
    Get real-time quote with intelligent fallback across multiple sources.
    Try in order: TWSE → Tencent → Sina
    """
    # Try TWSE for Taiwan stocks first
    if symbol.upper().endswith(".TW"):
        quote = _get_twse_realtime(symbol)
        if quote:
            return quote
    
    # Try Tencent
    quote = _get_tencent_realtime(symbol)
    if quote:
        return quote
    
    # Try Sina as fallback
    quote = _get_sina_realtime(symbol)
    if quote:
        return quote
    
    return {"error": f"Unable to fetch real-time quote for {symbol}"}


def get_intraday_kline(symbol: str, interval: int = 1) -> list[dict] | None:
    """
    Get intraday K-line data (1-min, 5-min, 15-min, 30-min, 60-min bars).
    interval: 1 (1-min), 5 (5-min), 15 (15-min), 30 (30-min), 60 (60-min)
    
    For Taiwan stocks: TWSE tick data
    For others: Sina/Tencent minute bars
    """
    try:
        # Taiwan stocks from TWSE
        if symbol.upper().endswith(".TW"):
            return _get_twse_intraday(symbol, interval)
        
        # Others from Sina
        return _get_sina_intraday(symbol, interval)
    
    except Exception as e:
        logger.warning(f"Intraday kline fetch failed for {symbol}: {e}")
        return None


def _get_twse_intraday(symbol: str, interval: int = 1) -> list[dict] | None:
    """Fetch intraday tick data from TWSE."""
    try:
        code = symbol.split(".")[0]
        url = "https://www.twse.com.tw/exchangeReport/STOCK_INTRADAY_PRICE"
        
        params = {
            "response": "json",
            "date": datetime.now().strftime("%Y%m%d"),
            "stockNo": code,
        }
        
        resp = requests.get(url, params=params, timeout=5, verify=False)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("stat") == "OK" and data.get("data"):
                klines = []
                for row in data["data"]:
                    # TWSE format: [time, open, high, low, close, volume, value]
                    try:
                        time_str = row[0]  # Format: HH:MM:SS
                        close_price = float(str(row[4]).replace(",", ""))
                        volume = int(str(row[5]).replace(",", ""))
                        
                        klines.append({
                            "time": f"{datetime.now().strftime('%Y-%m-%d')} {time_str}",
                            "open": float(str(row[1]).replace(",", "")),
                            "high": float(str(row[2]).replace(",", "")),
                            "low": float(str(row[3]).replace(",", "")),
                            "close": close_price,
                            "volume": volume,
                        })
                    except (ValueError, IndexError):
                        continue
                
                return klines if klines else None
    except Exception as e:
        logger.warning(f"TWSE intraday fetch failed for {symbol}: {e}")
    
    return None


def _get_sina_intraday(symbol: str, interval: int = 1) -> list[dict] | None:
    """Fetch intraday minute bars from Sina Finance."""
    try:
        # Symbol conversion for Sina
        sina_symbol = symbol.upper()
        if sina_symbol.endswith(".TW"):
            code = sina_symbol[:-3]
            sina_symbol = f"tw{code}"
        
        url = f"https://vip.stock.finance.sina.com.cn/q_min.php"
        
        params = {
            "symbol": sina_symbol,
            "fchrt": "pc",
            "begin": 0,
        }
        
        resp = requests.get(url, params=params, timeout=5)
        resp.encoding = "gb2312"
        
        if resp.status_code == 200:
            lines = resp.text.strip().split("\n")
            klines = []
            
            for line in lines:
                if "=" not in line:
                    continue
                
                data_str = line.split("=")[1].strip('";')
                rows = data_str.split(";")
                
                for row in rows:
                    parts = row.split(",")
                    if len(parts) >= 5:
                        try:
                            klines.append({
                                "time": parts[0],  # Time in HH:MM format
                                "open": float(parts[1]),
                                "close": float(parts[2]),
                                "high": max(float(parts[1]), float(parts[2])),
                                "low": min(float(parts[1]), float(parts[2])),
                                "volume": int(float(parts[3])),
                            })
                        except (ValueError, IndexError):
                            continue
            
            return klines if klines else None
    except Exception as e:
        logger.warning(f"Sina intraday fetch failed for {symbol}: {e}")
    
    return None


def validate_symbol(symbol: str) -> dict:
    """
    Validate if a symbol is valid and has data available.
    Returns {"valid": bool, "error": str, "suggestion": str}
    """
    symbol = symbol.strip().upper()
    
    if not symbol:
        return {"valid": False, "error": "Symbol is empty"}
    
    # Try to fetch quote
    quote = get_realtime_quote(symbol)
    
    if "error" in quote:
        # Symbol format validation
        if not (symbol.endswith(".TW") or symbol.endswith(".TWO") or 
                symbol.endswith(".US") or symbol.isupper()):
            return {
                "valid": False,
                "error": f"Invalid symbol format: {symbol}",
                "suggestion": "Taiwan stocks: XXXX.TW (e.g., 2330.TW), US stocks: AAPL (uppercase)"
            }
        
        return {
            "valid": False,
            "error": f"No data found for {symbol}",
            "suggestion": "Check if the stock symbol is correct and the stock is currently listed"
        }
    
    return {
        "valid": True,
        "price": quote.get("price"),
        "timestamp": quote.get("timestamp"),
    }
