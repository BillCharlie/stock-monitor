"""
GPT-4o daily report generator.
1. Fetches Google News headlines for key sectors via RSS
2. Collects all technical analysis from the in-memory store
3. Analyzes institutional trading patterns and major shareholders
4. Calls OpenAI GPT-4o to produce a comprehensive HTML report with institution identification
"""
from __future__ import annotations

import logging
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI
from trump_news_fetcher import fetch_trump_news, format_trump_news_for_prompt
from chip_analysis import identify_major_institutions

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
    ("比亞迪 A股 新能源汽車 中國股市", "zh-CN", "CN"),
    ("芯聯集成 688469 晶圓代工 功率半導體", "zh-CN", "CN"),
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
    # Keep each market distinct so the report can render a dedicated China block.
    sorted_items = sorted(
        all_results.values(),
        key=lambda x: (x.get("market", "其他"), -x.get("score", 0)),
    )
    current_market = None
    for r in sorted_items:
        if r.get("error"):
            continue
        market = r.get("market", "其他")
        if market != current_market:
            lines.append(f"\n【{market}】")
            current_market = market
        pred5 = r.get("prediction_5d", {})
        pred_str = ""
        if pred5:
            pred_str = f"，5日預測 {pred5.get('pred_price')} ({pred5.get('pred_change_pct',0):+.1f}%) R²={pred5.get('r_squared',0):.2f}"
        
        # Add institution info if available
        inst_info = ""
        if r.get("institutional_analysis"):
            buyers = r["institutional_analysis"].get("likely_buyers", [])
            sellers = r["institutional_analysis"].get("likely_sellers", [])
            if buyers or sellers:
                buyer_str = "買超：" + "、".join([b.get("type", "") for b in buyers[:2]]) if buyers else ""
                seller_str = "賣超：" + "、".join([s.get("type", "") for s in sellers[:2]]) if sellers else ""
                inst_info = f" | 機構：{buyer_str}{' | ' if buyer_str and seller_str else ''}{seller_str}"
        
        lines.append(
            f"  {r['name']}({r['symbol']}): 現價={r['price']}, 評級={r['rating']}, "
            f"評分={r['score']}, RSI={r.get('indicators',{}).get('RSI','─')}{pred_str}{inst_info}"
        )
    return "\n".join(lines)


