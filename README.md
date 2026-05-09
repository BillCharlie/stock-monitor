# 台灣/美國股市監控系統

## 功能

- **K線圖**：日K / 週K / 月K，含開高低收和成交量
- **均線**：MA5, MA10, MA20(月線), MA60(季線), MA120(半年線), MA240(年線)
- **布林通道**：20日 ±2σ
- **RSI**：14日相對強弱指數，含70/30超買超賣線
- **KD指標**：台灣標準 KD(9,3,3)，含80/20線
- **個股分析**：技術信號自動評分 + 綜合評級（強力買進/買進/持有/賣出/強力賣出）
- **量化預測**：OLS線性回歸 5日/20日價格預測，含95%置信區間和R²
- **每日報告**：收盤後自動生成全市場技術分析報告
- **市場總覽**：台灣加權、S&P500、那斯達克、費半、黃金期貨、銅期貨

## 追蹤標的

### 台灣半導體
- 記憶體：南亞科(2408)、華邦電(2344)、旺宏(2337)
- IC設計：聯發科(2454)、聯詠(3034)、瑞昱(2379)、信驊(5274)等
- 晶圓製造：台積電(2330)、聯電(2303)
- 材料：環球晶(6488)
- 功率元件：強茂(2481)、台半(5425)等
- 系統廠：鴻海(2317)、廣達(2382)等
- ETF：元大台灣50(0050)、中信關鍵半導體(00891)等

### 美國半導體
- 記憶體：Micron (MU)
- IC設計：NVDA, AMD, QCOM, AVGO, MRVL, INTC
- 設備材料：AMAT, LRCX, KLAC, ASML
- 功率元件：ON, WOLF, MPWR, TXN
- ETF：SMH, SOXX, SOXL

### 礦產資源
- 稀土：MP Materials (MP), REMX ETF
- 黃金：GLD, GDX, NEM, GOLD, AEM
- 銅礦：FCX, SCCO, COPX, TECK
- 鐵礦鋼鐵：NUE, CLF, VALE, RIO, BHP

## 安裝與啟動

### 快速啟動（Windows）
```
double-click start.bat
```

### 手動啟動

**後端**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8765
```

**前端**
```bash
cd frontend
npm install
npm run dev
```

開啟瀏覽器：http://localhost:5173

## API 端點

| 端點 | 說明 |
|------|------|
| `GET /api/watchlist` | 取得所有追蹤標的分類 |
| `GET /api/stocks/{symbol}/kline?interval=1d` | K線資料 + 所有技術指標 |
| `GET /api/stocks/{symbol}/quote` | 即時報價 |
| `GET /api/stocks/{symbol}/analysis` | 個股技術分析 |
| `GET /api/market/overview` | 大盤指數 |
| `GET /api/analysis/daily-report` | 每日報告 |
| `POST /api/analysis/generate` | 手動觸發全市場分析 |

## 免責聲明

本系統所有分析完全基於技術指標數學模型自動生成，**不構成任何投資建議**。
投資有風險，請自行評估並承擔相應責任。
