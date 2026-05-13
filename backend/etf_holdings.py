"""
Active ETF holdings fetcher for Taiwan exchange-listed active ETFs (主動式ETF).
TWSE requires daily portfolio disclosure per exchange rules.

Fetch flow:
  1. Cache hit (< 4 h)
  2. TWSE portfolioData API  →  structured holdings list
  3. Fallback: TWSE etfDailyInfo (basic NAV / count only)
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

HOLDINGS_CACHE_TTL = 4 * 3600   # 4 hours
ALL_CACHE_TTL      = 3 * 3600   # 3 hours (for the combined snapshot)

# ── Master list of Taiwan active ETFs ────────────────────────────────────────
ACTIVE_ETFS: dict[str, str] = {
    # Stock-type (A)
    "00980A": "主動野村台灣優選",
    "00981A": "主動統一台股增長",
    "00982A": "主動群益台灣強棒",
    "00983A": "主動中信ARK創新",
    "00984A": "主動安聯台灣高息",
    "00985A": "主動野村台灣50",
    "00986A": "主動台新龍頭成長",
    "00987A": "主動台新優勢成長",
    "00988A": "主動統一全球創新",
    "00989A": "主動摩根美國科技",
    "00990A": "主動元大AI新經濟",
    "00991A": "主動復華未來50",
    "00992A": "主動群益科技創新",
    "00993A": "主動安聯台灣",
    "00994A": "主動第一金台股優",
    "00995A": "主動中信台灣卓越",
    "00996A": "主動兆豐台灣豐收",
    "00997A": "主動群益美國增長",
    "00998A": "主動復華金融股息",
    "00999A": "主動野村台灣高息",
    "00400A": "主動國泰動能高息",
    "00401A": "主動摩根台灣鑫收",
    "00403A": "主動統一升級50",
    # Bond-type (D)
    "00980D": "主動聯博投等入息",
    "00981D": "主動中信非投等債",
    "00982D": "主動富邦動態入息",
    "00983D": "主動富邦複合收益",
    "00984D": "主動聯博全球非投",
    "00985D": "主動貝萊德投等債",
    "00986D": "主動復華金融債息",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.twse.com.tw/",
    "Accept-Language": "zh-TW,zh;q=0.9",
}


def _recent_trading_date() -> str:
    """Return the most recent weekday as YYYYMMDD."""
    d = datetime.now()
    # If today is weekend go back to Friday
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


def _parse_number(v: str) -> float | None:
    """Parse number strings that may contain commas."""
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


# ── Primary: TWSE portfolioData API ──────────────────────────────────────────
def _fetch_twse_portfolio(etf_code: str, date_str: str) -> list[dict]:
    """
    Returns list of holding dicts:
        {stock_code, stock_name, shares, weight_pct}
    Empty list on failure.
    """
    url = "https://www.twse.com.tw/rwd/zh/ETF/portfolioData"
    params = {"date": date_str, "stockNo": etf_code, "response": "json"}
    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=15, verify=False)
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        logger.warning("TWSE portfolioData failed %s %s: %s", etf_code, date_str, e)
        return []

    if raw.get("stat") != "OK":
        # Try yesterday if today's data not yet available
        return []

    fields = raw.get("fields", [])
    data   = raw.get("data", [])
    if not data:
        return []

    # Detect column indices by field name keywords
    def col(kw: str) -> int:
        for i, f in enumerate(fields):
            if kw in str(f):
                return i
        return -1

    idx_code   = col("代號")
    idx_name   = col("名稱")
    idx_shares = col("股數") if col("股數") >= 0 else col("持有")
    idx_weight = col("比重") if col("比重") >= 0 else col("淨資產")

    holdings = []
    for row in data:
        try:
            code   = str(row[idx_code]).strip()   if idx_code   >= 0 else ""
            name   = str(row[idx_name]).strip()   if idx_name   >= 0 else ""
            shares = _parse_number(row[idx_shares]) if idx_shares >= 0 else None
            weight = _parse_number(row[idx_weight]) if idx_weight >= 0 else None
            if code:
                holdings.append({
                    "stock_code": code,
                    "stock_name": name,
                    "shares":     int(shares) if shares is not None else None,
                    "weight_pct": round(weight, 4) if weight is not None else None,
                })
        except (IndexError, ValueError):
            continue

    return holdings


# ── Fallback: try the previous trading day ───────────────────────────────────
def _fetch_with_retry(etf_code: str) -> tuple[list[dict], str]:
    """Try today, then go back up to 5 trading days."""
    d = datetime.now()
    attempts = 0
    while attempts < 7:
        if d.weekday() < 5:
            date_str = d.strftime("%Y%m%d")
            holdings = _fetch_twse_portfolio(etf_code, date_str)
            if holdings:
                return holdings, date_str
            attempts += 1
        d -= timedelta(days=1)
    return [], ""


# ── Main public interface ─────────────────────────────────────────────────────
def fetch_etf_holdings(etf_code: str, force_refresh: bool = False) -> dict:
    """
    Fetch portfolio holdings for one active ETF.

    Returns:
        {code, name, type, date, holdings: [{stock_code, stock_name, shares, weight_pct}],
         top10_weight, total_holdings, fetched_at, error?}
    """
    code_upper = etf_code.upper().replace(".TW", "")
    cache_path = os.path.join(CACHE_DIR, f"etf_holdings_{code_upper}.json")

    if not force_refresh and os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < HOLDINGS_CACHE_TTL:
            try:
                with open(cache_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    name = ACTIVE_ETFS.get(code_upper, code_upper)
    etf_type = "bond" if code_upper.endswith("D") else "stock"

    holdings, date_str = _fetch_with_retry(code_upper)

    if not holdings:
        result = {
            "code":           code_upper,
            "name":           name,
            "type":           etf_type,
            "date":           _recent_trading_date(),
            "holdings":       [],
            "top10_weight":   None,
            "total_holdings": 0,
            "fetched_at":     datetime.now().isoformat(),
            "error":          "無法取得投資組合（非交易日或資料尚未更新）",
        }
    else:
        # Sort by weight desc
        holdings_sorted = sorted(
            [h for h in holdings if h.get("weight_pct") is not None],
            key=lambda x: x["weight_pct"],
            reverse=True,
        )
        # Add unweighted rows at end
        holdings_no_w = [h for h in holdings if h.get("weight_pct") is None]
        all_holdings = holdings_sorted + holdings_no_w

        top10_w = sum(h["weight_pct"] for h in holdings_sorted[:10] if h["weight_pct"])

        result = {
            "code":           code_upper,
            "name":           name,
            "type":           etf_type,
            "date":           date_str,
            "holdings":       all_holdings,
            "top10_weight":   round(top10_w, 2) if top10_w else None,
            "total_holdings": len(all_holdings),
            "fetched_at":     datetime.now().isoformat(),
        }

    # Persist cache
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
    except Exception:
        pass

    return result


def fetch_all_etf_holdings(force_refresh: bool = False) -> dict[str, dict]:
    """
    Fetch holdings for every active ETF in ACTIVE_ETFS.
    Returns {etf_code: holdings_dict}.
    """
    all_cache = os.path.join(CACHE_DIR, "etf_holdings_ALL.json")
    if not force_refresh and os.path.exists(all_cache):
        age = time.time() - os.path.getmtime(all_cache)
        if age < ALL_CACHE_TTL:
            try:
                with open(all_cache, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    logger.info("Fetching all active ETF holdings (%d ETFs)...", len(ACTIVE_ETFS))
    results: dict[str, dict] = {}
    for code in ACTIVE_ETFS:
        try:
            results[code] = fetch_etf_holdings(code, force_refresh=force_refresh)
            logger.info("  %s: %d holdings", code,
                        results[code].get("total_holdings", 0))
        except Exception as e:
            logger.warning("  %s fetch error: %s", code, e)
            results[code] = {
                "code": code, "name": ACTIVE_ETFS[code],
                "holdings": [], "total_holdings": 0,
                "error": str(e),
            }
        time.sleep(0.5)   # be polite to TWSE

    try:
        with open(all_cache, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False)
    except Exception:
        pass

    logger.info("Active ETF holdings refresh complete.")
    return results


def build_etf_email_section(all_holdings: dict[str, dict]) -> str:
    """
    Generate an HTML section for the daily email report
    summarising each active ETF's top holdings.
    """
    from html import escape

    stock_etfs = {k: v for k, v in all_holdings.items() if not k.endswith("D")}
    bond_etfs  = {k: v for k, v in all_holdings.items() if k.endswith("D")}

    def etf_block(code: str, info: dict) -> str:
        name  = escape(info.get("name", code))
        date  = escape(info.get("date", ""))
        total = info.get("total_holdings", 0)
        top10 = info.get("top10_weight")
        error = info.get("error")

        if error or not info.get("holdings"):
            return (
                f"<tr><td style='padding:4px 8px'><strong>{name}</strong> "
                f"<span style='color:#888;font-size:11px'>{code}</span></td>"
                f"<td colspan='3' style='padding:4px 8px;color:#888;font-size:12px'>"
                f"{escape(error or '無資料')}</td></tr>"
            )

        top5 = info["holdings"][:5]
        top5_html = ", ".join(
            f"<span style='color:#40C4FF'>{escape(h['stock_code'])}</span>"
            f" {escape(h['stock_name'])}"
            + (f" <span style='color:#FFA726'>{h['weight_pct']}%</span>" if h.get("weight_pct") else "")
            for h in top5
        )

        return (
            f"<tr>"
            f"<td style='padding:4px 8px;white-space:nowrap'>"
            f"<strong>{name}</strong>"
            f"<span style='color:#888;font-size:10px;margin-left:4px'>{code}</span></td>"
            f"<td style='padding:4px 8px;font-size:11px;color:#888'>{date}</td>"
            f"<td style='padding:4px 8px;font-size:11px'>{total} 檔</td>"
            f"<td style='padding:4px 8px;font-size:11px'>"
            f"Top10占比 <strong style='color:#FFA726'>"
            f"{f'{top10}%' if top10 else '—'}</strong><br>"
            f"<span style='font-size:10px;color:#aaa'>{top5_html}</span></td>"
            f"</tr>"
        )

    def section_table(title: str, etfs: dict) -> str:
        if not etfs:
            return ""
        rows = "".join(etf_block(c, v) for c, v in etfs.items())
        return f"""
<h3 style="color:#7AB8FF;margin-top:18px">{escape(title)}</h3>
<table style="border-collapse:collapse;width:100%;font-size:13px">
<tr style="background:#0A1A2A;color:#888;font-size:11px">
  <th style="padding:4px 8px;text-align:left">ETF</th>
  <th style="padding:4px 8px;text-align:left">日期</th>
  <th style="padding:4px 8px;text-align:left">持股數</th>
  <th style="padding:4px 8px;text-align:left">前5大持股</th>
</tr>
{rows}
</table>"""

    return (
        "<h2 style='color:#40C4FF;border-bottom:1px solid #1A2A3A;padding-bottom:6px'>"
        "🏦 主動式ETF 投資組合摘要</h2>"
        + section_table("股票型主動ETF (A類)", stock_etfs)
        + section_table("債券型主動ETF (D類)", bond_etfs)
    )
