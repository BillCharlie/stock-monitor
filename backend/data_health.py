"""
Scheduled data-health checks for Stock Monitor.

The report intentionally avoids dumping raw market values.  It only answers:
which module was checked, when the backend data was last updated, and whether
the expected payload fields are present.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from analysis import analyze_stock
from email_sender import send_data_health_report
from etf_holdings import ACTIVE_ETFS, fetch_all_etf_holdings, fetch_etf_sector_summary
from news_fetcher import fetch_all_news, get_last_updated
from stock_data import get_investors_data, get_ohlcv, get_ohlcv_last_updated, get_quote
from trump_news_fetcher import fetch_trump_news, get_trump_last_updated
from watchlist import MARKET_INDICES, WATCHLIST

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent)))
REPORTS_DIR = DATA_DIR / "reports"
CUSTOM_STOCKS_FILE = DATA_DIR / "custom_stocks.json"
USER_WATCHLIST_FILE = DATA_DIR / "user_watchlist.json"
LATEST_STATUS_FILE = REPORTS_DIR / "data_health_latest.json"

DEFAULT_STALE_HOURS = int(os.getenv("DATA_HEALTH_STALE_HOURS", "30"))
MAX_ISSUES_IN_REPORT = int(os.getenv("DATA_HEALTH_MAX_ISSUES", "120"))

STATUS_RANK = {"ok": 0, "unknown": 1, "warn": 2, "error": 3}
STATUS_LABEL = {
    "ok": "正常",
    "unknown": "未知",
    "warn": "警告",
    "error": "異常",
}


def _server_time_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("T", " ").replace("Z", "")
    text = re.sub(r"\.\d+", "", text)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19 if " " in fmt else 10], fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _latest_text(current: str | None, candidate: str | None) -> str:
    if not candidate:
        return current or ""
    if not current:
        return candidate
    current_dt = _parse_dt(current)
    candidate_dt = _parse_dt(candidate)
    if not current_dt:
        return candidate
    if not candidate_dt:
        return current
    return candidate if candidate_dt > current_dt else current


def _freshness_status(last_updated: str | None, stale_hours: int = DEFAULT_STALE_HOURS) -> tuple[str, str]:
    dt = _parse_dt(last_updated)
    if not dt:
        return "unknown", "沒有取得後端更新時間"
    age_hours = (datetime.now() - dt).total_seconds() / 3600
    if age_hours > stale_hours:
        return "warn", f"更新時間超過 {stale_hours} 小時"
    return "ok", ""


def _worst(*statuses: str) -> str:
    return max((s for s in statuses if s), key=lambda s: STATUS_RANK.get(s, 0), default="ok")


def _new_check(module: str) -> dict:
    return {
        "module": module,
        "status": "ok",
        "checked": 0,
        "ok": 0,
        "warn": 0,
        "error": 0,
        "unknown": 0,
        "last_updated": "",
        "notes": [],
    }


def _record(check: dict, status: str, item: str = "", reason: str = "",
            last_updated: str | None = None, issues: list[dict] | None = None) -> None:
    status = status if status in STATUS_RANK else "unknown"
    check["checked"] += 1
    check[status] += 1
    check["status"] = _worst(check["status"], status)
    check["last_updated"] = _latest_text(check.get("last_updated"), last_updated)
    if reason and reason not in check["notes"] and len(check["notes"]) < 6:
        check["notes"].append(reason)
    if issues is not None and status in ("warn", "error", "unknown"):
        issues.append({
            "module": check["module"],
            "status": status,
            "item": item,
            "reason": reason or STATUS_LABEL.get(status, status),
            "last_updated": last_updated or "",
        })


def _iter_stock_items(node: Any):
    if isinstance(node, dict):
        if isinstance(node.get("symbol"), str):
            yield node
            return
        for value in node.values():
            yield from _iter_stock_items(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_stock_items(item)


def _load_json(path: Path) -> Any:
    try:
        if path.exists():
            with path.open(encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
    return None


def _collect_stocks() -> list[dict]:
    full_watchlist: dict = dict(WATCHLIST)
    user_watchlist = _load_json(USER_WATCHLIST_FILE)
    if isinstance(user_watchlist, dict) and isinstance(user_watchlist.get("watchlist"), dict):
        full_watchlist.update(user_watchlist["watchlist"])

    custom = _load_json(CUSTOM_STOCKS_FILE)
    if isinstance(custom, dict) and isinstance(custom.get("stocks"), list):
        full_watchlist["自訂觀察清單"] = custom["stocks"]

    seen: set[str] = set()
    stocks: list[dict] = []
    for item in _iter_stock_items(full_watchlist):
        symbol = str(item.get("symbol", "")).strip()
        key = symbol.upper()
        if not symbol or key in seen:
            continue
        seen.add(key)
        stocks.append({
            "symbol": symbol,
            "name": item.get("name") or item.get("name_en") or symbol,
        })

    max_symbols = int(os.getenv("DATA_HEALTH_MAX_SYMBOLS", "0") or 0)
    if max_symbols > 0:
        return stocks[:max_symbols]
    return stocks


def _is_tw_symbol(symbol: str) -> bool:
    return symbol.upper().endswith((".TW", ".TWO"))


def _missing_required(data: dict, keys: list[str]) -> list[str]:
    return [key for key in keys if data.get(key) in (None, "", [])]


def _check_market_overview(issues: list[dict]) -> dict:
    check = _new_check("市場總覽/即時報價")
    for idx in MARKET_INDICES:
        symbol = idx.get("symbol", "")
        try:
            quote = get_quote(symbol)
            last_updated = quote.get("last_updated") if isinstance(quote, dict) else ""
            if not quote or quote.get("price") is None:
                _record(check, "error", symbol, "沒有抓到報價資料", last_updated, issues)
                continue
            freshness, note = _freshness_status(last_updated)
            _record(check, freshness, symbol, note, last_updated, issues)
        except Exception as e:
            _record(check, "error", symbol, f"檢查失敗：{e}", issues=issues)
    return check


def _check_stock_modules(issues: list[dict]) -> tuple[list[dict], dict]:
    stocks = _collect_stocks()
    kline_check = _new_check("K線/股價資料")
    analysis_check = _new_check("個股分析")
    investor_check = _new_check("主力動向/法人資料")
    margin_check = _new_check("融資融券")

    for stock in stocks:
        symbol = stock["symbol"]
        name = stock.get("name") or symbol

        try:
            df = get_ohlcv(symbol, "1d", force_refresh=False)
            last_updated = get_ohlcv_last_updated(symbol, "1d")
            if df is None or df.empty:
                _record(kline_check, "error", symbol, "K線資料為空", last_updated, issues)
            elif len(df) < 20:
                _record(kline_check, "warn", symbol, "K線筆數不足，技術指標可能不完整", last_updated, issues)
            else:
                freshness, note = _freshness_status(last_updated)
                _record(kline_check, freshness, symbol, note, last_updated, issues)
        except Exception as e:
            _record(kline_check, "error", symbol, f"K線檢查失敗：{e}", issues=issues)

        try:
            result = analyze_stock(symbol, name)
            last_updated = result.get("last_updated") if isinstance(result, dict) else ""
            if not isinstance(result, dict) or result.get("error"):
                _record(analysis_check, "error", symbol, "個股分析沒有產出完整結果", last_updated, issues)
            else:
                missing = _missing_required(result, ["price", "score", "rating_key", "date", "signals", "indicators"])
                indicators = result.get("indicators") or {}
                indicator_missing = [
                    key for key in ("MA5", "MA10", "MA20", "MA60", "RSI", "K", "D", "BB_upper", "BB_middle", "BB_lower")
                    if indicators.get(key) is None
                ]
                prediction_missing = [
                    key for key in ("prediction_5d", "prediction_20d")
                    if result.get(key) is None
                ]
                if missing:
                    _record(analysis_check, "error", symbol, "個股分析缺少必要欄位：" + ", ".join(missing), last_updated, issues)
                elif indicator_missing:
                    _record(analysis_check, "warn", symbol, "部分技術指標沒有數值：" + ", ".join(indicator_missing[:6]), last_updated, issues)
                elif prediction_missing:
                    _record(analysis_check, "warn", symbol, "預測欄位尚未產生：" + ", ".join(prediction_missing), last_updated, issues)
                else:
                    freshness, note = _freshness_status(last_updated)
                    _record(analysis_check, freshness, symbol, note, last_updated, issues)
        except Exception as e:
            _record(analysis_check, "error", symbol, f"個股分析檢查失敗：{e}", issues=issues)

        try:
            investors = get_investors_data(symbol, force_refresh=False)
            last_updated = investors.get("last_updated") if isinstance(investors, dict) else ""
            if not isinstance(investors, dict) or investors.get("error"):
                _record(investor_check, "error", symbol, "法人/主力資料沒有抓到", last_updated, issues)
            elif _is_tw_symbol(symbol):
                missing = _missing_required(investors, ["latest_date", "trend", "foreign_net", "trust_net", "dealer_net", "total_net"])
                if missing:
                    _record(investor_check, "error", symbol, "三大法人資料缺少欄位：" + ", ".join(missing), last_updated, issues)
                else:
                    freshness, note = _freshness_status(last_updated)
                    _record(investor_check, freshness, symbol, note, last_updated, issues)
            else:
                has_us_detail = bool(
                    investors.get("top_institutions")
                    or investors.get("major_holders_rows")
                    or investors.get("held_pct_institutions") is not None
                    or investors.get("held_pct_insiders") is not None
                )
                status = "ok" if has_us_detail else "warn"
                note = "" if has_us_detail else "美股法人持股資料來源沒有回傳細項"
                _record(investor_check, status, symbol, note, last_updated, issues)

            if _is_tw_symbol(symbol):
                margin = investors.get("margin") if isinstance(investors, dict) else {}
                margin_updated = margin.get("last_updated") if isinstance(margin, dict) else ""
                if not isinstance(margin, dict) or margin.get("error"):
                    _record(margin_check, "error", symbol, "融資融券資料沒有抓到", margin_updated, issues)
                else:
                    missing = _missing_required(margin, ["latest_date", "trend", "margin_buy", "margin_sell", "margin_bal", "short_sell", "short_buy", "short_bal"])
                    if missing:
                        _record(margin_check, "error", symbol, "融資融券資料缺少欄位：" + ", ".join(missing), margin_updated, issues)
                    else:
                        freshness, note = _freshness_status(margin_updated)
                        _record(margin_check, freshness, symbol, note, margin_updated, issues)
        except Exception as e:
            _record(investor_check, "error", symbol, f"法人/主力檢查失敗：{e}", issues=issues)
            if _is_tw_symbol(symbol):
                _record(margin_check, "error", symbol, f"融資融券檢查失敗：{e}", issues=issues)

    meta = {
        "stock_count": len(stocks),
        "limited_by_env": int(os.getenv("DATA_HEALTH_MAX_SYMBOLS", "0") or 0),
    }
    return [kline_check, analysis_check, investor_check, margin_check], meta


def _check_active_etf_holdings(issues: list[dict]) -> dict:
    check = _new_check("主動式ETF持股")
    try:
        all_holdings = fetch_all_etf_holdings(force_refresh=False)
    except Exception as e:
        _record(check, "error", "ALL", f"主動式ETF持股總表讀取失敗：{e}", issues=issues)
        return check

    for code, name in ACTIVE_ETFS.items():
        info = all_holdings.get(code) if isinstance(all_holdings, dict) else None
        last_updated = info.get("last_updated") if isinstance(info, dict) else ""
        if not isinstance(info, dict):
            _record(check, "error", code, "ETF 沒有回傳資料", last_updated, issues)
            continue
        if info.get("error"):
            _record(check, "error", code, "ETF 抓取來源回報錯誤", last_updated, issues)
            continue
        if not info.get("holdings") or int(info.get("total_holdings") or 0) <= 0:
            _record(check, "error", code, "ETF 持股清單為空", last_updated, issues)
            continue

        missing = _missing_required(info, ["date", "top10_weight", "total_holdings", "last_updated"])
        if not code.endswith("D") and not info.get("sector_breakdown"):
            missing.append("sector_breakdown")

        changes = info.get("changes") or {}
        if missing:
            _record(check, "warn", code, f"{name} 缺少欄位：" + ", ".join(missing), last_updated, issues)
        elif not changes.get("available"):
            reason = changes.get("reason") or "尚未取得前一交易日變化"
            _record(check, "warn", code, f"{name} 沒有可用的前一交易日變化：{reason}", last_updated, issues)
        else:
            freshness, note = _freshness_status(last_updated)
            _record(check, freshness, code, note, last_updated, issues)
    return check


def _check_active_etf_summary(issues: list[dict]) -> dict:
    check = _new_check("主動式ETF匯總/投資組合")
    try:
        summary = fetch_etf_sector_summary(force_refresh=False, holdings_refresh=False)
    except Exception as e:
        _record(check, "error", "sector_summary", f"主動式ETF匯總讀取失敗：{e}", issues=issues)
        return check

    last_updated = (summary.get("last_updated") or summary.get("generated_at")) if isinstance(summary, dict) else ""
    if not isinstance(summary, dict) or summary.get("error"):
        _record(check, "error", "sector_summary", "主動式ETF匯總沒有產生資料", last_updated, issues)
        return check

    sectors = summary.get("sectors") or []
    etf_summaries = summary.get("etf_summaries") or []
    chart = summary.get("chart") or {}
    slices = chart.get("slices") or []
    stock_etf_expected = sum(1 for code in ACTIVE_ETFS if not code.endswith("D"))

    missing = []
    if not sectors:
        missing.append("sectors")
    if not etf_summaries:
        missing.append("etf_summaries")
    if not summary.get("total_weight"):
        missing.append("total_weight")
    if not slices:
        missing.append("chart.slices")
    if len(etf_summaries) < stock_etf_expected:
        missing.append("etf_summaries_count")

    periods = ("day", "week", "month")
    missing_periods: list[str] = []
    day_change_available = 0
    for period in periods:
        period_available = 0
        for sector in sectors:
            change = (sector.get("changes") or {}).get(period) or {}
            if change.get("available"):
                period_available += 1
        if period_available == 0:
            missing_periods.append(period)
        if period == "day":
            day_change_available = period_available

    if missing:
        _record(check, "error", "sector_summary", "主動式ETF匯總缺少必要欄位：" + ", ".join(missing), last_updated, issues)
    elif missing_periods:
        _record(check, "warn", "sector_summary", "主動式ETF匯總缺少變化資料：" + ", ".join(missing_periods), last_updated, issues)
    elif day_change_available == 0:
        _record(check, "warn", "sector_summary", "主動式ETF匯總沒有前一交易日變化", last_updated, issues)
    else:
        freshness, note = _freshness_status(last_updated)
        _record(check, freshness, "sector_summary", note, last_updated, issues)
    return check


def _check_news_modules(issues: list[dict]) -> list[dict]:
    info_check = _new_check("資訊面")
    trump_check = _new_check("TrumpNews")

    try:
        news = fetch_all_news(force=False)
        last_updated = get_last_updated()
        if not isinstance(news, dict) or not news:
            _record(info_check, "error", "all_categories", "資訊面沒有抓到任何分類", issues=issues)
        else:
            for category, articles in news.items():
                updated = last_updated.get(category, "") if isinstance(last_updated, dict) else ""
                if not articles:
                    _record(info_check, "warn", category, "此資訊分類沒有文章", updated, issues)
                else:
                    freshness, note = _freshness_status(updated)
                    _record(info_check, freshness, category, note, updated, issues)
    except Exception as e:
        _record(info_check, "error", "all_categories", f"資訊面檢查失敗：{e}", issues=issues)

    try:
        trump = fetch_trump_news(force=False)
        updated = get_trump_last_updated() or (trump.get("last_updated") if isinstance(trump, dict) else "")
        sections = trump.get("sections") if isinstance(trump, dict) else {}
        if not isinstance(sections, dict) or not sections:
            _record(trump_check, "error", "sections", "TrumpNews 沒有抓到任何來源區塊", updated, issues)
        else:
            for section, items in sections.items():
                if not items:
                    _record(trump_check, "warn", section, "此 TrumpNews 來源沒有文章", updated, issues)
                else:
                    freshness, note = _freshness_status(updated)
                    _record(trump_check, freshness, section, note, updated, issues)
    except Exception as e:
        _record(trump_check, "error", "sections", f"TrumpNews 檢查失敗：{e}", issues=issues)

    return [info_check, trump_check]


def _build_report() -> dict:
    start = time.time()
    generated_at = _server_time_text()
    issues: list[dict] = []
    checks: list[dict] = []

    checks.append(_check_market_overview(issues))
    stock_checks, stock_meta = _check_stock_modules(issues)
    checks.extend(stock_checks)
    checks.append(_check_active_etf_holdings(issues))
    checks.append(_check_active_etf_summary(issues))
    checks.extend(_check_news_modules(issues))

    overall = _worst(*(check["status"] for check in checks))
    summary_counts = {
        "checks": len(checks),
        "ok": sum(check["ok"] for check in checks),
        "warn": sum(check["warn"] for check in checks),
        "error": sum(check["error"] for check in checks),
        "unknown": sum(check["unknown"] for check in checks),
        "items_checked": sum(check["checked"] for check in checks),
    }

    report = {
        "status": overall,
        "status_label": STATUS_LABEL.get(overall, overall),
        "generated_at": generated_at,
        "duration_seconds": round(time.time() - start, 1),
        "summary_counts": summary_counts,
        "checks": checks,
        "issues": issues,
        "issues_total": len(issues),
        "stock_meta": stock_meta,
        "schedule": "19:00 Asia/Taipei",
        "stale_hours": DEFAULT_STALE_HOURS,
    }
    return report


def _status_badge(status: str) -> str:
    return STATUS_LABEL.get(status, status)


def _build_markdown(report: dict) -> str:
    counts = report["summary_counts"]
    lines = [
        "# Stock Monitor 數據健康檢查",
        "",
        f"- 生成時間：{report['generated_at']}",
        f"- 排程：每日 {report['schedule']}",
        f"- 整體狀態：{report['status_label']}",
        f"- 檢查耗時：{report['duration_seconds']} 秒",
        f"- 判定過期門檻：{report['stale_hours']} 小時未更新",
        f"- 檢查項目：{counts['items_checked']} 項，正常 {counts['ok']}，警告 {counts['warn']}，異常 {counts['error']}，未知 {counts['unknown']}",
        "",
    ]

    if report.get("stock_meta", {}).get("limited_by_env"):
        lines.append(f"> 注意：本次個股檢查受 DATA_HEALTH_MAX_SYMBOLS 限制，只檢查前 {report['stock_meta']['limited_by_env']} 檔。")
        lines.append("")

    lines.extend([
        "## 模組更新狀態",
        "",
        "| 模組 | 狀態 | 檢查數 | 正常 | 警告 | 異常 | 未知 | 上次更新 | 備註 |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ])
    for check in report["checks"]:
        notes = "；".join(check.get("notes") or []) or "-"
        lines.append(
            f"| {check['module']} | {_status_badge(check['status'])} | {check['checked']} | "
            f"{check['ok']} | {check['warn']} | {check['error']} | {check['unknown']} | "
            f"{check.get('last_updated') or '-'} | {notes} |"
        )

    lines.extend([
        "",
        "## 異常與警告",
        "",
    ])
    issues = report.get("issues") or []
    if not issues:
        lines.append("沒有偵測到異常或警告。")
    else:
        shown = issues[:MAX_ISSUES_IN_REPORT]
        lines.extend([
            "| 狀態 | 模組 | 項目 | 原因 | 上次更新 |",
            "|---|---|---|---|---|",
        ])
        for issue in shown:
            lines.append(
                f"| {_status_badge(issue['status'])} | {issue['module']} | {issue.get('item') or '-'} | "
                f"{issue.get('reason') or '-'} | {issue.get('last_updated') or '-'} |"
            )
        if len(issues) > len(shown):
            lines.append("")
            lines.append(f"尚有 {len(issues) - len(shown)} 筆警告/異常未列出，避免報告過長。")

    lines.extend([
        "",
        "## 說明",
        "",
        "- 本報告只確認資料是否更新與欄位是否完整，不輸出原始價格、持股明細或新聞內容。",
        "- 主動式ETF持股會檢查持股筆數、前十大權重、產業分布與前一交易日變化是否存在。",
        "- 個股分析會檢查 K 線、技術指標、評分、預測欄位、法人/主力與融資融券資料是否可用。",
    ])
    return "\n".join(lines) + "\n"


def _build_html(report: dict) -> str:
    counts = report["summary_counts"]
    rows = []
    for check in report["checks"]:
        notes = escape("；".join(check.get("notes") or []) or "-")
        rows.append(
            f"<tr><td>{escape(check['module'])}</td>"
            f"<td class='{check['status']}'>{escape(_status_badge(check['status']))}</td>"
            f"<td>{check['checked']}</td><td>{check['ok']}</td><td>{check['warn']}</td>"
            f"<td>{check['error']}</td><td>{check['unknown']}</td>"
            f"<td>{escape(check.get('last_updated') or '-')}</td><td>{notes}</td></tr>"
        )
    issue_rows = []
    for issue in (report.get("issues") or [])[:20]:
        issue_rows.append(
            f"<tr><td class='{issue['status']}'>{escape(_status_badge(issue['status']))}</td>"
            f"<td>{escape(issue['module'])}</td><td>{escape(issue.get('item') or '-')}</td>"
            f"<td>{escape(issue.get('reason') or '-')}</td>"
            f"<td>{escape(issue.get('last_updated') or '-')}</td></tr>"
        )
    if not issue_rows:
        issue_rows.append("<tr><td colspan='5'>沒有偵測到異常或警告。</td></tr>")

    return f"""
