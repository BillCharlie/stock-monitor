"""
Active ETF holdings fetcher — MoneyDJ primary, etfinfo.tw fallback.

Fetch priority per ETF:
  1. Cache hit  (< 4 h, same date)
  2. MoneyDJ    Basic0007B page  →  pd.read_html
  3. etfinfo.tw /etf/{code}/holdings  →  pd.read_html

Key stored fields per holding row:
    stock_code  str    "2330"
    stock_name  str    "台積電"
    weight_pct  float  15.23
    shares      int    1_000_000

Daily snapshot logic:
  - Each successful fetch with a NEW date saves current to
      cache/etf_holdings_{code}.json        (current)
  - Before overwriting, old current is copied to
      cache/etf_holdings_{code}_prev.json   (previous trading day)
  - compute_changes(prev, curr) returns new/exited/increased/decreased positions

Email section:
  - build_etf_email_section(all_holdings) → HTML string
  - Includes top 5 holdings + share-change badges
"""
from __future__ import annotations

import glob
import io
import json
import logging
import math
import os
import re
import shutil
import time
from collections import defaultdict
from datetime import datetime, timedelta
from html import escape

import pandas as pd
import requests

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.getenv("DATA_DIR", os.path.dirname(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

HOLDINGS_CACHE_TTL = 4 * 3600    # 4 hours — skip re-fetch if cache is fresh
ALL_CACHE_TTL      = 3 * 3600    # 3 hours — combined all-ETF snapshot
STOCK_MASTER_CACHE_TTL = 24 * 3600
ETF_SECTOR_BASELINE_START_DATE = os.getenv("ETF_SECTOR_BASELINE_START_DATE", "2025-05-14")
ETF_SECTOR_HISTORY_VERSION = 4
GOAL_STAR_BASE_URL = os.getenv("GOAL_STAR_BASE_URL", "https://goal-star.com").rstrip("/")
GOAL_STAR_CACHE_TTL = int(os.getenv("GOAL_STAR_CACHE_TTL", str(6 * 3600)))
GOAL_STAR_FULL_HOLDINGS_MAX_DAYS = int(os.getenv("GOAL_STAR_FULL_HOLDINGS_MAX_DAYS", "14"))
GOAL_STAR_HISTORY_SCAN_DAYS = int(os.getenv("GOAL_STAR_HISTORY_SCAN_DAYS", "8"))

SECTOR_CHANGE_PERIODS = {
    "day": 1,
    "week": 7,
    "month": 30,
    "quarter_1": 91,
    "quarter_2": 182,
    "quarter_3": 273,
    "quarter_4": 365,
    "year": 365,
}


def _time_text(dt: datetime | None = None) -> str:
    return (dt or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")


def _mtime_text(path: str) -> str:
    try:
        return _time_text(datetime.fromtimestamp(os.path.getmtime(path)))
    except Exception:
        return ""


def _with_last_updated(result: dict, path: str | None = None) -> dict:
    if not isinstance(result, dict):
        return result
    result["last_updated"] = (
        result.get("last_updated")
        or result.get("fetched_at")
        or result.get("generated_at")
        or (_mtime_text(path) if path else "")
        or _time_text()
    )
    return result

TWSE_COMPANY_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_COMPANY_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"

_TW_INDUSTRY_SECTORS = {
    "01": "水泥",
    "02": "食品",
    "03": "化工/塑化",
    "04": "紡織",
    "05": "電機機械",
    "06": "電器電纜",
    "07": "化工/塑化",
    "08": "傳產",
    "09": "傳產",
    "10": "鋼鐵",
    "11": "傳產",
    "12": "汽車",
    "14": "建設",
    "15": "航運",
    "16": "觀光餐旅",
    "17": "金融",
    "18": "零售",
    "20": "傳產",
    "21": "化工/塑化",
    "22": "生技醫療",
    "23": "能源",
    "24": "半導體",
    "25": "科技系統廠",
    "26": "光學",
    "27": "通信網路",
    "28": "電子零組件",
    "29": "電子通路",
    "30": "資訊服務",
    "31": "其他電子",
    "32": "文創",
    "33": "農業科技",
    "34": "電子商務",
    "35": "太陽能/綠能",
    "36": "AI與雲端",
    "37": "運動休閒",
    "38": "居家生活",
}

_WATCHLIST_THEME_SECTORS = {"TSMC相關股", "主動式ETF"}

_US_STOCKS: dict[str, tuple[str, str]] = {
    "AAPL": ("Apple", "科技系統廠"),
    "AMZN": ("Amazon", "AI與雲端"),
    "AMD": ("AMD", "半導體"),
    "ARM": ("Arm", "半導體"),
    "ASML": ("ASML", "半導體"),
    "AVGO": ("Broadcom", "半導體"),
    "GOOG": ("Alphabet", "AI與雲端"),
    "GOOGL": ("Alphabet", "AI與雲端"),
    "META": ("Meta", "AI與雲端"),
    "MSFT": ("Microsoft", "AI與雲端"),
    "MU": ("Micron", "半導體"),
    "NFLX": ("Netflix", "AI與雲端"),
    "NVDA": ("NVIDIA", "半導體"),
    "ORCL": ("Oracle", "AI與雲端"),
    "PLTR": ("Palantir", "AI與雲端"),
    "QCOM": ("Qualcomm", "半導體"),
    "TSLA": ("Tesla", "汽車"),
    "TSM": ("TSMC ADR", "半導體"),
}

SECTOR_COLORS: dict[str, str] = {
    "半導體": "#40C4FF",
    "科技系統廠": "#26A69A",
    "電子零組件": "#80DEEA",
    "其他電子": "#90A4AE",
    "通信網路": "#64B5F6",
    "鋼鐵": "#A1887F",
    "電機機械": "#A5D6A7",
    "電器電纜": "#FFCC80",
    "太陽能/綠能": "#FFF176",
    "AI與雲端": "#7E57C2",
    "金融": "#CE93D8",
    "光學": "#80CBC4",
    "化工/塑化": "#FF7043",
    "生技醫療": "#B39DDB",
    "航運": "#4DD0E1",
    "零售": "#F48FB1",
    "汽車": "#FFCC80",
    "水泥": "#BCAAA4",
    "食品": "#E6EE9C",
    "建設": "#CFD8DC",
    "紡織": "#FFAB91",
    "傳產": "#90A4AE",
    "能源": "#B0BEC5",
    "資訊服務": "#64FFDA",
    "電子通路": "#81C784",
    "文創": "#BA68C8",
    "觀光餐旅": "#FFD54F",
    "居家生活": "#B39DDB",
    "其他": "#607D8B",
}

_FALLBACK_SECTOR_COLORS = [
    "#40C4FF", "#26A69A", "#FF9800", "#CE93D8", "#FFF176", "#80DEEA",
    "#A1887F", "#B39DDB", "#FF7043", "#90A4AE", "#66BB6A", "#F48FB1",
    "#4DB6AC", "#9575CD", "#DCE775", "#7986CB",
]

_GOAL_STAR_INDUSTRY_SECTORS = {
    "Semiconductors": "半導體",
    "Electronic Components": "電子零組件",
    "Computer Hardware": "科技系統廠",
    "Communications Equipment": "通信網路",
    "Electrical Equipment": "電器電纜",
    "Machinery": "電機機械",
    "Financial Services": "金融",
    "Banks": "金融",
    "Insurance": "金融",
    "Chemicals": "化工/塑化",
    "Plastics": "化工/塑化",
    "Steel": "鋼鐵",
    "Automobiles": "汽車",
    "Auto Parts": "汽車",
    "Solar": "太陽能/綠能",
    "Renewable Energy": "太陽能/綠能",
    "Biotechnology": "生技醫療",
    "Healthcare": "生技醫療",
    "Retail": "零售",
    "Transportation": "航運",
    "Shipping": "航運",
    "Construction": "建設",
    "Textiles": "紡織",
    "Food": "食品",
}

# ── Master list ───────────────────────────────────────────────────────────────
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
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.moneydj.com/",
}


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _clean_number(v) -> float | None:
    """Strip commas / % / spaces from a string number."""
    try:
        s = str(v).replace(",", "").replace("%", "").replace(" ", "").strip()
        return float(s) if s and s not in ("-", "—", "N/A", "") else None
    except (ValueError, AttributeError):
        return None


def _looks_latin1_mojibake(value: str) -> bool:
    """True for UTF-8 Chinese text that was accidentally decoded as latin-1."""
    if not value:
        return False
    suspicious = sum(
        1
        for ch in value
        if "\u0080" <= ch <= "\u00ff" or ch in {"å", "æ", "ç", "è", "é"}
    )
    return suspicious >= 2


def _repair_mojibake(value: str) -> str:
    """Repair the common MoneyDJ mojibake shape: 'å°ç©é»' → '台積電'."""
    text = str(value or "").strip()
    if not text:
        return ""
    if _looks_latin1_mojibake(text):
        try:
            fixed = text.encode("latin1").decode("utf-8")
            if fixed:
                return fixed.strip()
        except UnicodeError:
            pass
    return text


def _normalise_code(code: str) -> str:
    return re.sub(r"\.(TW|TWO|US|HK)$", "", str(code or "").strip().upper())


def _extract_stock_code(raw: str) -> str:
    """
    Extract a 4-6 digit TW stock code from various MoneyDJ column formats:
      - "2330"                   → "2330"
      - "台積電(2330)"            → "2330"
      - "2330 台積電"             → "2330"
      - "台積電(2330.TW)"         → "2330"
      - "NVIDIA CORP(NVDA.US)"    → "NVDA"
    """
    raw = _repair_mojibake(raw)
    raw_u = raw.upper()

    # Pure digit/letter code (e.g. "2330", "00940")
    if re.fullmatch(r"[0-9A-Z]{2,8}(?:\.(?:TW|TWO|US|HK))?", raw_u):
        return _normalise_code(raw_u)

    # Embedded in parentheses: "台積電(2330.TW)" / "NVIDIA(NVDA.US)"
    m = re.search(r"\(([0-9A-Z]{1,8})(?:\.(?:TW|TWO|US|HK))?\)", raw_u)
    if m:
        return _normalise_code(m.group(1))

    # Leading digits followed by space: "2330 台積電"
    m = re.match(r"^([0-9]{4,8})\s", raw_u)
    if m:
        return m.group(1)

    # Any TW-style stock code in the value. This recovers cached mojibake rows.
    m = re.search(r"\b([0-9]{4,6}[A-Z]?)(?:\.(?:TW|TWO))?\b", raw_u)
    if m:
        return m.group(1)
    return ""


def _strip_code_from_name(raw_name: str, code: str = "") -> str:
    """Remove display suffixes like '(2330.TW)' while keeping the separate code field."""
    name = _repair_mojibake(raw_name)
    name = re.sub(r"\s*\(([0-9A-Z]{1,8})(?:\.(?:TW|TWO|US|HK))?\)\s*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^([0-9]{4,8}[A-Z]?)(?:\.(?:TW|TWO))?\s+", "", name, flags=re.IGNORECASE)
    if code:
        name = re.sub(rf"\b{re.escape(code)}(?:\.(?:TW|TWO|US|HK))?\b", "", name, flags=re.IGNORECASE)
    return name.strip(" -*　")


def _find_holdings_table(tables: list[pd.DataFrame]) -> pd.DataFrame | None:
    """
    From a list of DataFrames parsed by pd.read_html, return the one that
    looks like an ETF holdings table (has weight / shares columns).
    """
    keywords_weight = {"比重", "權重", "佔比", "weight", "%"}
    keywords_shares = {"持有股數", "持有張數", "股數", "張數", "shares"}

    best: pd.DataFrame | None = None
    best_score = 0
    for df in tables:
        if df.empty or len(df) < 2:
            continue
        all_cols = " ".join(str(c) for c in df.columns).lower()
        score = 0
        if any(k in all_cols for k in keywords_weight):
            score += 2
        if any(k in all_cols for k in keywords_shares):
            score += 2
        if any(k in all_cols for k in {"代號", "股票", "名稱", "bond", "債券"}):
            score += 1
        if score > best_score and len(df) >= 3:
            best_score = score
            best = df
    return best


def _parse_holdings_df(df: pd.DataFrame) -> list[dict]:
    """
    Convert a raw holdings DataFrame into a clean list of dicts.
    Handles variable column naming conventions across ETFs.
    """
    cols = list(df.columns)
    col_str = " ".join(str(c) for c in cols).lower()

    # ── Identify key columns by content pattern ───────────────────────────────
    code_col   = None
    name_col   = None
    weight_col = None
    shares_col = None

    for c in cols:
        cs = str(c).lower()
        if any(k in cs for k in ["代號", "code", "股票代", "symbol"]):
            code_col = c
        elif any(k in cs for k in ["名稱", "name", "股票名", "債券名", "標的"]):
            name_col = c
        elif any(k in cs for k in ["比重", "權重", "佔淨資", "weight", "%"]):
            if weight_col is None:
                weight_col = c
        elif any(k in cs for k in ["持有股數", "持有張數", "股數", "張數", "shares"]):
            shares_col = c

    # If no dedicated code column, we'll extract from the name column
    if code_col is None and name_col is None:
        # Fallback: first text-ish column is name/code
        for c in cols:
            sample = str(df[c].dropna().iloc[0]) if not df[c].dropna().empty else ""
            if re.search(r"[一-龥A-Za-z]", sample) or re.match(r"\d{4}", sample):
                name_col = c
                break

    holdings = []
    for _, row in df.iterrows():
        raw_code = _repair_mojibake(str(row[code_col]).strip()) if code_col else ""
        raw_name = _repair_mojibake(str(row[name_col]).strip()) if name_col else ""

        stock_code = _extract_stock_code(raw_code) or _extract_stock_code(raw_name)

        # Strip embedded code from name if present, but preserve the separate stock_code
        stock_name = _strip_code_from_name(raw_name, stock_code) or _strip_code_from_name(raw_code, stock_code) or raw_name

        weight = _clean_number(row[weight_col]) if weight_col else None
        shares = None
        if shares_col:
            sv = _clean_number(row[shares_col])
            if sv is not None:
                try:
                    shares = int(sv)
                except (ValueError, OverflowError):
                    shares = None

        # Skip rows without meaningful data
        if not stock_name and not stock_code:
            continue
        if stock_name in ("NaN", "nan", "—", "-", "None", ""):
            continue

        holdings.append({
            "stock_code": stock_code,
            "stock_name": stock_name,
            "weight_pct": round(weight, 4) if weight is not None else None,
            "shares":     shares,
        })

    # Sort by weight desc (put None weights at end)
    holdings.sort(
        key=lambda h: h["weight_pct"] if h["weight_pct"] is not None else -1,
        reverse=True,
    )
    return holdings


# ── Stock name & sector enrichment ───────────────────────────────────────────

# Sub-category names that override their parent sector assignment
_SECTOR_OVERRIDE: dict[str, str] = {
    "鐵礦鋼鐵": "鋼鐵",
}

# Common TW stocks that may appear in ETF holdings but aren't in WATCHLIST
_EXTRA_STOCKS: dict[str, tuple[str, str]] = {
    # code: (name, sector)
    "2882": ("中信金控",    "金融"),   "2886": ("兆豐金控",    "金融"),
    "2884": ("玉山金控",    "金融"),   "2885": ("元大金控",    "金融"),
    "2887": ("台新金控",    "金融"),   "2880": ("華南金控",    "金融"),
    "2881": ("富邦金控",    "金融"),   "2883": ("開發金控",    "金融"),
    "2892": ("第一金控",    "金融"),   "5880": ("合庫金控",    "金融"),
    "5876": ("上海商銀",    "金融"),   "2834": ("臺企銀",      "金融"),
    "2801": ("彰化銀行",    "金融"),   "2820": ("華票",        "金融"),
    "4904": ("遠傳電信",    "電信"),   "3045": ("台灣大哥大",  "電信"),
    "2412": ("中華電信",    "電信"),
    "2603": ("長榮海運",    "航運"),   "2609": ("陽明海運",    "航運"),
    "2615": ("萬海航運",    "航運"),   "2618": ("長榮航空",    "航運"),
    "2610": ("華航",        "航運"),
    "1301": ("台塑",        "化工/塑化"), "1303": ("南亞塑膠",  "化工/塑化"),
    "1326": ("台化",        "化工/塑化"), "6505": ("台塑化",    "化工/塑化"),
    "1402": ("遠東新",      "紡織"),   "1216": ("統一企業",    "食品"),
    "1101": ("台泥",        "水泥"),   "1102": ("亞泥",        "水泥"),
    "2207": ("和泰車",      "汽車"),   "2204": ("中華汽車",    "汽車"),
    "2912": ("統一超商",    "零售"),   "5903": ("全家便利",    "零售"),
    "2915": ("潤泰全",      "零售"),
    "4174": ("浩鼎生技",    "生技醫療"), "6446": ("藥華藥",    "生技醫療"),
    "3481": ("頎邦科技",    "半導體"), "3008": ("大立光",      "光學"),
    "2049": ("上銀科技",    "機械"),   "1590": ("亞德客-KY",  "機械"),
    "6213": ("聯茂電子",    "PCB"),    "2474": ("可成科技",   "科技系統廠"),
    "2633": ("台灣高鐵",    "交通"),   "9933": ("中鼎工程",   "建設"),
    "5534": ("長虹建設",    "建設"),
    "2382": ("廣達電腦",    "科技系統廠"), "2317": ("鴻海精密", "科技系統廠"),
    "2324": ("仁寶電腦",    "科技系統廠"), "2356": ("英業達",   "科技系統廠"),
    "4938": ("和碩",        "科技系統廠"), "3231": ("緯創資通", "科技系統廠"),
    "6669": ("緯穎科技",    "科技系統廠"), "2354": ("鴻準精密", "科技系統廠"),
}

_name_map_cache:   dict | None = None
_sector_map_cache: dict | None = None


def _stock_master_cache_path() -> str:
    return os.path.join(CACHE_DIR, "tw_stock_master.json")


def _load_stock_master_cache() -> dict:
    path = _stock_master_cache_path()
    if not os.path.exists(path):
        return {}
    if time.time() - os.path.getmtime(path) > STOCK_MASTER_CACHE_TTL:
        return {}
    return _load_json(path)


def _fetch_json(url: str):
    resp = requests.get(url, headers=_HEADERS, timeout=20, verify=False)
    resp.raise_for_status()
    if resp.encoding and resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.json()


def _normalise_tw_industry(raw: str) -> str:
    code = str(raw or "").strip()
    if not code:
        return "其他"
    if code.isdigit():
        code = code.zfill(2)
    return _TW_INDUSTRY_SECTORS.get(code, "其他")


def _build_official_stock_maps() -> tuple[dict[str, str], dict[str, str]]:
    """Fetch TWSE/TPEx company masters so ETF holdings can resolve names by code."""
    cached = _load_stock_master_cache()
    if cached.get("names") and cached.get("sectors"):
        return cached["names"], cached["sectors"]

    names: dict[str, str] = {}
    sectors: dict[str, str] = {}
    sources = (
        (
            TWSE_COMPANY_URL,
            "公司代號",
            "公司簡稱",
            "公司名稱",
            "產業別",
        ),
        (
            TPEX_COMPANY_URL,
            "SecuritiesCompanyCode",
            "CompanyAbbreviation",
            "CompanyName",
            "SecuritiesIndustryCode",
        ),
    )

    for url, code_key, short_key, full_key, industry_key in sources:
        try:
            for row in _fetch_json(url):
                code = _normalise_code(row.get(code_key, ""))
                if not code:
                    continue
                name = str(row.get(short_key) or row.get(full_key) or "").strip()
                if name:
                    names[code] = name
                sectors[code] = _normalise_tw_industry(row.get(industry_key, ""))
        except Exception as e:
            logger.warning("Official stock master fetch failed %s: %s", url, e)

    if names:
        _save_json(_stock_master_cache_path(), {
            "fetched_at": datetime.now().isoformat(),
            "names": names,
            "sectors": sectors,
        })
    return names, sectors


def _has_cjk(value: str) -> bool:
    return bool(re.search(r"[一-鿿]", value or ""))


def _bad_stock_name(name: str, code: str = "") -> bool:
    clean = _strip_code_from_name(name, code)
    if not clean:
        return True
    if _looks_latin1_mojibake(name):
        return True
    if code and _normalise_code(clean) == code:
        return True
    return not _has_cjk(clean) and not re.search(r"[A-Za-z]", clean)


def _build_stock_maps() -> tuple[dict[str, str], dict[str, str]]:
    """Build (code→name, code→sector) from WATCHLIST + _EXTRA_STOCKS."""
    name_map:   dict[str, str] = {}
    sector_map: dict[str, str] = {}

    try:
        from watchlist import WATCHLIST  # local import avoids circular deps at module level

        def _strip(sym: str) -> str:
            return re.sub(r"\.(TWO?)$", "", sym, flags=re.IGNORECASE)

        def _walk(node, depth: int, sector: str) -> None:
            if isinstance(node, list):
                for item in node:
                    code = _strip(item.get("symbol", ""))
                    name = item.get("name", "")
                    if code:
                        name_map.setdefault(code, name)
                        sector_map.setdefault(code, sector or "其他")
            elif isinstance(node, dict):
                for key, val in node.items():
                    if depth <= 0:
                        # depth=0: root keys "台灣"/"美國" — don't use as sector
                        _walk(val, 1, sector)
                    elif depth == 1:
                        # depth=1: country-level keys ARE the sectors ("半導體", "科技系統廠"…)
                        new_sec = _SECTOR_OVERRIDE.get(key, key)
                        _walk(val, 2, new_sec)
                    else:
                        # Deeper: inherit parent sector, with optional override
                        new_sec = _SECTOR_OVERRIDE.get(key, sector)
                        _walk(val, depth + 1, new_sec)

        _walk(WATCHLIST, 0, "")
    except Exception as e:
        logger.warning("WATCHLIST stock-map build failed: %s", e)

    # Supplement with extra stocks (don't override WATCHLIST entries)
    for code, (name, sector) in _EXTRA_STOCKS.items():
        name_map.setdefault(code, name)
        sector_map.setdefault(code, sector)

    official_names, official_sectors = _build_official_stock_maps()
    for code, name in official_names.items():
        if code not in name_map or _bad_stock_name(name_map.get(code, ""), code):
            name_map[code] = name
    for code, sector in official_sectors.items():
        if (
            code not in sector_map
            or sector_map.get(code) in _WATCHLIST_THEME_SECTORS
            or sector_map.get(code) == "其他"
        ):
            sector_map[code] = sector

    for code, (name, sector) in _US_STOCKS.items():
        name_map.setdefault(code, name)
        sector_map.setdefault(code, sector)

    return name_map, sector_map


def _get_stock_maps() -> tuple[dict[str, str], dict[str, str]]:
    """Return cached maps, building on first call."""
    global _name_map_cache, _sector_map_cache
    if _name_map_cache is None:
        _name_map_cache, _sector_map_cache = _build_stock_maps()
    return _name_map_cache, _sector_map_cache  # type: ignore[return-value]


def _enrich_holdings(holdings: list[dict]) -> list[dict]:
    """
    Enrich each holding:
      - Replace garbled / digit-only stock_name with proper Chinese name from maps
      - Add 'sector' field
    """
    nm, sm = _get_stock_maps()
    enriched = []
    for h in holdings:
        raw_name = h.get("stock_name", "")
        code = _normalise_code(h.get("stock_code", "")) or _extract_stock_code(raw_name)
        repaired_name = _strip_code_from_name(raw_name, code)
        if code and _bad_stock_name(repaired_name, code):
            repaired_name = nm.get(code, repaired_name)
        elif code and code in nm and _looks_latin1_mojibake(raw_name):
            repaired_name = nm[code]

        sector = sm.get(code, "其他") if code else "其他"
        goal_star_sector = _GOAL_STAR_INDUSTRY_SECTORS.get(str(h.get("goal_star_industry") or "").strip())
        if goal_star_sector and sector == "其他":
            sector = goal_star_sector
        enriched.append({
            **h,
            "stock_code": code,
            "stock_name": repaired_name or nm.get(code, code),
            "sector": sector,
        })
    return enriched


def _build_sector_breakdown(holdings: list[dict]) -> dict[str, dict]:
    sector_bd: dict[str, dict] = {}
    for h in holdings:
        sec = h.get("sector", "其他")
        if sec not in sector_bd:
            sector_bd[sec] = {"count": 0, "total_weight": 0.0}
        sector_bd[sec]["count"] += 1
        sector_bd[sec]["total_weight"] = round(
            sector_bd[sec]["total_weight"] + (h.get("weight_pct") or 0), 4
        )
    return dict(sorted(sector_bd.items(), key=lambda x: -x[1]["total_weight"]))


def _refresh_result_enrichment(result: dict) -> dict:
    holdings = _enrich_holdings(result.get("holdings", []))
    result["holdings"] = holdings
    if holdings:
        weighted = [h for h in holdings if h.get("weight_pct") is not None]
        result["top10_weight"] = round(sum(h["weight_pct"] for h in weighted[:10]), 2) if weighted else None
        result["total_holdings"] = len(holdings)
        result["sector_breakdown"] = _build_sector_breakdown(holdings)
    code = _normalise_code(result.get("code", ""))
    if code in ACTIVE_ETFS:
        result["code"] = code
        result["name"] = ACTIVE_ETFS[code]
        result["type"] = "bond" if code.endswith("D") else "stock"
    return result


# ── Cross-ETF sector summary for frontend ────────────────────────────────────

def _sector_color(name: str, index: int = 0) -> str:
    return SECTOR_COLORS.get(name) or _FALLBACK_SECTOR_COLORS[index % len(_FALLBACK_SECTOR_COLORS)]


def _as_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        n = float(value)
        if math.isnan(n) or math.isinf(n):
            return default
        return n
    except Exception:
        return default


def _date_only(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).strip()
    m = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if m:
        return m.group(0)
    return text[:10]


def _parse_date_key(value: str | None) -> datetime | None:
    text = _date_only(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except Exception:
        return None


def _active_stock_etf_codes() -> list[str]:
    return sorted(code for code in ACTIVE_ETFS if not code.endswith("D"))


def _goal_star_json_cache_path(kind: str, code: str, date_key: str = "") -> str:
    suffix = f"_{date_key}" if date_key else ""
    return os.path.join(CACHE_DIR, f"goal_star_{kind}_{_normalise_code(code)}{suffix}.json")


def _load_fresh_json(path: str, ttl: int) -> dict:
    if not os.path.exists(path):
        return {}
    if ttl > 0 and time.time() - os.path.getmtime(path) > ttl:
        return {}
    return _load_json(path)


def _goal_star_headers() -> dict:
    return {
        **_HEADERS,
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://goal-star.com/",
    }


def _goal_star_items(data) -> list[dict]:
    if isinstance(data, dict):
        items = data.get("items") or data.get("data") or data.get("shares") or []
    else:
        items = data or []
    return items if isinstance(items, list) else []


def _fetch_goal_star_fund_meta(code: str, force_refresh: bool = False) -> dict:
    code = _normalise_code(code)
    path = _goal_star_json_cache_path("fund_meta", code)
    if not force_refresh:
        cached = _load_fresh_json(path, STOCK_MASTER_CACHE_TTL)
        if cached:
            return cached

    try:
        resp = requests.get(
            f"{GOAL_STAR_BASE_URL}/api/funds/{code}",
            headers=_goal_star_headers(),
            timeout=15,
        )
        if resp.status_code != 200:
            data = {"code": code, "error": f"Goal Star HTTP {resp.status_code}", "status_code": resp.status_code}
        else:
            data = resp.json() if resp.content else {}
            if isinstance(data, dict):
                data = {**data, "code": code}
            else:
                data = {"code": code, "error": "Goal Star meta format error"}
    except Exception as exc:
        data = {"code": code, "error": str(exc)}

    data["fetched_at"] = datetime.now().isoformat()
    _save_json(path, data)
    return data


def _goal_star_holding_to_local(item: dict) -> dict:
    code = _normalise_code(
        item.get("stock_symbol")
        or item.get("stock_code")
        or item.get("symbol")
        or ""
    )
    shares = item.get("shares")
    try:
        shares = int(float(str(shares).replace(",", ""))) if shares not in (None, "") else None
    except Exception:
        shares = None
    return {
        "stock_code": code,
        "stock_name": item.get("stock_name") or item.get("name") or code,
        "shares": shares,
        "weight_pct": _as_float(item.get("ratio") or item.get("weight") or item.get("weight_pct")),
        "goal_star_industry": item.get("industry"),
    }


def _fetch_goal_star_fund_shares(
    code: str,
    date_key: str | None = None,
    *,
    force_refresh: bool = False,
) -> dict:
    code = _normalise_code(code)
    date_key = _date_only(date_key)
    cache_key = date_key or "latest"
    path = _goal_star_json_cache_path("fund_shares", code, cache_key)
    if not force_refresh:
        cached = _load_fresh_json(path, GOAL_STAR_CACHE_TTL)
        if cached:
            return cached

    params = {"date": date_key} if date_key else None
    try:
        resp = requests.get(
            f"{GOAL_STAR_BASE_URL}/api/funds/{code}/shares",
            params=params,
            headers=_goal_star_headers(),
            timeout=20,
        )
        if resp.status_code != 200:
            result = {
                "code": code,
                "name": ACTIVE_ETFS.get(code, code),
                "date": date_key,
                "holdings": [],
                "total_holdings": 0,
                "source": "goal_star",
                "error": f"Goal Star HTTP {resp.status_code}",
                "status_code": resp.status_code,
            }
        else:
            data = resp.json() if resp.content else {}
            raw_items = _goal_star_items(data)
            holdings = []
            actual_dates = set()
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                if item.get("date"):
                    actual_dates.add(_date_only(item.get("date")))
                holding = _goal_star_holding_to_local(item)
                if holding.get("stock_code") and _as_float(holding.get("weight_pct")) > 0:
                    holdings.append(holding)
            result = {
                "code": code,
                "name": ACTIVE_ETFS.get(code, code),
                "type": "stock",
                "date": max(actual_dates) if actual_dates else date_key,
                "requested_date": date_key,
                "holdings": _enrich_holdings(holdings),
                "total_holdings": len(holdings),
                "source": "goal_star",
            }
            if not holdings:
                result["error"] = "Goal Star returned no holdings"
    except Exception as exc:
        result = {
            "code": code,
            "name": ACTIVE_ETFS.get(code, code),
            "date": date_key,
            "holdings": [],
            "total_holdings": 0,
            "source": "goal_star",
            "error": str(exc),
        }

    result["fetched_at"] = datetime.now().isoformat()
    _save_json(path, result)
    return result


def _fetch_goal_star_nearest_holdings(code: str, target_dt: datetime) -> dict | None:
    for offset in range(GOAL_STAR_HISTORY_SCAN_DAYS + 1):
        date_key = (target_dt - timedelta(days=offset)).strftime("%Y-%m-%d")
        result = _fetch_goal_star_fund_shares(code, date_key)
        if result.get("holdings"):
            return result
    return None


def _load_cached_holdings_near_target(code: str, target_dt: datetime) -> dict | None:
    candidates = [_load_json(_curr_path(code)), _load_json(_prev_path(code))]
    valid = []
    for result in candidates:
        result_dt = _parse_date_key(result.get("date"))
        if not result_dt or not result.get("holdings"):
            continue
        if result_dt <= target_dt and (target_dt - result_dt).days <= GOAL_STAR_HISTORY_SCAN_DAYS:
            valid.append((result_dt, result))
    if not valid:
        return None
    _, result = max(valid, key=lambda item: item[0])
    result = _refresh_result_enrichment(dict(result))
    result["source"] = result.get("source") or "local_holdings_cache"
    return result


def _goal_star_sector_snapshot_for_period(
    current_date: str,
    period_key: str,
    days_back: int,
) -> tuple[dict | None, dict]:
    current_dt = _parse_date_key(current_date) or datetime.now()
    target_dt = current_dt - timedelta(days=days_back)
    target_date = target_dt.strftime("%Y-%m-%d")
    meta = {
        "available": False,
        "source": "goal_star_full_holdings",
        "target_date": target_date,
        "max_public_days": GOAL_STAR_FULL_HOLDINGS_MAX_DAYS,
    }
    if days_back > GOAL_STAR_FULL_HOLDINGS_MAX_DAYS:
        meta["reason"] = "full_holdings_history_not_public"
        return None, meta

    historical: dict[str, dict] = {}
    missing: list[str] = []
    not_listed: list[str] = []
    actual_dates: dict[str, str] = {}
    source_counts: dict[str, int] = defaultdict(int)
    for code in _active_stock_etf_codes():
        fund_meta = _fetch_goal_star_fund_meta(code)
        listed_dt = _parse_date_key(fund_meta.get("listed_date"))
        if listed_dt and listed_dt > target_dt:
            not_listed.append(code)
            continue
        result = _fetch_goal_star_nearest_holdings(code, target_dt)
        if not (result and result.get("holdings")):
            result = _load_cached_holdings_near_target(code, target_dt)
        if result and result.get("holdings"):
            historical[code] = result
            actual_dates[code] = _date_only(result.get("date"))
            source_counts[result.get("source") or "unknown"] += 1
        else:
            missing.append(code)

    meta.update({
        "etf_total": len(_active_stock_etf_codes()),
        "etf_success": len(historical),
        "etf_not_listed": len(not_listed),
        "etf_missing": len(missing),
        "actual_dates": actual_dates,
        "source_counts": dict(source_counts),
        "missing": missing[:12],
        "not_listed": not_listed[:12],
    })
    if not historical:
        meta["reason"] = "no_historical_holdings"
        return None, meta

    payload = _build_active_etf_sector_payload(historical, top_n=0, include_chart=False)
    payload["baseline_kind"] = "goal_star_full_holdings"
    payload["history_method_version"] = ETF_SECTOR_HISTORY_VERSION
    snapshot = _sector_summary_snapshot(payload)
    snapshot.update({
        "date": max((v for v in actual_dates.values() if v), default=target_date),
        "target_date": target_date,
        "baseline_kind": "goal_star_full_holdings",
        "period_key": period_key,
        "coverage": meta,
    })
    meta.update({
        "available": True,
        "date": snapshot.get("date"),
        "baseline_kind": snapshot.get("baseline_kind"),
    })
    return snapshot, meta


def _build_sector_chart_geometry(sectors: list[dict]) -> dict:
    """Return frontend pie-chart geometry; the browser draws the chart interactively."""
    width, height = 720, 520
    cx, cy, radius = 260, 260, 210
    total = sum(_as_float(s.get("total_weight")) for s in sectors)
    if total <= 0:
        return {
            "width": width,
            "height": height,
            "center_x": cx,
            "center_y": cy,
            "radius": radius,
            "slices": [],
        }

    start = -90.0
    slices = []

    for index, sector in enumerate(sectors):
        weight = _as_float(sector.get("total_weight"))
        if weight <= 0:
            continue
        span = weight / total * 360.0
        end = start + span
        color = sector.get("color") or _sector_color(sector.get("name", "其他"), index)

        mid = start + span / 2.0
        rad = math.radians(mid)
        # Keep labels slightly outside tiny slices so they remain selectable/readable.
        label_radius = radius * (0.66 if span >= 18 else 0.88)
        slices.append({
            "name": sector.get("name", "其他"),
            "color": color,
            "pct": round(weight / total * 100.0, 2),
            "total_weight": round(weight, 4),
            "start_deg": round((start + 90.0) % 360.0, 4),
            "end_deg": round((end + 90.0) % 360.0, 4),
            "mid_deg": round((mid + 90.0) % 360.0, 4),
            "label_x": round((cx + label_radius * math.cos(rad)) / width, 4),
            "label_y": round((cy + label_radius * math.sin(rad)) / height, 4),
        })
        start = end

    return {
        "width": width,
        "height": height,
        "center_x": cx,
        "center_y": cy,
        "radius": radius,
        "slices": slices,
    }


def _build_active_etf_sector_payload(
    all_holdings: dict[str, dict],
    *,
    top_n: int = 20,
    include_chart: bool = True,
) -> dict:
    sectors: dict[str, dict] = {}
    etf_summaries = []
    latest_date = ""
    total_positions = 0
    stock_etf_count = 0
    errors = []

    for etf_code, raw_info in sorted((all_holdings or {}).items()):
        info = raw_info or {}
        if etf_code.endswith("D"):
            continue
        if info.get("error") or not info.get("holdings"):
            if info.get("error"):
                errors.append({"code": etf_code, "error": info.get("error")})
            continue

        info = _refresh_result_enrichment(info)
        holdings = info.get("holdings") or []
        stock_etf_count += 1
        total_positions += len(holdings)
        date_key = _date_only(info.get("date"))
        if date_key and (not latest_date or date_key > latest_date):
            latest_date = date_key

        etf_sector_weights: dict[str, float] = defaultdict(float)
        for holding in holdings:
            weight = _as_float(holding.get("weight_pct"))
            if weight <= 0:
                continue
            sector_name = holding.get("sector") or "其他"
            if sector_name not in sectors:
                sectors[sector_name] = {
                    "name": sector_name,
                    "total_weight": 0.0,
                    "positions": 0,
                    "etf_codes": set(),
                    "stocks": {},
                }
            sector = sectors[sector_name]
            sector["total_weight"] += weight
            sector["positions"] += 1
            sector["etf_codes"].add(etf_code)
            etf_sector_weights[sector_name] += weight

            stock_code = _normalise_code(holding.get("stock_code", "")) or holding.get("stock_name") or "UNKNOWN"
            stock_name = holding.get("stock_name") or stock_code
            stocks = sector["stocks"]
            if stock_code not in stocks:
                stocks[stock_code] = {
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "total_weight": 0.0,
                    "etfs": [],
                }
            stock = stocks[stock_code]
            stock["total_weight"] += weight
            stock["etfs"].append({
                "code": etf_code,
                "name": info.get("name") or ACTIVE_ETFS.get(etf_code, etf_code),
                "weight": round(weight, 4),
            })

        top_sectors = [
            {"name": name, "weight": round(weight, 4)}
            for name, weight in sorted(etf_sector_weights.items(), key=lambda x: -x[1])[:3]
        ]
        etf_summaries.append({
            "code": etf_code,
            "name": info.get("name") or ACTIVE_ETFS.get(etf_code, etf_code),
            "date": date_key,
            "holdings": len(holdings),
            "top10_weight": info.get("top10_weight"),
            "top_sectors": top_sectors,
            "top_holdings": holdings[:5],
        })

    total_weight = sum(_as_float(s.get("total_weight")) for s in sectors.values())
    sector_list = []
    for index, sector in enumerate(sorted(sectors.values(), key=lambda x: -x["total_weight"])):
        sector_total = _as_float(sector.get("total_weight"))
        sector_pct = sector_total / total_weight * 100.0 if total_weight else 0.0
        stocks = []
        for stock in sorted(sector["stocks"].values(), key=lambda x: -x["total_weight"])[:top_n]:
            stock_total = _as_float(stock.get("total_weight"))
            etfs = sorted(stock["etfs"], key=lambda x: -_as_float(x.get("weight")))
            stocks.append({
                "stock_code": stock.get("stock_code"),
                "stock_name": stock.get("stock_name"),
                "total_weight": round(stock_total, 4),
                "sector_pct": round(stock_total / sector_total * 100.0, 2) if sector_total else 0.0,
                "total_pct": round(stock_total / total_weight * 100.0, 2) if total_weight else 0.0,
                "etf_count": len(etfs),
                "etfs": etfs,
            })
        sector_list.append({
            "name": sector["name"],
            "color": _sector_color(sector["name"], index),
            "total_weight": round(sector_total, 4),
            "pct": round(sector_pct, 2),
            "positions": sector["positions"],
            "etf_count": len(sector["etf_codes"]),
            "stock_count": len(sector["stocks"]),
            "stocks": stocks,
            "changes": {},
        })

    payload = {
        "date": latest_date or datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().isoformat(),
        "last_updated": _time_text(),
        "history_method_version": ETF_SECTOR_HISTORY_VERSION,
        "method": "各股票型主動式ETF持股權重直接加總，再按全部持股權重換算產業占比；未依ETF規模加權。",
        "stock_etf_count": stock_etf_count,
        "sector_count": len(sector_list),
        "total_positions": total_positions,
        "total_weight": round(total_weight, 4),
        "sectors": sector_list,
        "etf_summaries": sorted(etf_summaries, key=lambda x: x["code"]),
        "errors": errors,
    }
    payload["chart"] = _build_sector_chart_geometry(sector_list) if include_chart else {}
    return payload


def _sector_summary_snapshot(payload: dict) -> dict:
    return {
        "date": payload.get("date"),
        "generated_at": payload.get("generated_at"),
        "baseline_kind": payload.get("baseline_kind", "sector_snapshot"),
        "history_method_version": payload.get("history_method_version", ETF_SECTOR_HISTORY_VERSION),
        "total_weight": payload.get("total_weight", 0),
        "sectors": {
            s.get("name"): {
                "total_weight": s.get("total_weight", 0),
                "pct": s.get("pct", 0),
                "etf_count": s.get("etf_count", 0),
                "stock_count": s.get("stock_count", 0),
            }
            for s in payload.get("sectors", [])
            if s.get("name")
        },
    }


def _sector_snapshot_path(date_key: str) -> str:
    return os.path.join(CACHE_DIR, f"etf_sector_summary_{date_key}.json")


def _is_real_sector_snapshot(snapshot: dict) -> bool:
    if not snapshot or not snapshot.get("sectors"):
        return False
    return (
        snapshot.get("baseline_kind") != "start_zero"
        and snapshot.get("history_method_version") == ETF_SECTOR_HISTORY_VERSION
    )


def _find_sector_snapshot(current_date: str, days_back: int) -> dict | None:
    current_dt = _parse_date_key(current_date) or datetime.now()
    target = current_dt - timedelta(days=days_back)
    start_dt = _parse_date_key(ETF_SECTOR_BASELINE_START_DATE)
    candidates = []
    for path in glob.glob(os.path.join(CACHE_DIR, "etf_sector_summary_*.json")):
        name = os.path.basename(path)
        m = re.search(r"etf_sector_summary_(\d{4}-\d{2}-\d{2})\.json$", name)
        if not m:
            continue
        snap_dt = _parse_date_key(m.group(1))
        if start_dt and snap_dt and snap_dt < start_dt:
            continue
        if snap_dt and snap_dt <= target:
            candidates.append((snap_dt, path))
    if not candidates:
        return None
    _, path = max(candidates, key=lambda item: item[0])
    snap = _load_json(path)
    return snap if _is_real_sector_snapshot(snap) else None


def _prev_day_sector_snapshot(all_holdings: dict[str, dict]) -> dict | None:
    prev_all: dict[str, dict] = {}
    for etf_code in all_holdings:
        if etf_code.endswith("D"):
            continue
        prev = _load_json(_prev_path(etf_code))
        if prev.get("holdings"):
            prev_all[etf_code] = prev
    if not prev_all:
        return None
    payload = _build_active_etf_sector_payload(prev_all, top_n=0, include_chart=False)
    payload["baseline_kind"] = "previous_holdings_cache"
    payload["history_method_version"] = ETF_SECTOR_HISTORY_VERSION
    return _sector_summary_snapshot(payload)


def _sector_baseline_for_period(
    payload: dict,
    all_holdings: dict[str, dict],
    period_key: str,
    days_back: int,
) -> tuple[dict | None, dict]:
    meta = {
        "available": False,
        "period_key": period_key,
        "days_back": days_back,
        "target_date": None,
        "source": None,
    }
    current_dt = _parse_date_key(payload.get("date")) or datetime.now()
    meta["target_date"] = (current_dt - timedelta(days=days_back)).strftime("%Y-%m-%d")

    baseline = _find_sector_snapshot(payload.get("date"), days_back)
    if _is_real_sector_snapshot(baseline or {}):
        meta.update({
            "available": True,
            "date": baseline.get("date"),
            "source": baseline.get("baseline_kind", "sector_snapshot"),
            "baseline_kind": baseline.get("baseline_kind", "sector_snapshot"),
        })
        if baseline.get("coverage"):
            meta.update(baseline.get("coverage"))
        return baseline, meta

    goal_star_snapshot, goal_star_meta = _goal_star_sector_snapshot_for_period(
        payload.get("date"),
        period_key,
        days_back,
    )
    if _is_real_sector_snapshot(goal_star_snapshot or {}):
        date_key = _date_only(goal_star_snapshot.get("date"))
        if date_key:
            _save_json(_sector_snapshot_path(date_key), goal_star_snapshot)
        return goal_star_snapshot, goal_star_meta
    meta.update(goal_star_meta)

    if period_key == "day":
        baseline = _prev_day_sector_snapshot(all_holdings)
        if _is_real_sector_snapshot(baseline or {}):
            meta.update({
                "available": True,
                "date": baseline.get("date"),
                "source": baseline.get("baseline_kind", "previous_holdings_cache"),
                "baseline_kind": baseline.get("baseline_kind", "previous_holdings_cache"),
            })
            return baseline, meta

    return None, meta


def _calc_sector_change(sector: dict, baseline: dict | None) -> dict:
    if not baseline or not baseline.get("sectors"):
        return {
            "available": False,
            "baseline_date": None,
            "previous_pct": None,
            "delta_pct_points": None,
            "previous_weight": None,
            "delta_weight": None,
        }
    base_sector = baseline.get("sectors", {}).get(sector.get("name")) or {}
    previous_pct = _as_float(base_sector.get("pct"))
    previous_weight = _as_float(base_sector.get("total_weight"))
    return {
        "available": True,
        "baseline_date": baseline.get("date"),
        "previous_pct": round(previous_pct, 2),
        "delta_pct_points": round(_as_float(sector.get("pct")) - previous_pct, 2),
        "previous_weight": round(previous_weight, 4),
        "delta_weight": round(_as_float(sector.get("total_weight")) - previous_weight, 4),
        "baseline_kind": baseline.get("baseline_kind", "snapshot"),
        "coverage": baseline.get("coverage"),
    }


def fetch_etf_sector_summary(force_refresh: bool = False, holdings_refresh: bool = False) -> dict:
    """
    Return a backend-prepared active ETF sector summary for the frontend:
    clickable pie-chart geometry, sector changes, and top-20 companies.
    """
    summary_cache = os.path.join(CACHE_DIR, "etf_sector_summary_latest.json")
    if not force_refresh and os.path.exists(summary_cache):
        age = time.time() - os.path.getmtime(summary_cache)
        if age < 10 * 60:
            cached = _load_json(summary_cache)
            cached_periods = set()
            if cached.get("sectors"):
                cached_periods = set((cached["sectors"][0].get("changes") or {}).keys())
            has_start_zero = any(
                (change or {}).get("baseline_kind") == "start_zero"
                for sector in cached.get("sectors", [])
                for change in (sector.get("changes") or {}).values()
            )
            if (
                cached.get("history_method_version") == ETF_SECTOR_HISTORY_VERSION
                and cached.get("sectors")
                and cached.get("chart")
                and "image" not in cached.get("chart", {})
                and all(key in cached_periods for key in SECTOR_CHANGE_PERIODS)
                and not has_start_zero
            ):
                return _with_last_updated(cached, summary_cache)

    all_holdings = fetch_all_etf_holdings(force_refresh=holdings_refresh)
    payload = _build_active_etf_sector_payload(all_holdings, top_n=20, include_chart=True)
    payload["history_method_version"] = ETF_SECTOR_HISTORY_VERSION
    payload["baseline_kind"] = "current_sector_snapshot"

    baseline_pairs = {
        key: _sector_baseline_for_period(payload, all_holdings, key, days_back)
        for key, days_back in SECTOR_CHANGE_PERIODS.items()
    }
    baselines = {key: value for key, (value, _meta) in baseline_pairs.items()}
    payload["change_sources"] = {key: meta for key, (_value, meta) in baseline_pairs.items()}
    for sector in payload.get("sectors", []):
        sector["changes"] = {
            key: _calc_sector_change(sector, baseline)
            for key, baseline in baselines.items()
        }

    snapshot = _sector_summary_snapshot(payload)
    date_key = _date_only(payload.get("date")) or datetime.now().strftime("%Y-%m-%d")
    _save_json(_sector_snapshot_path(date_key), snapshot)
    _with_last_updated(payload)
    _save_json(summary_cache, payload)
    return payload


# ── MoneyDJ scraper (primary) ─────────────────────────────────────────────────

def _moneydj_url(code: str) -> str:
    return (
        f"https://www.moneydj.com/ETF/X/Basic/Basic0007B.xdjhtm"
        f"?etfid={code}.TW"
    )


def _find_moneydj_holdings_table(tables: list[pd.DataFrame]) -> pd.DataFrame | None:
    """
    Content-based detection for MoneyDJ holdings table.

    MoneyDJ's new page layout has garbled/mojibake column headers but the DATA
    columns are always: [name+code_combined, weight_float, shares_int_or_nan].

    Stock ETFs: col[1]=weight, col[2]=shares (integer)
    Bond ETFs:  col[1]=weight, col[2]=NaN (no share counts for bonds)

    We detect by: col[1] is numeric with values 0-100, table has >= 5 rows.
    """
    best: pd.DataFrame | None = None
    best_score = 0
    for df in tables:
        if df.shape[1] < 2 or len(df) < 5:
            continue
        try:
            weights = pd.to_numeric(df.iloc[:, 1], errors="coerce")
            valid_w = weights.dropna()
            if len(valid_w) < 5 or float(valid_w.between(0, 100).mean()) <= 0.8:
                continue
            # Score: prefer tables with share counts in col[2]
            score = len(valid_w)
            if df.shape[1] >= 3:
                shares = pd.to_numeric(df.iloc[:, 2], errors="coerce")
                valid_s = shares.dropna()
                if len(valid_s) >= 5 and float(valid_s.gt(0).mean()) > 0.8:
                    score += 1000   # strongly prefer tables with shares
            if score > best_score:
                best_score = score
                best = df
        except Exception:
            continue
    return best


def _parse_moneydj_holdings(df: pd.DataFrame) -> list[dict]:
    """
    Parse MoneyDJ's 3-column holdings table:
      col[0]: 'Lam Research(LRCX.US)' or '4063.JP' style combined name+code
      col[1]: weight percentage (float)
      col[2]: shares held (integer)
    """
    holdings = []
    for _, row in df.iterrows():
        name_code = str(row.iloc[0]).strip()
        weight    = pd.to_numeric(row.iloc[1], errors="coerce")
        shares_v  = pd.to_numeric(row.iloc[2], errors="coerce")

        if pd.isna(weight) or name_code in ("nan", ""):
            continue

        # Extract code from parentheses: "Name(CODE.US)" or "(4063.JP)"
        m_code = re.search(r"\(([A-Z0-9]{1,8})\.[A-Z]{2}\)", name_code)
        stock_code = m_code.group(1) if m_code else ""

        # Clean name: strip trailing (CODE.XX) if present
        stock_name = re.sub(r"\s*\([^)]+\)\s*$", "", name_code).strip()
        if not stock_name:
            stock_name = name_code

        shares = int(shares_v) if not pd.isna(shares_v) else None

        if not stock_name and not stock_code:
            continue

        holdings.append({
            "stock_code": stock_code,
            "stock_name": stock_name,
            "weight_pct": round(float(weight), 4),
            "shares":     shares,
        })

    holdings.sort(
        key=lambda h: h["weight_pct"] if h["weight_pct"] is not None else -1,
        reverse=True,
    )
    return holdings


def _scrape_moneydj(code: str) -> tuple[str, list[dict]]:
    """
    Scrape MoneyDJ ETF holdings page.
    Returns (date_str "YYYY-MM-DD", holdings_list).
    Returns ("", []) on failure.

    Detection strategy: MoneyDJ now renders column headers in mojibake
    (garbled encoding), so we use content-based table detection instead of
    header-keyword matching.
    """
    url = _moneydj_url(code)
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20, verify=False)
        resp.raise_for_status()
        if resp.encoding and resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
    except Exception as e:
        logger.warning("MoneyDJ fetch failed %s: %s", code, e)
        return "", []

    # ── Extract date ──────────────────────────────────────────────────────────
    date_str = ""
    m = re.search(r"資料日期[：:]\s*(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", html)
    if not m:
        # Also try encoded date pattern
        m = re.search(r"(\d{4})/(\d{2})/(\d{2})", html)
    if m:
        y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
        date_str = f"{y}-{mo}-{d}"
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # ── Parse tables ──────────────────────────────────────────────────────────
    tables: list[pd.DataFrame] = []
    try:
        tables = pd.read_html(io.StringIO(html), flavor="lxml")
    except Exception:
        try:
            tables = pd.read_html(io.StringIO(html))
        except Exception as e2:
            logger.warning("pd.read_html failed for %s: %s", code, e2)

    # Try content-based detection first (handles garbled column headers)
    df = _find_moneydj_holdings_table(tables)
    if df is not None:
        holdings = _parse_moneydj_holdings(df)
        logger.info("MoneyDJ %s: %d holdings (content-detect), date=%s", code, len(holdings), date_str)
        return date_str, holdings

    # Fallback: legacy keyword-based detection
    df = _find_holdings_table(tables)
    if df is None:
        logger.info("No holdings table found on MoneyDJ for %s", code)
        return date_str, []

    holdings = _parse_holdings_df(df)
    logger.info("MoneyDJ %s: %d holdings (keyword-detect), date=%s", code, len(holdings), date_str)
    return date_str, holdings


def _parse_etfinfo_code(raw: str) -> tuple[str, str]:
    """
    Extract (stock_code, stock_name) from etfinfo.tw combined cell.

    etfinfo.tw renders code+name without separator, e.g.:
      'LRCX科林研發股份有限公司'  → ('LRCX', '科林研發股份有限公司')
      '4063信越化學工業'          → ('4063', '信越化學工業')
      'LINLinde PLC'             → ('LIN', 'Linde PLC')

    Rules:
      1. Leading 4+ digits = TW/JP numeric ticker
      2. Leading uppercase ASCII before first CJK character = ticker
      3. Leading uppercase ASCII before first lowercase letter = ticker
      4. Fallback: up to 5 leading uppercase/digits
    """
    if not raw or raw in ("nan", "NaN", "—", "-"):
        return "", raw

    # Rule 1: 4–6 leading digits (TW/JP codes)
    m = re.match(r"^(\d{4,6})(.*)", raw)
    if m:
        return m.group(1), m.group(2).strip()

    # Rule 2: uppercase/digits before first CJK char
    m = re.match(r"^([A-Z][A-Z0-9]*)(?=[一-鿿぀-ゟ゠-ヿ])", raw)
    if m:
        return m.group(1), raw[len(m.group(1)):].strip()

    # Rule 3: uppercase/digits before first lowercase letter (e.g. 'LINLinde PLC')
    m = re.match(r"^([A-Z][A-Z0-9]*)(?=[a-z])", raw)
    if m:
        return m.group(1), raw[len(m.group(1)):].strip()

    # Rule 4: fallback – take up to 5 leading uppercase chars/digits
    m = re.match(r"^([A-Z0-9]{1,5})", raw)
    if m:
        code = m.group(1)
        return code, raw[len(code):].strip()

    return "", raw.strip()


def _parse_etfinfo_weight_shares(raw: str) -> tuple[float | None, int | None]:
    """
    Parse etfinfo.tw combined weight+shares cell, e.g. '7.14%90,500'.
    Returns (weight_pct, shares).
    """
    raw = raw.strip()
    m = re.match(r"([\d.]+)%\s*([\d,]+)", raw)
    if m:
        try:
            weight = float(m.group(1))
            shares = int(m.group(2).replace(",", ""))
            return weight, shares
        except ValueError:
            pass
    # Fallback: try to extract just a weight percentage
    m2 = re.match(r"([\d.]+)%", raw)
    if m2:
        try:
            return float(m2.group(1)), None
        except ValueError:
            pass
    return None, None


# ── etfinfo.tw scraper (fallback) ─────────────────────────────────────────────

def _scrape_etfinfo(code: str) -> tuple[str, list[dict]]:
    """
    Scrape etfinfo.tw holdings page as fallback.
    Returns (date_str, holdings_list).

    etfinfo.tw combines (code+name) in col[0] and (weight%+shares) in col[2],
    requiring specialised parsing beyond the generic _parse_holdings_df().
    """
    url = f"https://www.etfinfo.tw/etf/{code}/holdings"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20, verify=False)
        resp.raise_for_status()
        if resp.encoding and resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
    except Exception as e:
        logger.warning("etfinfo fetch failed %s: %s", code, e)
        return "", []

    # Extract date
    date_str = ""
    m = re.search(r"(\d{4})[/-](\d{2})[/-](\d{2})", html)
    if m:
        date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # etfinfo.tw sometimes has encoding issues with later tables; use lxml
    # which reliably parses at least the first (holdings) table
    tables: list[pd.DataFrame] = []
    try:
        tables = pd.read_html(io.StringIO(html), flavor="lxml")
    except Exception as e:
        logger.warning("etfinfo pd.read_html failed %s: %s", code, e)

    if not tables:
        return date_str, []

    # etfinfo format: 4-col table [code+name | price | weight%+shares | contribution]
    # Identify the right table: >=3 rows, col[2] matches 'N.NN%M,MMM' pattern
    target_df: pd.DataFrame | None = None
    for df in tables:
        if df.shape[1] < 3 or len(df) < 3:
            continue
        # Check if col[2] values look like combined weight%shares
        sample = df.iloc[:, 2].astype(str).head(3)
        if sample.str.contains(r"\d+\.\d+%\d", regex=True).any():
            target_df = df
            break

    if target_df is None:
        # Fallback: use generic parsing on first available table
        df = _find_holdings_table(tables)
        if df is None:
            return date_str, []
        holdings = _parse_holdings_df(df)
        logger.info("etfinfo.tw %s: %d holdings (generic), date=%s", code, len(holdings), date_str)
        return date_str, holdings

    holdings = []
    for _, row in target_df.iterrows():
        raw_name_code = str(row.iloc[0]).strip()
        raw_ws        = str(row.iloc[2]).strip()

        stock_code, stock_name = _parse_etfinfo_code(raw_name_code)
        weight, shares = _parse_etfinfo_weight_shares(raw_ws)

        if not stock_name and not stock_code:
            continue
        if raw_name_code in ("nan", "NaN", "—", "-", ""):
            continue

        holdings.append({
            "stock_code": stock_code,
            "stock_name": stock_name,
            "weight_pct": round(weight, 4) if weight is not None else None,
            "shares":     shares,
        })

    holdings.sort(
        key=lambda h: h["weight_pct"] if h["weight_pct"] is not None else -1,
        reverse=True,
    )
    logger.info("etfinfo.tw %s: %d holdings (structured), date=%s", code, len(holdings), date_str)
    return date_str, holdings


# ── Snapshot & change-detection ───────────────────────────────────────────────

def _curr_path(code: str) -> str:
    return os.path.join(CACHE_DIR, f"etf_holdings_{code}.json")

def _prev_path(code: str) -> str:
    return os.path.join(CACHE_DIR, f"etf_holdings_{code}_prev.json")


def _load_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_json(path: str, data: dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("save_json failed %s: %s", path, e)


def compute_changes(prev_result: dict, curr_result: dict) -> dict:
    """
    Compare previous and current holdings by shares count.
    Returns:
        {
          new_positions:  [holding dicts],      # in curr but not prev
          exited:         [holding dicts],       # in prev but not curr
          increased:      [{...holding, shares_delta, prev_shares}],
          decreased:      [{...holding, shares_delta, prev_shares}],
          unchanged_count: int,
          prev_date:  str,
          curr_date:  str,
        }
    """
    prev_holdings = prev_result.get("holdings", [])
    curr_holdings = curr_result.get("holdings", [])

    prev_map = {h["stock_code"]: h for h in prev_holdings if h.get("stock_code")}
    curr_map = {h["stock_code"]: h for h in curr_holdings if h.get("stock_code")}

    new_positions, exited, increased, decreased, unchanged_count = [], [], [], [], 0

    def _change_abs(row: dict) -> float:
        val = row.get("shares_delta")
        if val is None:
            val = row.get("weight_delta")
        try:
            return abs(float(val))
        except Exception:
            return 0.0

    for sc, curr in curr_map.items():
        if sc not in prev_map:
            new_positions.append(curr)
        else:
            prev = prev_map[sc]
            cs = curr.get("shares")
            ps = prev.get("shares")
            if cs is not None and ps is not None:
                delta = int(cs or 0) - int(ps or 0)
                if delta > 0:
                    increased.append({**curr, "shares_delta": delta, "prev_shares": ps, "change_basis": "shares"})
                elif delta < 0:
                    decreased.append({**curr, "shares_delta": delta, "prev_shares": ps, "change_basis": "shares"})
                else:
                    unchanged_count += 1
                continue

            cw = _as_float(curr.get("weight_pct"))
            pw = _as_float(prev.get("weight_pct"))
            weight_delta = round(cw - pw, 4)
            if weight_delta > 0.005:
                increased.append({
                    **curr,
                    "weight_delta": weight_delta,
                    "prev_weight_pct": pw,
                    "change_basis": "weight",
                })
            elif weight_delta < -0.005:
                decreased.append({
                    **curr,
                    "weight_delta": weight_delta,
                    "prev_weight_pct": pw,
                    "change_basis": "weight",
                })
            else:
                unchanged_count += 1

    for sc in prev_map:
        if sc not in curr_map:
            exited.append(prev_map[sc])

    # Sort by absolute delta size
    increased.sort(key=_change_abs, reverse=True)
    decreased.sort(key=_change_abs, reverse=True)

    return {
        "available":       True,
        "new_positions":   new_positions,
        "exited":          exited,
        "increased":       increased,
        "decreased":       decreased,
        "unchanged_count": unchanged_count,
        "prev_date":       prev_result.get("date", ""),
        "curr_date":       curr_result.get("date", ""),
    }


# ── Main public interface ─────────────────────────────────────────────────────

def fetch_etf_holdings(etf_code: str, force_refresh: bool = False) -> dict:
    """
    Fetch portfolio holdings for one active ETF.

    Returns:
        {
          code, name, type, date,
          holdings: [{stock_code, stock_name, shares, weight_pct}],
          top10_weight, total_holdings, fetched_at,
          changes: {new_positions, exited, increased, decreased, ...},
          error?
        }
    """
    code_upper = etf_code.upper().replace(".TW", "")
    curr_p     = _curr_path(code_upper)
    prev_p     = _prev_path(code_upper)

    # ── Serve from cache if fresh ─────────────────────────────────────────────
    if not force_refresh and os.path.exists(curr_p):
        age = time.time() - os.path.getmtime(curr_p)
        if age < HOLDINGS_CACHE_TTL:
            cached = _load_json(curr_p)
            if cached.get("holdings") or cached.get("error"):
                # Only re-enrich if data lacks sector field (wasn't enriched yet)
                # This avoids expensive re-processing on every cache-read
                if cached.get("holdings"):
                    first_holding = cached["holdings"][0] if cached["holdings"] else None
                    if first_holding and "sector" not in first_holding:
                        logger.debug("%s cache missing sector field, enriching...", code_upper)
                        cached = _refresh_result_enrichment(cached)
                    if not cached.get("changes") or (cached.get("changes") or {}).get("available") is False:
                        prev_data = _load_json(prev_p)
                        change_source = "local_prev_snapshot"
                        if not prev_data.get("holdings"):
                            curr_dt = _parse_date_key(cached.get("date"))
                            if curr_dt:
                                target_dt = curr_dt - timedelta(days=1)
                                prev_data = (
                                    _load_cached_holdings_near_target(code_upper, target_dt)
                                    or _fetch_goal_star_nearest_holdings(code_upper, target_dt)
                                    or {}
                                )
                                if prev_data.get("holdings"):
                                    change_source = prev_data.get("source") or "historical_holdings"
                                    _save_json(prev_p, prev_data)
                        if prev_data.get("holdings") and prev_data.get("date") != cached.get("date"):
                            cached["changes"] = compute_changes(prev_data, cached)
                            cached["changes"]["source"] = change_source
                            _save_json(curr_p, cached)
                return _with_last_updated(cached, curr_p)

    name     = ACTIVE_ETFS.get(code_upper, code_upper)
    etf_type = "bond" if code_upper.endswith("D") else "stock"

    # ── Fetch from sources ───────────────────────────────────────────────────
    date_str, holdings = _scrape_moneydj(code_upper)
    if not holdings:
        logger.info("%s MoneyDJ empty — trying etfinfo.tw fallback", code_upper)
        date_str, holdings = _scrape_etfinfo(code_upper)

    if not holdings:
        result = {
            "code":           code_upper,
            "name":           name,
            "type":           etf_type,
            "date":           date_str or datetime.now().strftime("%Y-%m-%d"),
            "holdings":       [],
            "top10_weight":   None,
            "total_holdings": 0,
            "fetched_at":     datetime.now().isoformat(),
            "error":          "無法取得投資組合（MoneyDJ + etfinfo 均失敗）",
        }
        _with_last_updated(result)
        _save_json(curr_p, result)
        return result

    # ── Enrich names + add sector field ──────────────────────────────────────
    holdings = _enrich_holdings(holdings)

    # ── Compute top-10 weight ─────────────────────────────────────────────────
    weighted = [h for h in holdings if h.get("weight_pct") is not None]
    top10_w  = round(sum(h["weight_pct"] for h in weighted[:10]), 2) if weighted else None

    # ── Sector breakdown ──────────────────────────────────────────────────────
    sector_breakdown = _build_sector_breakdown(holdings)

    result = {
        "code":             code_upper,
        "name":             name,
        "type":             etf_type,
        "date":             date_str,
        "holdings":         holdings,
        "top10_weight":     top10_w,
        "total_holdings":   len(holdings),
        "fetched_at":       datetime.now().isoformat(),
        "sector_breakdown": sector_breakdown,
    }

    # ── Snapshot rotation & change detection ─────────────────────────────────
    prev_result = _load_json(curr_p)
    if prev_result.get("holdings") and prev_result.get("date") != date_str:
        # New trading day data arrived — rotate current → prev
        shutil.copy2(curr_p, prev_p)
        logger.info("%s new date %s (prev %s) — snapshot rotated",
                    code_upper, date_str, prev_result.get("date"))

    # Attach change summary if we have a previous snapshot with share data
    prev_data = _load_json(prev_p)
    change_source = "local_prev_snapshot"

    if not prev_data.get("holdings"):
        curr_dt = _parse_date_key(date_str)
        if curr_dt:
            target_dt = curr_dt - timedelta(days=1)
            prev_data = (
                _load_cached_holdings_near_target(code_upper, target_dt)
                or _fetch_goal_star_nearest_holdings(code_upper, target_dt)
                or {}
            )
            if prev_data.get("holdings"):
                change_source = prev_data.get("source") or "historical_holdings"
                _save_json(prev_p, prev_data)

    if prev_data.get("holdings") and prev_data.get("date") != date_str:
        result["changes"] = compute_changes(prev_data, result)
        result["changes"]["source"] = change_source
    else:
        result["changes"] = {
            "available": False,
            "reason": "尚未取得前一交易日持倉，後端會在下一次定時刷新或手動刷新時繼續補齊",
            "new_positions": [],
            "exited": [],
            "increased": [],
            "decreased": [],
            "unchanged_count": 0,
            "prev_date": prev_data.get("date", "") if isinstance(prev_data, dict) else "",
            "curr_date": date_str,
        }

    _with_last_updated(result)
    _save_json(curr_p, result)
    return result


def fetch_all_etf_holdings(force_refresh: bool = False) -> dict[str, dict]:
    """
    Fetch holdings for every active ETF in ACTIVE_ETFS.
    Returns {etf_code: result_dict}.
    """
    all_cache = os.path.join(CACHE_DIR, "etf_holdings_ALL.json")
    if not force_refresh and os.path.exists(all_cache):
        age = time.time() - os.path.getmtime(all_cache)
        if age < ALL_CACHE_TTL:
            try:
                with open(all_cache, encoding="utf-8") as f:
                    cached_all = json.load(f)
                for code, item in list(cached_all.items()):
                    if isinstance(item, dict):
                        _with_last_updated(item, _curr_path(code))
                logger.info("All ETF holdings cache hit (age=%.1fs, TTL=%d)", age, ALL_CACHE_TTL)
                return cached_all
            except Exception:
                pass

    logger.info("Fetching all active ETF holdings (%d ETFs)...", len(ACTIVE_ETFS))
    results: dict[str, dict] = {}
    for code in ACTIVE_ETFS:
        try:
            results[code] = fetch_etf_holdings(code, force_refresh=force_refresh)
            logger.info("  %s: %d holdings, date=%s",
                        code,
                        results[code].get("total_holdings", 0),
                        results[code].get("date", ""))
        except Exception as e:
            logger.warning("  %s error: %s", code, e)
            results[code] = {
                "code": code, "name": ACTIVE_ETFS[code],
                "holdings": [], "total_holdings": 0,
                "last_updated": _time_text(),
                "error": str(e),
            }
        time.sleep(0.5)   # polite delay between MoneyDJ requests (reduced from 1.2s)

    try:
        with open(all_cache, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False)
    except Exception:
        pass

    logger.info("Active ETF holdings refresh complete.")
    return results


# ── Cross-ETF analysis ────────────────────────────────────────────────────────

def cross_etf_common_holdings(all_holdings: dict[str, dict],
                               min_etfs: int = 2) -> list[dict]:
    """
    Find stocks held by >= min_etfs active ETFs simultaneously.
    Returns list of {stock_code, stock_name, etf_count, etfs, total_shares, avg_weight}.
    """
    stock_info: dict[str, dict] = defaultdict(lambda: {
        "stock_name": "",
        "etfs": [],
        "total_shares": 0,
        "weights": [],
    })

    for code, info in all_holdings.items():
        if info.get("error") or not info.get("holdings"):
            continue
        for h in info["holdings"]:
            sc = h.get("stock_code", "")
            if not sc:
                continue
            si = stock_info[sc]
            si["stock_name"] = h.get("stock_name", "")
            si["etfs"].append(code)
            si["total_shares"] += h.get("shares") or 0
            if h.get("weight_pct") is not None:
                si["weights"].append(h["weight_pct"])

    result = []
    for sc, si in stock_info.items():
        if len(si["etfs"]) >= min_etfs:
            result.append({
                "stock_code":   sc,
                "stock_name":   si["stock_name"],
                "etf_count":    len(si["etfs"]),
                "etfs":         si["etfs"],
                "total_shares": si["total_shares"],
                "avg_weight":   round(sum(si["weights"]) / len(si["weights"]), 2)
                                if si["weights"] else None,
            })

    result.sort(key=lambda x: x["etf_count"], reverse=True)
    return result


# ── Email HTML section ────────────────────────────────────────────────────────

def _changes_badge(changes: dict | None) -> str:
    """Compact HTML badge showing key changes from previous day."""
    if not changes:
        return ""
    new_c = len(changes.get("new_positions", []))
    exit_c = len(changes.get("exited", []))
    inc_c = len(changes.get("increased", []))
    dec_c = len(changes.get("decreased", []))
    if not any([new_c, exit_c, inc_c, dec_c]):
        return ""
    parts = []
    if new_c:   parts.append(f"<span style='color:#26A69A'>+{new_c}新</span>")
    if exit_c:  parts.append(f"<span style='color:#EF5350'>-{exit_c}出</span>")
    if inc_c:   parts.append(f"<span style='color:#40C4FF'>↑{inc_c}加</span>")
    if dec_c:   parts.append(f"<span style='color:#FFA726'>↓{dec_c}減</span>")
    return " ".join(parts)


def build_etf_email_section(all_holdings: dict[str, dict]) -> str:
    """
    Generate HTML section for daily email showing each active ETF's
    top holdings + change summary from previous trading day.
    """
    stock_etfs = {k: v for k, v in all_holdings.items() if not k.endswith("D")}
    bond_etfs  = {k: v for k, v in all_holdings.items() if k.endswith("D")}

    # ── Cross-ETF common holdings block ──────────────────────────────────────
    common = cross_etf_common_holdings(all_holdings, min_etfs=3)
    common_rows = "".join(
        f"<tr>"
        f"<td style='padding:3px 8px;color:#40C4FF'>{escape(h['stock_code'])}</td>"
        f"<td style='padding:3px 8px'>{escape(h['stock_name'])}</td>"
        f"<td style='padding:3px 8px;text-align:center'>{h['etf_count']} 檔</td>"
        f"<td style='padding:3px 8px;color:#FFA726'>"
        f"{h['avg_weight']}%</td>"
        f"<td style='padding:3px 8px;font-size:10px;color:#888'>"
        f"{escape(', '.join(h['etfs'][:6]))}</td>"
        f"</tr>"
        for h in common[:15]
    )
    cross_block = f"""
<h3 style="color:#7AB8FF;margin-top:18px">🔗 多檔主動ETF共同持股（≥3檔）</h3>
<table style="border-collapse:collapse;width:100%;font-size:12px">
<tr style="background:#0A1A2A;color:#888;font-size:11px">
  <th style="padding:3px 8px;text-align:left">代號</th>
  <th style="padding:3px 8px;text-align:left">名稱</th>
  <th style="padding:3px 8px;text-align:center">被持數</th>
  <th style="padding:3px 8px;text-align:left">平均權重</th>
  <th style="padding:3px 8px;text-align:left">持有ETF</th>
</tr>
{common_rows}
</table>""" if common else ""

    # ── Per-ETF rows ──────────────────────────────────────────────────────────
    def etf_row(code: str, info: dict) -> str:
        name    = escape(info.get("name", code))
        date    = escape(info.get("date", ""))
        total   = info.get("total_holdings", 0)
        top10   = info.get("top10_weight")
        error   = info.get("error")
        changes = info.get("changes")
        badge   = _changes_badge(changes)

        if error or not info.get("holdings"):
            return (
                f"<tr>"
                f"<td style='padding:4px 8px'><strong>{name}</strong> "
                f"<span style='color:#888;font-size:10px'>{code}</span></td>"
                f"<td colspan='3' style='padding:4px 8px;color:#888;font-size:11px'>"
                f"{escape(error or '無資料')}</td></tr>"
            )

        top5 = info["holdings"][:5]
        top5_html = ", ".join(
            f"<span style='color:#40C4FF'>{escape(h['stock_code'] or '')}</span>"
            f" {escape(h['stock_name'])}"
            + (f" <span style='color:#FFA726'>{h['weight_pct']}%</span>"
               if h.get("weight_pct") else "")
            for h in top5
        )

        return (
            f"<tr>"
            f"<td style='padding:4px 8px;white-space:nowrap'>"
            f"<strong>{name}</strong>"
            f"<span style='color:#888;font-size:10px;margin-left:4px'>{code}</span>"
            f"{'&nbsp;&nbsp;' + badge if badge else ''}</td>"
            f"<td style='padding:4px 8px;font-size:11px;color:#888'>{date}</td>"
            f"<td style='padding:4px 8px;font-size:11px'>{total} 檔"
            f"{'&nbsp;Top10 <strong style=\"color:#FFA726\">' + str(top10) + '%</strong>' if top10 else ''}</td>"
            f"<td style='padding:4px 8px;font-size:11px;color:#aaa'>{top5_html}</td>"
            f"</tr>"
        )

    def section_table(title: str, etfs: dict) -> str:
        if not etfs:
            return ""
        rows = "".join(etf_row(c, v) for c, v in etfs.items())
        return f"""
<h3 style="color:#7AB8FF;margin-top:18px">{escape(title)}</h3>
<table style="border-collapse:collapse;width:100%;font-size:13px">
<tr style="background:#0A1A2A;color:#888;font-size:11px">
  <th style="padding:4px 8px;text-align:left">ETF（昨日變化）</th>
  <th style="padding:4px 8px;text-align:left">日期</th>
  <th style="padding:4px 8px;text-align:left">持股數 / Top10</th>
  <th style="padding:4px 8px;text-align:left">前5大持股</th>
</tr>
{rows}
</table>"""

    return (
        "\n<h2 style='color:#40C4FF;border-bottom:1px solid #1A2A3A;"
        "padding-bottom:6px;margin-top:24px'>"
        "🏦 主動式ETF 投資組合摘要</h2>\n"
        + section_table("股票型主動ETF (A類)", stock_etfs)
        + section_table("債券型主動ETF (D類)", bond_etfs)
        + cross_block
    )
