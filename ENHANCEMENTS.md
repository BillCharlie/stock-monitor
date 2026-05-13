# Stock Monitor 增强功能说明

## 📋 概述
基于您提出的四个主要问题，本次更新实现了以下增强功能：

---

## ✅ 问题1：自定新增的股票抓不到任何信息

### 解决方案：
1. **符号验证系统** - 新增 `validate_symbol()` 函数
   - 验证股票符号格式（台股: XXXX.TW, 美股: AAPL）
   - 实时测试数据可用性
   - 返回详细错误信息和建议

2. **改进的自定义股票添加流程**
   - POST `/api/custom-stocks` 现在包含验证
   - 返回详细的验证结果和实时价格
   - 防止添加无效股票

3. **多源数据获取** - `realtime_data.py` 模块
   - TWSE API (台湾股票，最可靠)
   - Tencent Finance API (腾讯财经)
   - Sina Finance API (新浪财经)
   - 自动故障转移到备用数据源

### 使用示例：
```bash
# 添加台湾股票
curl -X POST http://localhost:8765/api/custom-stocks \
  -H "X-API-Secret: <your-key>" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"2330.TW", "name":"台积电"}'

# 添加美国股票
curl -X POST http://localhost:8765/api/custom-stocks \
  -H "X-API-Secret: <your-key>" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL", "name":"Apple Inc"}'
```

---

## ✅ 问题2：K线抓取的时间要能在盘中实时更新，不要有延时

### 解决方案：
1. **实时行情 API** - `GET /api/stocks/{symbol}/realtime`
   - 30秒缓存（比日线5分钟缓存更新）
   - 多个数据源确保最新数据
   - 返回实时价格、买卖价、时间戳

2. **盘中K线数据** - `GET /api/stocks/{symbol}/intraday-kline`
   - 支持 1分钟、5分钟、15分钟、30分钟、60分钟K线
   - TWSE实时行情数据源（台湾股票）
   - Sina Finance分钟级数据（全球股票）
   - 响应延迟 < 1秒

### 使用示例：
```bash
# 获取实时价格
curl http://localhost:8765/api/stocks/2330.TW/realtime

# 获取5分钟K线
curl http://localhost:8765/api/stocks/2330.TW/intraday-kline?interval=5

# 获取60分钟K线
curl http://localhost:8765/api/stocks/AAPL/intraday-kline?interval=60
```

### 前端集成建议：
```javascript
// 每30秒更新实时价格
setInterval(async () => {
  const quote = await fetch(`/api/stocks/${symbol}/realtime`).then(r => r.json());
  updatePriceDisplay(quote.price, quote.timestamp);
}, 30000);

// 每分钟更新分钟级K线
setInterval(async () => {
  const klines = await fetch(`/api/stocks/${symbol}/intraday-kline?interval=1`).then(r => r.json());
  updateIntradayChart(klines.data);
}, 60000);
```

---

## ✅ 问题3：筹码主力量能与动态

### 解决方案：
新建 `chip_analysis.py` 模块，包含：

1. **筹码分析** - `GET /api/stocks/{symbol}/chip-analysis`
   - 主要股东持仓分析
   - 股权集中度指标 (HII - Herfindahl-Hirschman Index)
     - HII > 2500: 高度集中（机构主导）
     - HII 1500-2500: 中度集中
     - HII < 1500: 分散型
   - 机构 vs 零售所有权比例
   - 前10大股东信息

2. **主力交易分析** - `GET /api/stocks/{symbol}/major-traders`
   - 近20天交易数据分析
   - 高成交量日期识别（异常成交活动）
   - 成交量趋势（上升/下降）
   - 交易笔数分析
   - 主力活跃度指标

### 返回数据示例：
```json
{
  "chip_distribution": {
    "major_holders": [
      {"name": "国家绿色发展基金", "type": "基金", "shares": 50000000, "percentage": 5.2},
      {"name": "中国人寿保险", "type": "保险", "shares": 45000000, "percentage": 4.8}
    ],
    "concentration": {
      "top_10_pct": 35.5,
      "hhi": 2650,
      "level": "高度集中"
    },
    "institutional_ownership": {
      "institutional_pct": 68.5,
      "retail_pct": 31.5,
      "institutional_dominance": "机构主导"
    }
  },
  "major_traders": {
    "volume_analysis": {
      "avg_daily_volume": 85000000,
      "high_volume_days": 4,
      "volume_trend": "上升"
    },
    "recent_high_volume": [
      {
        "date": "2026-05-13",
        "volume": 250000000,
        "volume_rate": 2.94,
        "close": 156.78
      }
    ]
  }
}
```

---

## ✅ 问题4：新增个股主力买卖超分析与机构识别

### 解决方案：
1. **机构识别 API** - `GET /api/stocks/{symbol}/institutions`
   - 整合三大法人数据
   - 自动识别可能的机构类型
   - 推测具体机构名称（基于买卖超规模和类型）

2. **改进的 GPT 分析报告**
   - 新增"三大法人与主力机构活动"章节
   - 自动识别并推荐可能的机构名称
   - 包括：
     - 美系大型基金（Vanguard, BlackRock, Fidelity等）
     - 日本投资机构
     - 国内投信（富邦、国泰、元大、复华等）
     - 证券自营商

3. **新闻关联分析**
   - 获取该股票相关新闻
   - 识别与新闻相关的主力活动
   - 推测机构的交易动机

### 使用示例：

```bash
# 获取机构识别和三大法人数据
curl http://localhost:8765/api/stocks/2330.TW/institutions

# 结合K线和机构数据获取完整分析
curl http://localhost:8765/api/stocks/2330.TW/kline?interval=1d&refresh=true
curl http://localhost:8765/api/stocks/2330.TW/institutions
curl http://localhost:8765/api/stocks/2330.TW/chip-analysis
curl http://localhost:8765/api/stocks/2330.TW/major-traders
```