<p><strong>整體狀態：</strong><span class="{report['status']}">{escape(report['status_label'])}</span></p>
<p>檢查項目：{counts['items_checked']} 項；正常 {counts['ok']}，警告 {counts['warn']}，異常 {counts['error']}，未知 {counts['unknown']}。耗時 {report['duration_seconds']} 秒。</p>
<h3>模組更新狀態</h3>
<table>
  <tr><th>模組</th><th>狀態</th><th>檢查數</th><th>正常</th><th>警告</th><th>異常</th><th>未知</th><th>上次更新</th><th>備註</th></tr>
  {''.join(rows)}
</table>
<h3>異常與警告（前 20 筆）</h3>
<table>
  <tr><th>狀態</th><th>模組</th><th>項目</th><th>原因</th><th>上次更新</th></tr>
  {''.join(issue_rows)}
</table>
<p>完整明細請看附件 Markdown；PDF 供快速存檔。</p>
"""


def _find_cjk_font() -> str | None:
    candidates = [
        r"C:\Windows\Fonts\msjh.ttc",
        r"C:\Windows\Fonts\mingliu.ttc",
        r"C:\Windows\Fonts\kaiu.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _ascii_pdf_text(report: dict) -> str:
    counts = report["summary_counts"]
    lines = [
        "Stock Monitor Data Health Check",
        "",
        f"Generated: {report['generated_at']}",
        f"Schedule: daily {report['schedule']}",
        f"Overall status: {report['status']}",
        f"Items checked: {counts['items_checked']}  OK: {counts['ok']}  WARN: {counts['warn']}  ERROR: {counts['error']}  UNKNOWN: {counts['unknown']}",
        "",
        "Module status:",
    ]
    for check in report["checks"]:
        lines.append(
            f"- {check['module']}: {check['status']} "
            f"(checked={check['checked']}, ok={check['ok']}, warn={check['warn']}, error={check['error']}, unknown={check['unknown']}, updated={check.get('last_updated') or '-'})"
        )
    lines.append("")
    lines.append("The full Chinese report is attached as Markdown.")
    return "\n".join(lines)


def _pdf_escape(text: str) -> str:
    return (
        text.encode("latin-1", "replace").decode("latin-1")
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _save_minimal_pdf(report: dict) -> str | None:
    """Write a small dependency-free ASCII PDF when fpdf2 is unavailable."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_key = report["generated_at"][:10]
    pdf_path = REPORTS_DIR / f"data_health_{date_key}.pdf"

    lines = _ascii_pdf_text(report).splitlines()[:220]
    page_lines = [lines[i:i + 45] for i in range(0, len(lines), 45)] or [[]]
    objects: list[bytes] = [b""]
    page_ids = []

    # Object 1 and 2 are Catalog and Pages. Page/content objects start at 3.
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"")
    for index, chunk in enumerate(page_lines):
        page_id = 3 + index * 2
        content_id = page_id + 1
        page_ids.append(page_id)
        text_ops = ["BT", "/F1 10 Tf", "50 760 Td", "14 TL"]
        for line in chunk:
            text_ops.append(f"({_pdf_escape(line[:105])}) Tj")
            text_ops.append("T*")
        text_ops.append("ET")
        stream = "\n".join(text_ops).encode("latin-1", "replace")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> "
            f"/Contents {content_id} 0 R >>".encode("latin-1")
        )
        objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
            + stream
            + b"\nendstream"
        )

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("latin-1")

    try:
        chunks = [b"%PDF-1.4\n"]
        offsets = [0]
        for obj_id, body in enumerate(objects[1:], start=1):
            offsets.append(sum(len(chunk) for chunk in chunks))
            chunks.append(f"{obj_id} 0 obj\n".encode("latin-1"))
            chunks.append(body)
            chunks.append(b"\nendobj\n")
        xref_offset = sum(len(chunk) for chunk in chunks)
        chunks.append(f"xref\n0 {len(objects)}\n".encode("latin-1"))
        chunks.append(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            chunks.append(f"{offset:010d} 00000 n \n".encode("latin-1"))
        chunks.append(
            f"trailer << /Size {len(objects)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
        )
        pdf_path.write_bytes(b"".join(chunks))
        return str(pdf_path)
    except Exception as e:
        logger.warning("Minimal data health PDF generation failed: %s", e)
        return None


def _save_pdf(markdown_text: str, report: dict) -> str | None:
    try:
        from fpdf import FPDF
    except Exception as e:
        logger.warning("fpdf2 is unavailable, data health PDF skipped: %s", e)
        return _save_minimal_pdf(report)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_key = report["generated_at"][:10]
    pdf_path = REPORTS_DIR / f"data_health_{date_key}.pdf"

    cjk_font = None if report.get("_ascii_retry") else _find_cjk_font()
    text = markdown_text if cjk_font else _ascii_pdf_text(report)

    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=14)
        pdf.add_page()
        font_name = "Helvetica"
        if cjk_font:
            pdf.add_font("CJK", "", cjk_font)
            pdf.add_font("CJK", "B", cjk_font)
            font_name = "CJK"

        pdf.set_font(font_name, "B", 15)
        pdf.set_text_color(16, 36, 58)
        pdf.multi_cell(0, 8, "Stock Monitor 數據健康檢查" if cjk_font else "Stock Monitor Data Health Check")
        pdf.ln(2)
        pdf.set_font(font_name, "", 9.5)
        pdf.set_text_color(35, 35, 35)
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                pdf.ln(2)
                continue
            if line.startswith("#"):
                pdf.set_font(font_name, "B", 12)
                pdf.set_text_color(13, 71, 161)
                pdf.multi_cell(0, 7, line.lstrip("# ").strip())
                pdf.set_font(font_name, "", 9.5)
                pdf.set_text_color(35, 35, 35)
                continue
            pdf.multi_cell(0, 5.5, line[:900])
        pdf.output(str(pdf_path))
        return str(pdf_path)
    except Exception as e:
        logger.warning("Data health PDF generation failed: %s", e, exc_info=True)
        if cjk_font:
            try:
                return _save_pdf(_ascii_pdf_text(report), {**report, "_ascii_retry": True})
            except Exception:
                return _save_minimal_pdf(report)
        return _save_minimal_pdf(report)


