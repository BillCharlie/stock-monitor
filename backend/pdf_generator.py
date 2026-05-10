"""
Convert the HTML daily report to a PDF using fpdf2.
Strips dark-mode styles and renders a clean light-mode PDF.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent))) / "reports"

# ─── HTML → clean text helpers ───────────────────────────────────────────────

def _strip_html_tags(html: str) -> str:
    """Remove all HTML tags, decode basic entities, strip emoji."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    text = re.sub(r"\s{2,}", " ", text)
    # Remove emoji / symbols outside BMP that CJK fonts don't cover
    text = re.sub(r"[\U00010000-\U0010FFFF]", "", text)
    # Remove common problematic symbols (⚠, variation selector, etc.)
    text = re.sub(r"[⚠️‼⁉▪-◾☀-⛿✀-➿]", "", text)
    return text.strip()


def _extract_sections(html: str) -> list[tuple[str, str]]:
    """
    Best-effort section extraction from GPT HTML.
    Returns list of (heading, body_text) pairs.
    """
    # Split on h2 headings
    parts = re.split(r"<h2[^>]*>(.*?)</h2>", html, flags=re.IGNORECASE | re.DOTALL)
    sections = []
    if len(parts) <= 1:
        # No h2 headings found — return the whole thing as one block
        return [("報告內容", _strip_html_tags(html))]

    # parts[0] is preamble (often empty), then alternating heading / body
    preamble = _strip_html_tags(parts[0]).strip()
    if preamble:
        sections.append(("報告摘要", preamble))

    for i in range(1, len(parts) - 1, 2):
        heading = _strip_html_tags(parts[i]).strip()
        body    = _strip_html_tags(parts[i + 1]).strip() if i + 1 < len(parts) else ""
        if heading:
            sections.append((heading, body))

    return sections


# ─── PDF generation ──────────────────────────────────────────────────────────

