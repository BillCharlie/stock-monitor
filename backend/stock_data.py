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
      Taiwan stocks (.TW / .TWO):
        1. yfinance                  — fastest when not rate-limited
        2. Bulk TWSE/TPEX Open Data  — one cached API call covers ALL stocks
        3. TWSE MIS real-time API    — per-stock real-time fallback
        4. TWSE/TPEX monthly data    — last-resort reliable fallback
      US / other stocks:
        1. yfinance history(5d)
    """
    upper = symbol.upper()
    is_tw = upper.endswith(".TW") or upper.endswith(".TWO")

    # ── Step 1: yfinance (primary for ALL symbols) ────────────────────────────
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

    # TW-only fallbacks ────────────────────────────────────────────────────────
    if not is_tw:
        return {}

    # ── TW Step 2: Bulk TWSE/TPEX (one cached call for all stocks) ───────────
    logger.info("yfinance failed for %s, trying bulk TWSE/TPEX...", symbol)
    q = _get_tw_bulk_quote(symbol)
    if q:
        return q

    # ── TW Step 3: MIS real-time ──────────────────────────────────────────────
    logger.info("Bulk failed for %s, trying MIS real-time...", symbol)
    q = _get_tw_mis_quote(symbol)
    if q:
        return q

    # ── TW Step 4: TWSE/TPEX monthly (fixed date) ────────────────────────────
    logger.info("MIS failed for %s, trying TWSE monthly...", symbol)
    q = _get_tw_quote_from_twse(symbol)
    if q:
        return q

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


def _fetch_tpex_three_forces(date_str: str) -> dict:
    """Fetch TPEX (OTC) 三大法人 buy/sell data for one date. Cached per date.
    date_str: YYYYMMDD"""
    cache_path = os.path.join(CACHE_DIR, f"tpex_3f_{date_str}.json")
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

    try:
        dt      = datetime.strptime(date_str, "%Y%m%d")
        roc_str = f"{dt.year - 1911}/{dt.month:02d}/{dt.day:02d}"
    except ValueError:
        return {}

    url = "https://www.tpex.org.tw/web/stock/fund/inst_trading/inst_trading_result.php"
    try:
        resp = requests.get(
            url,
            params={"l": "zh-tw", "o": "json", "d": roc_str, "se": "EW", "s": "0,asc,0"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15, verify=False,
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        logger.warning("TPEX inst trading fetch failed %s: %s", date_str, e)
        return {}

    rows = raw.get("aaData", [])
    if not rows:
        return {}

    # aaData cols: 0=代號,1=名稱,2=外資買,3=外資賣,4=外資超,5=投信買,6=投信賣,7=投信超,
    #              8=自營買(自行),9=自營賣(自行),10=自營超(自行),
    #              11=自營買(避險),12=自營賣(避險),13=自營超(避險),14=三大合計
    result: dict = {}
    for row in rows:
        try:
            code = str(row[0]).strip()
            if not code or len(row) < 15:
                continue
            result[code] = {
                "foreign_net": _parse_tw_number(row[4]),
                "trust_net":   _parse_tw_number(row[7]),
                "dealer_net":  _parse_tw_number(row[10]),
                "total_net":   _parse_tw_number(row[14]),
            }
        except (IndexError, ValueError):
            continue

    if result:
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except Exception:
            pass
    return result


def _fetch_twse_margin(date_str: str) -> dict:
    """TWSE 融資融券 bulk for one date. Returns {code: {...}}"""
    cache_path = os.path.join(CACHE_DIR, f"twse_margin_{date_str}.json")
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

    try:
        resp = requests.get(
            "https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN",
            params={"date": date_str, "selectType": "ALL", "response": "json"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15, verify=False,
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        logger.warning("TWSE margin fetch failed %s: %s", date_str, e)
        return {}

    if raw.get("stat") not in ("OK", "ok"):
        return {}

    # fields: 股票代號,股票名稱,融資買進,融資賣出,融資現償,融資餘額,融資限額,
    #         融券賣出,融券買進,融券現償,融券餘額,融券限額,資券相抵,備註
    result: dict = {}
    for row in raw.get("data", []):
        try:
            code = str(row[0]).strip()
            if not code or len(row) < 13:
                continue
            m_bal = _parse_tw_number(row[5])
            s_bal = _parse_tw_number(row[10])
            result[code] = {
                "margin_buy":          _parse_tw_number(row[2]),
                "margin_sell":         _parse_tw_number(row[3]),
                "margin_bal":          m_bal,
                "short_sell":          _parse_tw_number(row[7]),
                "short_buy":           _parse_tw_number(row[8]),
                "short_bal":           s_bal,
                "margin_short_ratio":  round(m_bal / s_bal, 2) if s_bal else None,
            }
        except (IndexError, ValueError, ZeroDivisionError):
            continue

    if result:
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except Exception:
            pass
    return result


def _fetch_tpex_margin(date_str: str) -> dict:
    """TPEX (OTC) 融資融券 bulk for one date."""
    cache_path = os.path.join(CACHE_DIR, f"tpex_margin_{date_str}.json")
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

    try:
        dt      = datetime.strptime(date_str, "%Y%m%d")
        roc_str = f"{dt.year - 1911}/{dt.month:02d}/{dt.day:02d}"
    except ValueError:
        return {}

    try:
        resp = requests.get(
            "https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php",
            params={"l": "zh-tw", "o": "json", "d": roc_str, "se": "EW"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15, verify=False,
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        logger.warning("TPEX margin fetch failed %s: %s", date_str, e)
        return {}

    # aaData cols: 0=代號,1=名稱,2=融資買進,3=融資賣出,4=融資現償,5=前日融資,6=今日融資餘額,7=限額,
    #              8=融券賣出,9=融券買進,10=融券現償,11=前日融券,12=今日融券餘額,13=限額,14=資券相抵
    result: dict = {}
    for row in raw.get("aaData", []):
        try:
            code = str(row[0]).strip()
            if not code or len(row) < 13:
                continue
            m_bal = _parse_tw_number(row[6])
            s_bal = _parse_tw_number(row[12])
            result[code] = {
                "margin_buy":          _parse_tw_number(row[2]),
                "margin_sell":         _parse_tw_number(row[3]),
                "margin_bal":          m_bal,
                "short_sell":          _parse_tw_number(row[8]),
                "short_buy":           _parse_tw_number(row[9]),
                "short_bal":           s_bal,
                "margin_short_ratio":  round(m_bal / s_bal, 2) if s_bal else None,
            }
        except (IndexError, ValueError, ZeroDivisionError):
            continue

    if result:
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except Exception:
            pass
    return result


def _get_tw_investors(symbol: str) -> dict:
    """Return 三大法人 trend (last 5 trading days). Supports both TWSE and TPEX."""
    code    = symbol.split(".")[0]
    is_otc  = symbol.upper().endswith(".TWO")
    fetch_fn = _fetch_tpex_three_forces if is_otc else _fetch_twse_three_forces

    trend: list = []
    d = datetime.now()
    attempts = 0
    while len(trend) < 5 and attempts < 20:
        if d.weekday() < 5:
            date_str = d.strftime("%Y%m%d")
            day_data = fetch_fn(date_str)
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
        "type":         "tw",
        "market":       "OTC" if is_otc else "TWSE",
        "symbol":       symbol,
        "latest_date":  latest["date"],
        "foreign_net":  latest["foreign_net"],
        "trust_net":    latest["trust_net"],
        "dealer_net":   latest["dealer_net"],
        "total_net":    latest["total_net"],
        "trend":        list(reversed(trend)),
    }


def get_tw_margin_data(symbol: str) -> dict:
    """Return 融資融券 trend (last 5 trading days). Supports both TWSE and TPEX."""
    code    = symbol.split(".")[0]
    is_otc  = symbol.upper().endswith(".TWO")
    fetch_fn = _fetch_tpex_margin if is_otc else _fetch_twse_margin

    trend: list = []
    d = datetime.now()
    attempts = 0
    while len(trend) < 5 and attempts < 20:
        if d.weekday() < 5:
            date_str = d.strftime("%Y%m%d")
            day_data = fetch_fn(date_str)
            if code in day_data:
                entry = dict(day_data[code])
                entry["date"] = d.strftime("%Y-%m-%d")
                trend.append(entry)
        d -= timedelta(days=1)
        attempts += 1

    if not trend:
        return {"symbol": symbol, "error": "無融資融券資料（非交易日或資料未更新）"}

    latest = trend[0]
    return {
        "symbol":             symbol,
        "market":             "OTC" if is_otc else "TWSE",
        "latest_date":        latest["date"],
        "margin_buy":         latest["margin_buy"],
        "margin_sell":        latest["margin_sell"],
        "margin_bal":         latest["margin_bal"],
        "short_sell":         latest["short_sell"],
        "short_buy":          latest["short_buy"],
        "short_bal":          latest["short_bal"],
        "margin_short_ratio": latest.get("margin_short_ratio"),
        "trend":              list(reversed(trend)),
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
    """Get investor composition data.
    TW → 三大法人 (TWSE or TPEX) + 融資融券; others → yfinance institutional."""
    upper = symbol.upper()
    if upper.endswith(".TW") or upper.endswith(".TWO"):
        result = _get_tw_investors(symbol)
        result["margin"] = get_tw_margin_data(symbol)
        return result
    return _get_us_investors(symbol)