def _save_report_files(report: dict, markdown_text: str) -> tuple[str, str | None]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_key = report["generated_at"][:10]
    md_path = REPORTS_DIR / f"data_health_{date_key}.md"
    md_path.write_text(markdown_text, encoding="utf-8")
    pdf_path = _save_pdf(markdown_text, report)
    return str(md_path), pdf_path


def run_data_health_check(send_email: bool = True) -> dict:
    """
    Run all data-health checks, save Markdown/PDF reports, and optionally email them.
    """
    logger.info("Running data health check...")
    report = _build_report()
    markdown_text = _build_markdown(report)
    html = _build_html(report)
    md_path, pdf_path = _save_report_files(report, markdown_text)

    email_sent = False
    if send_email:
        subject = (
            f"[Stock Monitor] 數據健康檢查 {report['generated_at'][:10]} | "
            f"{report['status_label']} | 異常 {report['summary_counts']['error']} / 警告 {report['summary_counts']['warn']}"
        )
        email_sent = send_data_health_report(html, subject, md_path=md_path, pdf_path=pdf_path)

    result = {
        "status": report["status"],
        "status_label": report["status_label"],
        "generated_at": report["generated_at"],
        "duration_seconds": report["duration_seconds"],
        "summary_counts": report["summary_counts"],
        "issues_total": report["issues_total"],
        "md_path": md_path,
        "pdf_path": pdf_path,
        "email_sent": email_sent,
        "schedule": report["schedule"],
    }
    try:
        LATEST_STATUS_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to save data health latest status: %s", e)
    logger.info("Data health check complete: %s", result)
    return result
