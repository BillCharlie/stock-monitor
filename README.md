# Stock Monitor — 台灣 / 中國 / 美股即時監控、技術分析與主動式 ETF 系統

> Author: Ping yu-Chen, Taiwan
> Repository: https://github.com/BillCharlie/stock-monitor
> Live frontend: https://billcharlie.github.io/stock-monitor/
> Backend API: https://stock-monitor-production-b630.up.railway.app
> License: Source-available proprietary license. Commercial use, redistribution, hosted operation, and derivative commercial use require prior written permission. See [LICENSE](./LICENSE).

Stock Monitor 是一套以 FastAPI + React 建構的股票監控與分析系統，涵蓋台灣股市、中國股市與美股。系統會自動抓取行情、K 線、技術指標、三大法人、融資融券、ETF 持股、新聞與政策資訊，並生成每日分析報告與 Email / PDF 版本。

此專案不是投資建議。所有分數、評等、預測與新聞摘要僅供研究、觀察與系統開發參考。

---

## 目錄

- [最新功能摘要](#最新功能摘要)
- [系統架構](#系統架構)
- [市場與觀察清單](#市場與觀察清單)
- [技術分析模型](#技術分析模型)
- [每日報告與中國股市板塊](#每日報告與中國股市板塊)
- [主動式 ETF 分析](#主動式-etf-分析)
- [資產管理與隔日策略](#資產管理與隔日策略)
- [新聞與政策監控](#新聞與政策監控)
- [安裝與本機啟動](#安裝與本機啟動)
- [環境變數](#環境變數)
- [API 端點](#api-端點)
- [排程任務](#排程任務)
- [部署](#部署)
- [授權與保護](#授權與保護)

---

## 最新功能摘要

目前版本的重點能力：

- 台灣 / 中國 / 美國三市場觀察清單，合計約 295 個標的。
- 中國股市已獨立成為一級市場分類，並在日報中有單獨板塊。
- 中國股市目前涵蓋新能源汽車、半導體、光通訊等分類，例如：
  - 比亞迪 `002594.SZ`
  - 賽力斯 `601127.SS`
  - 芯聯集成 `688469.SS`
  - 士蘭微 `600460.SS`
  - 華潤微 `688396.SS`
  - 斯達半導 `603290.SS`
  - 揚杰科技 `300373.SZ`
  - 英諾賽科 `02577.HK`
  - 三安光電 `600703.SS`
  - 立昂微 `605358.SS`
  - 卓勝微 `300782.SZ`
  - 長電科技 `600584.SS`
  - 長飛光纖 `601869.SS`
- 對中國 A 股 / 港股使用與台股、美股同一套技術分析流程：K 線、MA、RSI、KD、Bollinger Bands、OBV、量能、支撐壓力、線性回歸預測與評等。
- 每日報告輸出 `market_sections`，前端與 Email fallback 都能顯示「中國股市」獨立區塊。
- 台灣顏色慣例：紅色代表上漲 / 買進 / 偏多，綠色代表下跌 / 賣出 / 偏空。
- 主動式 ETF 持股追蹤目前涵蓋 30 支台灣主動式 ETF。
- 支援資產管理、多人持倉、隔日策略、技術訊號與跳空/關卡分析。
- 寫入型 API 使用雙密鑰保護：報告管理密鑰與股票管理密鑰分離。

---

## 系統架構

```text
GitHub Pages
└─ React SPA frontend
   ├─ 市場總覽
   ├─ 觀察清單
   ├─ 技術分析
   ├─ 主動式 ETF
   ├─ 資產管理
   ├─ 新聞 / TrumpNews
   └─ Access key panel

Railway / Local FastAPI backend
├─ /api/* REST API
├─ APScheduler 排程任務
├─ yfinance / TWSE / TPEX / FinMind / MoneyDJ / news sources
├─ GPT 報告生成
├─ PDF 報告生成
├─ Email 寄送
└─ JSON cache / user data files
```

後端以單一 FastAPI 服務同時提供 API 與已建置的 React 靜態檔。正式部署時，前端通常由 GitHub Pages 服務，後端由 Railway 服務；本機開發時也可以直接由 FastAPI 掛載 `backend/static`。

---

## 市場與觀察清單

觀察清單在 [backend/watchlist.py](./backend/watchlist.py) 中維護，採用遞迴階層：

```text
市場 / 地區
└─ 產業
   └─ 細分類
      └─ 股票列表
```

每個股票節點格式：

```json
{
  "symbol": "688469.SS",
  "name": "芯聯集成",
  "name_en": "United Nova Technology Co., Ltd.",
  "tags": ["A股", "特色工藝晶圓代工", "功率半導體/MEMS"]
}
```

目前內建三個主要市場：

| 市場 | 目前範圍 | 說明 |
|---|---:|---|
| 台灣 | 約 211 檔 | 半導體、AI、金融、生技、鋼鐵、航運、資源、主動式 ETF 等 |
| 中國股市 | 約 13 檔 | 新能源汽車、功率半導體、晶圓代工、封測、光通訊等 |
| 美國 | 約 71 檔 | 半導體、AI GPU、資源、黃金、銅礦、稀土、ETF 等 |

前端支援內建觀察清單與使用者自訂觀察清單。使用者自訂清單由 `/api/user-watchlist` 儲存，最多支援 5 層分類。

---

## 技術分析模型

每個標的會透過 `analyze_stock()` 執行同一套規則式技術分析。支援台股、中國 A 股 / 港股、美股與 ETF，只要資料來源能回傳足夠 OHLCV K 線即可。

### 評分與評等

模型會把多個訊號加總成分數，再轉成五級評等：

| 評等 key | 顯示名稱 | 條件 |
|---|---|---:|
| `strong_buy` | 強力買進 ▲▲ | score ≥ 2.5 |
| `buy` | 買進 ▲ | score ≥ 1.0 |
| `hold` | 持有 ─ | -1.0 ≤ score < 1.0 |
| `sell` | 賣出 ▼ | -2.5 ≤ score < -1.0 |
| `strong_sell` | 強力賣出 ▼▼ | score < -2.5 |

### 核心訊號

| 模組 | 訊號 | 分數方向 |
|---|---|---|
| MA 短期趨勢 | MA5 > MA10 / MA5 < MA10 | ±1.0 |
| MA 中期趨勢 | MA20 > MA60 / MA20 < MA60 | ±1.0 |
| MA5/MA20 交叉 | 黃金交叉 / 死亡交叉 | ±2.0 |
| 季線位置 | 價格在 MA60 上 / 下 | ±0.5 |
| 年線位置 | 價格在 MA240 上 / 下 | ±0.5 |
| RSI | 超買、超賣、偏多、偏空 | -2.0 到 +2.0 |
| RSI 背離 | 頂背離 / 底背離 | ±1.5 |
| KD | 黃金交叉、死亡交叉、超買超賣 | ±0.5 到 ±2.0 |
| Bollinger Bands | 突破、貼近上下軌、通道收斂 | -0.5 到 +1.0 |
| Volume | 爆量上漲 / 爆量下跌 | ±1.5 |
| OBV | 價量背離、同步上揚 / 下降 | ±0.5 到 ±1.5 |
| 法人 / 機構 | 三大法人、持續買賣、機構持股 | 依市場資料可用性加權 |

### 台灣 KD 公式

```text
RSV = (Close - Low_14) / (High_14 - Low_14) × 100
K   = (2/3) × prev_K + (1/3) × RSV
D   = (2/3) × prev_D + (1/3) × K
```

### 線性回歸預測

模型會對最近 20 / 60 根 K 棒做 OLS 線性回歸，輸出：

- 5 日預測價格
- 20 日預測價格
- 預測漲跌幅
- 95% confidence interval
- R² goodness-of-fit
- 每日斜率

這個預測是技術模型輸出，不代表實際投資建議。

---

## 每日報告與中國股市板塊

每日分析由 `generate_daily_report()` 產生，會先把觀察清單攤平成股票列表、去重，並使用 `ThreadPoolExecutor` 併發分析。

報告核心結構：

```json
{
  "date": "2026-06-29",
  "generated_at": "2026-06-29 07:00:00",
  "market_sentiment": "中性",
  "top_opportunities": [],
  "top_risks": [],
  "sector_summary": {},
  "market_sections": {
    "台灣": {},
    "中國股市": {},
    "美國": {}
  },
  "all_results": {}
}
```

`market_sections["中國股市"]` 會收納比亞迪、芯聯集成等中國市場標的的分析結果，因此前端日報與 Email fallback 都能單獨呈現「中國股市」章節。

GPT 報告會綜合：

- 三市場技術評分
- 台股籌碼與 ETF 資料
- 中國新能源汽車與半導體重點標的
- 美股與半導體 / 資源類股
- 新聞與政策風險
- TrumpNews / White House / X / Truth Social 相關政策訊息

---

## 主動式 ETF 分析

主動式 ETF 模組位於 [backend/etf_holdings.py](./backend/etf_holdings.py)，目前追蹤 30 支台灣主動式 ETF：

- 股票型 A 類：`00980A` 到 `00999A`，以及 `00400A`、`00401A`、`00403A`
- 債券型 D 類：`00980D` 到 `00986D`

主要能力：

- 從 MoneyDJ / 備援來源抓取持股明細。
- 產生每支 ETF 前 N 大持股。
- 比對前後快照，偵測：
  - 新進入
  - 已退出
  - 加碼
  - 減碼
- 彙總跨 ETF 產業分布。
- 建立 1d / 7d / 30d / 91d / 182d / 273d / 365d baseline，觀察產業權重變化。
- 在前端與 Email 報告中呈現 ETF 持股與異動摘要。

顏色規則遵循台灣盤面慣例：

- 紅色：上漲、買進、偏多、新進入、加碼
- 綠色：下跌、賣出、偏空、退出、減碼

---

## 資產管理與隔日策略

資產管理功能透過 `/api/portfolios` 儲存多人持股資料，前端可建立不同人物 / 帳戶的持倉清單。

`/api/portfolio/position-analysis` 會根據持股成本、張數、現價與技術訊號，輸出持倉狀態與隔日策略參考，例如：

- 損益與報酬率
- 目前價格相對成本位置
- 是否接近停利 / 停損 / 壓力 / 支撐
- 隔日可關注價位
- 技術訊號與持倉訊號合併後的行動提示

相關策略文件：

- [docs/position-management-strategy.md](./docs/position-management-strategy.md)
- [docs/next-day-timing-strategy.md](./docs/next-day-timing-strategy.md)

---

## 新聞與政策監控

新聞模組會依照產業分類抓取消息，並在報告中和技術訊號一起使用。

TrumpNews 模組會追蹤：

- Trump / 政策相關新聞
- X / Twitter 來源
- Truth Social 來源
- White House RSS

這些資訊會被納入晨報，特別用於評估關稅、出口管制、半導體政策、能源與地緣政治風險。

---

## 安裝與本機啟動

### 需求

| 項目 | 建議版本 |
|---|---|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |
| OpenAI API key | GPT 報告需要 |
| Resend API key 或 Gmail App Password | Email 寄送需要 |
| FinMind token | 台股三大法人 / 融資融券資料建議設定 |

### 後端

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

或：

```bash
cd backend
uvicorn main:app --reload --port 8765
```

健康檢查：

```text
http://127.0.0.1:8765/api/health
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

目前 `dev` script 使用 `vite build --watch`，會持續建置靜態檔。正式建置：

```bash
cd frontend
npm run build
```

---

## 環境變數

建立 `backend/.env`：

```dotenv
# GPT 報告
OPENAI_API_KEY=sk-proj-...

# Email transport：Resend 或 Gmail 擇一
RESEND_API_KEY=re_...
GMAIL_SENDER=your@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

# Report recipients
REPORT_RECIPIENT=your@email.com
REPORT_RECIPIENT_2=optional@email.com
REPORT_RECIPIENT_3=optional@email.com

# API write protection
API_SECRET_REPORT=your-report-secret
API_SECRET_STOCK=your-stock-secret

# Frontend / GitHub Pages build
VITE_API_BASE=https://stock-monitor-production-b630.up.railway.app
VITE_API_SECRET=your-stock-secret

# Schedule overrides, Asia/Taipei
REPORT_HOUR=7
REPORT_MINUTE=0
ETF_HOLDINGS_HOUR=18
ETF_HOLDINGS_MINUTE=0
DATA_REFRESH_HOUR=18
DATA_REFRESH_MINUTE=0
DATA_HEALTH_HOUR=19
DATA_HEALTH_MINUTE=0

# Optional data / news integrations
FINMIND_TOKEN=...
TRUMP_X_BEARER_TOKEN=...
TRUMP_X_USER_ID=...
TRUMP_X_RSS_URL=...
DATA_DIR=...
REPORT_MAX_WORKERS=8
MARKET_DATA_REFRESH_SLEEP_SECONDS=0.2
```

### API 密鑰規則

寫入型端點需要 `X-API-Secret` header，且前端會送出 SHA-256 後的密鑰值。

後端分成兩組權限：

| 密鑰 | 用途 |
|---|---|
| `API_SECRET_REPORT` | 觸發分析、GPT 報告、全量刷新、健康檢查、測試 Email |
| `API_SECRET_STOCK` | 自訂股票、使用者觀察清單、資產管理 |

GET 端點大多公開讀取；POST / PUT / DELETE 端點需要對應密鑰。

---

## API 端點

### 系統與授權

| Method | Path | 說明 |
|---|---|---|
| GET | `/api/health` | 服務狀態、排程與刷新狀態 |
| POST | `/api/auth/ping` | 驗證 access key 並可發送登入通知 |
| GET | `/api/test/env` | 檢查環境變數是否設定，需 report key |
| GET | `/api/test/quotes` | 批次測試報價 |
| POST | `/api/test/email` | 寄送測試 Email，需 report key |

### 觀察清單與資產

| Method | Path | 說明 |
|---|---|---|
| GET | `/api/watchlist` | 內建 + 使用者觀察清單 |
| GET | `/api/user-watchlist` | 使用者自訂階層 |
| PUT | `/api/user-watchlist` | 儲存使用者自訂階層，需 stock key |
| GET | `/api/custom-stocks` | 自訂股票 |
| POST | `/api/custom-stocks` | 新增自訂股票，需 stock key |
| DELETE | `/api/custom-stocks/{symbol}` | 刪除自訂股票，需 stock key |
| GET | `/api/portfolios` | 多人資產管理資料 |
| PUT | `/api/portfolios` | 儲存多人資產管理資料，需 stock key |
| GET | `/api/portfolio/position-analysis` | 持倉與隔日策略分析 |

### 股票資料與分析

| Method | Path | 說明 |
|---|---|---|
| GET | `/api/stocks/{symbol}/quote` | 即時 / 延遲報價 |
| GET | `/api/stocks/{symbol}/realtime` | 低延遲即時報價 |
| GET | `/api/stocks/{symbol}/kline` | OHLCV + MA / RSI / KD / OBV / Bollinger |
| GET | `/api/stocks/{symbol}/intraday-kline` | 分鐘級 K 線 |
| GET | `/api/stocks/{symbol}/analysis` | 技術分析結果 |
| GET | `/api/stocks/{symbol}/investors` | 三大法人 / 機構資料 |
| GET | `/api/stocks/{symbol}/margin` | 台股融資融券 |
| GET | `/api/stocks/{symbol}/chip-analysis` | 籌碼集中度 |
| GET | `/api/stocks/{symbol}/major-traders` | 主力交易型態 |
| GET | `/api/stocks/{symbol}/institutions` | 可能機構辨識 |
| GET | `/api/market/overview` | 指數與商品期貨概覽 |

### ETF、報告與新聞

| Method | Path | 說明 |
|---|---|---|
| GET | `/api/etf-holdings` | 全部主動式 ETF 持股 |
| GET | `/api/etf-holdings/{symbol}` | 單支主動式 ETF 持股 |
| GET | `/api/etf-holdings/sector-summary` | 主動式 ETF 產業分布 |
| GET | `/api/analysis/daily-report` | 結構化每日報告 |
| POST | `/api/analysis/generate` | 觸發每日分析，需 report key |
| POST | `/api/analysis/gpt-report` | 生成 GPT + PDF + Email 報告，需 report key |
| GET | `/api/analysis/gpt-report` | 取得最新 GPT HTML |
| GET | `/api/analysis/download-report` | 下載最新 PDF |
| POST | `/api/data/refresh-all` | 後台刷新資料，需 report key |
| POST | `/api/health/data-check` | 產生資料健康報告，需 report key |
| GET | `/api/news` | 產業新聞 |
| GET | `/api/trump-news` | Trump / 政策相關新聞 |

---

## 排程任務

所有排程使用 `Asia/Taipei` 時區。

| 時間 | 頻率 | 任務 |
|---|---|---|
| 05:10 | 週二到週六 | 美股收盤後分析 |
| 13:40 | 週一到週五 | 台股收盤後分析 |
| 15:10 | 週一到週五 | 中國 A 股收盤後分析 |
| `REPORT_HOUR:REPORT_MINUTE` | 週一到週五 | 晨報分析、GPT 報告、PDF、Email |
| 每 5 小時 | 持續 | 新聞與 TrumpNews 快取刷新 |
| `ETF_HOLDINGS_HOUR:ETF_HOLDINGS_MINUTE` | 週一到週五 | 主動式 ETF 持股刷新 |
| `DATA_REFRESH_HOUR:DATA_REFRESH_MINUTE` | 每日 | 三大法人、融資融券、ETF、新聞刷新 |
| `DATA_HEALTH_HOUR:DATA_HEALTH_MINUTE` | 每日 | 資料健康報告 |

---

## 部署

### GitHub Pages 前端

`.github/workflows/deploy.yml` 會建置前端並部署到 GitHub Pages。需要設定 repository secrets：

```text
VITE_API_BASE
VITE_API_SECRET
```

### Railway 後端

後端可使用 `backend/Procfile` 啟動：

```text
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Railway 建議設定：

```text
OPENAI_API_KEY
RESEND_API_KEY
REPORT_RECIPIENT
API_SECRET_REPORT
API_SECRET_STOCK
DATA_DIR
REPORT_HOUR
REPORT_MINUTE
```

---

## 授權與保護

本專案採用自訂 Source-Available Proprietary License，重點如下：

- 原始碼可供個人、教育、研究與非商業本機使用。
- 禁止未授權商業使用、SaaS 託管、API 服務、轉售、再授權、商業整合與競品化使用。
- 禁止移除作者、版權、授權與歸屬資訊。
- 衍生作品、展示、研究或引用必須標示作者與來源。
- 核心架構、技術分析模型、ETF pipeline、觀察清單 taxonomy、報告生成流程與資料處理邏輯均明確列為受保護內容。
- 第三方依賴各自受其原授權約束。

完整條款請見 [LICENSE](./LICENSE)。若需商業授權，請聯絡：chenbill718@gmail.com。
