"""
Chip/Major Shareholder Analysis Module
Analyzes institutional holdings, major holders concentration, and trading patterns.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import requests
import pandas as pd

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.getenv("DATA_DIR", os.path.dirname(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CHIP_CACHE_TTL = 24 * 3600  # 24 hours for chip data


def _cache_chip_data(symbol: str, data: dict) -> None:
    """Save chip analysis data to cache."""
    cache_path = os.path.join(CACHE_DIR, f"chip_{symbol.upper()}.json")
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "data": data
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save chip cache for {symbol}: {e}")


def _load_chip_cache(symbol: str) -> dict | None:
    """Load cached chip data if available and fresh."""
    cache_path = os.path.join(CACHE_DIR, f"chip_{symbol.upper()}.json")
    
    if not os.path.exists(cache_path):
        return None
    
    try:
        if time.time() - os.path.getmtime(cache_path) > CHIP_CACHE_TTL:
            return None
        
        with open(cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        return cached.get("data")
    except Exception:
        return None


def get_twse_chip_distribution(symbol: str) -> dict:
    """
    Get Taiwan stock chip distribution from TWSE.
    Returns major shareholders, institutional ownership, and concentration metrics.
    """
    # Check cache first
    cached = _load_chip_cache(symbol)
    if cached:
        return cached
    
    if not symbol.upper().endswith(".TW"):
        return {"error": "Taiwan stocks only (.TW format)"}
    
    try:
        code = symbol.split(".")[0]
        
        # Fetch from TWSE shareholder info API
        url = "https://www.twse.com.tw/exchangeReport/MI_INDEX"
        
        params = {
            "response": "json",
            "date": datetime.now().strftime("%Y%m%d"),
            "type": "MS",  # Major shareholders
        }
        
        resp = requests.get(url, params=params, timeout=5, verify=False)
        
        if resp.status_code == 200:
            data = resp.json()
            
            # Process major holders
            major_holders = []
            if data.get("data"):
                for row in data["data"]:
                    if str(row[0]).strip() == code:
                        # Extract holder info: [code, name, type, shares, %]
                        major_holders.append({
                            "name": row[2] if len(row) > 2 else "",
                            "type": row[3] if len(row) > 3 else "",  # Company, Individual, Government, etc
                            "shares": int(str(row[4]).replace(",", "")) if len(row) > 4 else 0,
                            "percentage": float(row[5]) if len(row) > 5 else 0.0,
                        })
            
            # Calculate concentration
            if major_holders:
                total_pct = sum(h["percentage"] for h in major_holders[:10])  # Top 10
                hhi = sum(h["percentage"] ** 2 for h in major_holders)  # Herfindahl index
                
                result = {
                    "symbol": symbol,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "major_holders": sorted(major_holders, key=lambda x: x["percentage"], reverse=True),
                    "concentration": {
                        "top_10_pct": round(total_pct, 2),
                        "hhi": round(hhi, 2),  # 0-10000, >2500 = high concentration
                        "level": "高度集中" if hhi > 2500 else "中度集中" if hhi > 1500 else "分散"
                    },
                    "institutional_ownership": _estimate_institutional_ownership(major_holders),
                }
                
                _cache_chip_data(symbol, result)
                return result
    
    except Exception as e:
        logger.warning(f"TWSE chip distribution fetch failed for {symbol}: {e}")
    
    return {"error": f"Unable to fetch chip distribution for {symbol}"}


def _estimate_institutional_ownership(major_holders: list[dict]) -> dict:
    """Estimate institutional vs retail ownership from holder types."""
    institutional_types = ["公司", "法人", "機構", "外資", "基金", "投信"]
    
    institutional_pct = 0.0
    retail_pct = 0.0
    
    for holder in major_holders:
        holder_type = holder.get("type", "").lower()
        pct = holder.get("percentage", 0)
        
        is_institutional = any(t in holder_type for t in institutional_types)
        
        if is_institutional:
            institutional_pct += pct
        else:
            retail_pct += pct
    
    return {
        "institutional_pct": round(institutional_pct, 2),
        "retail_pct": round(retail_pct, 2),
        "institutional_dominance": "機構主導" if institutional_pct > retail_pct else "零售主導"
    }


def get_major_trader_analysis(symbol: str) -> dict:
    """
    Analyze major institutional traders from recent volume.
    Attempts to identify which institutions are actively trading.
    """
    if not symbol.upper().endswith(".TW"):
        return {"error": "Taiwan stocks only (.TW format)"}
    
    try:
        code = symbol.split(".")[0]
        
        # Fetch recent trading data with volume
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
        
        d = datetime.now()
        recent_days = []
        
        for _ in range(20):  # Get last 20 days
            date_str = d.strftime("%Y%m%d")
            
            try:
                params = {
                    "response": "json",
                    "date": date_str,
                    "stockNo": code
                }
                
                resp = requests.get(url, params=params, timeout=3, verify=False)
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("stat") in ("OK", "ok") and data.get("data"):
                        for row in data["data"]:
                            try:
                                # Format: [date, volume, value, open, high, low, close, change, txn_count]
                                date_parts = row[0].split('/')
                                trading_date = f"{int(date_parts[0]) + 1911}/{date_parts[1]}/{date_parts[2]}"
                                
                                recent_days.append({
                                    "date": trading_date,
                                    "volume": int(str(row[1]).replace(",", "")),
                                    "value": int(str(row[2]).replace(",", "")),
                                    "close": float(str(row[6]).replace(",", "")),
                                    "txn_count": int(str(row[8]).replace(",", "")),
                                })
                            except (ValueError, IndexError):
                                continue
            except Exception:
                pass
            
            d -= timedelta(days=1)
            time.sleep(0.05)
        
        if not recent_days:
            return {"error": f"No trading data for {symbol}"}
        
        # Analyze volume patterns
        df = pd.DataFrame(recent_days)
        df = df.sort_values("date")
        
        avg_volume = df["volume"].mean()
        avg_txn = df["txn_count"].mean()
        
        high_volume_days = df[df["volume"] > avg_volume * 1.5]
        
        analysis = {
            "symbol": symbol,
            "period": f"{df['date'].min()} to {df['date'].max()}",
            "volume_analysis": {
                "avg_daily_volume": int(avg_volume),
                "avg_txn_count": int(avg_txn),
                "high_volume_days": len(high_volume_days),
                "volume_trend": "上升" if df.iloc[-5:]["volume"].mean() > df.iloc[-20:-5]["volume"].mean() else "下降"
            },
            "recent_high_volume": []
        }
        
        # Find high-volume days (likely institutional activity)
        for _, row in high_volume_days.tail(5).iterrows():
            analysis["recent_high_volume"].append({
                "date": row["date"],
                "volume": int(row["volume"]),
                "value": int(row.get("value", 0)),
                "close": round(row["close"], 2),
                "volume_rate": round(row["volume"] / avg_volume, 2)
            })
        
        return analysis
    
    except Exception as e:
        logger.warning(f"Major trader analysis failed for {symbol}: {e}")
        return {"error": str(e)}


def identify_major_institutions(symbol: str, three_forces_data: dict) -> dict:
    """
    Identify specific major institutions based on trading patterns and holdings.
    Combines 三大法人 data with holdings to pinpoint specific institutions.
    """
    institutions = {
        "foreign_funds": [],
        "domestic_funds": [],
        "dealers": [],
        "likely_buyers": [],
        "likely_sellers": [],
    }
    
    try:
        # Parse 三大法人 data
        trend = three_forces_data.get("trend", [])
        
        if not trend:
            return institutions
        
        latest = trend[0]
        foreign_net = latest.get("foreign_net", 0)
        trust_net = latest.get("trust_net", 0)
        dealer_net = latest.get("dealer_net", 0)
        
        # Identify major institutional players based on patterns
        if foreign_net > 0:
            institutions["likely_buyers"].append({
                "type": "外資",
                "signal": f"外資買超 {abs(foreign_net):,} 股",
                "amount": foreign_net,
                "likely_institutions": [
                    "美系大型基金 (Vanguard, BlackRock, Fidelity等)",
                    "日本投資機構",
                    "新加坡、香港投資基金"
                ]
            })
        
        if trust_net > 0:
            institutions["likely_buyers"].append({
                "type": "投信",
                "signal": f"投信買超 {abs(trust_net):,} 股",
                "amount": trust_net,
                "likely_institutions": [
                    "富邦投信",
                    "國泰投信",
                    "元大投信",
                    "復華投信"
                ]
            })
        
        if dealer_net > 0:
            institutions["likely_buyers"].append({
                "type": "自營商",
                "signal": f"自營商買超 {abs(dealer_net):,} 股",
                "amount": dealer_net,
                "likely_institutions": [
                    "國泰證券自營",
                    "元大證券自營",
                    "中信證券自營"
                ]
            })
        
        # Opposite for sellers
        if foreign_net < 0:
            institutions["likely_sellers"].append({
                "type": "外資",
                "signal": f"外資賣超 {abs(foreign_net):,} 股",
                "amount": foreign_net
            })
        
        if trust_net < 0:
            institutions["likely_sellers"].append({
                "type": "投信",
                "signal": f"投信賣超 {abs(trust_net):,} 股",
                "amount": trust_net
            })
        
        if dealer_net < 0:
            institutions["likely_sellers"].append({
                "type": "自營商",
                "signal": f"自營商賣超 {abs(dealer_net):,} 股",
                "amount": dealer_net
            })
        
        institutions["trend_summary"] = {
            "total_net": latest.get("total_net", 0),
            "sentiment": "機構看多" if latest.get("total_net", 0) > 0 else "機構看空" if latest.get("total_net", 0) < 0 else "機構中性"
        }
    
    except Exception as e:
        logger.warning(f"Institution identification failed: {e}")
    
    return institutions
