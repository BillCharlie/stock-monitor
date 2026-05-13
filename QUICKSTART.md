# Stock Monitor 快速启动指南

## 🚀 快速开始（5分钟）

### 1. 启动后端服务

```bash
cd backend

# 安装依赖（如果还没有安装）
pip install -r requirements.txt

# 启动服务
python test_enhancements.py    # 先运行测试脚本验证新功能
uvicorn main:app --reload --port 8765
```

### 2. 验证服务正常运行

打开浏览器访问：
- 主应用: http://localhost:8765
- API 文档: http://localhost:8765/docs

---

## 📝 四个问题的快速解决方案

### 问题 1️⃣: 自定新增的股票抓不到任何信息

**解决步骤:**
1. 确保符号格式正确
   - 台湾股票: `2330.TW` (代码 + .TW)
   - 美国股票: `AAPL` (大写，无后缀)

2. 添加自定义股票时，系统会自动验证
   - 返回错误信息（如有问题）
   - 返回实时价格（如成功）

**测试命令:**
```bash
# Python 快速测试
python3 -c "
from realtime_data import validate_symbol
result = validate_symbol('2330.TW')
print('Valid:', result['valid'])
print('Price:', result.get('price'))
"

# curl 快速测试
curl 'http://localhost:8765/api/custom-stocks' \
  -H 'X-API-Secret: sha256-hash-of-your-secret' \
  -H 'Content-Type: application/json' \
  -d '{\"symbol\":\"2330.TW\", \"name\":\"台积电\"}'
```

**常见问题:**
- ❌ "找不到数据" → 检查符号是否存在，非交易时间可能无数据
- ❌ "符号格式错误" → 台股需要 `.TW` 后缀
- ❌ "连接超时" → 检查网络和数据源可用性

---

### 问题 2️⃣: K线抓取的时间要能在盘中实时更新

**解决步骤:**

#### A. 获取实时价格（最新报价）
```javascript
// JavaScript 示例
async function getRealtime(symbol) {
  const res = await fetch(`/api/stocks/${symbol}/realtime`);
  const quote = await res.json();
  console.log(`${symbol} 现价: ${quote.price}`);
  console.log(`更新时间: ${quote.timestamp}`);
}

// 每30秒更新一次
setInterval(() => getRealtime('2330.TW'), 30000);
```

#### B. 获取盘中K线（分钟级）
```javascript
// 获取5分钟K线
async function getIntradayBars(symbol, interval = 5) {
  const res = await fetch(`/api/stocks/${symbol}/intraday-kline?interval=${interval}`);
  const data = await res.json();
  
  // 更新图表
  updateChart(data.data);
  
  // 设置自动刷新（每分钟）
  setTimeout(() => getIntradayBars(symbol, interval), 60000);
}

// 启动
getIntradayBars('2330.TW', 5);
```

#### C. 使用 TradingView/Chart.js 显示
```html
<!-- HTML 示例 -->
<canvas id="intraday-chart"></canvas>

<script>
const ctx = document.getElementById('intraday-chart').getContext('2d');

async function updateChart(symbol) {
  const res = await fetch(`/api/stocks/${symbol}/intraday-kline?interval=5`);
  const { data } = await res.json();
  
  // 转换为 Chart.js 格式
  const ohlcData = data.map(bar => ({
    x: bar.time,
    o: bar.open,
    h: bar.high,
    l: bar.low,
    c: bar.close
  }));
  
  // 创建或更新图表
  // 使用 Chart.js + candlestick 插件
}
</script>
```

**数据源说明:**
- 📊 实时报价 (30秒缓存): TWSE, Tencent, Sina
- 📈 分钟K线 (实时): TWSE (台股), Sina (全球股)
- 🔄 自动故障转移: 首选→备选→备选

---

### 问题 3️⃣: 筹码主力量能与动态

**解决步骤:**

