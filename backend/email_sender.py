"""
Gmail SMTP email sender for daily investment reports.
Uses App Password — does NOT require OAuth.
"""
from __future__ import annotations

import logging
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logger = logging.getLogger(__name__)


def _get_report_recipients() -> list[str]:
    recipients: list[str] = []
    for key in ("REPORT_RECIPIENT", "REPORT_RECIPIENT_2", "REPORT_RECIPIENT_3"):
        val = os.getenv(key, "").strip()
        if val:
            recipients.append(val)
    return recipients or ["chenbill718@gmail.com"]


def _build_chip_section_html(all_results: dict) -> str:
    """Build 三大法人/融資融券 summary HTML table from FinMind data in all_results."""
    rows_buy, rows_sell = [], []
    for symbol, result in all_results.items():
        if result.get("error"):
            continue
        inv = result.get("investors", {})
        if inv.get("type") != "tw":
            continue
        comp = inv.get("components", {})
        total = comp.get("total_net", 0)
        if total == 0:
            continue
        rows_buy.append({
            "symbol":      symbol,
            "name":        result.get("name", ""),
            "foreign_net": comp.get("foreign_net", 0),
            "trust_net":   comp.get("trust_net", 0),
            "dealer_net":  comp.get("dealer_net", 0),
            "total_net":   total,
        })

    rows_buy.sort(key=lambda x: x["total_net"], reverse=True)
    top_buy  = rows_buy[:8]
    top_sell = sorted(rows_buy, key=lambda x: x["total_net"])[:8]

    def fmt(n):
        color = "#26A69A" if n > 0 else ("#EF5350" if n < 0 else "#888")
        sign  = "+" if n > 0 else ""
        return f"<span style='color:{color}'>{sign}{n:,}</span>"

    header = (
        "<tr style='background:#0A1A2A;color:#888;font-size:12px'>"
        "<th style='padding:4px 8px;text-align:left'>代號</th>"
        "<th style='padding:4px 8px;text-align:left'>名稱</th>"
        "<th style='padding:4px 8px;text-align:right'>外資</th>"
        "<th style='padding:4px 8px;text-align:right'>投信</th>"
        "<th style='padding:4px 8px;text-align:right'>自營</th>"
        "<th style='padding:4px 8px;text-align:right'>合計</th>"
        "</tr>"
    )

    def make_rows(lst):
        return "".join(
            f"<tr><td style='padding:4px 8px'>{r['symbol']}</td>"
            f"<td style='padding:4px 8px'>{escape(r['name'])}</td>"
            f"<td style='padding:4px 8px;text-align:right;font-family:monospace'>{fmt(r['foreign_net'])}</td>"
            f"<td style='padding:4px 8px;text-align:right;font-family:monospace'>{fmt(r['trust_net'])}</td>"
            f"<td style='padding:4px 8px;text-align:right;font-family:monospace'>{fmt(r['dealer_net'])}</td>"
            f"<td style='padding:4px 8px;text-align:right;font-family:monospace'><strong>{fmt(r['total_net'])}</strong></td>"
            "</tr>"
            for r in lst
        )

    if not top_buy and not top_sell:
        return ""

    buy_table = (
        "<h3 style='color:#26A69A;margin-top:16px'>▲ 三大法人買超 TOP 8（股數）</h3>"
        f"<table style='border-collapse:collapse;width:100%'>{header}{make_rows(top_buy)}</table>"
        if top_buy else ""
    )
    sell_table = (
        "<h3 style='color:#EF5350;margin-top:16px'>▼ 三大法人賣超 TOP 8（股數）</h3>"
        f"<table style='border-collapse:collapse;width:100%'>{header}{make_rows(top_sell)}</table>"
        if top_sell else ""
    )

    return (
        "<h2 style='color:#40C4FF;margin-top:24px'>🏢 三大法人動向（FinMind）</h2>"
        + buy_table + sell_table
    )


