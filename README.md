# Stock Monitor — 台灣 / 美股即時監控與主動式 ETF 分析系統
# Stock Monitor — Taiwan / US Stock Real-Time Monitor & Active ETF Analysis

> **作者 / Author:** Ping yu-Chen, Taiwan
> **版本 / Version:** v2.0
> **授權 / License:** 請詳閱 `LICENSE` / See `LICENSE` — 商業使用須授權 / Commercial use requires written permission

**線上服務 / Live Service:**
- 前端 / Frontend (GitHub Pages): https://billcharlie.github.io/stock-monitor/
- 後端 API / Backend API (Railway): https://stock-monitor-production-b630.up.railway.app

---

## 目錄 / Table of Contents

- [系統簡介 / Overview](#系統簡介--overview)
- [功能總覽 / Features](#功能總覽--features)
- [環境需求 / Requirements](#環境需求--requirements)
- [安裝 / Installation](#安裝--installation)
- [環境設定 / Configuration](#環境設定--configuration)
- [啟動服務 / Start Services](#啟動服務--start-services)
- [排程任務 / Scheduled Jobs](#排程任務--scheduled-jobs)
- [個股分析模型 / Stock Analysis Model](#個股分析模型--stock-analysis-model)
- [主動式 ETF 分析 / Active ETF Analysis](#主動式-etf-分析--active-etf-analysis)
- [主要 API / Key API Endpoints](#主要-api--key-api-endpoints)
- [雲端部署 / Deployment](#雲端部署--deployment)

---

## 系統簡介 / Overview

**中文：**
Stock Monitor 是針對台灣 / 美股市場設計的全自動股市監控與分析系統。系統每日在台股收盤（13:40）與美股收盤（隔日 05:10）後自動執行技術分析，整合 60+ 技術指標訊號、三大法人籌碼、融資融券，並追蹤 34 支台灣主動式 ETF 的持股異動，每日早晨透過 GPT-4o 生成 HTML 報告並以 Email 夾帶 PDF 寄送。前端為 React SPA，部署於 GitHub Pages；後端 FastAPI 部署於 Railway。

**English:**
Stock Monitor is a fully automated stock monitoring and analysis system for Taiwan and US markets. The system runs technical analysis after the Taiwan market close (13:40) and US market close (05:10 next day), integrating 60+ technical indicator signals, Taiwan institutional investor data (三大法人), margin trading data, and tracking of 34 Taiwan active ETFs for holdings changes. Each morning, GPT-4o generates an HTML report delivered by email with a PDF attachment. The React SPA frontend is deployed on GitHub Pages; the FastAPI backend runs on Railway.

---

## 功能總覽 / Features

**中文：**
- **多指標技術分析** — 60+ 訊號加權評分（-2.0 ～ +2.0），五級評等（強力買進 / 買進 / 持有 / 賣出 / 強力賣出）
- **主動式 ETF 持股追蹤** — 34 支台灣主動式 ETF（A 類股票型 / D 類債券型），每日抓取 MoneyDJ 持股明細，偵測新進入 / 退出 / 增減倉位異動
- **三大法人 + 融資融券** — 外資 / 投信 / 自營商買賣超，3 日趨勢評分，融資融券比對分析
- **籌碼集中度分析** — 赫芬達爾指數（HHI），主力進出辨識
- **線性回歸預測** — 5 日 / 20 日預測，含 95% 信賴區間與 R² 準確度
- **RSI / OBV 背離偵測** — RSI 5 日窗口背離 ±1.5 分；OBV 10 日窗口背離 ±1.5 分
- **每日 GPT-4o 報告** — 自動合成技術分析 + 新聞 + 籌碼，生成 HTML 報告，Email 夾帶 PDF
- **Trump 新聞監控** — 追蹤 X、Truth Social、白宮 RSS，納入早報政策面評估
- **產業分類觀察清單** — 70+ 台灣細分類（半導體、AI 雲端、金融、生技等）及美股
- **主動式 ETF 產業分佈** — 各 ETF 持股跨產業匯總，含多時間段 baseline 追蹤（1d / 7d / 30d / 1y）

**English:**
- **Multi-indicator technical analysis** — 60+ signals with weighted scoring (-2.0 to +2.0); five-tier ratings (Strong Buy / Buy / Hold / Sell / Strong Sell)
- **Active ETF holdings tracking** — 34 Taiwan active ETFs (A-type equity / D-type bond); daily scraping of MoneyDJ holdings; detects new positions, exits, and weight changes
- **Institutional investor data (三大法人)** — Foreign / Trust / Dealer net buy/sell, 3-day trend scoring, margin trading analysis
- **Chip concentration analysis** — Herfindahl-Hirschman Index (HHI), major trader identification
- **Linear regression forecast** — 5-day and 20-day price prediction with 95% confidence intervals and R² fit
- **RSI / OBV divergence detection** — RSI 5-bar window divergence ±1.5; OBV 10-bar window divergence ±1.5
- **Daily GPT-4o report** — Synthesizes technical analysis + news + institutional data; delivers HTML report + PDF via email
- **Trump news monitoring** — Tracks X (Twitter), Truth Social, and White House RSS for policy-impact assessment
- **Industry watchlist** — 70+ Taiwan subcategories (semiconductors, AI/cloud, financials, biotech, etc.) and US stocks
- **Active ETF sector distribution** — Cross-ETF holdings aggregation with multi-horizon baseline tracking (1d / 7d / 30d / 1y)

---

## 環境需求 / Requirements

| 項目 / Item | 版本 / Version |
|-------------|----------------|
| Python | ≥ 3.10 |
| Node.js | ≥ 18 |
| OpenAI API Key | GPT-4o 建議 / GPT-4o recommended |
| Resend API Key | 雲端部署推薦 / Recommended for cloud |
| FinMind Token | 三大法人 / 融資融券數據（可選 / optional） |

---

## 安裝 / Installation

### 後端 / Backend

**Windows PowerShell：**

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux：**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 前端 / Frontend

```bash
cd frontend
npm install
```

---

## 環境設定 / Configuration

複製設定範本 / Copy template:

```bash
cp backend/.env.example backend/.env
```

編輯 `backend/.env` / Edit `backend/.env`:

```dotenv
# OpenAI（GPT 報告必要 / required for GPT reports）
OPENAI_API_KEY=sk-proj-...

# Email 傳輸 / Email transport（二選一 / choose one）
# Option A: Resend（雲端部署推薦 / recommended for Railway）
RESEND_API_KEY=re_...

# Option B: Gmail SMTP（本機開發 / local dev only）
GMAIL_SENDER=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

# 報告收件人 / Report recipients（最多三位 / up to 3）
REPORT_RECIPIENT=your@email.com
REPORT_RECIPIENT_2=optional@email.com

# 報告時間（台灣時間 / Taiwan time）
REPORT_HOUR=7
REPORT_MINUTE=0

# API 保護金鑰 / Write-endpoint protection
# 同步設定至 GitHub Secrets: VITE_API_SECRET
API_SECRET_REPORT=your-report-secret
API_SECRET_STOCK=your-stock-secret
```

> Write 端點（POST/DELETE）需在請求標頭加入 `X-API-Secret: <secret>`，與 `API_SECRET_REPORT` 或 `API_SECRET_STOCK` 比對。
> Write endpoints require `X-API-Secret: <secret>` header matching `API_SECRET_REPORT` or `API_SECRET_STOCK`.

---

## 啟動服務 / Start Services

### 後端 / Backend

```powershell
cd backend
python main.py
```

或使用 uvicorn / or with uvicorn:

```bash
uvicorn main:app --reload --port 8765
```

健康確認 / Health check:

```
http://127.0.0.1:8765/api/health
```

### 前端（開發模式）/ Frontend (Dev Mode)

```bash
cd frontend
npm run dev
```

開啟 / Open: `http://127.0.0.1:5173`

正式建置 / Production build:

```bash
cd frontend
npm run build
```

建置產物在 `frontend/dist/`，由 GitHub Actions 自動部署至 GitHub Pages。
Build output goes to `frontend/dist/`, auto-deployed to GitHub Pages via GitHub Actions.

---

## 排程任務 / Scheduled Jobs

所有排程以 **Asia/Taipei** 時區執行 / All jobs run in **Asia/Taipei** timezone:

| 時間 / Time | 說明 / Description | 觸發條件 / Trigger |
|-------------|--------------------|--------------------|
| 每日 13:40（週一–五）| 台股收盤分析 / Taiwan market close analysis | 週一–五 / Mon–Fri |
| 每日 05:10（週二–六）| 美股收盤分析 / US market close analysis | 週二–六 / Tue–Sat |
| 每日 07:00（可設定）| 早報 Email — 技術分析 + GPT 報告 + PDF | 週一–五 / Mon–Fri |
| 每日 18:00（可設定）| ETF 持股更新 / Active ETF holdings refresh | 週一–五 / Mon–Fri |
| 每日 18:30（可設定）| 三大法人 / 融資融券 / ETF / 新聞更新 | 週一–五 / Mon–Fri |
| 每日 19:00（可設定）| 數據健康報告 / Data health report | 每日 / Daily |
| 每 5 小時 | 新聞刷新 / News refresh | 持續 / Continuous |

時間可透過環境變數調整 / Time overrides via env vars:
`REPORT_HOUR`, `REPORT_MINUTE`, `ETF_HOLDINGS_HOUR`, `DATA_REFRESH_HOUR`, `DATA_HEALTH_HOUR`

---

## 個股分析模型 / Stock Analysis Model

系統以加權複合評分計算每支股票的技術訊號，評分範圍 **-2.0 ～ +2.0**，匯總後對應五級評等。

The system computes a weighted composite score from technical signals in the range **-2.0 to +2.0**, mapping to five rating tiers.

### 評分機制 / Scoring Mechanism

| 指標 / Indicator | 訊號 / Signal | 分數 / Score |
|-----------------|---------------|--------------|
| MA 黃金交叉 (MA5>MA20) | 多 / Bull | +2.0 |
| MA 死亡交叉 (MA5<MA20) | 空 / Bear | -2.0 |
| 短期趨勢 (MA5 vs MA10) | 多/空 / Bull/Bear | ±1.0 |
| 中期趨勢 (MA20 vs MA60) | 多/空 / Bull/Bear | ±1.0 |
| 季線位置 (Price vs MA60) | 上方/下方 / Above/Below | ±0.5 |
| 年線位置 (Price vs MA240) | 上方/下方 / Above/Below | ±0.5 |
| RSI 超買 (≥80) | 空 / Bear | -2.0 |
| RSI 超賣 (≤20) | 多 / Bull | +2.0 |
| RSI 背離（5 日視窗）| 頂背離/底背離 / Top/Bottom divergence | ±1.5 |
| KD 黃金交叉 | 多 / Bull | +2.0 |
| KD 死亡交叉 | 空 / Bear | -2.0 |
| OBV 背離（10 日視窗）| 量價背離/量增 / Volume divergence | ±1.5 |
| 成交量比（>2.0 上漲日）| 爆量做多 / Volume surge bull | +1.5 |
| 成交量比（>2.0 下跌日）| 爆量出逃 / Volume surge bear | -1.5 |
| 機構淨買超（三大法人）| 合計 / Total | ±1.0 |
| 機構 3 日持續買超 | 趨勢 / Trend | +1.0 |

**台灣 KD 公式（與國際標準不同）/ Taiwan KD Formula (different from international):**
```
RSV = (Close - Low_14) / (High_14 - Low_14) × 100
K   = (2/3) × prev_K + (1/3) × RSV
D   = (2/3) × prev_D + (1/3) × K
```

**線性回歸預測 / Linear Regression Forecast:**
- 擬合最近 20 / 60 根 K 棒，輸出 5 日 / 20 日預測價格
- 含 95% 信賴區間 [lower, upper] 與 R² 擬合準確度

---

## 主動式 ETF 分析 / Active ETF Analysis

系統追蹤 34 支台灣主動式 ETF，每日從 MoneyDJ 抓取完整持股明細。

The system tracks 34 Taiwan active ETFs with daily holdings scraping from MoneyDJ.

### ETF 分類 / ETF Classification

| 類型 / Type | 代碼範圍 / Code Range | 說明 / Description |
|-------------|----------------------|---------------------|
| A 類（股票型）/ A-type (equity) | 00980A–00999A、00400A–00403A | 主動式股票 ETF / Active equity ETF |
| D 類（債券型）/ D-type (bond) | 00980D–00986D | 主動式債券 ETF / Active bond ETF |

### 持股分析功能 / Holdings Analysis

- **持股明細** — 每支 ETF 前 N 大持股、權重百分比、股數
- **異動偵測** — `compute_holdings_changes()` 比對前後快照，標記：
  - 🟢 新進入 / New position
  - 🔴 已退出 / Exited position
  - ⬆️ 加碼 / Increased weight
  - ⬇️ 減碼 / Decreased weight
- **產業分佈** — 按台灣行業代碼（01–38）分類彙整，含多時間段對比
- **Email 摘要** — 每日晨報中自動附上各 ETF 前 5 大持股及異動標記

---

## 主要 API / Key API Endpoints

| 方法 / Method | 路徑 / Path | 說明 / Description |
|---------------|------------|---------------------|
| GET | `/api/stocks/{symbol}/quote` | 即時報價 / Real-time quote |
| GET | `/api/stocks/{symbol}/kline` | K 線 + 指標 / K-line with indicators |
| GET | `/api/stocks/{symbol}/analysis` | 技術分析評分 / Technical analysis score |
| GET | `/api/stocks/{symbol}/investors` | 三大法人 / 融資融券 |
| GET | `/api/stocks/{symbol}/chip-analysis` | 籌碼集中度 / Chip concentration |
| GET | `/api/etf-holdings` | 全部主動式 ETF 持股 / All active ETF holdings |
| GET | `/api/etf-holdings/{symbol}` | 單支 ETF 持股 / Single ETF holdings |
| GET | `/api/etf-holdings/sector-summary` | 產業分佈彙總 / Sector distribution summary |
| GET | `/api/analysis/daily-report` | 每日分析報告 / Daily analysis report |
| GET | `/api/news` | 產業分類新聞 / Categorized news |
| GET | `/api/trump-news` | Trump 相關新聞 / Trump-related news |
| GET | `/api/market/overview` | 大盤指數 / Market indices |
| GET | `/api/watchlist` | 觀察清單 / Watchlist |
| POST | `/api/analysis/generate` | 觸發分析（需 Auth）/ Trigger analysis (auth required) |
| POST | `/api/data/refresh-all` | 全量資料更新（需 Auth）/ Refresh all data (auth required) |

> POST / DELETE 端點需標頭 `X-API-Secret: <secret>`。
> POST / DELETE endpoints require `X-API-Secret: <secret>` header.

---

## 雲端部署 / Deployment

### 架構 / Architecture

```
GitHub Pages  ──→  frontend (React SPA)
     ↕  API calls
Railway        ──→  backend (FastAPI)
                    ├─ APScheduler（排程分析 / scheduled analysis）
                    ├─ Email（Resend API）
                    └─ Cache（JSON files in /data）
```

### Railway 後端部署 / Railway Backend

```bash
# Railway 自動從 Procfile 或 railway.toml 啟動
uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Railway 環境變數 / Environment Variables:**

```
OPENAI_API_KEY        = sk-proj-...
RESEND_API_KEY        = re_...
REPORT_RECIPIENT      = your@email.com
API_SECRET_REPORT     = your-report-secret
API_SECRET_STOCK      = your-stock-secret
REPORT_HOUR           = 7
REPORT_MINUTE         = 0
```

### GitHub Pages 前端部署 / GitHub Pages Frontend

GitHub Actions 自動建置並部署。設定 Repository Secret：

GitHub Actions auto-builds and deploys. Set Repository Secrets:

```
VITE_API_BASE    = https://stock-monitor-production-b630.up.railway.app
VITE_API_SECRET  = your-stock-secret
```

---

## 授權聲明 / License Notice

本系統核心代碼受自訂授權條款（Source Available License v2.0）保護。

This software is protected under a custom Source Available License v2.0.

- 任何使用、下載、部署、衍生開發，均須明確標示作者：**Ping yu-Chen, Taiwan**
- Any use, download, deployment, or derivative work must clearly credit: **Ping yu-Chen, Taiwan**
- 商業使用須事先取得書面授權 / Commercial use requires prior written authorization
- 商業授權洽詢 / Commercial licensing: **chenbill718@gmail.com**

詳見 [LICENSE](./LICENSE) / See [LICENSE](./LICENSE) for full terms.
