# 倉位管理策略 — 設計與計算文件

> 對應實作：[`backend/position_strategy.py`](../backend/position_strategy.py)、API `GET /api/portfolio/position-analysis`、前端「資產管理」分頁。
> 本文同時取代原始的 Word 設計稿，作為策略的唯一權威說明。
> 短線進出時機（明日 T+1）另見 [明日(T+1) 短線買賣時機策略](./next-day-timing-strategy.md)。

---

## 0. 定位

這是一套 **倉位管理（Position Management）** 系統，**不負責選股、不產生進場訊號**。它針對「已經持有的股票」回答四件事：

1. 下跌時該如何分批止損、如何退場；
2. 上漲時該續抱、加倉、還是分批止盈；
3. 趨勢轉弱時該減多少、何時清倉；
4. 以上動作對應到圖表上的具體**價位**。

核心思想：**用 ATR 與 R 單位做動態風控**，再依「市場狀態」決定止盈/減倉/換手節奏，而不是用一刀切的固定百分比。

> 重要設計：本系統內所有數值都以**每檔股票的彙總加權均價**為基準計算，**不按單筆買入**計算。

---

## 1. 系統原則

### 1.1 不用固定百分比
傳統「跌 10% 停損、漲 20% 全出」對所有股票一視同仁，但不同股票波動率差很多。本系統改為：

- 止損點 = 依 **ATR** 動態決定；
- 止盈/減倉 = 依 **R 單位**與**市場狀態**動態決定。

### 1.2 決策優先級（由高到低）
判斷順序固定為：

1. **止損控制**（最高）
2. **大趨勢破壞**（分級處理）
3. **市場狀態**（止盈 / 減倉 / 加倉）
4. **加倉**（最低，只在健康趨勢才考慮）

即：已經該止損就不要因為「看起來還會漲」而繼續持有；已經大趨勢破壞就不要因為「還在獲利」而硬撐。

---

## 2. 資料來源

每檔股票需要日線 OHLCV：`date / open / high / low / close / volume`，採用前複權價格。系統取得歷史資料後計算下列指標的「最新值」做快照判斷（需 ≥ 60 根 K 線，否則回傳 `INSUFFICIENT_DATA`）。

---

## 3. 指標計算

### 3.1 移動平均 MA
```
MA5  = close.rolling(5).mean()
MA10 = close.rolling(10).mean()
MA20 = close.rolling(20).mean()
MA60 = close.rolling(60).mean()
```
用途：MA5 短期強弱、MA10 短期趨勢、MA20 中期趨勢與成本、MA60 中期趨勢骨架。

### 3.2 布林通道 Bollinger Bands（20, 2）
```
BOLL_MID   = MA20
BOLL_STD   = close.rolling(20).std()
BOLL_UPPER = BOLL_MID + 2 * BOLL_STD
BOLL_LOWER = BOLL_MID - 2 * BOLL_STD
```
- `close > BOLL_UPPER`：價格偏離過大，可能過熱；
- `close` 跌回 `BOLL_MID` 下方：趨勢可能轉弱。

### 3.3 RSI（14）
```
RSI_PERIOD = 14
```
| RSI | 含義 |
|---|---|
| < 30 | 超賣 |
| 30–50 | 偏弱 |
| 50–55 | 中性偏弱 |
| 55–68 | 健康偏強 |
| 68–70 | 接近過熱 |
| > 70 | 過熱 |
| > 75 | 極端過熱 |

RSI 不直接觸發買賣，只作為狀態判斷的一個因子。

### 3.4 ATR（14）— 真實波動
```
TR      = max( high - low, |high - 前收|, |low - 前收| )
ATR14   = TR.rolling(14).mean()
ATR_PCT = ATR14 / close          # 以百分比表示波動
```
`ATR_PCT` 用於動態決定止損百分比。

### 3.5 成交量比 Volume Ratio
```
VOL_MA20     = volume.rolling(20).mean()
VOLUME_RATIO = volume / VOL_MA20
```
| 量比 | 含義 |
|---|---|
| < 0.8 | 縮量 |
| 0.8–1.0 | 偏低 |
| 1.0–2.0 | 正常 |
| 2.0–2.5 | 放量，警惕 |
| > 2.5 | 高位巨量 |
| > 3.0 | 極端放量 |

### 3.6 上影線比例
```
upper_shadow       = high - max(open, close)
total_range        = high - low
upper_shadow_ratio = upper_shadow / total_range
```
`upper_shadow_ratio > 0.35` 代表上影線偏長，配合放量 / 高 RSI / 大漲幅時，常見於高位衝高回落（見頂訊號之一）。

---

## 4. R 單位與動態止損

### 4.1 R 的定義
```
R = base_stop = 初始可承受的風險百分比
```
例：均價 100、止損 92 → R = 8%。之後股價漲到 108 即 +1R、漲到 116 即 +2R。