def _build_fallback_html(daily_report: dict) -> str:
    """Generate a basic HTML report from technical data (used when GPT is unavailable)."""
    date = daily_report.get("date", datetime.now().strftime("%Y-%m-%d"))
    sentiment = daily_report.get("market_sentiment", "中性")
    top_buy = daily_report.get("top_opportunities", [])
    top_sell = daily_report.get("top_risks", [])
    sector = daily_report.get("sector_summary", {})
    trump_news = daily_report.get("trump_news", {})
    trump_impact = trump_news.get("impact", {}) if isinstance(trump_news, dict) else {}
    all_results = daily_report.get("all_results", {})

    sentiment_color = "#26A69A" if sentiment == "多頭" else ("#EF5350" if sentiment == "空頭" else "#FFA726")

    buy_rows = "".join(
        f"<tr><td style='padding:4px 8px'>{s['name']}</td><td style='padding:4px 8px;color:#888'>{s['symbol']}</td>"
        f"<td style='padding:4px 8px;color:#26A69A;font-weight:bold'>{s['rating']}</td>"
        f"<td style='padding:4px 8px;font-family:monospace'>{s['score']:+.1f}</td></tr>"
        for s in top_buy
    )
    sell_rows = "".join(
        f"<tr><td style='padding:4px 8px'>{s['name']}</td><td style='padding:4px 8px;color:#888'>{s['symbol']}</td>"
        f"<td style='padding:4px 8px;color:#EF5350;font-weight:bold'>{s['rating']}</td>"
        f"<td style='padding:4px 8px;font-family:monospace'>{s['score']:+.1f}</td></tr>"
        for s in top_sell
    )
    sector_rows = "".join(
        f"<tr><td style='padding:4px 8px'>{sec}</td>"
        f"<td style='padding:4px 8px;color:{'#26A69A' if v['sentiment']=='多頭' else '#EF5350' if v['sentiment']=='空頭' else '#FFA726'}'>"
        f"{v['sentiment']}</td><td style='padding:4px 8px;font-family:monospace'>{v['avg_score']:+.2f}</td></tr>"
        for sec, v in sector.items()
    )
    china_market = daily_report.get("market_sections", {}).get("中國股市", {})
    china_rows = "".join(
        f"<tr><td style='padding:4px 8px'>{escape(r.get('name', ''))}</td>"
        f"<td style='padding:4px 8px;color:#888'>{escape(r.get('symbol', ''))}</td>"
        f"<td style='padding:4px 8px'>{r.get('price', '—')}</td>"
        f"<td style='padding:4px 8px;color:{'#26A69A' if r.get('score', 0) > 0 else '#EF5350' if r.get('score', 0) < 0 else '#FFA726'}'>"
        f"{escape(r.get('rating', '—'))} ({r.get('score', 0):+.1f})</td>"
        f"<td style='padding:4px 8px;font-family:monospace'>{r.get('indicators', {}).get('RSI') or '—'}</td>"
        f"<td style='padding:4px 8px;font-family:monospace'>{r.get('support') or '—'} / {r.get('resistance') or '—'}</td></tr>"
        for r in china_market.get("results", {}).values()
    )
    china_section = f"""
<h2 style="color:#DE2910;margin-top:24px">🇨🇳 中國股市</h2>
<p>板塊情緒：<strong style="color:#FFA726">{escape(china_market.get('sentiment', '暫無資料'))}</strong></p>
<table style="border-collapse:collapse;width:100%">
<tr style="background:#2A1010;color:#AAA;font-size:12px">
  <th style="padding:4px 8px;text-align:left">名稱</th><th style="padding:4px 8px;text-align:left">代號</th>
  <th style="padding:4px 8px;text-align:left">現價</th><th style="padding:4px 8px;text-align:left">技術評級</th>
  <th style="padding:4px 8px;text-align:left">RSI</th><th style="padding:4px 8px;text-align:left">支撐 / 壓力</th>
</tr>{china_rows or '<tr><td colspan="6" style="padding:8px;color:#888">本次沒有可用的中國股市技術分析資料</td></tr>'}</table>
"""
    trump_theme_rows = "".join(
        f"<tr><td style='padding:4px 8px'>{escape(t.get('label',''))}</td>"
        f"<td style='padding:4px 8px;color:#FFA726'>{escape(t.get('bias',''))}</td>"
        f"<td style='padding:4px 8px'>{escape('、'.join(t.get('sectors', [])[:4]))}</td>"
        f"<td style='padding:4px 8px;font-family:monospace'>{int(t.get('hit_count', 0))}</td></tr>"
        for t in trump_impact.get("themes", [])[:6]
    )
    trump_sections = trump_news.get("sections", {}) if isinstance(trump_news, dict) else {}
    trump_latest = []
    for key in ("truth_posts", "white_house", "english_news", "x_posts"):
        for item in trump_sections.get(key, [])[:2]:
            trump_latest.append(item)
    trump_latest_rows = "".join(
        f"<li style='margin:4px 0'><strong>{escape(item.get('source',''))}</strong> "
        f"<span style='color:#888'>{escape((item.get('published_at') or '')[:16])}</span> — "
        f"{escape(item.get('title') or item.get('summary') or '')}</li>"
        for item in trump_latest[:8]
    )
    trump_block = ""
    if trump_impact or trump_latest_rows:
        trump_block = f"""
<h3 style="color:#40C4FF;margin-top:16px">TrumpNews 政策訊號</h3>
<p>整體判讀：<strong style="color:#FFA726">{escape(trump_impact.get('overall', '目前未偵測到明確訊號'))}</strong></p>
<table style="border-collapse:collapse;width:100%">
<tr style="background:#0A1A2A;color:#888;font-size:12px">
  <th style="padding:4px 8px;text-align:left">主題</th><th style="padding:4px 8px;text-align:left">屬性</th>
  <th style="padding:4px 8px;text-align:left">可能影響板塊</th><th style="padding:4px 8px;text-align:left">訊號數</th>
</tr>{trump_theme_rows}</table>
<ul style="padding-left:18px">{trump_latest_rows}</ul>
"""

    chip_section = _build_chip_section_html(all_results)

    return f"""
<h2 style="color:#40C4FF">📊 量化技術分析報告（GPT分析未啟用）</h2>
<p>市場情緒：<strong style="color:{sentiment_color};font-size:16px">{sentiment}</strong></p>

<h3 style="color:#26A69A">🎯 買入候選 TOP 5</h3>
<table style="border-collapse:collapse;width:100%">
<tr style="background:#1A2A1A;color:#888;font-size:12px">
  <th style="padding:4px 8px;text-align:left">名稱</th><th style="padding:4px 8px;text-align:left">代號</th>
  <th style="padding:4px 8px;text-align:left">評級</th><th style="padding:4px 8px;text-align:left">評分</th>
</tr>{buy_rows}</table>

<h3 style="color:#EF5350;margin-top:16px">⚠️ 風險警示</h3>
<table style="border-collapse:collapse;width:100%">
<tr style="background:#2A1A1A;color:#888;font-size:12px">
  <th style="padding:4px 8px;text-align:left">名稱</th><th style="padding:4px 8px;text-align:left">代號</th>
  <th style="padding:4px 8px;text-align:left">評級</th><th style="padding:4px 8px;text-align:left">評分</th>
</tr>{sell_rows}</table>

<h3 style="color:#FFA726;margin-top:16px">📂 板塊情緒</h3>
<table style="border-collapse:collapse;width:100%">
<tr style="background:#1A1A0A;color:#888;font-size:12px">
  <th style="padding:4px 8px;text-align:left">板塊</th><th style="padding:4px 8px;text-align:left">情緒</th>
  <th style="padding:4px 8px;text-align:left">平均評分</th>
</tr>{sector_rows}</table>

{chip_section}

{china_section}

{trump_block}
"""


