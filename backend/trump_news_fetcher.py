"""
Trump-focused news and statement fetcher.

Sources are intentionally best-effort:
- English policy/market news via Google News RSS
- White House releases via official RSS feeds
- Truth Social direct public API when reachable, with trump.fm as fallback
- X via API bearer token when configured, with public archive/RSS fallbacks
"""
from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.getenv("DATA_DIR", os.path.dirname(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

TRUMP_NEWS_CACHE_TTL = int(os.getenv("TRUMP_NEWS_CACHE_TTL", str(45 * 60)))
TRUMP_CACHE_PATH = os.path.join(CACHE_DIR, "trump_news.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; StockMonitor/1.0; +https://github.com/BillCharlie/stock-monitor)",
    "Accept": "application/rss+xml, application/json, text/xml, */*",
}

TRUMP_NEWS_QUERIES = [
    (
        '"President Trump" OR "Donald Trump" stock market tariffs trade China Fed inflation oil chips AI',
        "en-US",
        "US",
    ),
    (
        '"Trump administration" market impact semiconductor energy defense healthcare crypto',
        "en-US",
        "US",
    ),
]

WHITE_HOUSE_FEEDS = [
    ("White House Releases", "https://www.whitehouse.gov/releases/feed/"),
    ("White House Briefings", "https://www.whitehouse.gov/briefings-statements/feed/"),
    ("White House Presidential Actions", "https://www.whitehouse.gov/presidential-actions/feed/"),
]

IMPACT_RULES = [
    {
        "id": "tariffs_trade",
        "label": "關稅 / 貿易 / 中國政策",
        "keywords": [
            "tariff", "tariffs", "trade war", "trade deal", "china", "beijing",
            "import", "export", "sanction", "sanctions", "supply chain",
        ],
        "sectors": ["半導體與AI硬體", "台灣出口/供應鏈", "工業股", "零售與進口商"],
        "bias": "波動升高",
        "summary": "貿易與關稅訊息容易改變毛利率、供應鏈移轉與風險溢價。",
    },
    {
        "id": "chips_ai",
        "label": "AI / 晶片 / 出口管制",
        "keywords": [
            "chip", "chips", "semiconductor", "tsmc", "nvidia", "amd", "ai",
            "data center", "export control", "hbm", "gpu", "technology",
        ],
        "sectors": ["半導體與AI硬體", "雲端資料中心", "PCB/伺服器供應鏈", "電力設備"],
        "bias": "題材敏感",
        "summary": "AI與晶片政策會直接牽動半導體、雲端資本支出與台灣供應鏈評價。",
    },
    {
        "id": "rates_macro",
        "label": "Fed / 利率 / 通膨 / 就業",
        "keywords": [
            "fed", "federal reserve", "powell", "interest rate", "rates",
            "inflation", "cpi", "jobs report", "unemployment", "treasury",
        ],
        "sectors": ["大型科技股", "金融股", "債券與利率敏感股", "美元/黃金"],
        "bias": "估值重估",
        "summary": "利率與通膨口徑會影響折現率、美元、黃金與高本益比成長股。",
    },
    {
        "id": "energy_geopolitics",
        "label": "能源 / 地緣政治",
        "keywords": [
            "oil", "gas", "drilling", "energy", "iran", "middle east", "opec",
            "russia", "ukraine", "war", "strike", "missile",
        ],
        "sectors": ["能源股", "航空/運輸", "化工材料", "黃金與避險資產"],
        "bias": "避險需求",
        "summary": "能源與衝突訊息可能推動油價、通膨預期與避險交易。",
    },
    {
        "id": "tax_budget",
        "label": "稅改 / 財政 / 政府支出",
        "keywords": [
            "tax", "tax cut", "budget", "deficit", "spending", "stimulus",
            "small business", "manufacturing", "factory",
        ],
        "sectors": ["小型股", "工業製造", "消費循環", "美債"],
        "bias": "政策受益/赤字風險",
        "summary": "稅改與支出可能支撐企業獲利，同時也會牽動赤字與殖利率。",
    },
    {
        "id": "defense_security",
        "label": "國防 / 國安 / 邊境",
        "keywords": [
            "defense", "military", "pentagon", "border", "homeland", "security",
            "nato", "weapon", "missiles", "ice",
        ],
        "sectors": ["國防航太", "網路安全", "政府承包商", "工業股"],
        "bias": "訂單/風險溢價",
        "summary": "國防與國安訊息可能推升相關訂單，也可能拉高市場風險溢價。",
    },
    {
        "id": "healthcare",
        "label": "醫療 / 藥價 / 保險",
        "keywords": [
            "health", "healthcare", "drug price", "medicare", "medicaid",
            "pharma", "vaccine", "fda", "maha",
        ],
        "sectors": ["醫療保健", "製藥", "保險", "醫療通路"],
        "bias": "監管敏感",
        "summary": "醫療政策會影響藥價、保險給付與醫療類股估值。",
    },
    {
        "id": "crypto_fintech",
        "label": "加密資產 / 金融科技",
        "keywords": ["crypto", "bitcoin", "ethereum", "stablecoin", "sec", "digital asset"],
        "sectors": ["加密資產", "金融科技", "交易所/礦機", "高Beta科技股"],
        "bias": "風險偏好",
        "summary": "加密政策訊息常快速反映在高Beta資產與金融科技類股。",
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _cache_age_seconds(path: str) -> float | None:
    if not os.path.exists(path):
        return None
    return time.time() - os.path.getmtime(path)


def _strip_html(text: str) -> str:
    text = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", text or "", flags=re.I)
    text = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _truncate(text: str, length: int = 420) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= length:
        return text
    return text[: length - 1].rstrip() + "..."


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _date_to_iso(value: str | None) -> str:
    parsed = _parse_date(value)
    if parsed:
        return parsed.isoformat().replace("+00:00", "Z")
    return value or ""


def _is_recent(value: str | None, max_days: int = 21) -> bool:
    parsed = _parse_date(value)
    if not parsed:
        return True
    age = datetime.now(timezone.utc) - parsed
    return age.days <= max_days


def _stable_id(*parts: str) -> str:
    payload = "|".join(p or "" for p in parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _item(
    *,
    section: str,
    source: str,
    title: str,
    summary: str = "",
    link: str = "",
    published_at: str = "",
    platform_id: str = "",
    aggregator: str = "",
) -> dict[str, Any]:
    title = _truncate(_strip_html(title), 220)
    summary = _truncate(_strip_html(summary), 620)
    return {
        "id": platform_id or _stable_id(section, source, title, link, published_at),
        "section": section,
        "source": source,
        "title": title or "Untitled update",
        "summary": summary,
        "link": link,
        "published_at": _date_to_iso(published_at),
        "pub_date": published_at,
        "lang": "en-US",
        "aggregator": aggregator,
        "market_tags": [],
    }


def _fetch_rss(url: str, source: str, section: str, max_items: int = 8) -> list[dict[str, Any]]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=14)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        logger.warning("RSS fetch failed %s: %s", url, e)
        return []

    items: list[dict[str, Any]] = []
    for node in root.findall(".//item")[:max_items]:
        title = node.findtext("title", "").strip()
        link = node.findtext("link", "").strip()
        pub_date = node.findtext("pubDate", "").strip()
        description = node.findtext("description", "").strip()
        source_el = node.find("source")
        feed_source = source_el.text.strip() if source_el is not None and source_el.text else source
        if title or description:
            items.append(
                _item(
                    section=section,
                    source=feed_source,
                    title=title,
                    summary=description,
                    link=link,
                    published_at=pub_date,
                )
            )
    return items


def _fetch_google_news(max_items: int = 12) -> list[dict[str, Any]]:
    seen: set[str] = set()
    articles: list[dict[str, Any]] = []
    for query, hl, gl in TRUMP_NEWS_QUERIES:
        encoded = urllib.parse.quote(query)
        lang_code = hl.split("-")[0]
        url = (
            "https://news.google.com/rss/search"
            f"?q={encoded}&hl={hl}&gl={gl}&ceid={gl}:{lang_code}&tbs=qdr:w"
        )
        for item in _fetch_rss(url, "Google News", "english_news", max_items=8):
            dedupe_key = item.get("link") or item.get("title")
            if dedupe_key and dedupe_key not in seen:
                seen.add(dedupe_key)
                articles.append(item)
        time.sleep(0.25)
    articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return articles[:max_items]


def _fetch_white_house(max_items: int = 12) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for source, url in WHITE_HOUSE_FEEDS:
        for item in _fetch_rss(url, source, "white_house", max_items=6):
            item["source"] = source
            key = item.get("link") or item.get("title")
            if key and key not in seen:
                seen.add(key)
                out.append(item)
        time.sleep(0.25)
    out.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return out[:max_items]


def _truth_status_to_item(status: dict[str, Any]) -> dict[str, Any] | None:
    platform_id = str(status.get("id") or "")
    content = status.get("content") or status.get("spoiler_text") or ""
    reblog = status.get("reblog") if isinstance(status.get("reblog"), dict) else None
    if reblog and not content:
        content = reblog.get("content") or ""
    text = _strip_html(content)
    if not text and status.get("media_attachments"):
        text = "Media-only Truth Social post"
    if not text:
        return None
    link = (
        status.get("url")
        or f"https://truthsocial.com/users/realDonaldTrump/statuses/{platform_id}"
    )
    return _item(
        section="truth_posts",
        source="Truth Social",
        title=_truncate(text, 160),
        summary=text,
        link=link,
        published_at=status.get("created_at", ""),
        platform_id=f"truth_{platform_id}",
    )


def _fetch_truth_direct(max_items: int = 10) -> list[dict[str, Any]]:
    try:
        lookup = requests.get(
            "https://truthsocial.com/api/v1/accounts/lookup",
            params={"acct": "realDonaldTrump"},
            headers=HEADERS,
            timeout=14,
        )
        lookup.raise_for_status()
        account_id = lookup.json().get("id")
        if not account_id:
            return []
        statuses = requests.get(
            f"https://truthsocial.com/api/v1/accounts/{account_id}/statuses",
            params={"limit": max_items, "exclude_replies": "true"},
            headers=HEADERS,
            timeout=14,
        )
        statuses.raise_for_status()
        return [
            item for item in (_truth_status_to_item(s) for s in statuses.json())
            if item is not None
        ][:max_items]
    except Exception as e:
        logger.info("Truth Social direct fetch unavailable, using fallback: %s", e)
        return []


def _trump_fm_to_item(post: dict[str, Any], section: str) -> dict[str, Any] | None:
    platform = post.get("platform")
    platform_id = str(post.get("platformId") or "")
    content = post.get("content") or _strip_html(post.get("contentHtml") or "")
    if not content and post.get("mediaUrls"):
        content = "Media-only post"
    if not content:
        return None

    if platform == "truth":
        source = "Truth Social"
        link = post.get("url") or f"https://truthsocial.com/users/realDonaldTrump/statuses/{platform_id}"
    else:
        source = "X"
        link = post.get("url") or f"https://x.com/realDonaldTrump/status/{platform_id}"

    return _item(
        section=section,
        source=source,
        title=_truncate(content, 160),
        summary=content,
        link=link,
        published_at=post.get("createdAt", ""),
        platform_id=f"{platform}_{platform_id}",
        aggregator="trump.fm",
    )


def _fetch_trump_fm(platform: str, section: str, max_items: int = 10) -> list[dict[str, Any]]:
    try:
        resp = requests.get(
            "https://trump.fm/api/posts",
            params={"platform": platform, "limit": max_items},
            headers=HEADERS,
            timeout=14,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return [
            item for item in (_trump_fm_to_item(post, section) for post in data)
            if item is not None
        ][:max_items]
    except Exception as e:
        logger.warning("trump.fm fetch failed platform=%s: %s", platform, e)
        return []


def _fetch_x_api(max_items: int = 10) -> list[dict[str, Any]]:
    bearer = os.getenv("TRUMP_X_BEARER_TOKEN", "").strip() or os.getenv("X_BEARER_TOKEN", "").strip()
    if not bearer:
        return []
    headers = {**HEADERS, "Authorization": f"Bearer {bearer}"}
    try:
        user_id = os.getenv("TRUMP_X_USER_ID", "").strip()
        if not user_id:
            user_resp = requests.get(
                "https://api.twitter.com/2/users/by/username/realDonaldTrump",
                headers=headers,
                timeout=12,
            )
            user_resp.raise_for_status()
            user_id = user_resp.json().get("data", {}).get("id", "")
        if not user_id:
            return []
        tweets = requests.get(
            f"https://api.twitter.com/2/users/{user_id}/tweets",
            params={
                "max_results": max_items,
                "tweet.fields": "created_at,public_metrics",
                "exclude": "retweets,replies",
            },
            headers=headers,
            timeout=12,
        )
        tweets.raise_for_status()
        out = []
        for tweet in tweets.json().get("data", []):
            tweet_id = str(tweet.get("id") or "")
            text = tweet.get("text") or ""
            out.append(
                _item(
                    section="x_posts",
                    source="X",
                    title=_truncate(text, 160),
                    summary=text,
                    link=f"https://x.com/realDonaldTrump/status/{tweet_id}",
                    published_at=tweet.get("created_at", ""),
                    platform_id=f"x_{tweet_id}",
                )
            )
        return out[:max_items]
    except Exception as e:
        logger.warning("X API fetch failed: %s", e)
        return []


def _fetch_x_nitter(max_items: int = 8) -> list[dict[str, Any]]:
    rss_url = os.getenv("TRUMP_X_RSS_URL", "https://nitter.net/realDonaldTrump/rss").strip()
    if not rss_url:
        return []
    items = _fetch_rss(rss_url, "X", "x_posts", max_items=max_items)
    for item in items:
        item["aggregator"] = "RSS fallback"
        if "nitter.net" in item.get("link", ""):
            item["link"] = item["link"].replace("https://nitter.net/realDonaldTrump/status/", "https://x.com/realDonaldTrump/status/")
    return items[:max_items]


def _fetch_truth(max_items: int = 10) -> list[dict[str, Any]]:
    direct = _fetch_truth_direct(max_items=max_items)
    if direct:
        return direct
    return _fetch_trump_fm("truth", "truth_posts", max_items=max_items)


def _fetch_x(max_items: int = 10) -> list[dict[str, Any]]:
    api_items = _fetch_x_api(max_items=max_items)
    if api_items:
        return api_items

    archive_items = _fetch_trump_fm("twitter", "x_posts", max_items=max_items)
    if archive_items:
        return archive_items
    return _fetch_x_nitter(max_items=max_items)


def _dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = item.get("id") or item.get("link") or item.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    out.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return out


def _matched_rules(text: str) -> list[dict[str, Any]]:
    lower = text.lower()
    matches = []
    for rule in IMPACT_RULES:
        hits = sorted({kw for kw in rule["keywords"] if kw in lower})
        if hits:
            matches.append({**rule, "hits": hits})
    return matches


def analyze_trump_market_impact(sections: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    all_items = [
        item
        for section_items in sections.values()
        for item in section_items
        if _is_recent(item.get("published_at"), max_days=21)
    ]
    rule_hits: dict[str, dict[str, Any]] = {}
    sector_map: dict[str, set[str]] = {}

    for item in all_items:
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        matched = _matched_rules(text)
        item["market_tags"] = [m["label"] for m in matched]
        for match in matched:
            current = rule_hits.setdefault(
                match["id"],
                {
                    "id": match["id"],
                    "label": match["label"],
                    "hit_count": 0,
                    "keywords": set(),
                    "sectors": match["sectors"],
                    "bias": match["bias"],
                    "summary": match["summary"],
                    "examples": [],
                },
            )
            current["hit_count"] += 1
            current["keywords"].update(match["hits"])
            if len(current["examples"]) < 3:
                current["examples"].append(item.get("title", ""))
            for sector in match["sectors"]:
                sector_map.setdefault(sector, set()).add(match["label"])

    themes = sorted(rule_hits.values(), key=lambda x: x["hit_count"], reverse=True)
    for theme in themes:
        theme["keywords"] = sorted(theme["keywords"])[:10]

    sectors = sorted(
        (
            {"sector": sector, "drivers": sorted(drivers), "driver_count": len(drivers)}
            for sector, drivers in sector_map.items()
        ),
        key=lambda x: x["driver_count"],
        reverse=True,
    )

    if not themes:
        overall = "目前未偵測到明確市場板塊衝擊訊號"
    elif themes[0]["hit_count"] >= 3 or len(themes) >= 4:
        overall = "政策訊息密集，需留意相關板塊波動"
    else:
        overall = "有局部政策題材，暫以事件驅動觀察"

    return {
        "generated_at": _now_iso(),
        "overall": overall,
        "themes": themes[:6],
        "sectors": sectors[:10],
        "recent_item_count": len(all_items),
        "note": "此影響分析依公開文字關鍵字自動分類，僅作為日報整理線索，不構成投資建議。",
    }


def fetch_trump_news(force: bool = False) -> dict[str, Any]:
    """Return cached or freshly fetched TrumpNews data."""
    if not force:
        age = _cache_age_seconds(TRUMP_CACHE_PATH)
        if age is not None and age < TRUMP_NEWS_CACHE_TTL:
            try:
                with open(TRUMP_CACHE_PATH, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    source_status: dict[str, str] = {}
    sections = {
        "english_news": [],
        "x_posts": [],
        "truth_posts": [],
        "white_house": [],
    }

    fetchers = [
        ("english_news", lambda: _fetch_google_news(max_items=12)),
        ("x_posts", lambda: _fetch_x(max_items=10)),
        ("truth_posts", lambda: _fetch_truth(max_items=12)),
        ("white_house", lambda: _fetch_white_house(max_items=12)),
    ]

    for section, fn in fetchers:
        try:
            sections[section] = _dedupe_items(fn())
            source_status[section] = f"ok:{len(sections[section])}"
        except Exception as e:
            logger.warning("TrumpNews section failed %s: %s", section, e)
            source_status[section] = f"error:{e}"
            sections[section] = []

    impact = analyze_trump_market_impact(sections)
    result = {
        "generated_at": _now_iso(),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "cache_ttl_seconds": TRUMP_NEWS_CACHE_TTL,
        "sections": sections,
        "impact": impact,
        "source_status": source_status,
        "source_note": (
            "X direct fetch requires TRUMP_X_BEARER_TOKEN. Without it, the module uses public "
            "archives/RSS fallbacks, which may lag or contain only historical posts."
        ),
    }

    try:
        with open(TRUMP_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("TrumpNews cache save failed: %s", e)

    return result


def get_trump_last_updated() -> str:
    if os.path.exists(TRUMP_CACHE_PATH):
        return datetime.fromtimestamp(os.path.getmtime(TRUMP_CACHE_PATH)).strftime("%Y-%m-%d %H:%M")
    return ""


def format_trump_news_for_prompt(data: dict[str, Any] | None = None) -> str:
    """Compact TrumpNews block for the GPT daily report prompt."""
    data = data or fetch_trump_news()
    sections = data.get("sections", {})
    impact = data.get("impact", {})
    lines: list[str] = []

    lines.append("【自動板塊影響判讀】")
    lines.append(f"- 整體：{impact.get('overall', '無')}")
    for theme in impact.get("themes", [])[:5]:
        sectors = "、".join(theme.get("sectors", [])[:5])
        keywords = ", ".join(theme.get("keywords", [])[:6])
        lines.append(
            f"- {theme.get('label')}：{theme.get('bias')}；可能影響 {sectors}；"
            f"關鍵字 {keywords}；說明：{theme.get('summary')}"
        )

    labels = {
        "english_news": "英文新聞",
        "x_posts": "X 發言",
        "truth_posts": "Truth Social 發言",
        "white_house": "白宮新聞稿/官方訊息",
    }
    for key, label in labels.items():
        items = sections.get(key, [])[:6]
        lines.append(f"\n【{label}】")
        if not items:
            lines.append("- 無可用資料")
            continue
        for item in items:
            stamp = item.get("published_at") or item.get("pub_date") or ""
            source = item.get("source") or ""
            title = item.get("title") or ""
            summary = item.get("summary") or ""
            tags = "、".join(item.get("market_tags") or [])
            extra = f"；標籤：{tags}" if tags else ""
            body = summary if key in ("x_posts", "truth_posts") else title
            lines.append(f"- {stamp} | {source} | {_truncate(body, 260)}{extra}")

    lines.append("\n請在日報中用繁體中文整理上述 TrumpNews，明確分析可能影響的股市領域與觀察重點。")
    return "\n".join(lines)
