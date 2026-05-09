"""
GPT-4o daily report generator.
1. Fetches Google News headlines for key sectors via RSS
2. Collects all technical analysis from the in-memory store
3. Calls OpenAI GPT-4o to produce a comprehensive HTML report
"""
from __future__ import annotations

import logging
import os
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logger = logging.getLogger(__name__)

# ─── News fetching via Google News RSS ───────────────────────────────────────

NEWS_QUERIES = [
    ("台灣半導體 IC設計", "zh-TW", "TW"),
    ("台積電 聯發科 晶圓", "zh-TW", "TW"),
    ("功率半導體 SiC GaN", "zh-TW", "TW"),
    ("NVIDIA AMD semiconductor AI chip", "en-US", "US"),
    ("memory DRAM NAND flash Micron", "en-US", "US"),
    ("rare earth gold copper mining", "en-US", "US"),
    ("台股 大盤 半導體類股", "zh-TW", "TW"),
    ("US stock market tech sector", "en-US", "US"),
]

def _fetch_google_news_rss(query: str, hl: str = "zh-TW", gl: str = "TW", max_items: int = 5) -> list[dict]:
    """Fetch headlines from Google News RSS for a given query."""
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl={hl}&gl={gl}&ceid={gl}:{hl.split('-')[0]}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; StockMonitor/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall(".//item")[:max_items]:
            title = item.findtext("title", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            source = item.find("source")
            source_name = source.text if source is not None else ""
            if title:
                items.append({
                    "title": title,
                    "source": source_name,
                    "pub_date": pub_date,
                })
        return items
    except Exception as e:
        logger.warning(f"News fetch failed for '{query}': {e}")
        return []


def fetch_all_news() -> dict[str, list[dict]]:
    """Fetch news for all predefined sectors. Returns {query: [articles]}."""
    all_news = {}
    for query, hl, gl in NEWS_QUERIES:
        articles = _fetch_google_news_rss(query, hl, gl, max_items=4)
        if articles:
            all_news[query] = articles
        logger.info(f"News '{query}': {len(articles)} articles")
    return all_news


# ─── GPT report generation ────────────────────────────────────────────────────

def _build_news_section(all_news: dict) -> str:
    lines = []
    for query, articles in all_news.items():
        lines.append(f"\n【{query}】")
        for a in articles:
            lines.append(f"  - {a['title']} ({a['source']})")
    return "\n".join(lines)


def _build_analysis_section(all_results: dict) -> str:
    """Summarise technical analysis results for GPT."""
    if not all_results:
        return "（尚無技術分析資料）"
    lines = []
    # Sort by score descending
    sorted_items = sorted(all_results.values(), key=lambda x: x.get("score", 0), reverse=True)
    for r in sorted_items:
        if r.get("error"):
            continue
        pred5 = r.get("prediction_5d", {})
        pred_str = ""
        if pred5:
            pred_str = f"，5日預測 {pred5.get('pred_price')} ({pred5.get('pred_change_pct',0):+.1f}%) R²={pred5.get('r_squared',0):.2f}"
        lines.append(
            f"  {r['name']}({r['symbol']}): 現價={r['price']}, 評級={r['rating']}, "
            f"評分={r['score']}, RSI={r.get('indicators',{}).get('RSI','─')}{pred_str}"
        )
    return "\n".join(lines)


def _build_prompt(all_results: dict, all_news: dict, market_sentiment: str, date_str: str) -> str:
    analysis_text = _build_analysis_section(all_results)
    news_text = _build_news_section(all_news)

    return f"""你是一位專業的台灣/美國股市投資分析師，擅長技術分析、產業趨勢判斷與風險管理。
今天是 {date_str}，請根據以下數據產生一份完整的每日投資分析報告。

═══════════════════════════════════
【一、技術分析數據（來自量化系統）】
系統整體市場情緒：{market_sentiment}

{analysis_text}

═══════════════════════════════════
【二、今日相關產業新聞（Google News）】
{news_text}

═══════════════════════════════════
【報告要求】
請產生一份完整的 HTML 格式投資分析報告，包含以下六個章節：

1. 📊 大盤與市場總覽
   - 今日市場情緒研判（多頭/空頭/中性）
   - 台股與美股盤面特徵分析
   - 主要風險因子

2. 🔬 產業趨勢深度分析
   - 半導體（IC設計/製造/封裝/記憶體/功率/材料/磊晶）各子產業動態
   - 礦產資源（稀土/黃金/銅/鐵礦）商品走勢

3. 🎯 技術面精選機會（前5名買入候選）
   - 列出技術指標評分最高的5支股票
   - 每支股票說明進場邏輯、目標價、止損位

4. ⚠️ 風險警示（需特別留意的標的）
   - 列出技術指標偏空或訊號危險的股票
   - 說明持有者的應對策略

5. 📰 新聞事件影響分析
   - 結合今日新聞，分析對各產業/個股的潛在影響
   - 是否有重大事件需要特別關注

6. 🔮 明日展望與操作建議
   - 基於數學模型的短期預測摘要
   - 明日盤前建議關注的關鍵點位與事件

【格式要求】
- 使用繁體中文
- 輸出純 HTML（不含 <!DOCTYPE>、<html>、<body> 標籤，只輸出內容部分）
- 使用 inline style，顏色：正面訊息 #26A69A，負面 #EF5350，中性 #FFA726
- 每個章節加上標題 h2，重要數字用 <strong> 標記
- 結尾加上免責聲明

⚠️ 本分析完全基於技術指標與公開新聞，不構成投資建議，投資人需自行評估風險。"""


def generate_gpt_report(all_results: dict, market_sentiment: str = "中性") -> Optional[str]:
    """
    Call GPT-4o and return the HTML report string.
    Returns None if API key is not set or call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-xxx"):
        logger.warning("OPENAI_API_KEY not configured — skipping GPT report")
        return None

    date_str = datetime.now().strftime("%Y年%m月%d日 %A")

    logger.info("Fetching Google News for report...")
    all_news = fetch_all_news()

    logger.info("Calling GPT-4o for report generation...")
    try:
        client = OpenAI(api_key=api_key)
        prompt = _build_prompt(all_results, all_news, market_sentiment, date_str)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是頂尖的台美股市投資分析師，熟悉技術分析、半導體產業鏈、礦產資源市場。"
                        "你的報告準確、專業、有洞察力，同時提醒投資風險。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            temperature=0.4,
        )
        html_content = response.choices[0].message.content.strip()
        logger.info(f"GPT report generated: {len(html_content)} chars")
        return html_content
    except Exception as e:
        logger.error(f"GPT API error: {e}")
        return None
