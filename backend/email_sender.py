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

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logger = logging.getLogger(__name__)


def _build_fallback_html(daily_report: dict) -> str:
    """Generate a basic HTML report from technical data (used when GPT is unavailable)."""
    date = daily_report.get("date", datetime.now().strftime("%Y-%m-%d"))
    sentiment = daily_report.get("market_sentiment", "中性")
    top_buy = daily_report.get("top_opportunities", [])
    top_sell = daily_report.get("top_risks", [])
    sector = daily_report.get("sector_summary", {})

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

    # Support multiple recipients via REPORT_RECIPIENT and REPORT_RECIPIENT_2..N
    recipients: list[str] = []
    for key in ("REPORT_RECIPIENT", "REPORT_RECIPIENT_2", "REPORT_RECIPIENT_3"):
        val = os.getenv(key, "").strip()
        if val:
            recipients.append(val)
    if not recipients:
        recipients = ["chenbill718@gmail.com"]

    if not sender or not password or password == "xxxxxxxxxxxxxxxx":
        logger.warning("Gmail credentials not configured in .env — email skipped")
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

    return _smtp_send(sender, password, recipients, msg)


def _smtp_send(sender: str, password: str, recipients: list[str], msg) -> bool:
    """Try port 465 (SSL) first; fall back to port 587 (STARTTLS) if it fails."""
    raw = msg.as_bytes()

    # --- attempt 1: port 465 SSL ---
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(sender, password)
            server.sendmail(sender, recipients, raw)
        logger.info(f"Email sent via port 465 to {recipients}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error("Gmail auth failed (465): %s", e)
        return False          # wrong credentials — no point retrying
    except Exception as e:
        logger.warning("Port 465 failed (%s), trying port 587…", e)

    # --- attempt 2: port 587 STARTTLS ---
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender, password)
            server.sendmail(sender, recipients, raw)
        logger.info(f"Email sent via port 587 to {recipients}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error("Gmail auth failed (587): %s", e)
        return False
    except Exception as e:
        logger.error("Port 587 also failed: %s", e)
        return False


def send_test_email(to: str | None = None) -> dict:
    """
    Attempt to send a minimal test email and return a detailed status dict.
    Used by the /api/test/email endpoint for live diagnosis.
    """
    sender   = os.getenv("GMAIL_SENDER", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    recipient = to or os.getenv("REPORT_RECIPIENT", "chenbill718@gmail.com").strip()

    result: dict = {
        "sender_configured": bool(sender),
        "password_configured": bool(password) and password != "xxxxxxxxxxxxxxxx",
        "recipient": recipient,
        "port_tried": None,
        "success": False,
        "error": None,
    }

    if not sender or not password or password == "xxxxxxxxxxxxxxxx":
        result["error"] = "Gmail credentials missing in environment"
        return result

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[股市監控] ✅ 測試郵件 {now}"
    msg["From"]    = f"股市監控系統 <{sender}>"
    msg["To"]      = recipient
    msg.attach(MIMEText(
        f"<h3>✅ 測試郵件</h3><p>Railway SMTP 連線正常。時間：{now}</p>",
        "html", "utf-8"
    ))
    raw = msg.as_bytes()

    for port, use_ssl in [(465, True), (587, False)]:
        result["port_tried"] = port
        try:
            if use_ssl:
                with smtplib.SMTP_SSL("smtp.gmail.com", port, timeout=20) as s:
                    s.login(sender, password)
                    s.sendmail(sender, [recipient], raw)
            else:
                with smtplib.SMTP("smtp.gmail.com", port, timeout=20) as s:
                    s.ehlo(); s.starttls(); s.ehlo()
                    s.login(sender, password)
                    s.sendmail(sender, [recipient], raw)
            result["success"] = True
            result["error"] = None
            return result
        except smtplib.SMTPAuthenticationError as e:
            result["error"] = f"Auth failed (port {port}): {e}"
            return result   # wrong password → no point retrying other port
        except Exception as e:
            result["error"] = f"port {port}: {e}"
            # try next port

    return result