def _wrap_email_template(content_html: str, date_str: str, generated_at: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{
    margin: 0; padding: 0;
    background-color: #0D0D0D;
    color: #E0E0E0;
    font-family: -apple-system, 'PingFang TC', 'Microsoft JhengHei', Arial, sans-serif;
    font-size: 14px; line-height: 1.6;
  }}
  .container {{
    max-width: 800px; margin: 0 auto; padding: 24px 16px;
  }}
  .header {{
    background: linear-gradient(135deg, #0A2A4A 0%, #0D1A2A 100%);
    border-bottom: 2px solid #1565C0;
    padding: 20px 24px; border-radius: 8px 8px 0 0;
  }}
  .header h1 {{ margin: 0; color: #40C4FF; font-size: 20px; }}
  .header p  {{ margin: 4px 0 0; color: #7A9BBB; font-size: 12px; }}
  .content {{ background: #141414; padding: 24px; border-radius: 0 0 8px 8px; }}
  h2 {{ color: #40C4FF; border-bottom: 1px solid #1A2A3A; padding-bottom: 6px; margin-top: 24px; }}
  h3 {{ color: #7AB8FF; margin-top: 18px; }}
  a {{ color: #40C4FF; }}
  .footer {{
    text-align: center; color: #3A3A3A; font-size: 11px;
    margin-top: 20px; padding-top: 12px; border-top: 1px solid #1A1A1A;
  }}
  table {{ width: 100%; border-collapse: collapse; }}
  tr:nth-child(even) {{ background: #1A1A1A; }}
  strong {{ color: inherit; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📈 每日投資分析報告</h1>
    <p>{date_str} &nbsp;|&nbsp; 生成時間：{generated_at} &nbsp;|&nbsp; 台灣/美國股市監控系統</p>
  </div>
  <div class="content">
    {content_html}
  </div>
  <div class="footer">
    ⚠ 本報告由 AI 自動生成，完全基於技術指標與公開新聞，不構成投資建議。<br>
    投資有風險，請自行評估並承擔相應責任。<br>
    如需取消訂閱，請回覆此信件。
  </div>
</div>
</body>
</html>"""


def send_login_notification(ip: str, key_type: str, geo: dict) -> None:
    """Send a security alert when someone successfully authenticates."""
    sender   = os.getenv("GMAIL_SENDER", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    alert_to = "chenbill718@gmail.com"

    if not sender or not password or password == "xxxxxxxxxxxxxxxx":
        logger.warning("Gmail not configured — login notification skipped")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    country     = geo.get("country", "未知")
    region      = geo.get("regionName", "")
    city        = geo.get("city", "")
    isp         = geo.get("isp", "")
    lat         = geo.get("lat", "")
    lon         = geo.get("lon", "")
    maps_link   = f"https://www.google.com/maps?q={lat},{lon}" if lat and lon else ""
    location    = ", ".join(filter(None, [city, region, country]))

    maps_html = (
        f'<a href="{maps_link}" style="color:#40C4FF">在 Google Maps 查看</a>'
        if maps_link else "無法取得座標"
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><meta charset="UTF-8">
<style>
  body {{ background:#0D0D0D; color:#E0E0E0; font-family:-apple-system,'PingFang TC',Arial,sans-serif; font-size:14px; margin:0; padding:0; }}
  .wrap {{ max-width:520px; margin:0 auto; padding:24px 16px; }}
  .card {{ background:#1A1A1A; border:1px solid #FF5252; border-radius:8px; padding:24px; }}
  h2   {{ color:#FF5252; margin:0 0 16px; font-size:18px; }}
  .row {{ display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #222; }}
  .lbl {{ color:#888; font-size:12px; }}
  .val {{ color:#E0E0E0; font-size:13px; font-weight:500; }}
  .footer {{ color:#333; font-size:11px; text-align:center; margin-top:16px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h2>🔐 密鑰登入警報</h2>
    <div class="row"><span class="lbl">時間</span><span class="val">{now} (本地)</span></div>
    <div class="row"><span class="lbl">密鑰類型</span><span class="val">{key_type}</span></div>
    <div class="row"><span class="lbl">IP 地址</span><span class="val">{ip}</span></div>
    <div class="row"><span class="lbl">國家</span><span class="val">{country}</span></div>
    <div class="row"><span class="lbl">地區 / 城市</span><span class="val">{location or '未知'}</span></div>
    <div class="row"><span class="lbl">ISP / 運營商</span><span class="val">{isp or '未知'}</span></div>
    <div class="row"><span class="lbl">座標</span><span class="val">{maps_html}</span></div>
  </div>
  <div class="footer">此為股市監控系統自動安全警報，若非本人操作請立即更換密鑰。</div>
</div>
</body>
</html>"""

    key_label = {"report": "報告生成密鑰", "stock": "股票管理密鑰"}.get(key_type, key_type)
    subject = f"[股市監控] 🔐 密鑰登入警報 — {key_label} | {location or ip} | {now[:16]}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"股市監控安全警報 <{sender}>"
    msg["To"]      = alert_to
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(sender, password)
            server.sendmail(sender, [alert_to], msg.as_bytes())
        logger.info("Login notification sent to %s (IP: %s, %s)", alert_to, ip, location)
    except Exception as e:
        logger.error("Login notification email failed: %s", e)


def send_daily_report(html_content: str, daily_report: dict, pdf_path: str | None = None) -> bool:
    """
    Send the daily report email via Gmail SMTP.
    html_content : GPT-generated or fallback HTML body content
    daily_report : raw analysis dict (used for subject line stats)
    pdf_path     : optional path to a PDF attachment
    Returns True on success.
    """
    sender   = os.getenv("GMAIL_SENDER", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    resend_key = os.getenv("RESEND_API_KEY", "").strip()

    recipients = _get_report_recipients()

    smtp_configured = bool(sender) and bool(password) and password != "xxxxxxxxxxxxxxxx"
    if not resend_key and not smtp_configured:
        logger.warning("No RESEND_API_KEY or Gmail credentials configured in .env — email skipped")
        return False

    date_str     = daily_report.get("date", datetime.now().strftime("%Y-%m-%d"))
    sentiment    = daily_report.get("market_sentiment", "─")
    analyzed     = len(daily_report.get("all_results", {}))
    generated_at = daily_report.get("generated_at", datetime.now().strftime("%H:%M"))

    subject = (
        f"[股市監控] {date_str} 每日報告 | "
        f"市場情緒: {sentiment} | {analyzed} 支股票"
    )

    full_html = _wrap_email_template(html_content, date_str, generated_at)

    if resend_key:
        if _send_via_resend(resend_key, recipients, subject, full_html, pdf_path):
            return True
        if not smtp_configured:
            return False
        logger.warning("Resend failed; falling back to Gmail SMTP")

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = f"股市監控系統 <{sender}>"
    msg["To"]      = ", ".join(recipients)

    # HTML body
    html_part = MIMEMultipart("alternative")
    html_part.attach(MIMEText(full_html, "html", "utf-8"))
    msg.attach(html_part)

    # PDF attachment (if provided and file exists)
    if pdf_path and os.path.exists(pdf_path):
        pdf_filename = os.path.basename(pdf_path)
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        attachment = MIMEApplication(pdf_data, _subtype="pdf")
        attachment.add_header("Content-Disposition", "attachment", filename=pdf_filename)
        msg.attach(attachment)
        logger.info(f"PDF attached: {pdf_filename}")

    # ── fallback: Gmail SMTP (local dev only) ─────────────────────────────────
    return _smtp_send(sender, password, recipients, msg)


def _build_resend_attachments(paths: list[str | None]) -> list[dict]:
    import base64

    attachments: list[dict] = []
    for path in paths:
        if not path or not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            attachments.append({
                "filename": os.path.basename(path),
                "content": base64.b64encode(f.read()).decode(),
            })
    return attachments


def _send_via_resend_with_attachments(
    api_key: str,
    recipients: list[str],
    subject: str,
    full_html: str,
    attachments: list[str | None],
) -> bool:
    import requests as _req

    payload: dict = {
        "from": "股市監控系統 <onboarding@resend.dev>",
        "to": recipients,
        "subject": subject,
        "html": full_html,
    }
    encoded = _build_resend_attachments(attachments)
    if encoded:
        payload["attachments"] = encoded

    try:
        resp = _req.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            logger.info("Resend API: data health email sent -> %s", recipients)
            return True
        logger.error("Resend API %d: %s", resp.status_code, resp.text)
        return False
    except Exception as e:
        logger.error("Resend API request failed: %s", e)
        return False


def _attach_file(msg: MIMEMultipart, path: str | None, subtype: str | None = None) -> None:
    if not path or not os.path.exists(path):
        return
    filename = os.path.basename(path)
    ext = os.path.splitext(filename)[1].lower()
    if subtype == "markdown" or ext in (".md", ".markdown"):
        with open(path, encoding="utf-8") as f:
            attachment = MIMEText(f.read(), "markdown", "utf-8")
    else:
        with open(path, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype=subtype or "octet-stream")
    attachment.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(attachment)
    logger.info("Attachment added: %s", filename)


def send_data_health_report(
    html_content: str,
    subject: str,
    md_path: str | None = None,
    pdf_path: str | None = None,
) -> bool:
    """
    Send the scheduled data-health report with Markdown and PDF attachments.
    Reuses the same recipient and delivery settings as the daily report.
    """
    sender = os.getenv("GMAIL_SENDER", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    recipients = _get_report_recipients()

    smtp_configured = bool(sender) and bool(password) and password != "xxxxxxxxxxxxxxxx"
    if not resend_key and not smtp_configured:
        logger.warning("No RESEND_API_KEY or Gmail credentials configured in .env - data health email skipped")
        return False

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ margin:0; padding:0; background:#0D0D0D; color:#E0E0E0; font-family:-apple-system,'PingFang TC','Microsoft JhengHei',Arial,sans-serif; font-size:15px; line-height:1.65; }}
  .container {{ max-width:860px; margin:0 auto; padding:24px 16px; }}
  .header {{ background:#10243a; border-bottom:2px solid #40C4FF; padding:20px 24px; border-radius:8px 8px 0 0; }}
  .header h1 {{ margin:0; color:#8fd8ff; font-size:21px; }}
  .header p {{ margin:6px 0 0; color:#a8bdd1; font-size:13px; }}
  .content {{ background:#151515; padding:24px; border-radius:0 0 8px 8px; }}
  table {{ width:100%; border-collapse:collapse; }}
  th, td {{ border-bottom:1px solid #2a2a2a; padding:8px 10px; text-align:left; }}
  th {{ color:#9db7d1; background:#101820; }}
  .ok {{ color:#55d6a7; }} .warn {{ color:#ffc857; }} .error {{ color:#ff6b6b; }} .unknown {{ color:#9aa4ad; }}
  .footer {{ color:#666; font-size:12px; margin-top:18px; text-align:center; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Stock Monitor 數據健康檢查</h1>
    <p>生成時間：{generated_at} | 排程：每日 19:00 Asia/Taipei | 附件含 Markdown 與 PDF</p>
  </div>
  <div class="content">{html_content}</div>
  <div class="footer">本報告只檢查更新狀態與資料完整性，不附原始價格、持股或新聞明細。</div>
</div>
</body>
</html>"""

    if resend_key:
        if _send_via_resend_with_attachments(resend_key, recipients, subject, full_html, [md_path, pdf_path]):
            return True
        if not smtp_configured:
            return False
        logger.warning("Resend failed; falling back to Gmail SMTP")

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"股市監控系統 <{sender}>"
    msg["To"] = ", ".join(recipients)

    html_part = MIMEMultipart("alternative")
    html_part.attach(MIMEText(full_html, "html", "utf-8"))
    msg.attach(html_part)
    _attach_file(msg, md_path, subtype="markdown")
    _attach_file(msg, pdf_path, subtype="pdf")
    return _smtp_send(sender, password, recipients, msg)


def _send_via_resend(api_key: str, recipients: list[str], subject: str,
                     full_html: str, pdf_path: str | None = None) -> bool:
    """
    Send via Resend HTTP API (port 443 — works on Railway).
    Free tier: 3 000 emails/month, 100/day.
    Sends FROM onboarding@resend.dev unless a custom verified domain is configured.
    """
    import requests as _req, base64

    payload: dict = {
        "from": "股市監控系統 <onboarding@resend.dev>",
        "to": recipients,
        "subject": subject,
        "html": full_html,
    }

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            payload["attachments"] = [{
                "filename": os.path.basename(pdf_path),
                "content": base64.b64encode(f.read()).decode(),
            }]

    try:
        resp = _req.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            logger.info("Resend API: email sent → %s", recipients)
            return True
        logger.error("Resend API %d: %s", resp.status_code, resp.text)
        return False
    except Exception as e:
        logger.error("Resend API request failed: %s", e)
        return False


def _smtp_send(sender: str, password: str, recipients: list[str], msg) -> bool:
    """
    Try Gmail SMTP — port 465 (SSL) first, then port 587 (STARTTLS).
    NOTE: Most cloud hosts (including Railway) block SMTP ports.
    This is kept as a fallback for local development only.
    """
    raw = msg.as_bytes()

    for port, use_ssl in [(465, True), (587, False)]:
        try:
            if use_ssl:
                with smtplib.SMTP_SSL("smtp.gmail.com", port, timeout=30) as s:
                    s.login(sender, password)
                    s.sendmail(sender, recipients, raw)
            else:
                with smtplib.SMTP("smtp.gmail.com", port, timeout=30) as s:
                    s.ehlo(); s.starttls(); s.ehlo()
                    s.login(sender, password)
                    s.sendmail(sender, recipients, raw)
            logger.info("Email sent via SMTP port %d to %s", port, recipients)
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error("Gmail auth failed (port %d): %s", port, e)
            return False
        except Exception as e:
            logger.warning("SMTP port %d failed: %s", port, e)

    logger.error("All SMTP ports blocked — use RESEND_API_KEY on cloud hosts")
    return False


def send_test_email(to: str | None = None) -> dict:
    """
    Attempt to send a minimal test email and return a detailed status dict.
    Tries Resend HTTP API first, falls back to Gmail SMTP.
    Used by the /api/test/email endpoint for live diagnosis.
    """
    recipient  = to or os.getenv("REPORT_RECIPIENT", "chenbill718@gmail.com").strip()
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    sender     = os.getenv("GMAIL_SENDER", "").strip()
    password   = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    now        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result: dict = {
        "resend_configured": bool(resend_key),
        "smtp_configured": bool(sender) and bool(password) and password != "xxxxxxxxxxxxxxxx",
        "recipient": recipient,
        "method": None,
        "success": False,
        "error": None,
    }

    test_html = f"<h3>✅ 股市監控 — 測試郵件</h3><p>Railway 郵件系統連線正常。時間：{now}</p>"
    subject   = f"[股市監控] ✅ 測試郵件 {now}"

    # ── try Resend first ──────────────────────────────────────────────────────
    if resend_key:
        import requests as _req
        result["method"] = "resend"
        try:
            resp = _req.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}"},
                json={
                    "from": "股市監控系統 <onboarding@resend.dev>",
                    "to": [recipient],
                    "subject": subject,
                    "html": test_html,
                },
                timeout=30,
            )
            result["resend_status"] = resp.status_code
            result["resend_body"] = resp.text[:500]
            result["success"] = resp.status_code in (200, 201)
            if not result["success"]:
                result["error"] = f"Resend HTTP {resp.status_code}: {resp.text[:300]}"
        except Exception as e:
            result["error"] = f"Resend request exception: {e}"
        return result

    # ── fallback: Gmail SMTP ──────────────────────────────────────────────────
    if not sender or not password or password == "xxxxxxxxxxxxxxxx":
        result["error"] = "No RESEND_API_KEY and Gmail credentials missing — email cannot be sent"
        return result

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"股市監控系統 <{sender}>"
    msg["To"]      = recipient
    msg.attach(MIMEText(test_html, "html", "utf-8"))
    raw = msg.as_bytes()

    for port, use_ssl in [(465, True), (587, False)]:
        result["method"] = f"smtp:{port}"
        try:
            if use_ssl:
                with smtplib.SMTP_SSL("smtp.gmail.com", port, timeout=20) as s:
                    s.login(sender, password); s.sendmail(sender, [recipient], raw)
            else:
                with smtplib.SMTP("smtp.gmail.com", port, timeout=20) as s:
                    s.ehlo(); s.starttls(); s.ehlo()
                    s.login(sender, password); s.sendmail(sender, [recipient], raw)
            result["success"] = True
            return result
        except smtplib.SMTPAuthenticationError as e:
            result["error"] = f"Gmail auth failed (port {port}): {e}"
            return result
        except Exception as e:
            result["error"] = f"SMTP port {port}: {e}"

    return result