#### A. 查看筹码分布
```bash
# 获取筹码分析数据
curl 'http://localhost:8765/api/stocks/2330.TW/chip-analysis'

# Python 脚本
python3 -c "
from chip_analysis import get_twse_chip_distribution
chip = get_twse_chip_distribution('2330.TW')
print('前10大股东占比:', chip['concentration']['top_10_pct'], '%')
print('集中度等级:', chip['concentration']['level'])
print('主要股东:')
for h in chip['major_holders'][:5]:
    print(f\"  {h['name']}: {h['percentage']}%\")
"
```

#### B. 分析主力成交
```bash
# 获取主力交易分析
curl 'http://localhost:8765/api/stocks/2330.TW/major-traders'
```

**返回信息:**
- 📊 股权集中度 (HHI 指标)
  - HHI > 2500: 高度集中 = 机构主导，容易拉升/砸盘
  - HHI 1500-2500: 中度集中 = 平衡
  - HHI < 1500: 分散 = 零售主导，波动性大

- 📈 成交量趋势
  - 成交量上升 + 价格上升 = 强势
  - 成交量下降 + 价格下降 = 弱势
  - 成交量异常 = 主力活动信号

---

### 问题 4️⃣: 新增个股主力买卖超分析 + 机构识别

**解决步骤:**

#### A. 识别主力机构
```bash
# 获取完整机构分析
curl 'http://localhost:8765/api/stocks/2330.TW/institutions'
```

#### B. 理解返回结果
```json
{
  "three_forces": {
    "foreign_net": 5200000,      // 外资买超 (正数=买入)
    "trust_net": -800000,         // 投信賣超 (负数=卖出)
    "dealer_net": 500000,         // 自营商买超
    "total_net": 4900000          // 合计买超
  },
  "institutions": {
    "likely_buyers": [
      {
        "type": "外资",
        "signal": "外资买超 5,200,000 股",
        "likely_institutions": [
          "美系大型基金 (Vanguard, BlackRock, Fidelity等)",
          "日本投资机构"
        ]
      }
    ]
  },
  "summary": {
    "sentiment": "机构看多"  // ← 整体判断
  }
}
```

#### C. 结合 GPT 深度分析
```bash
# 自动每天生成 GPT 分析报告（包含机构识别）
# 报告包含：
# - 三大法人活动总结
# - 推测的具体机构名单
# - 可能的交易动机（基于行业新闻）
# - 后续操作预测

# 人工触发报告生成：
curl -X POST 'http://localhost:8765/api/report/gpt-generate' \
  -H 'X-API-Secret: your-secret'
```

---

## 🎯 使用流程示例

### 完整的股票分析流程

```javascript
async function analyzeStock(symbol) {
  console.log(`开始分析 ${symbol}...`);
  
  // 1. 获取基本K线和指标
  const kline = await fetch(`/api/stocks/${symbol}/kline`).then(r => r.json());
  console.log(`K线数据: ${kline.data.length} 根`);
  
  // 2. 获取实时报价
  const realtime = await fetch(`/api/stocks/${symbol}/realtime`).then(r => r.json());
  console.log(`现价: ${realtime.price}`);
  
  // 3. 获取筹码分析
  const chip = await fetch(`/api/stocks/${symbol}/chip-analysis`).then(r => r.json());
  console.log(`筹码集中度: ${chip.chip_distribution.concentration.level}`);
  
  // 4. 获取主力交易
  const traders = await fetch(`/api/stocks/${symbol}/major-traders`).then(r => r.json());
  console.log(`近期成交量趋势: ${traders.major_traders.volume_analysis.volume_trend}`);
  
  // 5. 识别主力机构
  const institutions = await fetch(`/api/stocks/${symbol}/institutions`).then(r => r.json());
  console.log(`市场情绪: ${institutions.summary.sentiment}`);
  
  // 6. 汇总分析
  const analysis = await fetch(`/api/stocks/${symbol}/analysis`).then(r => r.json());
  console.log(`技术评级: ${analysis.rating}`);
  
  // 7. 生成报告（可选）
  return {
    symbol,
    price: realtime.price,
    rating: analysis.rating,
    chipConcentration: chip.chip_distribution.concentration.level,
    volumeTrend: traders.major_traders.volume_analysis.volume_trend,
    sentiment: institutions.summary.sentiment,
    buySignals: institutions.institutions.likely_buyers,
    sellSignals: institutions.institutions.likely_sellers
  };
}

// 使用示例
const result = await analyzeStock('2330.TW');
console.log(JSON.stringify(result, null, 2));
```