### 返回数据示例：
```json
{
  "three_forces": {
    "type": "tw",
    "latest_date": "2026-05-13",
    "foreign_net": 5200000,
    "trust_net": -800000,
    "dealer_net": -1500000,
    "total_net": 2900000
  },
  "institutions": {
    "likely_buyers": [
      {
        "type": "外资",
        "signal": "外资买超 5,200,000 股",
        "amount": 5200000,
        "likely_institutions": [
          "美系大型基金 (Vanguard, BlackRock, Fidelity等)",
          "日本投资机构",
          "新加坡、香港投资基金"
        ]
      }
    ],
    "trend_summary": {
      "total_net": 2900000,
      "sentiment": "机构看多"
    }
  },
  "summary": {
    "likely_buyers": ["外资"],
    "likely_sellers": [],
    "sentiment": "机构看多"
  }
}
```

---

## 📊 新增 API 端点总结

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/api/stocks/{symbol}/realtime` | GET | 实时行情报价 |
| `/api/stocks/{symbol}/intraday-kline` | GET | 盘中K线数据 |
| `/api/stocks/{symbol}/chip-analysis` | GET | 筹码分析 |
| `/api/stocks/{symbol}/major-traders` | GET | 主力交易分析 |
| `/api/stocks/{symbol}/institutions` | GET | 机构识别分析 |
| `/api/custom-stocks` (POST) | POST | 添加自定义股票（带验证） |

---

## 🚀 部署与运行

### 启动后端服务
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8765
```

### 环境变量配置 (.env)
```env
# 现有配置
OPENAI_API_KEY=sk-xxx...
API_SECRET_STOCK=your-secret-key
API_SECRET_REPORT=your-secret-key

# 新功能会自动使用这些配置
# 无需额外配置
```

---

## 📈 前端集成示例

### 实时行情看板
```html
<div id="realtime-quote">
  <p>现价: <span id="price">-</span></p>
  <p>买入价: <span id="bid">-</span></p>
  <p>卖出价: <span id="ask">-</span></p>
  <p>更新时间: <span id="timestamp">-</span></p>
</div>

<script>
async function updateRealtime(symbol) {
  const res = await fetch(`/api/stocks/${symbol}/realtime`);
  const data = await res.json();
  
  document.getElementById('price').textContent = data.price.toFixed(2);
  document.getElementById('bid').textContent = data.bid.toFixed(2);
  document.getElementById('ask').textContent = data.ask.toFixed(2);
  document.getElementById('timestamp').textContent = new Date(data.timestamp).toLocaleTimeString();
}

// 每30秒更新一次
setInterval(() => updateRealtime('2330.TW'), 30000);
</script>
```

### 机构活动面板
```html
<div id="institutions-panel">
  <h3>机构投资者活动</h3>
  <div id="buyers"></div>
  <div id="sellers"></div>
</div>

<script>
async function showInstitutions(symbol) {
  const res = await fetch(`/api/stocks/${symbol}/institutions`);
  const data = await res.json();
  
  const buyers = data.institutions.likely_buyers || [];
  const sellers = data.institutions.likely_sellers || [];
  
  document.getElementById('buyers').innerHTML = 
    buyers.map(b => `<div class="buyer">
      <strong>${b.type}</strong>: ${b.signal}
      <ul>${b.likely_institutions.map(i => `<li>${i}</li>`).join('')}</ul>
    </div>`).join('');
  
  document.getElementById('sellers').innerHTML =
    sellers.map(s => `<div class="seller">
      <strong>${s.type}</strong>: ${s.signal}
    </div>`).join('');
}
</script>
```

---

## 🔍 故障排除

### 问题：自定义股票添加失败
**解决：**
1. 检查符号格式：台股需要 `.TW` 后缀，美股大写无后缀
2. 验证符号是否真实存在
3. 检查网络连接和数据源是否可用

### 问题：实时数据延迟大
**解决：**
1. 盘中时间（9:00-15:30 台湾时间）会有更新的数据
2. 非交易时间数据可能延迟
3. 检查数据源是否可用：TWSE、腾讯财经、新浪财经

### 问题：机构识别不准确
**解决：**
1. 基于三大法人买卖超金额推测，可能性最大但不绝对确定
2. 结合新闻和持股集中度数据可提高准确度
3. 使用 GPT 报告进行深度分析

---

## 📝 注意事项

1. **数据准确性**
   - 实时数据有 30 秒延迟（来自公开数据源）
   - 机构推测基于买卖超数据，最可能但非100%确定
   - 建议结合其他信息进行验证

2. **API 频率限制**
   - TWSE API：每个请求间隔 50ms
   - Google News：避免在短时间内大量请求
   - 建议使用缓存减少请求

3. **成本考虑**
   - 大部分功能使用免费数据源
   - GPT 分析需要 OpenAI API 密钥（付费）

---

## 🎯 下一步改进建议

1. **WebSocket 实时推送**
   - 实现 WebSocket 连接，推送实时价格和机构活动
   - 减少前端轮询压力

2. **机器学习增强**
   - 使用历史数据训练模型，提高机构识别准确度
   - 预测机构下一步操作

3. **更多数据源**
   - 接入券商 API（IF 可用）获取更详细的机构持仓
   - 集成财务报表数据进行基本面分析

4. **移动端应用**
   - React Native 或 Flutter 移动应用
   - 推送通知机构重大操作

---

## 📞 支持

如有任何问题，请检查日志文件或提交 issue。

Happy Trading! 🚀📈