def save_report_pdf(html_content: str, daily_report: dict) -> str | None:
    """
    Convert html_content to a structured PDF and save to reports/ directory.
    Returns the absolute path of the saved PDF, or None on failure.
    """
    try:
        from fpdf import FPDF  # noqa: PLC0415
    except ImportError:
        logger.error("fpdf2 not installed — run: pip install fpdf2")
        return None

    REPORTS_DIR.mkdir(exist_ok=True)

    date_str      = daily_report.get("date", datetime.now().strftime("%Y-%m-%d"))
    generated_at  = daily_report.get("generated_at", datetime.now().strftime("%H:%M"))
    sentiment     = daily_report.get("market_sentiment", "─")
    analyzed      = len(daily_report.get("all_results", {}))
    filename      = f"daily_report_{date_str}.pdf"
    pdf_path      = REPORTS_DIR / filename

    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # ── Use a Unicode-capable built-in font ──────────────────────────────
        # fpdf2 ships DejaVu fonts that cover CJK characters starting from
        # fpdf2 2.7.9 (not yet the default). Fallback: write ASCII summary when
        # CJK rendering is unavailable, and attach the HTML as a note.
        #
        # More reliable: use the system Microsoft JhengHei (Windows)
        import os
        cjk_font_loaded = False
        for font_path in [
            r"C:\Windows\Fonts\msjh.ttc",    # Microsoft JhengHei Regular
            r"C:\Windows\Fonts\msjhbd.ttc",  # Microsoft JhengHei Bold
            r"C:\Windows\Fonts\mingliu.ttc",  # MingLiU fallback
            r"C:\Windows\Fonts\kaiu.ttf",     # DFKai-SB
        ]:
            if os.path.exists(font_path):
                try:
                    pdf.add_font("CJK", style="", fname=font_path, uni=True)
                    pdf.add_font("CJK", style="B", fname=font_path, uni=True)
                    cjk_font_loaded = True
                    break
                except Exception:
                    continue

        body_font  = "CJK" if cjk_font_loaded else "Helvetica"
        title_font = "CJK" if cjk_font_loaded else "Helvetica"

        # ── Cover / header ────────────────────────────────────────────────────
        pdf.set_fill_color(13, 71, 161)   # #0D47A1
        pdf.rect(0, 0, 210, 28, "F")

        pdf.set_font(title_font, "B", 16)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, 6)
        pdf.cell(0, 10, "[ 每日投資分析報告 ]", ln=True)

        pdf.set_font(body_font, "", 9)
        pdf.set_xy(10, 17)
        pdf.cell(0, 6, f"{date_str}  |  生成時間：{generated_at}  |  台灣/美國股市監控系統", ln=True)

        # ── Stats bar ─────────────────────────────────────────────────────────
        pdf.set_fill_color(232, 245, 253)
        pdf.rect(0, 28, 210, 12, "F")
        pdf.set_text_color(13, 71, 161)
        pdf.set_font(body_font, "B", 10)
        pdf.set_xy(10, 30)
        sentiment_txt = f"市場情緒：{sentiment}     分析股票：{analyzed} 支"
        pdf.cell(0, 8, sentiment_txt, ln=True)

        pdf.set_xy(10, 42)
        pdf.set_text_color(30, 30, 30)

        # ── Report sections ───────────────────────────────────────────────────
        sections = _extract_sections(html_content)
        for heading, body in sections:
            # Section heading
            pdf.ln(3)
            pdf.set_font(title_font, "B", 12)
            pdf.set_text_color(13, 71, 161)
            pdf.set_fill_color(227, 242, 253)
            pdf.cell(0, 8, f"  {heading}", fill=True, ln=True)
            pdf.ln(1)

            # Body text — word-wrap
            pdf.set_font(body_font, "", 9)
            pdf.set_text_color(30, 30, 30)
            if body:
                # Split into paragraphs by sentence / newline for readability
                paragraphs = re.split(r"[。！？\n]{1,}", body)
                for para in paragraphs:
                    para = para.strip()
                    if len(para) < 2:
                        continue
                    # fpdf2 multi_cell handles line wrapping
                    pdf.multi_cell(0, 5.5, para, ln=True)
                    pdf.ln(0.5)

        # ── Top buy / sell table ──────────────────────────────────────────────
        top_buy  = daily_report.get("top_opportunities", [])[:5]
        top_sell = daily_report.get("top_risks", [])[:5]

        if top_buy or top_sell:
            pdf.ln(4)
            pdf.set_font(title_font, "B", 12)
            pdf.set_text_color(13, 71, 161)
            pdf.set_fill_color(227, 242, 253)
            pdf.cell(0, 8, "  技術面評分彙總", fill=True, ln=True)
            pdf.ln(2)

            col_w = [60, 30, 25, 25]
            headers = ["名稱", "代號", "評級", "評分"]

            def table_row(row_data, is_header=False, color=(230, 230, 230)):
                pdf.set_fill_color(*color)
                for i, cell in enumerate(row_data):
                    if is_header:
                        pdf.set_font(body_font, "B", 8)
                        pdf.set_text_color(13, 71, 161)
                    else:
                        pdf.set_font(body_font, "", 8)
                        pdf.set_text_color(30, 30, 30)
                    pdf.cell(col_w[i], 6, str(cell), border=1, fill=is_header, ln=(i == len(row_data) - 1))

            if top_buy:
                pdf.set_font(body_font, "B", 9)
                pdf.set_text_color(0, 121, 107)
                pdf.cell(0, 6, "買入候選", ln=True)
                table_row(headers, is_header=True)
                for s in top_buy:
                    table_row([s.get("name",""), s.get("symbol",""), s.get("rating",""), f"{s.get('score',0):+.1f}"])
                pdf.ln(3)

            if top_sell:
                pdf.set_font(body_font, "B", 9)
                pdf.set_text_color(198, 40, 40)
                pdf.cell(0, 6, "風險警示", ln=True)
                table_row(headers, is_header=True)
                for s in top_sell:
                    table_row([s.get("name",""), s.get("symbol",""), s.get("rating",""), f"{s.get('score',0):+.1f}"])

        # ── Footer ────────────────────────────────────────────────────────────
        pdf.ln(6)
        pdf.set_font(body_font, "", 7.5)
        pdf.set_text_color(120, 120, 120)
        pdf.multi_cell(
            0, 4.5,
            "【免責聲明】本報告由 AI 自動生成，完全基於技術指標與公開新聞，不構成投資建議。"
            "投資有風險，請自行評估並承擔相應責任。",
            ln=True,
        )

        pdf.output(str(pdf_path))
        logger.info(f"PDF saved: {pdf_path}")
        return str(pdf_path)

    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        return None


def latest_report_path() -> str | None:
    """Return the path of the most recently generated PDF, or None."""
    if not REPORTS_DIR.exists():
        return None
    pdfs = sorted(REPORTS_DIR.glob("daily_report_*.pdf"))
    return str(pdfs[-1]) if pdfs else None
