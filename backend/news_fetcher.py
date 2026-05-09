"""
Industry-categorized news fetcher via Google News RSS.
Organizes news by 3rd-level watchlist industry categories with per-category JSON caching.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

NEWS_CACHE_TTL = 4 * 3600  # 4 hours

# Map UI category name → list of (query, hl, gl) RSS queries
NEWS_CATEGORIES: dict[str, list[tuple[str, str, str]]] = {
    "IC設計": [
        ("IC設計 聯發科 瑞昱 聯詠 novatek", "zh-TW", "TW"),
        ("fabless semiconductor design NVIDIA AMD Qualcomm", "en-US", "US"),
    ],
    "IC代工": [
        ("IC代工 台積電 TSMC 聯電 晶圓廠", "zh-TW", "TW"),
        ("TSMC foundry wafer semiconductor manufacturing", "en-US", "US"),
    ],
    "封裝測試": [
        ("封裝測試 日月光 京元電 矽格 先進封裝", "zh-TW", "TW"),
        ("semiconductor packaging CoWoS advanced packaging OSAT", "en-US", "US"),
    ],
    "系統模組PCB": [
        ("PCB電路板 台光電 欣興 景碩 系統廠", "zh-TW", "TW"),
        ("PCB circuit board server AI system module", "en-US", "US"),
    ],
    "記憶體": [
        ("記憶體 DRAM HBM NOR Flash NAND控制器", "zh-TW", "TW"),
        ("DRAM memory HBM Micron Samsung SK Hynix NAND", "en-US", "US"),
    ],
    "功率半導體": [
        ("功率半導體 SiC GaN 碳化矽 氮化鎵", "zh-TW", "TW"),
        ("power semiconductor SiC GaN wide bandgap EV", "en-US", "US"),
    ],
    "磊晶": [
        ("磊晶 SiC晶圓 GaN晶圓 化合物半導體 砷化鎵", "zh-TW", "TW"),
        ("epitaxy compound semiconductor wafer SiC GaN substrate", "en-US", "US"),
    ],
    "AI與雲端": [
        ("AI伺服器 雲端 台灣AI供應鏈 算力", "zh-TW", "TW"),
        ("AI cloud hyperscaler data center GPU inference", "en-US", "US"),
    ],
    "資源與原物料": [
        ("稀土 銅 金 礦業 能源原物料", "zh-TW", "TW"),
        ("rare earth copper gold silver mining commodities energy", "en-US", "US"),
    ],
    "總體經濟": [
        ("台股 大盤 Fed 升降息 貿易戰 關稅", "zh-TW", "TW"),
        ("US stock market Fed interest rate trade tariff macro", "en-US", "US"),
    ],
}


def _cache_path(category: str) -> str:
    safe = category.replace("/", "_").replace(" ", "_")
    return os.path.join(CACHE_DIR, f"news_{safe}.json")


def _fetch_rss(query: str, hl: str = "zh-TW", gl: str = "TW", max_items: int = 10) -> list[dict]:
    """Fetch articles from Google News RSS. Includes past-month filter and article URLs."""
    encoded = urllib.parse.quote(query)
    lang_code = hl.split("-")[0]
    url = (
        f"https://news.google.com/rss/search"
        f"?q={encoded}&hl={hl}&gl={gl}&ceid={gl}:{lang_code}&tbs=qdr:m"
    )
    headers = {"User-Agent": "Mozilla/5.0 (compatible; StockMonitor/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall(".//item")[:max_items]:
            title = item.findtext("title", "").strip()
            link  = item.findtext("link", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            source_el = item.find("source")
            source = source_el.text.strip() if source_el is not None else ""
            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "source": source,
                    "pub_date": pub_date,
                    "lang": hl,
                })
        return items
    except Exception as e:
        logger.warning("News RSS fetch failed '%s': %s", query, e)
        return []


def fetch_category_news(category: str, force: bool = False) -> list[dict]:
    """Return cached (or freshly fetched) news for a single category."""
    path = _cache_path(category)
    if not force and os.path.exists(path):
        age = time.time() - os.path.getmtime(path)
        if age < NEWS_CACHE_TTL:
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    queries = NEWS_CATEGORIES.get(category, [])
    seen_links: set[str] = set()
    articles: list[dict] = []
    for query, hl, gl in queries:
        for art in _fetch_rss(query, hl, gl, max_items=8):
            if art["link"] not in seen_links:
                seen_links.add(art["link"])
                articles.append(art)

    # Sort by pub_date descending (RFC-2822 strings sort reasonably as-is)
    articles.sort(key=lambda a: a.get("pub_date", ""), reverse=True)

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("News cache save failed: %s", e)

    return articles


def fetch_all_news(force: bool = False) -> dict[str, list[dict]]:
    """Fetch news for all categories. Rate-limited between requests."""
    result: dict[str, list[dict]] = {}
    for i, category in enumerate(NEWS_CATEGORIES):
        if i > 0:
            time.sleep(1.5)  # be polite to Google News RSS
        articles = fetch_category_news(category, force=force)
        result[category] = articles
        logger.info("News '%s': %d articles", category, len(articles))
    return result


def get_last_updated() -> dict[str, str]:
    """Return ISO timestamp of cache file mtime per category."""
    out: dict[str, str] = {}
    for cat in NEWS_CATEGORIES:
        path = _cache_path(cat)
        if os.path.exists(path):
            ts = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
            out[cat] = ts
    return out
