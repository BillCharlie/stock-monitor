# 股市監控系統 — 完整使用說明書(请必须阅读License）

> 版本 2.0 · 最後更新 2026-05-10

---

## 目錄

1. [系統概覽](#1-系統概覽)
2. [架構說明](#2-架構說明)
3. [功能清單](#3-功能清單)
4. [快速開始](#4-快速開始)
5. [環境設定](#5-環境設定)
6. [本地部署](#6-本地部署)
7. [觀察清單結構](#7-觀察清單結構)
8. [前端介面說明](#8-前端介面說明)
9. [技術分析指標](#9-技術分析指標)
10. [每日報告系統](#10-每日報告系統)
11. [郵件推送設定](#11-郵件推送設定)
12. [API 文件](#12-api-文件)
13. [安全機制](#13-安全機制)
14. [GitHub Pages 部署](#14-github-pages-部署)
15. [PIggycat 整合](#15-piggycat-整合)
16. [定時任務說明](#16-定時任務說明)
17. [常見問題](#17-常見問題)

---

## 1. 系統概覽

股市監控系統是一個**全棧個人投資研究工具**，同時追蹤台灣與美國股市，提供：

- 即時報價與技術指標 K 線圖
- 規則引擎量化技術分析（評分 + 評級）
- GPT-4o 每日智慧投資報告（抓取 Google News + 分析技術指標）
- PDF 報告本地儲存
- Gmail 自動推送（含 PDF 附件）
- 支援 GitHub Pages 公開網頁存取（後端運行於本機）

### 技術棧

| 層次 | 技術 |
|------|------|
| 後端 API | Python 3.13 + FastAPI + APScheduler |
| 行情數據 | yfinance（Yahoo Finance） |
| AI 分析 | OpenAI GPT-4o |
| 新聞來源 | Google News RSS |
| PDF 生成 | fpdf2 + Microsoft JhengHei 字型 |
| 郵件發送 | Gmail SMTP App Password |
| 前端框架 | React 18 + Vite + Tailwind CSS |
| K 線圖表 | lightweight-charts |
| 前端託管 | GitHub Pages（靜態）|
| 穿透代理 | Cloudflare Tunnel（cloudflared） |
| 啟動管理 | PIggycat 多代理管理器 |

---

## 2. 架構說明

```
┌─────────────────────────────────────────────────────────┐
│                     使用者瀏覽器                          │
│  GitHub Pages (靜態 React App)                           │
│  https://billcharlie.github.io/stock-monitor/            │
└────────────────────────┬────────────────────────────────┘
                         │  HTTPS API 請求
                         ▼
┌─────────────────────────────────────────────────────────┐
│         Cloudflare Tunnel（摸鱼神遊模式）                 │
│  https://xxxx.trycloudflare.com  →  localhost:8765       │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│            FastAPI 後端  http://127.0.0.1:8765            │
│                                                          │
│  /api/*      ─── REST API 端點                           │
│  /           ─── 靜態資源（本地使用時）                   │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ analysis │  │  stock   │  │   gpt    │              │
│  │  .py     │  │ _data.py │  │_analysis │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │indicators│  │  email   │  │   pdf    │              │
│  │  .py     │  │_sender.py│  │_generator│              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                          │
│  APScheduler 定時任務                                    │
│  ├── 週一至五 13:40  台股收盤分析                         │
│  ├── 週二至六 05:10  美股收盤分析                         │
│  └── 週一至五 07:00  晨報生成 + PDF + Email               │
└─────────────────────────────────────────────────────────┘
```

### 單埠設計

後端與前端**共用埠 8765**。FastAPI 優先處理 `/api/*` 請求，其餘路徑由 React 靜態資源接管。部署到 GitHub Pages 時，靜態前端由 CDN 提供，前端透過 Cloudflare Tunnel URL 呼叫後端 API。

---

## 3. 功能清單

### 前端功能

| 功能 | 說明 |
|------|------|
| 市場概覽頂部欄 | 台灣加權、S&P 500、那斯達克、道瓊、費城半導體、黃金期貨、銅期貨 即時報價 |
| 觀察清單側欄 | 四層分類樹（地區 > 產業 > 細分類 > 個股），即時顯示漲跌幅 |
| K 線圖 | 日K / 週K / 月K 切換，疊加 MA5/10/20/60/120/240、布林通道、RSI、KD |
| 個股分析 | 量化評分 + 評級 + 技術信號清單 + 線性迴歸預測 |
| 每日報告 | 展示 GPT-4o 生成的 HTML 報告，含買入/賣出候選、板塊情緒 |
| 下載 PDF | 下載最新報告的 PDF 版本 |
| 存取密鑰管理 | 前端輸入報告密鑰 / 股票管理密鑰，加密儲存於 localStorage |
| 自訂觀察清單 | 新增 / 刪除個人自選股 |

### 後端功能

| 功能 | 說明 |
|------|------|
| 行情快取 | yfinance 抓取 OHLCV，快取避免重複請求 |
| 技術指標計算 | MA、布林通道、RSI(14)、KD(9,3,3)、OBV |
| 量化分析引擎 | 各指標評分 [-2, 2]，加權合計決定評級 |
| 線性迴歸預測 | OLS 20 日線性迴歸，預測未來 5 日走勢 + 置信區間 |
| 新聞抓取 | Google News RSS 8 個板塊查詢 |
| GPT-4o 報告 | 匯整技術分析 + 新聞 → GPT-4o 生成完整 HTML 報告 |
| PDF 生成 | fpdf2 生成含中文的 PDF，儲存至 `backend/reports/` |
| 郵件推送 | Gmail SMTP 發送 HTML + PDF 附件至多個收件人 |
| Write 端點保護 | SHA-256 驗證 `X-API-Secret` 標頭 |

---

## 4. 快速開始

### 前置需求

- Python 3.11 或以上（已測試 3.13）
- Node.js 18 或以上
- Gmail 帳號（需開啟兩步驟驗證並建立 App Password）
- OpenAI API Key（GPT-4o 存取權限）

### 最快啟動方式（透過 PIggycat）

1. 開啟 PIggycat → Stock 貓咪顯示在畫面上
2. PIggycat 啟動時會**自動啟動** Stock（`autostart: true`）
3. 若要開啟 Cloudflare 穿透，點選 Stock 貓咪 → **摸鱼神遊**

### 手動啟動

```powershell
cd E:\vscode\stock-monitor\backend
# 啟動後端
.\venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8765

# 或使用啟動腳本（也會建置前端）
cd E:\vscode\piggycat
python scripts\launch_stock_monitor.py

# 摸鱼神遊（同時開啟 Cloudflare Tunnel）
python scripts\launch_stock_monitor.py --tunnel
```

---

## 5. 環境設定

所有機密資訊存放於 `backend/.env`（**不進入版本控制**）：

```ini
# ── OpenAI ──────────────────────────────────────────────
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx

# ── Gmail 寄件設定 ──────────────────────────────────────
GMAIL_SENDER=your.email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   # 16位應用程式密碼，非登入密碼

# ── 收件人（支援最多 3 位）────────────────────────────────
REPORT_RECIPIENT=recipient1@example.com
REPORT_RECIPIENT_2=recipient2@example.com
# REPORT_RECIPIENT_3=recipient3@example.com

# ── 晨報時間（台灣時間，預設 07:00）──────────────────────
REPORT_HOUR=7
REPORT_MINUTE=0

# ── Write 端點保護密鑰 ─────────────────────────────────
API_SECRET_REPORT=你的報告密鑰
API_SECRET_STOCK=你的股票管理密鑰
```

### 取得 Gmail App Password

1. 登入 Google 帳戶 → **安全性**
2. 確認已啟用「兩步驟驗證」
3. 搜尋「應用程式密碼」→ 選擇「郵件」→「Windows 電腦」
4. 複製產生的 16 位密碼（格式：`xxxx xxxx xxxx xxxx`）

---

## 6. 本地部署

### Step 1 — 建立 Python 虛擬環境

```powershell
cd E:\vscode\stock-monitor\backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` 需包含：
```
fastapi
uvicorn[standard]
apscheduler
yfinance
pandas
numpy
openai
requests
python-dotenv
fpdf2
```

### Step 2 — 建置前端

```powershell
cd E:\vscode\stock-monitor\frontend
npm install
npm run build          # 輸出到 backend/static/
```

### Step 3 — 設定 .env

複製 `backend/.env.example` 為 `backend/.env` 並填入真實金鑰。

### Step 4 — 啟動服務

```powershell
cd E:\vscode\stock-monitor\backend
.\venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8765
```

瀏覽器開啟 [http://localhost:8765](http://localhost:8765)

---

## 7. 觀察清單結構

觀察清單定義於 `backend/watchlist.py`，採用**四層樹狀分類**：

```
地區（台灣 / 美國）
└── 產業（半導體 / 資源）
    └── 細分類（CPU/GPU產業 / 記憶體產業 / 功率半導體 / 材料 / 磊晶 / ETF）
        └── 四級分類（IC設計 / IC代工 / 封裝測試 / 系統模組PCB產業）
            └── 個股 { symbol, name, name_en }
```

### 台灣板塊總覽

#### 半導體

| 分類 | 代表個股 |
|------|---------|
| IC設計 | 聯發科(2454)、聯詠(3034)、瑞昱(2379)、創意電子(3443) |
| IC代工 | 台積電(2330)、聯電(2303)、世界先進(5347) |
| 封裝測試 | 日月光(2311)、力成(6239)、京元電(2449) |
| 系統模組PCB | 南亞科技(2408)、華邦電子(2344)、旺宏(2337)、新唐(4919) |
| DRAM | 南亞科技(2408) |
| NOR Flash | 旺宏(2337)、華邦(2344) |
| NAND控制 | 群聯(8299)、慧榮(6286) |
| SiC | 漢磊(3707)、朋程(8255)、強茂(2481) |
| GaN | 穩懋(3105)、宏捷科(8086) |
| Si晶圓 | 環球晶(6488)、合晶(6182) |
| 材料 | 永光化學(1711)、長興材料(1717) |
| 黃金ETF | 元大黃金(00635U) |

#### 美國板塊總覽

| 分類 | 代表個股 |
|------|---------|
| IC設計 | NVDA、AMD、QCOM、AVGO、MRVL |
| IC代工 | TSM、GFS、INTC、UMC |
| DRAM | MU（美光） |
| NAND/SSD | WDC、STX |
| SiC | WOLF、ON、STM、TXN |
| GaN | NVTS、POWI |
| 稀土 | MP、REMX ETF |
| 黃金 | GLD ETF、GDX ETF、NEM、GOLD |
| 銅礦 | FCX、SCCO、COPX ETF |
| 鐵礦鋼鐵 | NUE、VALE、RIO、BHP |
| 半導體ETF | SMH、SOXX、SOXL、PSI |

### 市場大盤指數

頂部欄顯示的即時指數：

| 代號 | 名稱 |
|------|------|
| ^TWII | 台灣加權指數 |
| ^GSPC | S&P 500 |
| ^IXIC | 那斯達克綜合 |
| ^DJI | 道瓊工業 |
| ^SOX | 費城半導體 |
| GC=F | 黃金期貨 |
| HG=F | 銅期貨 |

### 自訂觀察清單

在前端可新增個人自選股，儲存於 `backend/custom_stocks.json`，需要**股票管理密鑰**。

---

## 8. 前端介面說明

### 整體佈局

```
┌─────────────────────────── 市場概覽頂部欄 ──────────────────────────────┐
│ 台灣加權  S&P500  那斯達克  道瓊  費城半導體  黃金期貨  銅期貨           │
└──────────────────────────────────────────────────────────────────────────┘
┌─────────────┬────────────────────────────────────────────────────────────┐
│             │ [K線圖] [個股分析] [每日報告]   [生成每日報告] [下載PDF] 🔑  │
│  觀察清單   ├────────────────────────────────────────────────────────────┤
│  側欄       │                                                            │
│             │          主內容區（K線 / 分析 / 報告）                     │
│  台灣       │                                                            │
│  └ 半導體   │                                                            │
│    └ CPU/GPU│                                                            │
│      └ IC設計                                                           │
│        └ 台積電                                                          │
│   ...       │                                                            │
└─────────────┴────────────────────────────────────────────────────────────┘
```

### 標籤頁說明

#### K 線圖
- **日K / 週K / 月K** 切換按鈕
- 主圖：蠟燭圖 + MA5/10/20/60/120/240（彩色線）+ 布林通道
- 下方子圖一：RSI(14)，超買線 70 / 超賣線 30
- 下方子圖二：KD 指標，K 線（藍）+ D 線（橙）
- 成交量：柱狀圖（漲紅 / 跌綠）

#### 個股分析
- **量化評分** 與 **評級**（強力買進 ▲▲ / 買進 ▲ / 持有 ─ / 賣出 ▼ / 強力賣出 ▼▼）
- **技術信號** 清單（多頭/空頭/中性信號逐條列出）
- **線性迴歸預測**（未來 5 日預測價、漲跌幅、R² 係數）
- **指標數值表格**（MA5~240、RSI、K、D、布林三軌）

#### 每日報告
- 顯示 GPT-4o 生成的 HTML 報告
- 包含：市場情緒判斷、買入候選 TOP 5、風險警示、板塊輪動、新聞摘要

### 密鑰設定

點選右上角 🔒（未設定）或 🔑（已設定）按鈕開啟密鑰面板：

| 密鑰 | 用途 |
|------|------|
| 報告生成密鑰 | 手動觸發「生成每日報告」按鈕 |
| 股票管理密鑰 | 新增 / 刪除自訂觀察清單股票 |

密鑰**僅儲存於瀏覽器本地**（`localStorage`），透過 XOR+Base64 混淆保存，傳輸時只傳送 SHA-256 雜湊值，明文永遠不離開瀏覽器。

---

## 9. 技術分析指標

### 計算方式

| 指標 | 參數 | 說明 |
|------|------|------|
| MA | 5/10/20/60/120/240 日 | 簡單移動平均 |
| 布林通道 | 20 日均線 ± 2σ | 上軌/中軌/下軌 |
| RSI | 14 日 | 相對強弱指標，70 超買 / 30 超賣 |
| KD | K=9, D=3, Smooth=3 | 隨機指標，80 超買 / 20 超賣 |
| OBV | — | 能量潮（用於判斷成交量趨勢） |

### 評分邏輯

各指標依技術條件評分 **[-2, +2]**，加權合計後轉換為評級：

| 評分區間 | 評級 |
|---------|------|
| ≥ 2.5 | 強力買進 ▲▲ |
| 1.0 ~ 2.4 | 買進 ▲ |
| -1.0 ~ 0.9 | 持有 ─ |
| -2.5 ~ -1.1 | 賣出 ▼ |
| < -2.5 | 強力賣出 ▼▼ |

### 線性迴歸預測

使用最近 20 根 K 線的收盤價進行 **OLS 線性迴歸**，預測未來 5 日：

- 預測價格與漲跌幅
- 95% 置信區間（±1.96σ）
- R² 判定係數
- 每日斜率（趨勢強度）

---

## 10. 每日報告系統

### 自動觸發流程（每日）

```
13:40（台股收盤）─── 分析台股
05:10（美股收盤）─── 分析美股
07:00（台灣時間）─── GPT報告 → 生成PDF → 發送Email
```

### 手動觸發

在前端點擊「**生成每日報告**」按鈕（需報告密鑰），或呼叫 API：

```bash
curl -X POST http://localhost:8765/api/analysis/gpt-report \
  -H "X-API-Secret: <SHA256(密鑰)>"
```

### GPT 報告內容

GPT-4o 分析時會收到：
1. 所有觀察清單個股的量化技術分析結果
2. 市場情緒評估（多頭/空頭/中性）
3. 8 個板塊的 Google News 最新頭條

報告輸出包含：
- 市場整體情緒判斷
- 本日重點新聞摘要（中英文）
- 買入候選 TOP 5（附分析理由）
- 風險警示（弱勢股）
- 板塊輪動分析
- 操作建議

### PDF 報告

- 儲存至 `backend/reports/daily_report_YYYY-MM-DD.pdf`
- 使用 Microsoft JhengHei（微軟正黑體）字型，正確顯示中文
- 可從前端點擊「下載PDF」或呼叫 `GET /api/analysis/download-report`

---

## 11. 郵件推送設定

### 收件人設定

在 `.env` 中設定最多 3 位收件人：

```ini
REPORT_RECIPIENT=主要收件人@example.com
REPORT_RECIPIENT_2=第二收件人@example.com
REPORT_RECIPIENT_3=第三收件人@example.com
```

### 郵件格式

- 主旨：`📊 每日投資分析報告 — YYYY-MM-DD`
- 正文：GPT-4o 生成的 HTML 報告（富文字格式）
- 附件：當日 PDF 報告

### 備援機制

若 GPT-4o 不可用（API 金鑰無效、網路問題），系統自動降級為**規則引擎備援報告**，仍會正常發送郵件。

---

## 12. API 文件

基礎 URL：`http://localhost:8765/api`

### 行情資料

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/stocks/{symbol}/kline` | K 線資料 + 技術指標 |
| GET | `/stocks/{symbol}/quote` | 即時報價 |
| GET | `/stocks/{symbol}/analysis` | 技術分析結果 |
| GET | `/market/overview` | 大盤指數 |

**K 線查詢參數：**

| 參數 | 預設值 | 說明 |
|------|------|------|
| `interval` | `1d` | 週期：`1d` / `1wk` / `1mo` |
| `refresh` | `false` | 強制重新抓取行情 |

### 報告管理（需報告密鑰）

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/analysis/daily-report` | 取得最新量化報告 |
| POST | `/analysis/generate` | 觸發量化分析 |
| POST | `/analysis/gpt-report` | 觸發 GPT 報告 + PDF + Email |
| GET | `/analysis/gpt-report` | 取得已生成的 GPT 報告 HTML |
| GET | `/analysis/download-report` | 下載最新 PDF |

### 自訂觀察清單（需股票管理密鑰）

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/custom-stocks` | 列出自選股 |
| POST | `/custom-stocks` | 新增自選股 `{symbol, name}` |
| DELETE | `/custom-stocks/{symbol}` | 刪除自選股 |

### 系統

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/health` | 健康狀態 + 已分析股票數 |
| GET | `/watchlist` | 完整觀察清單（含自訂） |

---

## 13. 安全機制

### Write 端點保護

所有 POST / DELETE 端點需要在 Header 傳送密鑰雜湊：

```
X-API-Secret: <SHA-256(原始密鑰)>
```

後端驗證流程：
1. 從 `.env` 讀取 `API_SECRET_REPORT` 或 `API_SECRET_STOCK`
2. 與傳入的 SHA-256 雜湊比對
3. 不符合則回傳 `401 Unauthorized`

若 `.env` 中密鑰為空，對應端點**不做驗證**（僅限本機使用時）。

### 前端密鑰保護

前端密鑰的儲存與傳輸採雙層保護：

```
儲存層（localStorage）：XOR 混淆 + Base64 編碼
傳輸層（HTTP Header）：SHA-256 雜湊（明文永不離開瀏覽器）
```

XOR 混淆原理（`crypto.js`）：
1. 使用固定種子 `sm-v1-xk-2026` 對每個字元進行 XOR
2. 結果 Base64 編碼後存入 `localStorage`
3. 讀取時先 Base64 解碼再 XOR 還原

傳輸時通過 Web Crypto API 計算 SHA-256：
```javascript
const hash = await crypto.subtle.digest('SHA-256', encoder.encode(plaintext))
// 只傳送 hash，從不傳送 plaintext
```

---

## 14. GitHub Pages 部署

### 前置設定

1. 在 GitHub repo **Settings → Secrets and variables → Actions** 新增：

   | 類型 | 名稱 | 值 | 說明 |
   |------|------|-----|------|
   | Secret | `VITE_API_BASE_URL` | `https://xxxx.trycloudflare.com` | 後端公網 URL |
   | Variable | `VITE_BASE_PATH` | `/stock-monitor/` | 若 repo 名稱非 stock-monitor 則修改 |

2. 在 GitHub repo **Settings → Pages** → Source 選擇 `GitHub Actions`

### 自動部署流程

推送到 `main` 分支時，GitHub Actions 自動執行：

```yaml
1. Checkout 代碼
2. 安裝 Node.js 20
3. npm ci（安裝前端相依）
4. npm run build（GITHUB_PAGES=true，輸出到 frontend/dist）
5. 上傳 artifact
6. 部署到 GitHub Pages
```

### 本地測試 GitHub Pages 建置

```powershell
cd E:\vscode\stock-monitor\frontend
$env:GITHUB_PAGES = 'true'
$env:VITE_API_BASE_URL = 'https://your-tunnel.trycloudflare.com'
npm run build
# 輸出在 frontend/dist/
```

### Vite 雙模式建置

`vite.config.js` 根據環境變數決定建置模式：

| 模式 | `GITHUB_PAGES` | `base` | `outDir` |
|------|---------------|--------|---------|
| 本地（後端靜態） | 未設置 | `/` | `../backend/static` |
| GitHub Pages | `true` | `/stock-monitor/` | `dist` |

---

## 15. PIggycat 整合

### 代理設定（`data/agents.json`）

```json
{
  "id": "stock-monitor",
  "name": "Stock",
  "description": "台灣/美國股市監控系統",
  "command": "python scripts/launch_stock_monitor.py",
  "cwd": ".",
  "color": "#26A69A",
  "emoji": "📈",
  "dashboard_url": "http://127.0.0.1:8765",
  "autostart": true
}
```

### 啟動模式

在 PIggycat 中點選 Stock 貓咪可看到三個按鈕：

| 按鈕 | 模式 | 說明 |
|------|------|------|
| 工作 | work | 正常啟動，只服務本地 |
| 摸鱼神遊 | tunnel | 啟動後端 + Cloudflare Tunnel，GitHub Pages 可連線 |
| 睡覺 | sleep | 停止所有進程 |

### 開機自動啟動

由於 `"autostart": true`，每次 PIggycat 啟動時，Stock 代理自動以「工作」模式啟動。

### 啟動腳本（`scripts/launch_stock_monitor.py`）

啟動腳本負責：
1. 偵測前端靜態資源是否存在，不存在則自動建置
2. 使用虛擬環境 Python 啟動 uvicorn
3. 等待 8765 埠就緒（最多 15 秒）
4. 若傳入 `--tunnel` 參數，額外啟動 cloudflared.exe
5. 監控子進程，任一退出時關閉所有子進程

### Cloudflare Tunnel（摸鱼神遊）

```
backend/cloudflared.exe 必須放置在 backend/ 目錄下
下載：https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
```

啟動後，Tunnel 公網 URL 會出現在 PIggycat 的 Log 面板中，格式為：
```
https://xxxx-xxxx-xxxx.trycloudflare.com
```

將此 URL 更新到 GitHub repo 的 `VITE_API_BASE_URL` Secret，再觸發一次 Actions 重新部署前端即可。

---

## 16. 定時任務說明

定時任務由 `APScheduler`（`BackgroundScheduler`，時區 `Asia/Taipei`）管理：

| 任務 | Cron 表達式 | 說明 |
|------|------------|------|
| 台股分析 | 週一至五 13:40 | 抓取台股收盤後行情並重新計算指標 |
| 美股分析 | 週二至六 05:10 | 抓取美股收盤後行情（台灣時間） |
| 晨報任務 | 週一至五 07:00 | 分析 → GPT 報告 → PDF → Email |

晨報時間可通過環境變數自訂：

```ini
REPORT_HOUR=7
REPORT_MINUTE=0
```

---

## 17. 常見問題

### Q: 為什麼前端顯示「請先設定報告生成密鑰」？

前端密鑰未設定。點右上角 🔒 按鈕開啟密鑰面板，輸入分發給你的報告密鑰（與後端 `.env` 中 `API_SECRET_REPORT` 相同的明文值）。

### Q: 為什麼 PDF 中的中文顯示為方塊？

PDF 生成使用 `C:\Windows\Fonts\msjh.ttc`（微軟正黑體）。確認該字型檔案存在。若作業系統非繁體中文版，可能需要手動安裝字型。

### Q: GitHub Pages 顯示空白頁或 404？

1. 確認 GitHub Pages 的 Source 設為 `GitHub Actions`
2. 確認 `VITE_BASE_PATH` 與 repo 名稱匹配（預設 `/stock-monitor/`）
3. 確認最新一次 Actions 建置成功

### Q: API 呼叫失敗，顯示 CORS 錯誤？

後端已設定 `allow_origins=["*"]`，理論上不應出現 CORS 問題。若發生，確認前端 `VITE_API_BASE_URL` 設定了正確的後端 URL（包含協議和埠）。

### Q: 行情資料更新太慢？

K 線資料有快取，可在前端 K 線圖頁面加 `?refresh=true` 參數強制重新抓取，或在 API 呼叫時設定 `refresh=true`。

### Q: cloudflared.exe 啟動後找不到 Tunnel URL？

Tunnel URL 會輸出到 PIggycat Log 面板。向上捲動 Log 找到包含 `.trycloudflare.com` 的行。每次重新啟動 Tunnel URL 都會變更，需要重新更新 GitHub Secret。

### Q: 如何新增觀察清單股票？

**永久新增**（修改 `watchlist.py`）：直接編輯 `backend/watchlist.py`，在適當分類下新增 `{"symbol": "代號", "name": "名稱", "name_en": "English Name"}`。

**臨時新增**（自訂觀察清單）：在前端觀察清單底部找到自訂區塊，點擊 + 按鈕，輸入股票代號和名稱（需股票管理密鑰）。

### Q: 如何修改每日報告發送時間？

修改 `.env` 中的 `REPORT_HOUR` 和 `REPORT_MINUTE`，重啟服務生效。

---

## 附錄：檔案結構

```
stock-monitor/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions 自動部署
├── backend/
│   ├── main.py                 # FastAPI 應用入口、路由、排程器
│   ├── analysis.py             # 量化技術分析引擎
│   ├── gpt_analysis.py         # GPT-4o 報告生成（含新聞抓取）
│   ├── email_sender.py         # Gmail SMTP 郵件發送
│   ├── pdf_generator.py        # fpdf2 PDF 生成
│   ├── indicators.py           # 技術指標計算（MA/BB/RSI/KD/OBV）
│   ├── stock_data.py           # yfinance 行情抓取與快取
│   ├── watchlist.py            # 觀察清單定義（台灣 + 美國）
│   ├── custom_stocks.json      # 使用者自訂觀察清單（自動生成）
│   ├── reports/                # 每日 PDF 報告儲存目錄
│   ├── static/                 # React 建置輸出（本地模式）
│   ├── cloudflared.exe         # Cloudflare Tunnel 執行檔
│   ├── .env                    # 機密設定（不進版控）
│   └── .env.example            # 設定範本
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # 主應用元件、Tab 切換、報告觸發
│   │   ├── api/
│   │   │   ├── stocks.js       # API 呼叫封裝、密鑰管理
│   │   │   └── crypto.js       # XOR 混淆 + SHA-256 雜湊
│   │   └── components/
│   │       ├── MarketOverview.jsx   # 頂部大盤指數欄
│   │       ├── WatchlistPanel.jsx   # 左側觀察清單樹
│   │       ├── StockChart.jsx       # K 線圖（lightweight-charts）
│   │       ├── AnalysisPanel.jsx    # 個股分析 + 每日報告
│   │       └── AccessKeyPanel.jsx   # 密鑰設定 Modal
│   ├── vite.config.js          # Vite 雙模式建置設定
│   └── package.json
├── .gitignore                  # 排除 .env, venv, reports, static, node_modules
└── docs/
    ├── README.md               # 本說明書（Markdown）
    └── README.html             # 本說明書（靜態 HTML）
```

---

*本系統由 Bill Chen 建構，使用 Claude Code 輔助開發。*