### 4.2 動態止損 base_stop
```
atr_pct       = ATR14 / close
base_stop_raw = 2.5 * atr_pct
base_stop     = min( max(base_stop_raw, 0.08), 0.18 )
```
- 係數 **2.5 × ATR%**；
- **最小 8%**（避免太緊被洗）；
- **最大 18%**（單檔最大風險上限）；
- 若 `base_stop_raw > 0.18`，標記 **高波動**（前端顯示「⚠ 高波動，建議降低部位」）。

---

## 5. 進場基準與價位計算

進場基準採用該檔股票的**加權平均買入價**：
```
均價 entry = 總投資額 / 總股數
```

### 5.1 止損價（均價下方，倍數 0.6 / 1.0 / 1.5 R）
```
止損1 (-0.6R) = entry × (1 - 0.6 × base_stop)   → 減 30%
止損2 (-1.0R) = entry × (1 - 1.0 × base_stop)   → 減 40%
止損3 (-1.5R) = entry × (1 - 1.5 × base_stop)   → 清倉
```

### 5.2 目標價（均價上方，倍數 1 / 2 / 3 R）
```
目標 +1R = entry × (1 + 1 × base_stop)
目標 +2R = entry × (1 + 2 × base_stop)
目標 +3R = entry × (1 + 3 × base_stop)
```

### 5.3 範例（均價 1000、ATR% = 2.65%）
`2.5 × 2.65% = 6.6% < 8%` → `base_stop = 8%`
- 止損：952 / 920 / 880（−4.8% / −8% / −12%）
- 目標：1080 / 1160 / 1240（+8% / +16% / +24%）

> 注意：止損用 **0.6 / 1.0 / 1.5 R**（分批減倉），目標用 **1 / 2 / 3 R**（分批止盈），此不對稱來自原始設計。

---

## 6. profit_R（目前盈利換算成幾個 R）
```
pnl_pct  = close / entry - 1
profit_R = pnl_pct / base_stop
```

---

## 7. 移動止損（依 profit_R 分檔）
```
profit_R < 1      : 無（僅用初始止損）
1 ≤ profit_R < 2  : trailing = entry                       # 保本
2 ≤ profit_R < 3  : trailing = max(entry, 峰值 × 0.92)
profit_R ≥ 3      : trailing = max(MA20, 峰值 × 0.90)
峰值 peak = 最早買入日至今的最高收盤價
回撤 drawdown_from_peak = close / peak - 1
```

---

## 8. 市場狀態分類

依多因子打分，順序判斷（先判出即返回）：

### 8.1 高潮頂 CLIMAX_TOP（命中 ≥ 3）
```
volume_ratio > 2.5
rsi > 75
close > BOLL_UPPER
upper_shadow_ratio > 0.35
daily_return > 0.06
close < high × 0.97
close / MA20 > 1.15
```

### 8.2 轉弱 WEAKENING
先判「重大破壞」——任一成立即轉弱：
```
close < MA20  或  drawdown_from_peak ≤ -0.12  或  MA10 < MA20
```
否則再看「轉弱打分」（命中 ≥ 2）：
```
close < MA10
MA5 < MA10
close < BOLL_MID
volume_ratio > 1.5 且 close < open
drawdown_from_peak < -0.08
```

### 8.3 過熱 OVERHEATED（命中 ≥ 2）
```
rsi > 70
close > BOLL_UPPER
close / MA20 > 1.12
volume_ratio > 2.0
```

### 8.4 健康趨勢 HEALTHY_TREND（全部成立）
```
close > MA5 > MA10 > MA20 > MA60
55 ≤ rsi ≤ 68
1.0 ≤ volume_ratio ≤ 2.0
close / MA20 ≤ 1.10
close > BOLL_MID
```

### 8.5 否則 → NEUTRAL（中性）

---

## 9. 決策引擎

每次評估按 §1.2 的優先級執行：

### 9.1 優先級 1 — 止損控制
```
pnl ≤ -1.5 × base_stop  → 全部出場 (EXIT_ALL)
pnl ≤ -1.0 × base_stop  → 減倉 40%
pnl ≤ -0.6 × base_stop  → 減倉 30%
```

### 9.2 優先級 2 — 大趨勢破壞（分級）
> 這是相對原始設計的改良：原本「跌破 MA20 / 回撤過大 / MA10<MA20」任一成立即**全部清倉**，過於突然；改為依「確認程度 + 盈利高低」分級。

```
below_ma20    = close < MA20
deep_drawdown = drawdown_from_peak ≤ -0.12
confirmed     = (below_ma20 且 (MA10 < MA20 或 回撤 ≤ -0.08)) 或 deep_drawdown
```

| 情形 | 動作 |
|---|---|
| `confirmed`（確認破壞，或回撤 ≥ 12%） | **全部出場** |
| 跌破 MA20 但未確認，且 profit_R ≥ 3 | 減倉 **50%**（高利潤先保護） |
| 跌破 MA20 但未確認，且 profit_R ≥ 1 | 減倉 **40%** |
| 跌破 MA20 但未確認，且 profit_R < 1 | 減倉 **30%** |
| 未破 MA20，但自高點回撤 ≥ 8% | 減倉 **50%**（保護利潤） |
| 以上皆否 | 不觸發，交給狀態處理 |