def _build_institution_analysis_section(all_results: dict) -> str:
    """Build institutional trading analysis section for GPT prompt.
    Reads from result['investors'] (FinMind actual data) and
    result['institutional_analysis'] (chip_analysis inference).
    """
    lines = ["\n【三大法人與主力分析（FinMind 實際數據）】"]

    # ── 1. Collect actual FinMind chip data ───────────────────────────────────
    tw_chip = []   # TW stocks with real 三大法人 data
    for symbol, result in all_results.items():
        if result.get("error"):
            continue
        inv = result.get("investors", {})
        if inv.get("type") != "tw":
            continue
        comp = inv.get("components", {})
        total_net = comp.get("total_net", 0)
        if total_net == 0:
            continue
        tw_chip.append({
            "symbol":      symbol,
            "name":        result.get("name", ""),
            "foreign_net": comp.get("foreign_net", 0),
            "trust_net":   comp.get("trust_net", 0),
            "dealer_net":  comp.get("dealer_net", 0),
            "total_net":   total_net,
            "latest_date": inv.get("latest_date", ""),
            "trend":       inv.get("trend", []),
        })

    # Sort by abs(total_net) so biggest movers appear first
    tw_chip.sort(key=lambda x: abs(x["total_net"]), reverse=True)

    if tw_chip:
        # Split buy / sell top lists
        top_buy  = [x for x in tw_chip if x["total_net"] > 0][:8]
        top_sell = [x for x in tw_chip if x["total_net"] < 0][:8]

        if top_buy:
            lines.append("\n▲ 三大法人合計買超前 8（股數）：")
            for i, s in enumerate(top_buy, 1):
                lines.append(
                    f"  {i}. {s['symbol']} {s['name']}  "
                    f"合計+{s['total_net']:,}  "
                    f"外資{s['foreign_net']:+,} 投信{s['trust_net']:+,} 自營{s['dealer_net']:+,}  "
                    f"[{s['latest_date']}]"
                )

        if top_sell:
            lines.append("\n▼ 三大法人合計賣超前 8（股數）：")
            for i, s in enumerate(top_sell, 1):
                lines.append(
                    f"  {i}. {s['symbol']} {s['name']}  "
                    f"合計{s['total_net']:,}  "
                    f"外資{s['foreign_net']:+,} 投信{s['trust_net']:+,} 自營{s['dealer_net']:+,}  "
                    f"[{s['latest_date']}]"
                )

        # Continuous-buy / continuous-sell (≥3 of 5 trend days same direction)
        persistent_buy, persistent_sell = [], []
        for s in tw_chip:
            trend = s.get("trend", [])
            if len(trend) >= 3:
                nets = [t.get("total_net", 0) for t in trend[:5]]
                buy_days  = sum(1 for n in nets if n > 0)
                sell_days = sum(1 for n in nets if n < 0)
                cum = sum(nets)
                if buy_days >= 3 and cum > 0:
                    persistent_buy.append((s["symbol"], s["name"], cum, buy_days))
                elif sell_days >= 3 and cum < 0:
                    persistent_sell.append((s["symbol"], s["name"], cum, sell_days))
        if persistent_buy:
            persistent_buy.sort(key=lambda x: x[2], reverse=True)
            lines.append("\n📈 持續買超（近5日中≥3日買超）：")
            for sym, nm, cum, days in persistent_buy[:5]:
                lines.append(f"  {sym} {nm}  近5日累計{cum:+,}股 ({days}日買超)")
        if persistent_sell:
            persistent_sell.sort(key=lambda x: x[2])
            lines.append("\n📉 持續賣超（近5日中≥3日賣超）：")
            for sym, nm, cum, days in persistent_sell[:5]:
                lines.append(f"  {sym} {nm}  近5日累計{cum:+,}股 ({days}日賣超)")
    else:
        lines.append("（今日尚無台股三大法人 FinMind 數據）")

    # ── 2. Supplement with chip_analysis inference (likely institutions) ───────
    inferred = []
    for symbol, result in all_results.items():
        if result.get("error") or not result.get("institutional_analysis"):
            continue
        inst = result["institutional_analysis"]
        for buyer in inst.get("likely_buyers", []):
            if buyer.get("amount", 0) > 0 and buyer.get("likely_institutions"):
                inferred.append(
                    f"  {symbol} {result.get('name','')} — "
                    f"推測 {'、'.join(buyer['likely_institutions'][:2])} 買進"
                )
        for seller in inst.get("likely_sellers", []):
            if seller.get("amount", 0) < 0 and seller.get("likely_institutions"):
                inferred.append(
                    f"  {symbol} {result.get('name','')} — "
                    f"推測 {'、'.join(seller.get('likely_institutions', [])[:2])} 賣出"
                )
    if inferred:
        lines.append("\n🔍 主力機構推測（chip_analysis）：")
        lines.extend(inferred[:8])

    return "\n".join(lines)