---

## 📱 API 端点快速参考

```
【实时数据】
GET /api/stocks/{symbol}/realtime              - 实时价格（30秒更新）
GET /api/stocks/{symbol}/intraday-kline        - 分钟K线（可选: ?interval=1|5|15|30|60）

【筹码分析】
GET /api/stocks/{symbol}/chip-analysis         - 筹码分布 + 集中度
GET /api/stocks/{symbol}/major-traders         - 主力交易分析

【机构分析】
GET /api/stocks/{symbol}/institutions          - 机构识别 + 三大法人

【既有端点】
GET /api/stocks/{symbol}/kline                 - 日K线（每日 5 分钟更新）
GET /api/stocks/{symbol}/quote                 - 昨日收盘价（每日更新）
GET /api/stocks/{symbol}/analysis              - 完整技术分析
```

---

## ⚡ 性能优化建议

### 前端缓存策略
```javascript
// 使用 IndexedDB 缓存历史数据
const cache = await idb.open('stockCache', 1);

async function getCachedOrFresh(symbol, maxAge = 60000) {
  const cached = await cache.get('realtime', symbol);
  
  if (cached && Date.now() - cached.timestamp < maxAge) {
    return cached.data;  // 返回缓存（60秒内）
  }
  
  const fresh = await fetch(`/api/stocks/${symbol}/realtime`).then(r => r.json());
  await cache.put('realtime', symbol, { data: fresh, timestamp: Date.now() });
  return fresh;
}
```

### 批量请求优化
```javascript
// 同时获取多个股票数据
async function getMultipleStocks(symbols) {
  const promises = symbols.map(symbol =>
    Promise.all([
      fetch(`/api/stocks/${symbol}/realtime`),
      fetch(`/api/stocks/${symbol}/institutions`)
    ]).then(([r1, r2]) => Promise.all([r1.json(), r2.json()]))
  );
  
  return Promise.all(promises);
}
```

---

## 🐛 故障排除

| 问题 | 原因 | 解决方案 |
|-----|------|---------|
| `404 Not Found` | 股票符号不存在 | 检查符号格式: 台股 `XXXX.TW`, 美股 `AAPL` |
| `503 Service Unavailable` | 数据源不可用 | 检查网络，稍后重试 |
| 实时数据延迟 | 非交易时间 | 仅在 9:00-15:30 (台北时间) 有最新数据 |
| 机构识别不准确 | 基于买卖超推测 | 这是最可能但非确定，结合其他信息验证 |
| API 返回 401 | API 密钥错误 | 检查 `X-API-Secret` header (如需要) |

---

## 📞 快速命令参考

```bash
# 运行测试
cd backend && python test_enhancements.py

# 启动服务
cd backend && uvicorn main:app --reload --port 8765

# 查看日志
tail -f logs/*.log

# 测试单个功能
python3 -c "from realtime_data import get_realtime_quote; print(get_realtime_quote('2330.TW'))"

# 批量验证符号
python3 << 'EOF'
from realtime_data import validate_symbol
for symbol in ['2330.TW', 'AAPL', 'MSFT']:
    result = validate_symbol(symbol)
    print(f"{symbol}: {result['valid']} - {result.get('price', result.get('error'))}")
EOF
```

---

## 🎓 学习资源

- 📖 完整文档: 查看 `ENHANCEMENTS.md`
- 🔍 API 文档: http://localhost:8765/docs
- 💻 源代码: `backend/realtime_data.py`, `backend/chip_analysis.py`
- 🧪 测试脚本: `backend/test_enhancements.py`

---

**祝您使用愉快！如有问题，请查阅 ENHANCEMENTS.md 或检查日志。** 🚀