要點：**只是跌破 MA20 不再立即清倉**，而是先按盈利高低分批保護；**只有「確認轉弱」或深度回撤才全清**。

### 9.3 優先級 3 — 各狀態處理

**高潮頂 CLIMAX_TOP**
```
profit_R ≥ 3 → 減倉 80%
profit_R ≥ 2 → 減倉 70%
profit_R ≥ 1 → 減倉 50%
否則         → 減倉 30%（即使盈利不足也先減頭寸）
```

**過熱 OVERHEATED**
```
profit_R ≥ 3   → 減倉 70%（留觀察倉）
profit_R ≥ 2   → 減倉 30%
profit_R ≥ 1.5 → 減倉 25%
profit_R ≥ 1   → 減倉 20%（開始減倉）
否則           → 續抱（盈利不足，暫不操作）
```

**轉弱 WEAKENING**
```
profit_R ≥ 2 → 減倉 70%
profit_R ≥ 1 → 減倉 50%
否則         → 全部出場
```

**健康趨勢 HEALTHY_TREND**
```
0.8 ≤ profit_R ≤ 1.8 → 加倉 20%（趨勢健康才加倉）
profit_R ≥ 3         → 減倉 25%（部分止盈，其餘移動止盈）
profit_R ≥ 2         → 減倉 20%（部分止盈）
否則                 → 續抱
```

**中性 NEUTRAL** → 續抱（無明確訊號）

---

## 10. 加倉規則（僅供參考）

只在 `HEALTHY_TREND` 且 `0.8 ≤ profit_R ≤ 1.8` 時考慮加倉；下列任一成立則**禁止加倉**：
```
rsi > 70
close > BOLL_UPPER
volume_ratio > 2.5
close / MA20 > 1.12
upper_shadow_ratio > 0.35
profit_R > 2
```
原則：不追高、不在見頂/長上影時加倉。

---

## 11. 參數總表

| 參數 | 預設值 | 說明 |
|---|---|---|
| `ATR_PERIOD` | 14 | ATR 週期 |
| `ATR_STOP_MULTIPLIER` | 2.5 | ATR 止損倍數 |
| `MIN_BASE_STOP` | 0.08 | 最小基礎止損 |
| `MAX_BASE_STOP` | 0.18 | 最大基礎止損 |
| `LOSS_LEVEL_1_MULT` | 0.6 | 第一層止損（減 30%） |
| `LOSS_LEVEL_2_MULT` | 1.0 | 第二層止損（減 40%） |
| `LOSS_LEVEL_3_MULT` | 1.5 | 第三層止損（清倉） |
| `VOLUME_MA_PERIOD` | 20 | 量能均線週期 |
| RSI 健康區間 | 55–68 | 健康趨勢 RSI |
| RSI 過熱 / 極端 | 70 / 75 | 過熱、極端過熱 |
| 量比 過熱 / 高潮 | 2.0 / 2.5 | 過熱、見頂巨量 |
| MA20 乖離 健康/過熱/極端 | 1.10 / 1.12 / 1.15 | close/MA20 上限 |
| 上影線門檻 | 0.35 | 見頂上影線 |
| 單日大漲門檻 | 0.06 | 高潮頂日漲幅 |

以上常數集中在 `position_strategy.py` 頂部，調整即可改變策略行為。

---

## 12. 系統實作對應

| 元件 | 位置 | 說明 |
|---|---|---|
| 策略核心 | `backend/position_strategy.py` | 指標、狀態分類、決策引擎、價位 |
| API | `GET /api/portfolio/position-analysis?symbol=&entry=&entry_date=` | 回傳單檔快照分析 |
| 前端面板 | `frontend/src/components/PortfolioPanel.jsx` | 每檔「分析」展開、價位按鈕 |
| K 線圖 | `frontend/src/components/StockChart.jsx` | 策略價位線（可逐條勾選）+ 買入點 |

API 回傳重點欄位：
```
state / state_label        # 市場狀態
decision { action, reason, ratio, ratio_type }   # 建議動作與比例
base_stop_pct / profit_R / pnl_pct / atr_pct
indicators { ma5 ma10 ma20 ma60 rsi volume_ratio
             upper_shadow_ratio drawdown_from_peak_pct peak_price }
levels { stop_loss_1/2/3, trailing_stop, target_1R/2R/3R }
high_volatility
```

---

## 13. 注意事項與邊界

- **僅做倉位管理，不負責選股**：標的應由其他方式選出，本系統只在「持有期間」給管理建議。
- **快照、非狀態機**：目前實作為單次快照建議，不追蹤「各層級是否已觸發」「目前部位大小」等歷時狀態。多次觸發控制、回測等屬未來擴充。
- **資料不足**：K 線少於 60 根回傳 `INSUFFICIENT_DATA`；量能為 0 時量比視為無效，不進入過熱/高潮判斷。
- **配色慣例**：本專案「漲/獲利為紅、跌/虧損為綠」；圖表中止損線綠、目標線紅、均價線藍、移動止損橙。
- 本分析完全基於技術指標與公開資料，**不構成投資建議**，使用者需自行評估風險。
