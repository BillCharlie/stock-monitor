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


def _time_text(dt: datetime | None = None) -> str:
    return (dt or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")


def _mtime_text(path: str) -> str:
    try:
        return _time_text(datetime.fromtimestamp(os.path.getmtime(path)))
    except Exception:
        return ""


def _latest_mtime_text(paths: list[str]) -> str:
    mtimes = []
    for path in paths:
        try:
            if os.path.exists(path):
                mtimes.append(os.path.getmtime(path))
        except Exception:
            continue
    if not mtimes:
        return ""
    return _time_text(datetime.fromtimestamp(max(mtimes)))


def is_tw_symbol(symbol: str) -> bool:
    upper = symbol.upper()
    return upper.endswith(".TW") or upper.endswith(".TWO")


def _parse_twse_roc_date(value: str) -> str:
    parts = str(value).split("/")
    if len(parts) != 3:
        return ""
    try:
        return f"{int(parts[0]) + 1911:04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    except Exception:
        return ""


def _market_day_cache_path() -> str:
    return os.path.join(CACHE_DIR, "tw_market_days.json")


def _load_market_day_cache() -> dict:
    path = _market_day_cache_path()
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_market_day_cache(cache: dict) -> None:
    try:
        with open(_market_day_cache_path(), "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.debug("Market-day cache save failed: %s", e)


def is_tw_market_closed_today(now: datetime | None = None) -> bool:
    """Return True on Taiwan weekends/known no-trade weekdays."""
    now = now or datetime.now()
    if now.weekday() >= 5:
        return True
    if now.hour < 14:
        return False

    key = now.strftime("%Y-%m-%d")
    cache = _load_market_day_cache()
    cached = cache.get(key)
    if isinstance(cached, dict) and "closed" in cached:
        return bool(cached["closed"])

    try:
        resp = requests.get(
            "https://www.twse.com.tw/exchangeReport/STOCK_DAY",
            params={"response": "json", "date": now.strftime("%Y%m%d"), "stockNo": "2330"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
            verify=False,
        )
        data = resp.json()
        rows = data.get("data") or []
        has_today = any(_parse_twse_roc_date(row[0]) == key for row in rows if row)
        closed = not has_today
        cache[key] = {
            "closed": closed,
            "checked_at": _time_text(now),
            "reason": "official trading row found" if has_today else "no official trading row for today",
        }
        _save_market_day_cache(cache)
        return closed
    except Exception as e:
        logger.debug("TW market-day probe failed: %s", e)
        return False


# ─── Bulk quote cache (TWSE + TPEX) ──────────────────────────────────────────
# One API call fetches ALL stocks; we cache for 5 min and serve individual lookups
_bulk_cache: dict = {"twse": {}, "tpex": {}, "twse_ts": 0.0, "tpex_ts": 0.0}
_BULK_TTL = 300  # 5 minutes


def _load_twse_bulk() -> dict:
    """Fetch all TWSE current-day quotes in one call. Returns {code: {price,change,change_pct,volume}}"""
    now = time.time()
    if now - _bulk_cache["twse_ts"] < _BULK_TTL and _bulk_cache["twse"]:
        return _bulk_cache["twse"]
    try:
        # TWSE Open Data: daily trading summary for ALL stocks
        resp = requests.get(
            "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=15, verify=False,
        )
        rows = resp.json()
        data: dict = {}
        for r in rows:
            code  = str(r.get("Code", "")).strip()
            close = r.get("ClosingPrice", "") or r.get("closing_price", "")
            open_ = r.get("OpeningPrice", "") or r.get("opening_price", "")
            vol   = r.get("TradeVolume", "0") or "0"
            chg   = r.get("Change", "") or ""
            if not code or not close:
                continue
            try:
                close_f  = float(str(close).replace(",", ""))
                change_f = float(str(chg).replace(",", "").replace("+", "")) if chg else 0.0
                prev_f   = close_f - change_f
                chg_pct  = (change_f / prev_f * 100) if prev_f else 0.0
                data[code] = {
                    "price":      round(close_f, 4),
                    "change":     round(change_f, 4),
                    "change_pct": round(chg_pct, 2),
                    "volume":     int(str(vol).replace(",", "")),
                }
            except (ValueError, ZeroDivisionError):
                continue
        if data:
            _bulk_cache["twse"] = data
            _bulk_cache["twse_ts"] = now
            logger.info("TWSE bulk: loaded %d stocks", len(data))
        return data
    except Exception as e:
        logger.warning("TWSE bulk fetch failed: %s", e)
        return _bulk_cache["twse"]   # return stale if available


def _load_tpex_bulk() -> dict:
    """Fetch all TPEX (OTC) current-day quotes in one call. Returns {code: {price,...}}"""
    now = time.time()
    if now - _bulk_cache["tpex_ts"] < _BULK_TTL and _bulk_cache["tpex"]:
        return _bulk_cache["tpex"]
    try:
        resp = requests.get(
            "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=15, verify=False,
        )
        rows = resp.json()
        data: dict = {}
        for r in rows:
            code  = str(r.get("SecuritiesCompanyCode", "") or r.get("Code", "")).strip()
            close = r.get("Close", "") or r.get("ClosingPrice", "")
            chg   = r.get("Change", "") or ""
            vol   = r.get("TradeVolume", "0") or "0"
            if not code or not close or str(close).strip() in ("", "-", "---"):
                continue
            try:
                close_f  = float(str(close).replace(",", ""))
                change_f = float(str(chg).replace(",", "").replace("+", "")) if chg and str(chg).strip() not in ("-", "---") else 0.0
                prev_f   = close_f - change_f
                chg_pct  = (change_f / prev_f * 100) if prev_f else 0.0
                data[code] = {
                    "price":      round(close_f, 4),
                    "change":     round(change_f, 4),
                    "change_pct": round(chg_pct, 2),
                    "volume":     int(str(vol).replace(",", "")),
                }
            except (ValueError, ZeroDivisionError):
                continue
        if data:
            _bulk_cache["tpex"] = data
            _bulk_cache["tpex_ts"] = now
            logger.info("TPEX bulk: loaded %d stocks", len(data))
        return data
    except Exception as e:
        logger.warning("TPEX bulk fetch failed: %s", e)
        return _bulk_cache["tpex"]


def _get_tw_bulk_quote(symbol: str) -> dict | None:
    """Look up a Taiwan stock quote from the bulk TWSE/TPEX cache.
    OTC stocks (.TWO) try TPEX first; TWSE stocks try main-board first."""
    code   = symbol.split(".")[0]
    suffix = symbol.upper().rsplit(".", 1)[-1]

    # Route OTC stocks to TPEX first for efficiency
    if suffix == "TWO":
        loaders = [(_load_tpex_bulk, "TPEX"), (_load_twse_bulk, "TWSE")]
    else:
        loaders = [(_load_twse_bulk, "TWSE"), (_load_tpex_bulk, "TPEX")]

    for loader, label in loaders:
        bulk = loader()
        if code in bulk:
            logger.info("Bulk %s quote for %s: %.2f", label, symbol, bulk[code]["price"])
            return bulk[code]

    return None

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


def get_ohlcv_last_updated(symbol: str, interval: str = "1d") -> str:
    period = INTERVAL_PERIOD.get(interval, "5y")
    return _mtime_text(_cache_path(symbol, interval, period))


def _load_cache(path: str, ttl: int | None) -> pd.DataFrame | None:
    if not os.path.exists(path):
        return None
    if ttl is not None and time.time() - os.path.getmtime(path) > ttl:
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


def _quote_from_cached_ohlcv(symbol: str) -> dict | None:
    period = INTERVAL_PERIOD.get("1d", "5y")
    cache_path = _cache_path(symbol, "1d", period)
    df = _load_cache(cache_path, None)
    if df is None or df.empty:
        return None
    try:
        df = df.dropna(subset=["Close"]).sort_index()
        if df.empty:
            return None
        close = float(df["Close"].iloc[-1])
        prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else close
        change = close - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        volume = int(df["Volume"].iloc[-1]) if "Volume" in df.columns and not pd.isna(df["Volume"].iloc[-1]) else 0
        return {
            "price": round(close, 4),
            "change": round(change, 4),
            "change_pct": round(change_pct, 2),
            "volume": volume,
            "date": df.index[-1].strftime("%Y-%m-%d"),
            "source": "cached_last_close",
            "last_updated": _mtime_text(cache_path) or _time_text(),
        }
    except Exception as e:
        logger.debug("Cached OHLCV quote failed for %s: %s", symbol, e)
        return None



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


def _get_tw_mis_quote(symbol: str) -> dict | None:
    """
    Fetch real-time quote from TWSE MIS API (works during and after market hours).
    Tries tse (TWSE) first, then otc (TPEX) automatically.
    Returns None if both fail or price field is '-'.
    """
    raw_code = symbol.split(".")[0]
    suffix   = symbol.upper().rsplit(".", 1)[-1]
    exchanges = ["otc"] if suffix == "TWO" else ["tse", "otc"]

    for ex in exchanges:
        try:
            resp = requests.get(
                "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
                params={"ex_ch": f"{ex}_{raw_code}.tw", "json": "1", "delay": "0"},
                headers={"User-Agent": "Mozilla/5.0", "Referer": "https://mis.twse.com.tw/"},
                timeout=8, verify=False,
            )
            items = resp.json().get("msgArray", [])
            if not items:
                continue
            item = items[0]
            z = item.get("z", "-")   # last/current price
            y = item.get("y", "-")   # yesterday close
            v = item.get("v", "0")   # volume

            # After close, z may be "-"; fall back to closing price field "z" from y
            price_str = z if z and z != "-" else item.get("pz", "-")
            if not price_str or price_str == "-":
                continue

            close    = float(price_str)
            prev_c   = float(y) if y and y != "-" else close
            change   = close - prev_c
            vol      = int(float(v)) if v and v not in ("-", "") else 0
            logger.info("MIS quote OK for %s (%s): %.2f", symbol, ex, close)
            return {
                "price":      round(close, 4),
                "change":     round(change, 4),
                "change_pct": round(change / prev_c * 100, 2) if prev_c else 0,
                "volume":     vol,
            }
        except Exception as e:
            logger.debug("MIS API error %s (%s): %s", symbol, ex, e)

    return None


def _get_tw_quote_from_twse(symbol: str) -> dict | None:
    """
    Fallback: fetch latest close from TWSE/TPEX monthly data.
    BUG FIX: use today's actual date (not replace(day=1)) so we never
    land on a public holiday like 勞動節 May 1.
    Tries current month first, then previous month.
    """
    raw_code = symbol.split(".")[0]
    suffix   = symbol.upper().rsplit(".", 1)[-1]

    cur = datetime.now()
    for _ in range(3):
        try:
            # Use today's date (not first-of-month) — TWSE returns whole-month data
            # regardless of which day within the month you send.
            date_str = cur.strftime("%Y%m%d")

            if suffix == "TWO":
                roc_year   = cur.year - 1911
                date_param = f"{roc_year}/{cur.month:02d}"
                url    = "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php"
                params = {"d": date_param, "stkno": raw_code, "o": "json"}
                resp   = requests.get(url, params=params,
                                      headers={"User-Agent": "Mozilla/5.0"},
                                      timeout=10, verify=False)
                data   = resp.json()
                rows   = data.get("aaData") or data.get("data") or []
                if rows:
                    latest = rows[-1]
                    close  = float(str(latest[7]).replace(",", ""))
                    prev_c = float(str(rows[-2][7]).replace(",", "")) if len(rows) > 1 else close
                    vol    = int(str(latest[1]).replace(",", ""))
                    change = close - prev_c
                    return {"price": round(close, 4), "change": round(change, 4),
                            "change_pct": round(change / prev_c * 100, 2) if prev_c else 0,
                            "volume": vol}
            else:
                url    = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
                params = {"response": "json", "date": date_str, "stockNo": raw_code}
                resp   = requests.get(url, params=params,
                                      headers={"User-Agent": "Mozilla/5.0"},
                                      timeout=10, verify=False)
                data   = resp.json()
                if data.get("stat") in ("OK", "ok") and data.get("data"):
                    rows   = data["data"]
                    latest = rows[-1]
                    close  = float(str(latest[6]).replace(",", ""))
                    prev_c = float(str(rows[-2][6]).replace(",", "")) if len(rows) > 1 else close
                    vol    = int(str(latest[1]).replace(",", ""))
                    change = close - prev_c
                    return {"price": round(close, 4), "change": round(change, 4),
                            "change_pct": round(change / prev_c * 100, 2) if prev_c else 0,
                            "volume": vol}

        except Exception as e:
            logger.debug("TWSE/TPEX quote error %s: %s", symbol, e)

        # Step back ~1 month
        cur = cur - timedelta(days=30)

    return None


def _fetch_yfinance(symbol: str, period: str, interval: str) -> pd.DataFrame:
    """Shared yfinance fetch helper — returns cleaned DataFrame or empty.

    yfinance 0.2.55+ may return:
    - Timezone-aware index (Asia/Taipei for TW stocks) — strip with tz_convert(None)
    - NaN rows for today's incomplete intraday data — drop to prevent JSON serialization errors
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval,
                            auto_adjust=True, actions=False)
        if df.empty:
            logger.warning("yfinance returned empty data for %s", symbol)
            return pd.DataFrame()
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        # Strip timezone while preserving the exchange-local calendar date.
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        else:
            df.index = df.index.tz_localize(None)
        # Drop rows with NaN Close (today's incomplete data from yfinance 0.2.55+)
        df = df.dropna(subset=["Close"])
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
    tw_closed  = is_tw_symbol(symbol) and is_tw_market_closed_today()

    if not force_refresh:
        cached = _load_cache(cache_path, None if tw_closed else ttl)
        if cached is not None and not cached.empty:
            logger.debug("Cache hit for %s", symbol)
            return cached

    if tw_closed:
        cached = _load_cache(cache_path, None)
        if cached is not None and not cached.empty:
            logger.info("TW market closed; serving cached OHLCV for %s", symbol)
            return cached
        logger.info("TW market closed but no OHLCV cache exists for %s; trying fallback fetch", symbol)

    # ── Step 1: yfinance (primary for everything) ─────────────────────────────
    df = _fetch_yfinance(symbol, period, interval)
    if not df.empty:
        _save_cache(cache_path, df)
        return df

    # ── Step 2: TWSE / TPEX fallback (Taiwan stocks only) ────────────────────
    if is_tw_symbol(symbol):
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
      Taiwan stocks (.TW / .TWO):
        1. yfinance                  — fastest when not rate-limited
        2. Bulk TWSE/TPEX Open Data  — one cached API call covers ALL stocks
        3. TWSE MIS real-time API    — per-stock real-time fallback
        4. TWSE/TPEX monthly data    — last-resort reliable fallback
      US / other stocks:
        1. yfinance history(5d)
    """
    is_tw = is_tw_symbol(symbol)
    tw_closed = is_tw and is_tw_market_closed_today()

    def with_update(data: dict) -> dict:
        if not data:
            return data
        out = dict(data)
        out["last_updated"] = out.get("last_updated") or _time_text()
        return out

    # ── Step 1: yfinance (primary for ALL symbols) ────────────────────────────
    if tw_closed:
        q = _quote_from_cached_ohlcv(symbol)
        if q:
            logger.info("TW market closed; serving cached last close quote for %s", symbol)
            return with_update(q)

    try:
        t  = yf.Ticker(symbol)
        df = t.history(period="5d", interval="1d", auto_adjust=True, actions=False)
        # yfinance 0.2.55+ may add today's row with NaN prices before market closes
        df = df.dropna(subset=["Close"])
        if not df.empty:
            close      = float(df["Close"].iloc[-1])
            prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else close
            change     = close - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0
            volume     = int(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0
            logger.info("yfinance quote OK for %s: %.2f", symbol, close)
            return with_update({
                "price":      round(close, 4),
                "change":     round(change, 4),
                "change_pct": round(change_pct, 2),
                "volume":     volume,
            })
        logger.warning("yfinance history empty for %s", symbol)
    except Exception as e:
        logger.warning("yfinance quote failed for %s: %s", symbol, e)

    # TW-only fallbacks ────────────────────────────────────────────────────────
    if not is_tw:
        return {}

    # ── TW Step 2: Bulk TWSE/TPEX (one cached call for all stocks) ───────────
    logger.info("yfinance failed for %s, trying bulk TWSE/TPEX...", symbol)
    q = _get_tw_bulk_quote(symbol)
    if q:
        return with_update(q)

    # ── TW Step 3: MIS real-time ──────────────────────────────────────────────
    logger.info("Bulk failed for %s, trying MIS real-time...", symbol)
    q = _get_tw_mis_quote(symbol)
    if q:
        return with_update(q)

    # ── TW Step 4: TWSE/TPEX monthly (fixed date) ────────────────────────────
    logger.info("MIS failed for %s, trying TWSE monthly...", symbol)
    q = _get_tw_quote_from_twse(symbol)
    if q:
        return with_update(q)

    return {}


def df_to_ohlcv_list(df: pd.DataFrame) -> list:
    records = []
    for idx, row in df.iterrows():
        # Skip rows with NaN prices — yfinance 0.2.55+ may include incomplete today's row
        if pd.isna(row.get("Close")):
            continue
        records.append({
            "time": idx.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(row["Volume"]) if not pd.isna(row.get("Volume")) else 0,
        })
    return records


# ─── Chip data: 三大法人 + 融資融券 ────────────────────────────────────────────
# Primary:  FinMind API  (finmindtrade.com) — single endpoint, TWSE+TPEX unified
# Fallback: TWSE / TPEX direct exchange APIs

INVESTORS_CACHE_TTL = 3600   # 1 hour

_FINMIND_URL   = "https://api.finmindtrade.com/api/v4/data"
_FINMIND_TOKEN = os.getenv("FINMIND_TOKEN", "")   # optional; raises rate limit


def _parse_tw_number(s) -> int:
    try:
        return int(str(s).replace(",", "").replace("+", "").strip() or "0")
    except (ValueError, AttributeError):
        return 0


# ── FinMind helpers ───────────────────────────────────────────────────────────

def _fm_request(dataset: str, stock_id: str, start_date: str, end_date: str) -> list:
    """Call FinMind v4 data API. Returns list of row-dicts or [] on failure."""
    params: dict = {
        "dataset":    dataset,
        "data_id":    stock_id,
        "start_date": start_date,
        "end_date":   end_date,
    }
    if _FINMIND_TOKEN:
        params["token"] = _FINMIND_TOKEN
    try:
        resp = requests.get(_FINMIND_URL, params=params, timeout=20)
        resp.raise_for_status()
        j = resp.json()
        if int(j.get("status", 0)) != 200:
            logger.warning("FinMind %s %s: %s", dataset, stock_id, j.get("msg", ""))
            return []
        return j.get("data", [])
    except Exception as e:
        logger.warning("FinMind request failed %s %s: %s", dataset, stock_id, e)
        return []


def _fm_three_forces(code: str, days: int = 5, force_refresh: bool = False) -> list:
    """
    FinMind TaiwanStockInstitutionalInvestorsBuySell → 5-day 三大法人 list.
    Returns list of dicts newest-first:
        {date, foreign_net, trust_net, dealer_net, total_net}
    """
    cache_path = os.path.join(CACHE_DIR, f"fm_3f_{code}.json")
    market_closed = is_tw_market_closed_today()
    if (not force_refresh or market_closed) and os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < INVESTORS_CACHE_TTL or market_closed:
            try:
                with open(cache_path, encoding="utf-8") as f:
                    cached = json.load(f)
                if cached:
                    return cached
            except Exception:
                pass

    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=20)   # ~14 calendar days → ≥5 trading days
    rows = _fm_request(
        "TaiwanStockInstitutionalInvestorsBuySell",
        code,
        start_dt.strftime("%Y-%m-%d"),
        end_dt.strftime("%Y-%m-%d"),
    )
    if not rows:
        return []

    # Aggregate per date: multiple rows per date (one per institution type)
    from collections import defaultdict
    by_date: dict = defaultdict(lambda: {"foreign": 0, "trust": 0, "dealer": 0})
    for r in rows:
        date_key = str(r.get("date", ""))[:10]
        name     = str(r.get("name", ""))
        buy      = int(r.get("buy",  0) or 0)
        sell     = int(r.get("sell", 0) or 0)
        net      = buy - sell
        if "Foreign_Investor" in name:
            by_date[date_key]["foreign"] += net     # covers base + hedging
        elif name == "Investment_Trust":
            by_date[date_key]["trust"]  = net
        elif "Dealer" in name:
            # Prefer the aggregated "Dealer" row; if we see Dealer_self/Hedging,
            # accumulate — the aggregate row will overwrite later if present.
            by_date[date_key]["dealer"] += net

    result = []
    for dk in sorted(by_date.keys(), reverse=True):
        d = by_date[dk]
        foreign = d["foreign"]
        trust   = d["trust"]
        dealer  = d["dealer"]
        result.append({
            "date":        dk,
            "foreign_net": foreign,
            "trust_net":   trust,
            "dealer_net":  dealer,
            "total_net":   foreign + trust + dealer,
        })

    result = result[:days]
    if result:
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except Exception:
            pass
    return result


def _fm_margin(code: str, days: int = 5, force_refresh: bool = False) -> list:
    """
    FinMind TaiwanStockMarginPurchaseShortSale → 5-day 融資融券 list.
    Returns list of dicts newest-first:
        {date, margin_buy, margin_sell, margin_bal,
         short_sell, short_buy, short_bal, margin_short_ratio}
    """
    cache_path = os.path.join(CACHE_DIR, f"fm_margin_{code}.json")
    market_closed = is_tw_market_closed_today()
    if (not force_refresh or market_closed) and os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < INVESTORS_CACHE_TTL or market_closed:
            try:
                with open(cache_path, encoding="utf-8") as f:
                    cached = json.load(f)
                if cached:
                    return cached
            except Exception:
                pass

    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=20)
    rows = _fm_request(
        "TaiwanStockMarginPurchaseShortSale",
        code,
        start_dt.strftime("%Y-%m-%d"),
        end_dt.strftime("%Y-%m-%d"),
    )
    if not rows:
        return []

    result = []
    for r in sorted(rows, key=lambda x: x.get("date", ""), reverse=True):
        m_bal = int(r.get("MarginPurchaseTodayBalance", 0) or 0)
        s_bal = int(r.get("ShortSaleTodayBalance",      0) or 0)
        result.append({
            "date":               str(r.get("date", ""))[:10],
            "margin_buy":         int(r.get("MarginPurchaseBuy",  0) or 0),
            "margin_sell":        int(r.get("MarginPurchaseSell", 0) or 0),
            "margin_bal":         m_bal,
            "short_sell":         int(r.get("ShortSaleSell", 0) or 0),
            "short_buy":          int(r.get("ShortSaleBuy",  0) or 0),
            "short_bal":          s_bal,
            "margin_short_ratio": round(m_bal / s_bal, 2) if s_bal else None,
        })

    result = result[:days]
    if result:
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except Exception:
            pass
    return result


# ── TWSE / TPEX direct APIs (fallback only) ──────────────────────────────────

def _twse_three_forces_fallback(code: str, force_refresh: bool = False) -> list:
    """TWSE T86 day-by-day fallback for 三大法人. Returns 5-day list newest-first."""
    result = []
    d = datetime.now()
    attempts = 0
    while len(result) < 5 and attempts < 20:
        if d.weekday() < 5:
            date_str   = d.strftime("%Y%m%d")
            cache_path = os.path.join(CACHE_DIR, f"twse_3f_{date_str}.json")
            day_data: dict = {}
            if not force_refresh and os.path.exists(cache_path):
                try:
                    with open(cache_path, encoding="utf-8") as f:
                        day_data = json.load(f)
                except Exception:
                    pass
            if not day_data:
                url = (
                    "https://www.twse.com.tw/rwd/zh/fund/T86"
                    f"?date={date_str}&selectType=ALLBUT0999&response=json"
                )
                try:
                    raw = requests.get(url, headers={"User-Agent": "Mozilla/5.0"},
                                       timeout=15).json()
                    if raw.get("stat") in ("OK", "ok"):
                        fields = raw.get("fields", [])
                        def fi(n):
                            try: return fields.index(n)
                            except ValueError: return -1
                        ic = fi("證券代號") if fi("證券代號") >= 0 else 0
                        iF = fi("外陸資買賣超股數") if fi("外陸資買賣超股數") >= 0 else 4
                        iT = fi("投信買賣超股數")   if fi("投信買賣超股數")   >= 0 else 7
                        iD = fi("自營商買賣超股數") if fi("自營商買賣超股數") >= 0 else 8
                        iN = fi("三大法人買賣超股數") if fi("三大法人買賣超股數") >= 0 else 15
                        for row in raw.get("data", []):
                            c = str(row[ic]).strip()
                            day_data[c] = {
                                "foreign_net": _parse_tw_number(row[iF]),
                                "trust_net":   _parse_tw_number(row[iT]),
                                "dealer_net":  _parse_tw_number(row[iD]),
                                "total_net":   _parse_tw_number(row[iN]),
                            }
                        try:
                            with open(cache_path, "w", encoding="utf-8") as f:
                                json.dump(day_data, f)
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug("TWSE T86 fallback %s: %s", date_str, e)
            if code in day_data:
                entry = dict(day_data[code])
                entry["date"] = d.strftime("%Y-%m-%d")
                result.append(entry)
        d -= timedelta(days=1)
        attempts += 1
    return result


def _tpex_three_forces_fallback(code: str, force_refresh: bool = False) -> list:
    """TPEX OTC inst-trading day-by-day fallback for 三大法人. Returns newest-first."""
    result = []
    d = datetime.now()
    attempts = 0
    while len(result) < 5 and attempts < 20:
        if d.weekday() < 5:
            date_str   = d.strftime("%Y%m%d")
            cache_path = os.path.join(CACHE_DIR, f"tpex_3f_{date_str}.json")
            day_data: dict = {}
            if not force_refresh and os.path.exists(cache_path):
                try:
                    with open(cache_path, encoding="utf-8") as f:
                        day_data = json.load(f)
                except Exception:
                    pass
            if not day_data:
                try:
                    dt      = datetime.strptime(date_str, "%Y%m%d")
                    roc_str = f"{dt.year - 1911}/{dt.month:02d}/{dt.day:02d}"
                    raw = requests.get(
                        "https://www.tpex.org.tw/web/stock/fund/inst_trading/inst_trading_result.php",
                        params={"l": "zh-tw", "o": "json", "d": roc_str, "se": "EW", "s": "0,asc,0"},
                        headers={"User-Agent": "Mozilla/5.0"},
                        timeout=15, verify=False,
                    ).json()
                    for row in raw.get("aaData", []):
                        c = str(row[0]).strip()
                        if c and len(row) >= 15:
                            day_data[c] = {
                                "foreign_net": _parse_tw_number(row[4]),
                                "trust_net":   _parse_tw_number(row[7]),
                                "dealer_net":  _parse_tw_number(row[10]),
                                "total_net":   _parse_tw_number(row[14]),
                            }
                    try:
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump(day_data, f)
                    except Exception:
                        pass
                except Exception as e:
                    logger.debug("TPEX 3F fallback %s: %s", date_str, e)
            if code in day_data:
                entry = dict(day_data[code])
                entry["date"] = d.strftime("%Y-%m-%d")
                result.append(entry)
        d -= timedelta(days=1)
        attempts += 1
    return result


def _twse_margin_fallback(code: str, force_refresh: bool = False) -> list:
    """TWSE MI_MARGN day-by-day fallback for 融資融券. Returns newest-first."""
    result = []
    d = datetime.now()
    attempts = 0
    while len(result) < 5 and attempts < 20:
        if d.weekday() < 5:
            date_str   = d.strftime("%Y%m%d")
            cache_path = os.path.join(CACHE_DIR, f"twse_margin_{date_str}.json")
            day_data: dict = {}
            if not force_refresh and os.path.exists(cache_path):
                try:
                    with open(cache_path, encoding="utf-8") as f:
                        day_data = json.load(f)
                except Exception:
                    pass
            if not day_data:
                try:
                    raw = requests.get(
                        "https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN",
                        params={"date": date_str, "selectType": "ALL", "response": "json"},
                        headers={"User-Agent": "Mozilla/5.0"},
                        timeout=15, verify=False,
                    ).json()
                    if raw.get("stat") in ("OK", "ok"):
                        for row in raw.get("data", []):
                            c = str(row[0]).strip()
                            if c and len(row) >= 13:
                                mb = _parse_tw_number(row[5])
                                sb = _parse_tw_number(row[10])
                                day_data[c] = {
                                    "margin_buy": _parse_tw_number(row[2]),
                                    "margin_sell": _parse_tw_number(row[3]),
                                    "margin_bal": mb,
                                    "short_sell": _parse_tw_number(row[7]),
                                    "short_buy":  _parse_tw_number(row[8]),
                                    "short_bal":  sb,
                                    "margin_short_ratio": round(mb / sb, 2) if sb else None,
                                }
                        try:
                            with open(cache_path, "w", encoding="utf-8") as f:
                                json.dump(day_data, f)
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug("TWSE margin fallback %s: %s", date_str, e)
            if code in day_data:
                entry = dict(day_data[code])
                entry["date"] = d.strftime("%Y-%m-%d")
                result.append(entry)
        d -= timedelta(days=1)
        attempts += 1
    return result


def _tpex_margin_fallback(code: str, force_refresh: bool = False) -> list:
    """TPEX margin_bal day-by-day fallback for 融資融券. Returns newest-first."""
    result = []
    d = datetime.now()
    attempts = 0
    while len(result) < 5 and attempts < 20:
        if d.weekday() < 5:
            date_str   = d.strftime("%Y%m%d")
            cache_path = os.path.join(CACHE_DIR, f"tpex_margin_{date_str}.json")
            day_data: dict = {}
            if not force_refresh and os.path.exists(cache_path):
                try:
                    with open(cache_path, encoding="utf-8") as f:
                        day_data = json.load(f)
                except Exception:
                    pass
            if not day_data:
                try:
                    dt      = datetime.strptime(date_str, "%Y%m%d")
                    roc_str = f"{dt.year - 1911}/{dt.month:02d}/{dt.day:02d}"
                    raw = requests.get(
                        "https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php",
                        params={"l": "zh-tw", "o": "json", "d": roc_str, "se": "EW"},
                        headers={"User-Agent": "Mozilla/5.0"},
                        timeout=15, verify=False,
                    ).json()
                    for row in raw.get("aaData", []):
                        c = str(row[0]).strip()
                        if c and len(row) >= 13:
                            mb = _parse_tw_number(row[6])
                            sb = _parse_tw_number(row[12])
                            day_data[c] = {
                                "margin_buy": _parse_tw_number(row[2]),
                                "margin_sell": _parse_tw_number(row[3]),
                                "margin_bal": mb,
                                "short_sell": _parse_tw_number(row[8]),
                                "short_buy":  _parse_tw_number(row[9]),
                                "short_bal":  sb,
                                "margin_short_ratio": round(mb / sb, 2) if sb else None,
                            }
                        try:
                            with open(cache_path, "w", encoding="utf-8") as f:
                                json.dump(day_data, f)
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug("TPEX margin fallback %s: %s", date_str, e)
            if code in day_data:
                entry = dict(day_data[code])
                entry["date"] = d.strftime("%Y-%m-%d")
                result.append(entry)
        d -= timedelta(days=1)
        attempts += 1
    return result


# ── Public interface: 三大法人 ────────────────────────────────────────────────

def _get_tw_investors(symbol: str, force_refresh: bool = False) -> dict:
    """
    Return 三大法人 5-day trend for a TW stock.
    Priority: FinMind → TWSE/TPEX direct fallback
    """
    code   = symbol.split(".")[0]
    is_otc = symbol.upper().endswith(".TWO")

    # 1. Try FinMind (works for both TWSE and TPEX)
    trend = _fm_three_forces(code, force_refresh=force_refresh)

    # 2. Fallback: direct exchange API
    if not trend:
        logger.info("FinMind 三大法人 empty for %s — trying exchange fallback", symbol)
        trend = (_tpex_three_forces_fallback(code, force_refresh=force_refresh) if is_otc
                 else _twse_three_forces_fallback(code, force_refresh=force_refresh))
        for entry in trend:
            if "total_net" not in entry:
                entry["total_net"] = (
                    entry.get("foreign_net", 0)
                    + entry.get("trust_net", 0)
                    + entry.get("dealer_net", 0)
                )

    if not trend:
        return {"type": "tw", "symbol": symbol,
                "error": "無三大法人資料（非交易日或資料未更新）"}

    latest = trend[0]   # newest
    data_updated_at = _latest_mtime_text([
        os.path.join(CACHE_DIR, f"fm_3f_{code}.json"),
        os.path.join(CACHE_DIR, f"{'tpex' if is_otc else 'twse'}_3f_{latest['date'].replace('-', '')}.json"),
    ]) or _time_text()
    return {
        "type":        "tw",
        "market":      "OTC" if is_otc else "TWSE",
        "symbol":      symbol,
        "latest_date": latest["date"],
        "last_updated": data_updated_at,
        "foreign_net": latest["foreign_net"],
        "trust_net":   latest["trust_net"],
        "dealer_net":  latest["dealer_net"],
        "total_net":   latest["total_net"],
        "trend":       list(reversed(trend)),   # oldest→newest for charts
    }


# ── Public interface: 融資融券 ────────────────────────────────────────────────

def get_tw_margin_data(symbol: str, force_refresh: bool = False) -> dict:
    """
    Return 融資融券 5-day trend for a TW stock.
    Priority: FinMind → TWSE/TPEX direct fallback
    """
    code   = symbol.split(".")[0]
    is_otc = symbol.upper().endswith(".TWO")

    # 1. Try FinMind
    trend = _fm_margin(code, force_refresh=force_refresh)

    # 2. Fallback: direct exchange API
    if not trend:
        logger.info("FinMind margin empty for %s — trying exchange fallback", symbol)
        trend = (_tpex_margin_fallback(code, force_refresh=force_refresh) if is_otc
                 else _twse_margin_fallback(code, force_refresh=force_refresh))

    if not trend:
        return {"symbol": symbol, "error": "無融資融券資料（非交易日或資料未更新）"}

    latest = trend[0]
    data_updated_at = _latest_mtime_text([
        os.path.join(CACHE_DIR, f"fm_margin_{code}.json"),
        os.path.join(CACHE_DIR, f"{'tpex' if is_otc else 'twse'}_margin_{latest['date'].replace('-', '')}.json"),
    ]) or _time_text()
    return {
        "symbol":             symbol,
        "market":             "OTC" if is_otc else "TWSE",
        "latest_date":        latest["date"],
        "last_updated":       data_updated_at,
        "margin_buy":         latest["margin_buy"],
        "margin_sell":        latest["margin_sell"],
        "margin_bal":         latest["margin_bal"],
        "short_sell":         latest["short_sell"],
        "short_buy":          latest["short_buy"],
        "short_bal":          latest["short_bal"],
        "margin_short_ratio": latest.get("margin_short_ratio"),
        "trend":              list(reversed(trend)),  # oldest→newest for charts
    }


def _get_us_investors(symbol: str, force_refresh: bool = False) -> dict:
    """Return institutional/retail breakdown for a US stock via yfinance."""
    inv_cache = os.path.join(CACHE_DIR, f"investors_{symbol.upper()}.json")
    if not force_refresh and os.path.exists(inv_cache):
        age = time.time() - os.path.getmtime(inv_cache)
        if age < INVESTORS_CACHE_TTL * 4:  # 4 h cache for US data
            try:
                with open(inv_cache, encoding="utf-8") as f:
                    cached = json.load(f)
                cached["last_updated"] = cached.get("last_updated") or _mtime_text(inv_cache)
                return cached
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
            "last_updated": _time_text(),
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


def get_investors_data(symbol: str, force_refresh: bool = False) -> dict:
    """Get investor composition data.
    TW → 三大法人 (TWSE or TPEX) + 融資融券; others → yfinance institutional."""
    upper = symbol.upper()
    if upper.endswith(".TW") or upper.endswith(".TWO"):
        result = _get_tw_investors(symbol, force_refresh=force_refresh)
        margin = get_tw_margin_data(symbol, force_refresh=force_refresh)
        result["margin"] = margin
        result["margin_last_updated"] = margin.get("last_updated")
        result["last_updated"] = _latest_mtime_text([
            os.path.join(CACHE_DIR, f"fm_3f_{symbol.split('.')[0]}.json"),
            os.path.join(CACHE_DIR, f"fm_margin_{symbol.split('.')[0]}.json"),
        ]) or result.get("last_updated") or margin.get("last_updated") or _time_text()
        return result
    return _get_us_investors(symbol, force_refresh=force_refresh)
