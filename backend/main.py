"""
Stock Monitor Backend — FastAPI
Single port: serves both API (/api/*) and React static build (/)
Run: uvicorn main:app --reload --port 8765
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from analysis import analyze_stock, generate_daily_report
from email_sender import send_daily_report, send_login_notification, send_test_email
from gpt_analysis import generate_gpt_report
from news_fetcher import fetch_all_news, fetch_category_news, get_last_updated, NEWS_CATEGORIES
from pdf_generator import latest_report_path, save_report_pdf
from trump_news_fetcher import fetch_trump_news, get_trump_last_updated
from indicators import (
    calculate_bollinger_bands,
    calculate_kd,
    calculate_ma,
    calculate_obv,
    calculate_rsi,
    series_to_list,
)
from stock_data import df_to_ohlcv_list, get_investors_data, get_ohlcv, get_quote, get_tw_margin_data
from watchlist import MARKET_INDICES, WATCHLIST
from etf_holdings import (
    fetch_etf_holdings,
    fetch_all_etf_holdings,
    fetch_etf_sector_summary,
    build_etf_email_section,
    ACTIVE_ETFS,
)
from realtime_data import get_realtime_quote, get_intraday_kline, validate_symbol
from chip_analysis import (
    get_twse_chip_distribution,
    get_major_trader_analysis,
    identify_major_institutions,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_BASE_DIR             = os.path.dirname(__file__)
_DATA_DIR             = os.getenv("DATA_DIR", _BASE_DIR)
os.makedirs(_DATA_DIR, exist_ok=True)

CUSTOM_STOCKS_FILE    = os.path.join(_DATA_DIR, "custom_stocks.json")
USER_WATCHLIST_FILE   = os.path.join(_DATA_DIR, "user_watchlist.json")
STATIC_DIR            = os.path.join(_BASE_DIR, "static")

# ─── In-memory caches ─────────────────────────────────────────────────────────
_daily_report: dict = {}
_stock_analyses: dict = {}
_etf_holdings: dict = {}          # populated by 15:00 scheduler job


def load_custom_stocks() -> list:
    if not os.path.exists(CUSTOM_STOCKS_FILE):
        return []
    try:
        with open(CUSTOM_STOCKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("stocks", [])
    except Exception:
        return []


def save_custom_stocks(stocks: list) -> None:
    with open(CUSTOM_STOCKS_FILE, "w", encoding="utf-8") as f:
        json.dump({"stocks": stocks}, f, ensure_ascii=False, indent=2)


def load_user_watchlist() -> dict:
    if not os.path.exists(USER_WATCHLIST_FILE):
        return {}
    try:
        with open(USER_WATCHLIST_FILE, encoding="utf-8") as f:
            return json.load(f).get("watchlist", {})
    except Exception:
        return {}


def save_user_watchlist(wl: dict) -> None:
    with open(USER_WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump({"watchlist": wl}, f, ensure_ascii=False, indent=2)


def _check_watchlist_depth(node, depth: int = 0) -> None:
    if depth > 5:
        raise HTTPException(status_code=400, detail="目錄最多5層")
    if isinstance(node, dict):
        for v in node.values():
            _check_watchlist_depth(v, depth + 1)
    elif isinstance(node, list):
        for item in node:
            if not isinstance(item, dict) or "symbol" not in item:
                raise HTTPException(status_code=400, detail="股票格式錯誤（需含 symbol 欄位）")


# ─── Cached GPT report ────────────────────────────────────────────────────────
_gpt_report_html: str = ""


def _run_daily_analysis():
    logger.info("Running scheduled daily analysis...")
    global _daily_report, _stock_analyses
    full_wl = dict(WATCHLIST)
    custom = load_custom_stocks()
    if custom:
        full_wl["自訂觀察清單"] = custom
    report = generate_daily_report(full_wl)
    try:
        report["trump_news"] = fetch_trump_news()
    except Exception as e:
        logger.warning("TrumpNews fetch failed during daily analysis: %s", e)
        report["trump_news"] = {}
    _daily_report = report
    _stock_analyses = report.get("all_results", {})
    logger.info(f"Daily analysis complete: {len(_stock_analyses)} stocks")


def _generate_and_deliver(trigger: str = "scheduler"):
    """Shared logic: GPT report → save PDF → send email with attachment."""
    global _gpt_report_html
    logger.info(f"Generating report (trigger={trigger})...")

    html = generate_gpt_report(
        _stock_analyses,
        market_sentiment=_daily_report.get("market_sentiment", "中性"),
        trump_news=_daily_report.get("trump_news"),
    )
    if html:
        _gpt_report_html = html
        logger.info("GPT report generated successfully")
    else:
        from email_sender import _build_fallback_html
        html = _build_fallback_html(_daily_report)
        _gpt_report_html = html
        logger.info("Using fallback HTML report (GPT not available)")

    # Append active ETF holdings section
    try:
        holdings = _etf_holdings if _etf_holdings else fetch_all_etf_holdings()
        if holdings:
            etf_section = build_etf_email_section(holdings)
            # Insert before closing </div> of content block (or just append)
            html = html + etf_section
    except Exception as e:
        logger.warning("ETF email section failed: %s", e)

    pdf_path = save_report_pdf(html, _daily_report)
    send_daily_report(html, _daily_report, pdf_path=pdf_path)


def _run_morning_email():
    """7 AM scheduled job: run full analysis → generate report → PDF → email."""
    logger.info("Running 7 AM morning report job...")
    _run_daily_analysis()
    _generate_and_deliver(trigger="scheduler")


def _refresh_news():
    logger.info("Refreshing news cache for all categories and TrumpNews...")
    fetch_all_news(force=True)
    fetch_trump_news(force=True)
    logger.info("News cache refresh complete.")


def _run_etf_holdings_refresh():
    """15:00 scheduler: fetch all active ETF portfolio disclosures from TWSE."""
    global _etf_holdings
    logger.info("Running 15:00 active ETF holdings refresh (%d ETFs)...", len(ACTIVE_ETFS))
    try:
        _etf_holdings = fetch_all_etf_holdings(force_refresh=True)
        ok  = sum(1 for v in _etf_holdings.values() if v.get("total_holdings", 0) > 0)
        err = sum(1 for v in _etf_holdings.values() if v.get("error"))
        logger.info("ETF holdings refresh done: %d OK, %d errors", ok, err)
        fetch_etf_sector_summary(force_refresh=True, holdings_refresh=False)
        logger.info("ETF sector summary snapshot refreshed.")
    except Exception as e:
        logger.error("ETF holdings refresh failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading
    report_hour   = int(os.getenv("REPORT_HOUR", "17"))
    report_minute = int(os.getenv("REPORT_MINUTE", "0"))

    scheduler = BackgroundScheduler(timezone="Asia/Taipei")
    # Taiwan close: Mon–Fri 13:40
    scheduler.add_job(_run_daily_analysis, "cron", day_of_week="mon-fri", hour=13, minute=40)
    # US close: Tue–Sat 05:10 (Taiwan time)
    scheduler.add_job(_run_daily_analysis, "cron", day_of_week="tue-sat", hour=5, minute=10)
    # Morning email: every day at configured time (default 07:00 Taiwan)
    scheduler.add_job(_run_morning_email, "cron",
                      day_of_week="mon-fri", hour=report_hour, minute=report_minute,
                      id="morning_email")
    # TrumpNews / news refresh every 5 hours.
    scheduler.add_job(_refresh_news, "interval", hours=5, id="news_refresh")
    # Active ETF holdings: Mon–Fri 15:00 (after TWSE close + disclosure window)
    scheduler.add_job(_run_etf_holdings_refresh, "cron",
                      day_of_week="mon-fri", hour=15, minute=0, id="etf_holdings")
    scheduler.start()
    logger.info(f"Scheduler started — morning email at {report_hour:02d}:{report_minute:02d} (Asia/Taipei)")

    # Background initial news fetch (only fills cache if missing/stale)
    threading.Thread(target=fetch_all_news, daemon=True).start()
    threading.Thread(target=fetch_trump_news, daemon=True).start()

    yield
    scheduler.shutdown()


# ─── Write-endpoint auth ──────────────────────────────────────────────────────
# POST/DELETE endpoints require  X-API-Secret: <value of API_SECRET in .env>
# GET endpoints are public — no token needed.
# Set API_SECRET in .env; if left empty, write endpoints are localhost-only.

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _require_report_auth(x_api_secret: str = Header(default="")):
    secret = os.getenv("API_SECRET_REPORT", "").strip()
    if not secret:
        return
    if x_api_secret != _sha256(secret):
        raise HTTPException(status_code=401, detail="報告密鑰錯誤")


def _require_stock_auth(x_api_secret: str = Header(default="")):
    secret = os.getenv("API_SECRET_STOCK", "").strip()
    if not secret:
        return
    if x_api_secret != _sha256(secret):
        raise HTTPException(status_code=401, detail="股票管理密鑰錯誤")


def _get_real_ip(request: Request) -> str:
    """Return the real client IP, respecting Cloudflare and reverse-proxy headers."""
    for header in ("CF-Connecting-IP", "X-Real-IP"):
        val = request.headers.get(header, "").strip()
        if val:
            return val
    forwarded = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _lookup_geo(ip: str) -> dict:
    import requests as _req
    try:
        r = _req.get(
            f"https://ip-api.com/json/{ip}",
            params={"fields": "status,country,regionName,city,lat,lon,isp"},
            timeout=6,
        )
        data = r.json()
        if data.get("status") == "success":
            return data
    except Exception as e:
        logger.warning("Geo lookup failed for %s: %s", ip, e)
    return {}


app = FastAPI(title="Stock Monitor API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Auth ping (login notification) ──────────────────────────────────────────

@app.post("/api/auth/ping")
async def auth_ping(request: Request, x_api_secret: str = Header(default="")):
    """
    Verify a key and fire a login-notification email.
    Returns {"verified": true/false} immediately; email is sent in background.
    """
    report_secret = os.getenv("API_SECRET_REPORT", "").strip()
    stock_secret  = os.getenv("API_SECRET_STOCK", "").strip()

    key_type: str | None = None
    if report_secret and x_api_secret == _sha256(report_secret):
        key_type = "report"
    elif stock_secret and x_api_secret == _sha256(stock_secret):
        key_type = "stock"

    if not key_type:
        return {"verified": False}

    real_ip = _get_real_ip(request)

    def _notify():
        geo = _lookup_geo(real_ip)
        send_login_notification(real_ip, key_type, geo)

    import threading
    threading.Thread(target=_notify, daemon=True).start()

    return {"verified": True, "key_type": key_type}


# ─── Watchlist ────────────────────────────────────────────────────────────────

@app.get("/api/watchlist")
def get_watchlist():
    cats = dict(WATCHLIST)
    user_wl = load_user_watchlist()
    cats.update(user_wl)           # user categories merge on top of built-ins
    custom = load_custom_stocks()
    if custom:
        cats["自訂觀察清單"] = custom  # individual custom stocks always at end
    return {"categories": cats}


# ─── User watchlist (editable categories) ─────────────────────────────────────

class UserWatchlistBody(BaseModel):
    watchlist: dict

@app.get("/api/user-watchlist")
def get_user_watchlist():
    return {"watchlist": load_user_watchlist()}

@app.put("/api/user-watchlist", dependencies=[Depends(_require_stock_auth)])
def put_user_watchlist(body: UserWatchlistBody):
    _check_watchlist_depth(body.watchlist)
    save_user_watchlist(body.watchlist)
    return {"status": "ok"}


# ─── Custom stocks ────────────────────────────────────────────────────────────

class StockItem(BaseModel):
    symbol: str
    name: str

@app.get("/api/custom-stocks")
def get_custom_stocks():
    return {"stocks": load_custom_stocks()}

@app.post("/api/custom-stocks", dependencies=[Depends(_require_stock_auth)])
def add_custom_stock(item: StockItem):
    """
    Add a custom stock with validation.
    Returns detailed validation result or error information.
    """
    stocks = load_custom_stocks()
    symbol = item.symbol.strip().upper()
    
    # Check for duplicates
    if any(s["symbol"] == symbol for s in stocks):
        raise HTTPException(status_code=400, detail="股票代號已存在")
    
    # Validate symbol format and data availability
    logger.info(f"Validating custom stock: {symbol}")
    validation = validate_symbol(symbol)
    
    if not validation.get("valid"):
        raise HTTPException(
            status_code=400,
            detail=validation.get("error", "Invalid stock symbol"),
        )
    
    # Symbol is valid, add to list
    stocks.append({
        "symbol": symbol,
        "name": item.name.strip() or symbol,
        "added_at": datetime.now().isoformat(),
        "price": validation.get("price"),
        "timestamp": validation.get("timestamp"),
    })
    save_custom_stocks(stocks)
    logger.info(f"Custom stock added: {symbol}")
    
    return {
        "status": "ok",
        "stocks": stocks,
        "validation": validation
    }

@app.delete("/api/custom-stocks/{symbol}", dependencies=[Depends(_require_stock_auth)])
def delete_custom_stock(symbol: str):
    stocks = load_custom_stocks()
    original_len = len(stocks)
    stocks = [s for s in stocks if s["symbol"] != symbol.upper()]
    if len(stocks) == original_len:
        raise HTTPException(status_code=404, detail="找不到該股票")
    save_custom_stocks(stocks)
    return {"status": "ok", "stocks": stocks}


# ─── K-line data + indicators ─────────────────────────────────────────────────

@app.get("/api/stocks/{symbol}/kline")
def get_kline(
    symbol: str,
    interval: str = Query("1d", pattern="^(1d|1wk|1mo)$"),
    refresh: bool = Query(False),
):
    df = get_ohlcv(symbol, interval=interval, force_refresh=refresh)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    mas = calculate_ma(df, [5, 10, 20, 60, 120, 240])
    bb = calculate_bollinger_bands(df)
    rsi_s = calculate_rsi(df)
    kd = calculate_kd(df)
    obv_s = calculate_obv(df)

    dates = df.index
    return {
        "symbol": symbol,
        "interval": interval,
        "data": df_to_ohlcv_list(df),
        "indicators": {
            "MA5":       series_to_list(mas["MA5"], dates),
            "MA10":      series_to_list(mas["MA10"], dates),
            "MA20":      series_to_list(mas["MA20"], dates),
            "MA60":      series_to_list(mas["MA60"], dates),
            "MA120":     series_to_list(mas["MA120"], dates),
            "MA240":     series_to_list(mas["MA240"], dates),
            "BB_upper":  series_to_list(bb["BB_upper"], dates),
            "BB_middle": series_to_list(bb["BB_middle"], dates),
            "BB_lower":  series_to_list(bb["BB_lower"], dates),
            "RSI":       series_to_list(rsi_s, dates),
            "K":         series_to_list(kd["K"], dates),
            "D":         series_to_list(kd["D"], dates),
            "OBV":       series_to_list(obv_s, dates),
        },
    }


# ─── Quote ────────────────────────────────────────────────────────────────────

@app.get("/api/stocks/{symbol}/quote")
def get_stock_quote(symbol: str):
    return get_quote(symbol)


# ─── Investor / institutional data ────────────────────────────────────────────

@app.get("/api/stocks/{symbol}/investors")
def get_stock_investors(symbol: str):
    return get_investors_data(symbol)


# ─── Margin trading (融資融券) ───────────────────────────────────────────────

@app.get("/api/stocks/{symbol}/margin")
def get_stock_margin(symbol: str):
    """Get 融資融券 (margin/short-sell balance) for Taiwan stocks — last 5 trading days."""
    upper = symbol.upper()
    if not (upper.endswith(".TW") or upper.endswith(".TWO")):
        raise HTTPException(status_code=400, detail="融資融券 only available for Taiwan stocks (.TW / .TWO)")
    return get_tw_margin_data(symbol)


# ─── Active ETF holdings ─────────────────────────────────────────────────────

@app.get("/api/etf-holdings")
def get_all_etf_holdings(refresh: bool = False):
    """Return cached holdings for all active ETFs. Pass ?refresh=true to force re-fetch."""
    global _etf_holdings
    if refresh or not _etf_holdings:
        _etf_holdings = fetch_all_etf_holdings(force_refresh=refresh)
    return _etf_holdings


@app.get("/api/etf-holdings/sector-summary")
def get_etf_sector_summary(refresh: bool = False, holdings_refresh: bool = False):
    """Return sector-level active ETF summary with frontend pie-chart geometry."""
    return fetch_etf_sector_summary(force_refresh=refresh, holdings_refresh=holdings_refresh)


@app.get("/api/etf-holdings/{symbol}")
def get_single_etf_holdings(symbol: str, refresh: bool = False):
    """Return holdings for one active ETF (e.g. 00980A or 00980A.TW)."""
    code = symbol.upper().replace(".TW", "")
    if code not in ACTIVE_ETFS:
        raise HTTPException(status_code=404, detail=f"{symbol} 不在主動式ETF清單中")
    return fetch_etf_holdings(code, force_refresh=refresh)


# ─── Real-time quote (for intraday updates) ──────────────────────────────────

@app.get("/api/stocks/{symbol}/realtime")
def get_stock_realtime(symbol: str):
    """Get real-time price quote with minimal delay (30 seconds cache)."""
    try:
        return get_realtime_quote(symbol)
    except Exception as e:
        logger.warning(f"Realtime quote fetch failed for {symbol}: {e}")
        raise HTTPException(status_code=503, detail="Unable to fetch real-time data")


# ─── Intraday K-line (for intraday trading) ──────────────────────────────────

@app.get("/api/stocks/{symbol}/intraday-kline")
def get_stock_intraday_kline(
    symbol: str,
    interval: int = Query(1, ge=1, le=60),  # 1, 5, 15, 30, 60 minutes
):
    """Get intraday K-line bars with minimal delay for active trading."""
    try:
        klines = get_intraday_kline(symbol, interval=interval)
        
        if not klines:
            raise HTTPException(status_code=404, detail=f"No intraday data for {symbol}")
        
        return {
            "symbol": symbol,
            "interval": f"{interval}m",
            "timestamp": datetime.now().isoformat(),
            "data": klines,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Intraday kline fetch failed for {symbol}: {e}")
        raise HTTPException(status_code=503, detail="Unable to fetch intraday data")


# ─── Chip/Major Shareholder Analysis ─────────────────────────────────────────

@app.get("/api/stocks/{symbol}/chip-analysis")
def get_stock_chip_analysis(symbol: str):
    """
    Analyze institutional holdings, major shareholders, and concentration.
    Includes chip distribution and institutional breakdown.
    """
    try:
        chip_data = get_twse_chip_distribution(symbol)
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "chip_distribution": chip_data,
        }
    except Exception as e:
        logger.warning(f"Chip analysis fetch failed for {symbol}: {e}")
        raise HTTPException(status_code=503, detail="Unable to fetch chip analysis data")


# ─── Major Traders (institutional activity pattern analysis) ────────────────

@app.get("/api/stocks/{symbol}/major-traders")
def get_stock_major_traders(symbol: str):
    """
    Analyze major institutional trading activity and patterns.
    Identifies high-volume trading days and trends.
    """
    try:
        trader_data = get_major_trader_analysis(symbol)
        
        if "error" in trader_data:
            raise HTTPException(status_code=404, detail=trader_data["error"])
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "major_traders": trader_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Major traders analysis failed for {symbol}: {e}")
        raise HTTPException(status_code=503, detail="Unable to fetch major traders data")


# ─── Institution Identification (with ML/pattern matching) ──────────────────

@app.get("/api/stocks/{symbol}/institutions")
def get_stock_institutions(symbol: str):
    """
    Identify specific major institutions involved in recent trading.
    Combines 三大法人 data with holdings and patterns to pinpoint institutions.
    """
    try:
        # First get 三大法人 data
        investors_data = get_investors_data(symbol)
        
        if "error" in investors_data:
            return {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "institutions": {},
                "error": investors_data.get("error"),
            }
        
        # Identify specific institutions
        institutions = identify_major_institutions(symbol, investors_data)
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "three_forces": investors_data,
            "institutions": institutions,
            "summary": {
                "likely_buyers": [inst["type"] for inst in institutions.get("likely_buyers", [])],
                "likely_sellers": [inst["type"] for inst in institutions.get("likely_sellers", [])],
                "sentiment": institutions.get("trend_summary", {}).get("sentiment", "未知"),
            }
        }
    except Exception as e:
        logger.warning(f"Institution identification failed for {symbol}: {e}")
        raise HTTPException(status_code=503, detail="Unable to identify institutions")


# ─── Analysis ─────────────────────────────────────────────────────────────────

@app.get("/api/stocks/{symbol}/analysis")
def get_stock_analysis(symbol: str, name: Optional[str] = ""):
    if symbol in _stock_analyses:
        return _stock_analyses[symbol]
    result = analyze_stock(symbol, name or "")
    _stock_analyses[symbol] = result
    return result


# ─── Market overview ──────────────────────────────────────────────────────────

@app.get("/api/market/overview")
def get_market_overview():
    results = []
    for idx in MARKET_INDICES:
        q = get_quote(idx["symbol"])
        results.append({"symbol": idx["symbol"], "name": idx["name"], "name_en": idx["name_en"], **q})
    return {"indices": results}


# ─── Daily report ─────────────────────────────────────────────────────────────

@app.get("/api/analysis/daily-report")
def get_daily_report():
    if not _daily_report:
        raise HTTPException(status_code=404, detail="尚無分析報告，請先觸發生成")
    return _daily_report


@app.post("/api/analysis/generate", dependencies=[Depends(_require_report_auth)])
def trigger_analysis():
    _run_daily_analysis()
    return {"status": "ok", "message": f"已分析 {len(_stock_analyses)} 支股票"}


@app.post("/api/analysis/gpt-report", dependencies=[Depends(_require_report_auth)])
def trigger_gpt_report():
    """Manually trigger GPT report → save PDF locally → send email with PDF attachment."""
    if not _daily_report:
        _run_daily_analysis()
    if not _daily_report.get("trump_news"):
        _daily_report["trump_news"] = fetch_trump_news()

    html = generate_gpt_report(
        _stock_analyses,
        market_sentiment=_daily_report.get("market_sentiment", "中性"),
        trump_news=_daily_report.get("trump_news"),
    )
    status = "ok"
    if not html:
        from email_sender import _build_fallback_html
        html = _build_fallback_html(_daily_report)
        status = "fallback"

    global _gpt_report_html
    _gpt_report_html = html

    pdf_path = save_report_pdf(html, _daily_report)
    ok = send_daily_report(html, _daily_report, pdf_path=pdf_path)

    return {
        "status": status,
        "email_sent": ok,
        "pdf_saved": pdf_path,
        "html_length": len(html),
    }


@app.get("/api/analysis/gpt-report")
def get_gpt_report():
    if not _gpt_report_html:
        raise HTTPException(status_code=404, detail="尚無GPT報告，請先觸發生成")
    return {"html": _gpt_report_html}


@app.get("/api/health")
def health():
    report_hour   = int(os.getenv("REPORT_HOUR", "17"))
    report_minute = int(os.getenv("REPORT_MINUTE", "0"))
    return {
        "status": "ok",
        "stocks_analyzed": len(_stock_analyses),
        "email_schedule": f"{report_hour:02d}:{report_minute:02d} Asia/Taipei (Mon-Fri)",
        "news_refresh_schedule": "every 5 hours",
        "trump_news_last_updated": get_trump_last_updated(),
    }


@app.post("/api/test/email", dependencies=[Depends(_require_report_auth)])
def test_email(to: Optional[str] = Query(None)):
    """Send a minimal test email and return SMTP diagnostic info."""
    result = send_test_email(to)
    return result


@app.get("/api/test/quotes")
def test_quotes(symbols: str = Query(..., description="逗號分隔代號，如 5347.TW,5274.TW")):
    """
    Batch quote test — calls the real get_quote() for each symbol.
    Shows price if successful, or the source that was tried.
    No auth needed.
    """
    import requests as _req
    from stock_data import get_quote, _get_tw_mis_quote

    results = {}
    for raw in symbols.split(","):
        s = raw.strip()
        if not s:
            continue

        # Test MIS directly so we can see its raw response
        mis_detail = "N/A"
        if s.upper().endswith(".TW") or s.upper().endswith(".TWO"):
            raw_code = s.split(".")[0]
            for ex in ["tse", "otc"]:
                try:
                    r = _req.get(
                        "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
                        params={"ex_ch": f"{ex}_{raw_code}.tw", "json": "1", "delay": "0"},
                        headers={"User-Agent": "Mozilla/5.0",
                                 "Referer": "https://mis.twse.com.tw/"},
                        timeout=8, verify=False,
                    )
                    items = r.json().get("msgArray", [])
                    if items:
                        item = items[0]
                        z = item.get("z", "-")
                        y = item.get("y", "-")
                        mis_detail = f"✅ {ex}: z={z} y={y}"
                        break
                    else:
                        mis_detail = f"❌ {ex}: msgArray empty"
                except Exception as e:
                    mis_detail = f"❌ {ex}: {e}"

        # Call the real get_quote
        try:
            q = get_quote(s)
            results[s] = {
                "quote": q if q else "❌ 無資料",
                "mis_probe": mis_detail,
            }
        except Exception as e:
            results[s] = {"quote": f"❌ exception: {e}", "mis_probe": mis_detail}

    return results


@app.get("/api/test/env", dependencies=[Depends(_require_report_auth)])
def test_env():
    """Return which expected env vars are present (values masked) for diagnosis."""
    keys = [
        "GMAIL_SENDER", "GMAIL_APP_PASSWORD",
        "REPORT_RECIPIENT", "REPORT_RECIPIENT_2",
        "OPENAI_API_KEY", "REPORT_HOUR", "REPORT_MINUTE",
        "API_SECRET_REPORT", "API_SECRET_STOCK", "DATA_DIR",
        "TRUMP_X_BEARER_TOKEN", "TRUMP_X_USER_ID", "TRUMP_X_RSS_URL",
    ]
    result = {}
    for k in keys:
        val = os.getenv(k, "")
        if not val:
            result[k] = "❌ 未設定"
        elif k in ("GMAIL_APP_PASSWORD", "OPENAI_API_KEY", "API_SECRET_REPORT", "API_SECRET_STOCK", "TRUMP_X_BEARER_TOKEN"):
            result[k] = f"✅ 已設定 ({len(val)} chars)"
        else:
            result[k] = f"✅ {val}"
    return result


# ─── News ─────────────────────────────────────────────────────────────────────

@app.get("/api/news")
def get_news(
    category: Optional[str] = Query(None),
    force: bool = Query(False),
):
    """
    GET /api/news               → all categories with their articles
    GET /api/news?category=IC設計 → single category
    GET /api/news?force=true    → bypass cache and re-fetch
    """
    if category:
        if category not in NEWS_CATEGORIES:
            raise HTTPException(status_code=404, detail=f"Unknown category: {category}")
        articles = fetch_category_news(category, force=force)
        return {
            "categories": [category],
            "news": {category: articles},
            "last_updated": get_last_updated(),
        }
    news = {}
    for cat in NEWS_CATEGORIES:
        news[cat] = fetch_category_news(cat, force=force)
    return {
        "categories": list(NEWS_CATEGORIES.keys()),
        "news": news,
        "last_updated": get_last_updated(),
    }


@app.get("/api/trump-news")
def get_trump_news(force: bool = Query(False)):
    """
    GET /api/trump-news              → Trump-related English news, X, Truth Social, White House updates
    GET /api/trump-news?force=true   → bypass cache and re-fetch
    """
    return fetch_trump_news(force=force)


# ─── PDF report download ──────────────────────────────────────────────────────

@app.get("/api/analysis/download-report")
def download_latest_pdf():
    path = latest_report_path()
    if not path:
        raise HTTPException(status_code=404, detail="尚無PDF報告，請先觸發生成")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=os.path.basename(path),
    )


# ─── Serve React SPA (MUST be last) ──────────────────────────────────────────
os.makedirs(STATIC_DIR, exist_ok=True)
if os.path.exists(os.path.join(STATIC_DIR, "index.html")):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
else:
    logger.warning("Static build not found. Run: cd frontend && npm run build")