def _build_prompt(
    all_results: dict,
    all_news: dict,
    market_sentiment: str,
    date_str: str,
    trump_news: dict | None = None,
) -> str:
    analysis_text = _build_analysis_section(all_results)
    institution_text = _build_institution_analysis_section(all_results)
    news_text = _build_news_section(all_news)
    trump_text = format_trump_news_for_prompt(trump_news)

    return f"""你是一位專業的台灣、美國與中國股市投資分析師，擅長技術分析、產業趨勢判斷、機構投資者行為分析與風險管理。
今天是 {date_str}，請根據以下數據產生一份完整的每日投資分析報告。

═══════════════════════════════════
【一、技術分析數據（來自量化系統）】
系統整體市場情緒：{market_sentiment}

{analysis_text}

═══════════════════════════════════
【二、三大法人與主力機構活動】
{institution_text}

═══════════════════════════════════
【三、今日相關產業新聞（Google News）】
{news_text}

═══════════════════════════════════
【四、TrumpNews（川普英文新聞、X/Truth 發言、白宮官方訊息）】
{trump_text}

═══════════════════════════════════
【報告要求】
請產生一份完整的 HTML 格式投資分析報告。**整份報告必須以「台灣 / 中國 / 美國」三大市場為主軸分塊呈現，每個市場各自獨立成一個區塊，內容不可互相混雜**。先用一段簡短的全球總覽開頭，接著依序輸出三個市場區塊。結構如下：

🌐 全球市場總覽（簡短，3–5 行）
   - 今日台灣、中國、美國三大市場的情緒研判（多頭/空頭/中性）各一句總結
   - 跨市場共同的主要風險因子

═══ 🇹🇼 台灣股市 ═══（本區塊只談台股，所有資料僅限台灣標的）
   1. 盤面特徵與半導體（IC設計/製造/封裝/記憶體/功率/材料/磊晶）、礦產資源（稀土/黃金/銅/鐵礦）產業趨勢
   2. 三大法人與主力機構：分析外資/投信/自營商買賣超數據，推測可能涉及的具體機構（如 Vanguard/BlackRock、國內投信富邦/國泰/元大等），並判斷大戶持股變動跡象
   3. 技術面精選買入機會（台股評分前5）：每支說明進場邏輯、目標價、止損位，納入機構買超訊號
   4. 風險警示（台股偏空或訊號危險標的）與持有者應對策略
   5. 相關新聞影響與明日展望、操作建議

═══ 🇨🇳 中國股市 ═══（本區塊只談中國標的，不可併入台股或美股）
   1. 逐一整理中國股市標的的技術評級、MA、RSI、KD、布林通道、量價/OBV、支撐壓力與短期量化預測
   2. 需涵蓋以下板塊與標的，並分別說明各板塊的主要機會與風險：
      · 新能源汽車：比亞迪（002594.SZ）、賽力斯（601127.SS）
      · 半導體／晶圓代工：芯聯集成（688469.SS）
      · 半導體／功率半導體：士蘭微（600460.SS）、華潤微（688396.SS）、斯達半導（603290.SS）、揚杰科技（300373.SZ）、英諾賽科（02577.HK）
      · 半導體／化合物半導體：三安光電（600703.SS）
      · 半導體／矽片材料：立昂微（605358.SS）
      · 半導體／射頻IC：卓勝微（300782.SZ）
      · 半導體／封裝測試：長電科技（600584.SS）
      · 光通訊：長飛光纖（601869.SS）
   3. 相關新聞影響與明日展望、操作建議

═══ 🇺🇸 美國股市 ═══（本區塊只談美股，TrumpNews 一律歸入此區塊）
   1. 盤面特徵與半導體、礦產資源產業趨勢
   2. 技術面精選買入機會（美股評分前5）：每支說明進場邏輯、目標價、止損位
   3. 風險警示（美股偏空或訊號危險標的）與應對策略
   4. 相關新聞影響
   5. 🏛️ TrumpNews 政策訊號與板塊衝擊：整理川普相關英文新聞、X 發言、Truth Social 發言與白宮新聞稿，明確分析可能影響的領域（半導體/AI、能源、金融利率、國防、醫療、加密資產、台灣供應鏈），並區分「直接政策訊號」與「媒體解讀/市場反應」
   6. 明日展望與操作建議

【格式要求】
- 每個市場區塊以 <h2> 大標題開頭（如「🇹🇼 台灣股市」），區塊內各小節用 <h3>，三大市場區塊之間以 <hr> 分隔，確保視覺上清楚分開
- 使用繁體中文
- 輸出純 HTML（不含 <!DOCTYPE>、<html>、<body> 標籤，只輸出內容部分）
- 使用 inline style，台灣股市配色：上漲／買進／正面訊息 #EF5350，跌／賣出／負面訊息 #26A69A，中性 #FFA726
- 每個章節加上標題 h2，重要數字用 <strong> 標記
- 機構名稱與買賣訊號用 <mark> 標記突出顯示
- 結尾加上免責聲明

⚠️ 本分析完全基於技術指標、機構投資數據與公開新聞，不構成投資建議，投資人需自行評估風險。"""


def generate_gpt_report(
    all_results: dict,
    market_sentiment: str = "中性",
    trump_news: dict | None = None,
) -> Optional[str]:
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
    if trump_news is None:
        logger.info("Fetching TrumpNews for report...")
        trump_news = fetch_trump_news()

    logger.info("Calling GPT-4o for report generation...")
    try:
        client = OpenAI(api_key=api_key)
        prompt = _build_prompt(all_results, all_news, market_sentiment, date_str, trump_news)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是頂尖的台灣、美國與中國股市投資分析師，熟悉技術分析、半導體產業鏈、汽車產業與礦產資源市場。"
                        "你的報告準確、專業、有洞察力，同時提醒投資風險。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            temperature=0.4,
        )
        html_content = response.choices[0].message.content.strip()
        # GPT often wraps the HTML in a ```html … ``` markdown fence; strip it so
        # the email/page don't render the literal fence markers.
        if html_content.startswith("```"):
            html_content = re.sub(r"^```[a-zA-Z]*\s*", "", html_content)
            html_content = re.sub(r"\s*```$", "", html_content).strip()
        logger.info(f"GPT report generated: {len(html_content)} chars")
        return html_content
    except Exception as e:
        logger.error(f"GPT API error: {e}")
        return None
