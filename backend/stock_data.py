import os
import json
import time
import hashlib
import logging

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Cache TTL per interval type (seconds)
CACHE_TTL = {
    "1d": 300,    # 5 min during market hours
    "1wk": 3600,  # 1 hour
    "1mo": 7200,  # 2 hours
}

# Period to fetch per interval
INTERVAL_PERIOD = {
    "1d": "2y",
    "1wk": "5y",
    "1mo": "max",
}


def _cache_path(symbol: str, interval: str, period: str) -> str:
    key = hashlib.md5(f"{symbol}_{interval}_{period}".encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{key}.json")


def _load_cache(path: str, ttl: int) -> pd.DataFrame | None:
    if not os.path.exists(path):
        return None
    if time.time() - os.path.getmtime(path) > ttl:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        df = pd.DataFrame(raw)
        df.index = pd.to_datetime(df["Date"])
        df = df.drop(columns=["Date"])
        return df
    except Exception:
        return None


def _save_cache(path: str, df: pd.DataFrame) -> None:
    try:
        out = df.copy().reset_index()
        out["Date"] = out["Date"].astype(str)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out.to_dict(orient="records"), f)
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")


def get_ohlcv(symbol: str, interval: str = "1d", force_refresh: bool = False) -> pd.DataFrame:
    period = INTERVAL_PERIOD.get(interval, "2y")
    ttl = CACHE_TTL.get(interval, 300)
    cache_path = _cache_path(symbol, interval, period)

    if not force_refresh:
        cached = _load_cache(cache_path, ttl)
        if cached is not None and not cached.empty:
            return cached

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True, actions=False)
        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return pd.DataFrame()
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index = df.index.tz_localize(None)
        df = df[~df.index.duplicated(keep="last")]
        df = df.sort_index()
        _save_cache(cache_path, df)
        return df
    except Exception as e:
        logger.error(f"yfinance error for {symbol}: {e}")
        return pd.DataFrame()


def get_quote(symbol: str) -> dict:
    """Get latest price and change info"""
    try:
        t = yf.Ticker(symbol)
        info = t.fast_info
        price = getattr(info, "last_price", None)
        prev_close = getattr(info, "previous_close", None)
        change = (price - prev_close) if price and prev_close else None
        change_pct = (change / prev_close * 100) if change and prev_close else None
        return {
            "price": round(float(price), 4) if price else None,
            "change": round(float(change), 4) if change else None,
            "change_pct": round(float(change_pct), 2) if change_pct else None,
            "volume": int(getattr(info, "regular_market_volume", 0) or 0),
        }
    except Exception as e:
        logger.warning(f"Quote fetch failed for {symbol}: {e}")
        return {}


def df_to_ohlcv_list(df: pd.DataFrame) -> list:
    records = []
    for idx, row in df.iterrows():
        records.append({
            "time": idx.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(row["Volume"]),
        })
    return records
