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


def _get_tw_stock_from_tradingview(symbol: str, max_retries: int = 3) -> pd.DataFrame:
    """
    Fallback: Fetch Taiwan stock data from TradingView using Playwright.
    TradingView symbols: TWSE:3363 (Taiwan exchange format)
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    except ImportError:
        logger.warning("playwright not installed, skipping TradingView fallback")
        return pd.DataFrame()

    # Convert symbol: 3363.TW -> TWSE:3363
    if symbol.endswith(".TW"):
        tw_symbol = f"TWSE:{symbol[:-3]}"
    else:
        return pd.DataFrame()

    try:
        for attempt in range(max_retries):
            try:
                with sync_playwright() as p:
                    # Use headless browser
                    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    )
                    page = context.new_page()
                    
                    # Navigate to TradingView chart
                    url = f"https://www.tradingview.com/chart/?symbol={tw_symbol}"
                    page.goto(url, wait_until="load", timeout=15000)
                    time.sleep(2)  # Wait for data to load
                    
                    # Try to extract chart data from page
                    data_script = page.content()
                    
                    browser.close()
                    logger.warning(f"TradingView fetch incomplete for {symbol}")
                    return pd.DataFrame()
            except PlaywrightTimeoutError:
                if attempt < max_retries - 1:
                    logger.info(f"TradingView timeout, retry {attempt+1}/{max_retries} for {symbol}")
                    continue
                else:
                    raise
    except Exception as e:
        logger.error(f"TradingView fallback failed for {symbol}: {e}")
    
    return pd.DataFrame()


def _get_tw_stock_from_twse_api(symbol: str, days: int = 250) -> pd.DataFrame:
    """
    Fetch Taiwan stock data directly from TWSE (Taiwan Stock Exchange).
    TWSE API returns: [日期, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數, 註記]
    Index: 0=date, 1=volume, 2=value, 3=open, 4=high, 5=low, 6=close, 7=change, 8=txn_count
    Date format: 民國紀年 (e.g., 115/05/04 = 2026/05/04)
    """
    if not symbol.upper().endswith(".TW"):
        return pd.DataFrame()
    
    stock_code = symbol[:symbol.find(".")]  # Remove .TW suffix
    records = []
    
    try:
        # Start from recent dates and work backwards
        current_date = datetime.now()
        request_count = 0
        max_requests = 300  # Limit requests
        days_checked = 0
        max_days_to_check = 500  # Check up to 500 calendar days back
        
        while len(records) < days and request_count < max_requests and days_checked < max_days_to_check:
            date_str = current_date.strftime("%Y%m%d")
            days_checked += 1
            
            try:
                url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
                params = {
                    "response": "json",
                    "date": date_str,
                    "stockNo": stock_code
                }
                resp = requests.get(url, params=params, timeout=5, verify=False)
                request_count += 1
                
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        # Check if we got valid response
                        if data.get("stat") in ("OK", "ok") and "data" in data and data["data"]:
                            # TWSE format: [date, volume, value, open, high, low, close, change, txn_count, notes]
                            # Index: 0=date, 3=open, 4=high, 5=low, 6=close, 1=volume
                            for row in data["data"]:
                                try:
                                    # Date format: 民國年/月/日 (e.g., 115/05/04)
                                    # Convert to Gregorian: 民國 + 1911 = 西元
                                    date_parts = row[0].split('/')
                                    roc_year = int(date_parts[0])
                                    gregorian_year = roc_year + 1911
                                    date_str_gregorian = f"{gregorian_year}/{date_parts[1]}/{date_parts[2]}"
                                    date_obj = datetime.strptime(date_str_gregorian, "%Y/%m/%d")
                                    
                                    # Parse prices and volume, removing commas and spaces
                                    open_price = float(str(row[3]).replace(",", "").strip())
                                    high_price = float(str(row[4]).replace(",", "").strip())
                                    low_price = float(str(row[5]).replace(",", "").strip())
                                    close_price = float(str(row[6]).replace(",", "").strip())
                                    volume = int(str(row[1]).replace(",", "").strip())
                                    
                                    records.append({
                                        "Date": date_obj,
                                        "Open": open_price,
                                        "High": high_price,
                                        "Low": low_price,
                                        "Close": close_price,
                                        "Volume": volume,
                                    })
                                except (ValueError, IndexError) as e:
                                    logger.debug(f"Failed to parse TWSE row {row}: {e}")
                                    continue
                    except json.JSONDecodeError:
                        pass
                
                current_date -= timedelta(days=1)
                time.sleep(0.05)  # Rate limiting
                
            except requests.RequestException as e:
                logger.debug(f"TWSE fetch error for {date_str}: {e}")
                current_date -= timedelta(days=1)
                continue
        
        if records:
            df = pd.DataFrame(records)
            df.set_index("Date", inplace=True)
            df = df.sort_index()
            df = df[~df.index.duplicated(keep="last")]
            logger.info(f"Fetched {len(df)} records for {symbol} from TWSE ({request_count} requests)")
            return df
        else:
            logger.warning(f"No data fetched for {symbol} from TWSE after {request_count} requests")
    except Exception as e:
        logger.error(f"TWSE API failed for {symbol}: {e}")
    
    return pd.DataFrame()


def _get_tw_quote_from_twse(symbol: str) -> dict | None:
    """
    Fetch latest price and change info from TWSE for Taiwan stocks.
    TWSE format: [date, volume, value, open, high, low, close, change, txn_count, notes]
    Returns dict with price, change, change_pct, volume.
    Returns None if unable to fetch.
    """
    if not symbol.upper().endswith(".TW"):
        return None
    
    stock_code = symbol[:symbol.find(".")]  # Remove .TW suffix
    
    try:
        # Try to get latest trading data
        current_date = datetime.now()
        
        for _ in range(10):  # Try last 10 days
            date_str = current_date.strftime("%Y%m%d")
            
            try:
                url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
                params = {
                    "response": "json",
                    "date": date_str,
                    "stockNo": stock_code
                }
                resp = requests.get(url, params=params, timeout=5, verify=False)
                
                if resp.status_code == 200:
                    data = resp.json()
                    # Check if we got valid response
                    if data.get("stat") in ("OK", "ok") and "data" in data and data["data"]:
                        # Get the most recent record (last entry)
                        latest = data["data"][-1]
                        try:
                            # Extract values with correct indices
                            # Index: 0=date, 3=open, 4=high, 5=low, 6=close, 1=volume
                            close_price = float(str(latest[6]).replace(",", "").strip())  # Close price
                            volume = int(str(latest[1]).replace(",", "").strip())  # Volume
                            
                            # Get previous close to calculate change
                            prev_close = close_price
                            if len(data["data"]) > 1:
                                prev_close = float(str(data["data"][-2][6]).replace(",", "").strip())
                            
                            change = close_price - prev_close
                            change_pct = (change / prev_close * 100) if prev_close != 0 else 0
                            
                            logger.info(f"Got quote for {symbol} from TWSE: {close_price}")
                            return {
                                "price": round(close_price, 4),
                                "change": round(change, 4),
                                "change_pct": round(change_pct, 2),
                                "volume": volume,
                            }
                        except (ValueError, IndexError) as e:
                            logger.debug(f"Failed to parse TWSE quote: {e}")
            except requests.RequestException:
                pass
            
            current_date -= timedelta(days=1)
            time.sleep(0.05)
        
        logger.warning(f"Could not fetch quote for {symbol} from TWSE")
        return None
        
    except Exception as e:
        logger.error(f"TWSE quote fetch failed for {symbol}: {e}")
        return None


def get_ohlcv(symbol: str, interval: str = "1d", force_refresh: bool = False) -> pd.DataFrame:
    """
    Get OHLCV data with intelligent fallback for different sources.
    For Taiwan stocks (.TW): TWSE API → yfinance → TradingView
    For others: yfinance
    """
    period = INTERVAL_PERIOD.get(interval, "2y")
    ttl = CACHE_TTL.get(interval, 300)
    cache_path = _cache_path(symbol, interval, period)

    if not force_refresh:
        cached = _load_cache(cache_path, ttl)
        if cached is not None and not cached.empty:
            logger.debug(f"Loaded {symbol} from cache")
            return cached

    # Taiwan stocks have special handling
    if symbol.upper().endswith(".TW"):
        logger.info(f"Fetching Taiwan stock {symbol}...")
        
        # Step 1: Try TWSE API (most reliable for Taiwan stocks)
        df = _get_tw_stock_from_twse_api(symbol, days=500)
        if not df.empty:
            logger.info(f"Successfully got {symbol} from TWSE API ({len(df)} records)")
            _save_cache(cache_path, df)
            return df
        
        logger.warning(f"TWSE API failed for {symbol}, trying yfinance...")
        
        # Step 2: Fallback to yfinance
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval, auto_adjust=True, actions=False)
            if not df.empty:
                df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
                df.index = df.index.tz_localize(None)
                df = df[~df.index.duplicated(keep="last")]
                df = df.sort_index()
                logger.info(f"Got {symbol} from yfinance ({len(df)} records)")
                _save_cache(cache_path, df)
                return df
            else:
                logger.warning(f"yfinance returned empty data for {symbol}")
        except Exception as e:
            logger.warning(f"yfinance failed for {symbol}: {e}")
        
        # Step 3: Try alternative data sources (could be extended)
        logger.warning(f"Both TWSE and yfinance failed for {symbol}")
        return pd.DataFrame()

    # For non-Taiwan stocks, use yfinance
    try:
        logger.info(f"Fetching {symbol} from yfinance...")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True, actions=False)
        if df.empty:
            logger.warning(f"No data from yfinance for {symbol}")
            return pd.DataFrame()
        else:
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.index = df.index.tz_localize(None)
            df = df[~df.index.duplicated(keep="last")]
            df = df.sort_index()
            logger.info(f"Got {symbol} from yfinance ({len(df)} records)")
            _save_cache(cache_path, df)
            return df
    except Exception as e:
        logger.error(f"yfinance error for {symbol}: {e}")
        return pd.DataFrame()


def get_quote(symbol: str) -> dict:
    """Get latest price and change info. For Taiwan stocks, use TWSE API first."""
    # For Taiwan stocks, try TWSE API first
    if symbol.upper().endswith(".TW"):
        logger.info(f"Fetching quote for Taiwan stock {symbol} from TWSE...")
        tw_quote = _get_tw_quote_from_twse(symbol)
        if tw_quote is not None:
            return tw_quote
        logger.warning(f"TWSE quote fetch failed for {symbol}, falling back to yfinance...")
    
    # Fallback to yfinance
    try:
        t = yf.Ticker(symbol)
        info = t.fast_info
        price = getattr(info, "last_price", None)
        prev_close = getattr(info, "previous_close", None)
        change = (price - prev_close) if price and prev_close else None
        change_pct = (change / prev_close * 100) if change and prev_close else None
        
        quote = {
            "price": round(float(price), 4) if price else None,
            "change": round(float(change), 4) if change else None,
            "change_pct": round(float(change_pct), 2) if change_pct else None,
            "volume": int(getattr(info, "regular_market_volume", 0) or 0),
        }
        
        # Filter out None values
        return {k: v for k, v in quote.items() if v is not None}
        
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
