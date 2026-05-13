import os
import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
import base64
import urllib3

import numpy as np
import pandas as pd
import requests
import yfinance as yf

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.getenv("DATA_DIR", os.path.dirname(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Cache TTL per interval type (seconds)
CACHE_TTL = {
    "1d": 300,    # 5 min during market hours
    "1wk": 3600,  # 1 hour
    "1mo": 7200,  # 2 hours
}

# Period to fetch per interval — enough for MA240 + long-term analysis
INTERVAL_PERIOD = {
    "1d": "5y",   # 5 years daily → ~1250 bars (MA240 needs 240+)
    "1wk": "max", # full weekly history
    "1mo": "max", # full monthly history
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



def _get_tw_stock_from_twse_api(symbol: str, months: int = 60) -> pd.DataFrame:
    """
    Fetch Taiwan stock OHLCV from TWSE, iterating month-by-month (NOT day-by-day).
    TWSE STOCK_DAY returns ALL trading days for the queried month in one response,
    so we only need one request per month — much faster and complete.

    Supports both TWSE (.TW) and TPEX/OTC (.TWO) markets.
    Date format in response: 民國紀年 YYY/MM/DD → add 1911 for Gregorian.
    """
    raw_code = symbol.split(".")[0]
    suffix   = symbol.upper().rsplit(".", 1)[-1]   # "TW" or "TWO"

    if suffix == "TWO":
        # OTC stocks use TPEX API
        base_url = "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php"
    else:
        base_url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"

    records: list = []
    cur = datetime.now()

    for _ in range(months):
        # Always use the 1st of the month — TWSE/TPEX return the whole month
        year_month_day = cur.replace(day=1).strftime("%Y%m%d")

        try:
            if suffix == "TWO":
                # TPEX uses different params and date format
                roc_year  = cur.year - 1911
                date_param = f"{roc_year}/{cur.month:02d}"
                params = {"d": date_param, "stkno": raw_code, "o": "json"}
                resp = requests.get(base_url, params=params,
                                    headers={"User-Agent": "Mozilla/5.0"},
                                    timeout=10, verify=False)
            else:
                params = {"response": "json", "date": year_month_day, "stockNo": raw_code}
                resp = requests.get(base_url, params=params,
                                    headers={"User-Agent": "Mozilla/5.0"},
                                    timeout=10, verify=False)

            if resp.status_code != 200:
                cur = (cur.replace(day=1) - timedelta(days=1))
                time.sleep(0.3)
                continue

            data = resp.json()

            # ── TWSE parse ──────────────────────────────────────────────────
            if suffix != "TWO":
                if data.get("stat") not in ("OK", "ok") or not data.get("data"):
                    cur = (cur.replace(day=1) - timedelta(days=1))
                    time.sleep(0.3)
                    continue
                for row in data["data"]:
                    try:
                        dp = row[0].split("/")
                        date_obj = datetime(int(dp[0]) + 1911, int(dp[1]), int(dp[2]))
                        records.append({
                            "Date":   date_obj,
                            "Open":   float(str(row[3]).replace(",", "")),
                            "High":   float(str(row[4]).replace(",", "")),
                            "Low":    float(str(row[5]).replace(",", "")),
                            "Close":  float(str(row[6]).replace(",", "")),
                            "Volume": int(str(row[1]).replace(",", "")),
                        })
                    except (ValueError, IndexError):
                        continue

            # ── TPEX parse ───────────────────────────────────────────────────
            else:
                rows = data.get("aaData") or data.get("data") or []
                for row in rows:
                    try:
                        dp = str(row[0]).split("/")
                        date_obj = datetime(int(dp[0]) + 1911, int(dp[1]), int(dp[2]))
                        records.append({
                            "Date":   date_obj,
                            "Open":   float(str(row[4]).replace(",", "")),
                            "High":   float(str(row[5]).replace(",", "")),
                            "Low":    float(str(row[6]).replace(",", "")),
                            "Close":  float(str(row[7]).replace(",", "")),
                            "Volume": int(str(row[1]).replace(",", "")),
                        })
                    except (ValueError, IndexError):
                        continue

        except Exception as e:
            logger.debug("TWSE/TPEX fetch error %s %s: %s", symbol, year_month_day, e)

        # Step back one month
        cur = (cur.replace(day=1) - timedelta(days=1))
        time.sleep(0.35)   # polite rate-limit: ~3 req/sec max

    if not records:
        logger.warning("No TWSE/TPEX data for %s after %d months", symbol, months)
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df.set_index("Date", inplace=True)
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    logger.info("TWSE/TPEX: %d records for %s (%d months fetched)", len(df), symbol, months)
    return df


def _get_tw_quote_from_twse(symbol: str) -> dict | None:
    """
    Fallback: fetch latest close/change from TWSE (TWSE listed) or TPEX (OTC).
    Uses the month endpoint and grabs the last row — 1 request only.
    """
    raw_code = symbol.split(".")[0]
    suffix   = symbol.upper().rsplit(".", 1)[-1]

    cur = datetime.now()
    for _ in range(3):   # try current month, then go back
        try:
            if suffix == "TWO":
                roc_year   = cur.year - 1911
                date_param = f"{roc_year}/{cur.month:02d}"
                url    = "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php"
                params = {"d": date_param, "stkno": raw_code, "o": "json"}
                resp   = requests.get(url, params=params,
                                      headers={"User-Agent": "Mozilla/5.0"},
                                      timeout=8, verify=False)
                data   = resp.json()
                rows   = data.get("aaData") or data.get("data") or []
                if rows:
                    latest    = rows[-1]
                    close     = float(str(latest[7]).replace(",", ""))
                    prev_c    = float(str(rows[-2][7]).replace(",", "")) if len(rows) > 1 else close
                    volume    = int(str(latest[1]).replace(",", ""))
                    change    = close - prev_c
                    return {"price": round(close, 4),
                            "change": round(change, 4),
                            "change_pct": round(change / prev_c * 100, 2) if prev_c else 0,
                            "volume": volume}
            else:
                date_str = cur.replace(day=1).strftime("%Y%m%d")
                url    = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
                params = {"response": "json", "date": date_str, "stockNo": raw_code}
                resp   = requests.get(url, params=params,
                                      headers={"User-Agent": "Mozilla/5.0"},
                                      timeout=8, verify=False)
                data   = resp.json()
                if data.get("stat") in ("OK", "ok") and data.get("data"):
                    rows   = data["data"]
                    latest = rows[-1]
                    close  = float(str(latest[6]).replace(",", ""))
                    prev_c = float(str(rows[-2][6]).replace(",", "")) if len(rows) > 1 else close
                    volume = int(str(latest[1]).replace(",", ""))
                    change = close - prev_c
                    return {"price": round(close, 4),
                            "change": round(change, 4),
                            "change_pct": round(change / prev_c * 100, 2) if prev_c else 0,
                            "volume": volume}
        except Exception as e:
            logger.debug("TWSE/TPEX quote error %s: %s", symbol, e)

        cur = (cur.replace(day=1) - timedelta(days=1))

    return None


def _fetch_yfinance(symbol: str, period: str, interval: str) -> pd.DataFrame:
    """Shared yfinance fetch helper — returns cleaned DataFrame or empty."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval,
                            auto_adjust=True, actions=False)
        if df.empty:
            logger.warning("yfinance returned empty data for %s", symbol)
            return pd.DataFrame()
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index = df.index.tz_localize(None)
        df = df[~df.index.duplicated(keep="last")]
        df = df.sort_index()
        logger.info("yfinance: %d records for %s (period=%s)", len(df), symbol, period)
        return df
    except Exception as e:
        logger.warning("yfinance failed for %s: %s", symbol, e)
        return pd.DataFrame()


def get_ohlcv(symbol: str, interval: str = "1d", force_refresh: bool = False) -> pd.DataFrame:
    """
    Get OHLCV data.  Priority order for ALL symbols:
      1. yfinance  — fast, full history, works for both TW (.TW/.TWO) and US
      2. TWSE/TPEX — fallback for Taiwan stocks when yfinance is rate-limited or empty

    Full history is always requested (see INTERVAL_PERIOD) so MA240 and
    long-term indicators have enough data.
    """
    period     = INTERVAL_PERIOD.get(interval, "5y")
    ttl        = CACHE_TTL.get(interval, 300)
    cache_path = _cache_path(symbol, interval, period)

    if not force_refresh:
        cached = _load_cache(cache_path, ttl)
        if cached is not None and not cached.empty:
            logger.debug("Cache hit for %s", symbol)
            return cached

    # ── Step 1: yfinance (primary for everything) ─────────────────────────────
    df = _fetch_yfinance(symbol, period, interval)
    if not df.empty:
        _save_cache(cache_path, df)
        return df

    # ── Step 2: TWSE / TPEX fallback (Taiwan stocks only) ────────────────────
    upper = symbol.upper()
    if upper.endswith(".TW") or upper.endswith(".TWO"):
        logger.warning("yfinance empty for %s — trying TWSE/TPEX fallback...", symbol)
        # 60 months = 5 years; for weekly/monthly use full history
        months = 60 if interval == "1d" else 120
        df = _get_tw_stock_from_twse_api(symbol, months=months)
        if not df.empty:
            _save_cache(cache_path, df)
            return df
        logger.error("Both yfinance and TWSE/TPEX failed for %s", symbol)

    return pd.DataFrame()


def get_quote(symbol: str) -> dict:
    """
    Get latest price and change info.
    Priority:
      1. yfinance history(5d)  — reliable close price for both TW and US
      2. TWSE/TPEX REST API    — fallback for Taiwan stocks
    """
    # ── Step 1: yfinance history (more reliable than fast_info for TW stocks) ─
    try:
        t  = yf.Ticker(symbol)
        df = t.history(period="5d", interval="1d", auto_adjust=True, actions=False)
        if not df.empty:
            close      = float(df["Close"].iloc[-1])
            prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else close
            change     = close - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0
            volume     = int(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0
            logger.info("yfinance quote OK for %s: %.2f", symbol, close)
            return {
                "price":      round(close, 4),
                "change":     round(change, 4),
                "change_pct": round(change_pct, 2),
                "volume":     volume,
            }
        logger.warning("yfinance history empty for %s", symbol)
    except Exception as e:
        logger.warning("yfinance quote failed for %s: %s", symbol, e)

    # ── Step 2: TWSE/TPEX fallback for Taiwan stocks ──────────────────────────
    upper = symbol.upper()
    if upper.endswith(".TW") or upper.endswith(".TWO"):
        logger.info("TWSE/TPEX fallback quote for %s", symbol)
        tw_quote = _get_tw_quote_from_twse(symbol)
        if tw_quote:
            return tw_quote

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


# ─── Investor / institutional data ────────────────────────────────────────────

INVESTORS_CACHE_TTL = 3600  # 1 hour per day-file


def _parse_tw_number(s) -> int:
    try:
        return int(str(s).replace(",", "").replace("+", "").strip() or "0")
    except (ValueError, AttributeError):
        return 0


def _fetch_twse_three_forces(date_str: str) -> dict:
    """Fetch TWSE 三大法人 buy/sell data for one date. Cached per date."""
    cache_path = os.path.join(CACHE_DIR, f"twse_3f_{date_str}.json")
    if os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < INVESTORS_CACHE_TTL:
            try:
                with open(cache_path, encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    return data
            except Exception:
                pass

    url = (
        "https://www.twse.com.tw/rwd/zh/fund/T86"
        f"?date={date_str}&selectType=ALLBUT0999&response=json"
    )
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        logger.warning("TWSE T86 fetch failed %s: %s", date_str, e)
        return {}

    if raw.get("stat") not in ("OK", "ok"):
        return {}

    fields: list = raw.get("fields", [])
    rows: list = raw.get("data", [])

    def fi(name: str) -> int:
        try:
            return fields.index(name)
        except ValueError:
            return -1

    i_code    = fi("證券代號")
    i_foreign = fi("外陸資買賣超股數")
    i_trust   = fi("投信買賣超股數")
    i_dealer  = fi("自營商買賣超股數")   # first occurrence = 合計
    i_total   = fi("三大法人買賣超股數")

    # Positional fallback if field names differ
    if i_code < 0:   i_code    = 0
    if i_foreign < 0: i_foreign = 4
    if i_trust < 0:  i_trust   = 7
    if i_dealer < 0: i_dealer  = 8
    if i_total < 0:  i_total   = 15

    result: dict = {}
    for row in rows:
        if len(row) <= max(i_code, i_foreign, i_trust, i_dealer, i_total):
            continue
        code = str(row[i_code]).strip()
        result[code] = {
            "foreign_net": _parse_tw_number(row[i_foreign]),
            "trust_net":   _parse_tw_number(row[i_trust]),
            "dealer_net":  _parse_tw_number(row[i_dealer]),
            "total_net":   _parse_tw_number(row[i_total]),
        }

    if result:
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except Exception:
            pass

    return result


def _get_tw_investors(symbol: str) -> dict:
    """Return 三大法人 trend (last 5 trading days) for a TWSE stock."""
    code = symbol.split(".")[0]
    trend: list = []
    d = datetime.now()
    attempts = 0
    while len(trend) < 5 and attempts < 20:
        if d.weekday() < 5:
            date_str = d.strftime("%Y%m%d")
            day_data = _fetch_twse_three_forces(date_str)
            if code in day_data:
                entry = dict(day_data[code])
                entry["date"] = d.strftime("%Y-%m-%d")
                trend.append(entry)
        d -= timedelta(days=1)
        attempts += 1

    if not trend:
        return {"type": "tw", "symbol": symbol, "error": "無三大法人資料（非交易日或資料未更新）"}

    latest = trend[0]
    return {
        "type": "tw",
        "symbol": symbol,
        "latest_date": latest["date"],
        "foreign_net":  latest["foreign_net"],
        "trust_net":    latest["trust_net"],
        "dealer_net":   latest["dealer_net"],
        "total_net":    latest["total_net"],
        "trend": list(reversed(trend)),  # oldest → newest
    }


def _get_us_investors(symbol: str) -> dict:
    """Return institutional/retail breakdown for a US stock via yfinance."""
    inv_cache = os.path.join(CACHE_DIR, f"investors_{symbol.upper()}.json")
    if os.path.exists(inv_cache):
        age = time.time() - os.path.getmtime(inv_cache)
        if age < INVESTORS_CACHE_TTL * 4:  # 4 h cache for US data
            try:
                with open(inv_cache, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    try:
        t = yf.Ticker(symbol)
        info: dict = {}
        try:
            info = t.info or {}
        except Exception:
            pass

        result: dict = {
            "type": "us",
            "symbol": symbol,
            "held_pct_insiders":     info.get("heldPercentInsiders"),
            "held_pct_institutions": info.get("heldPercentInstitutions"),
            "float_shares":          info.get("floatShares"),
            "shares_outstanding":    info.get("sharesOutstanding"),
        }

        # Top institutional holders
        try:
            ih = t.institutional_holders
            if ih is not None and not ih.empty:
                top = []
                for _, row in ih.head(10).iterrows():
                    shares = row.get("Shares")
                    pct    = row.get("% Out")
                    value  = row.get("Value")
                    top.append({
                        "holder": str(row.get("Holder", "")),
                        "shares": int(shares) if pd.notna(shares) else None,
                        "pct_out": round(float(pct) * 100, 2) if pd.notna(pct) else None,
                        "value":  int(value) if pd.notna(value) else None,
                    })
                result["top_institutions"] = top
        except Exception:
            pass

        # Major holders summary
        try:
            mh = t.major_holders
            if mh is not None and not mh.empty:
                rows_list = []
                for _, row in mh.iterrows():
                    rows_list.append([str(x) for x in row.tolist()])
                result["major_holders_rows"] = rows_list
        except Exception:
            pass

        try:
            with open(inv_cache, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False)
        except Exception:
            pass

        return result

    except Exception as e:
        logger.warning("US investors fetch failed %s: %s", symbol, e)
        return {"type": "us", "symbol": symbol, "error": str(e)}


def get_investors_data(symbol: str) -> dict:
    """Get investor composition data. TW → TWSE 三大法人; others → yfinance."""
    upper = symbol.upper()
    if upper.endswith(".TW") or upper.endswith(".TWO"):
        return _get_tw_investors(symbol)
    return _get_us_investors(symbol)
