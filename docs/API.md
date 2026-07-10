# API 接口文档

完整 OpenAPI 文档启动后访问：`http://localhost:8000/docs`

## 认证

所有 `/api/*` 接口（除登录外）需在 Header 中携带 JWT：

```
Authorization: Bearer <token>
```

## 接口列表

### 1. 认证

#### POST /api/auth/login
用户登录

请求：
```json
{
  "username": "admin",
  "password": "admin123"
}
```

响应：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### GET /api/auth/me
获取当前用户信息

### 2. 股票

#### GET /api/stocks
分页获取股票列表

参数：
- `q` (可选): 搜索关键词
- `page` (默认 1): 页码
- `size` (默认 50, 最大 500): 每页数量

响应：
```json
{
  "items": [
    {"symbol": "000001.SZ", "name": "平安银行", "market": "深圳", "industry": "银行", "list_date": "19910403"}
  ],
  "total": 5000
}
```

#### GET /api/stocks/search?q=...
快速搜索（最多20条）

#### GET /api/stocks/{symbol}
获取单个股票详情

### 3. 数据

#### POST /api/data/kline
获取 K 线数据，可选叠加技术指标

请求：
```json
{
  "symbol": "000001.SZ",
  "start_date": "20230101",
  "end_date": "20241231",
  "indicators": ["MA", "EMA", "MACD", "RSI", "KDJ", "BOLL"]
}
```

响应：
```json
{
  "symbol": "000001.SZ",
  "dates": ["20230101", "20230102", ...],
  "opens": [13.5, 13.6, ...],
  "highs": [...],
  "lows": [...],
  "closes": [...],
  "volumes": [...],
  "indicators": {
    "MA": {"MA5": [...], "MA10": [...], "MA20": [...]},
    "MACD": {"DIF": [...], "DEA": [...], "HIST": [...]}
  }
}
```

#### POST /api/data/sync
触发数据同步（异步）

#### GET /api/data/sync/status
查询同步状态

```json
{
  "running": false,
  "progress": "完成",
  "total_symbols": 500,
  "synced_symbols": 500,
  "last_update": "2024-12-31T16:30:00"
}
```

### 4. 指标

#### POST /api/indicators/calculate
按需计算指标，支持自定义参数

请求：
```json
{
  "symbol": "000001.SZ",
  "indicators": ["MACD", "RSI"],
  "start_date": "20230101",
  "end_date": "20241231",
  "params": {
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "rsi_period": 14
  }
}
```

### 5. 回测

#### GET /api/backtest/strategies
列出可用策略

响应：
```json
[
  {
    "name": "ma_cross",
    "description": "快速 EMA 上穿慢速 EMA 买入，下穿卖出",
    "params": {"fast_period": 5, "slow_period": 20}
  }
]
```

#### POST /api/backtest/run
运行回测

请求：
```json
{
  "strategy": "ma_cross",
  "symbol": "000001.SZ",
  "start_date": "20200101",
  "end_date": "20241231",
  "initial_capital": 1000000,
  "params": {"fast_period": 5, "slow_period": 20}
}
```

响应：
```json
{
  "metrics": {
    "total_return": 0.234,
    "annual_return": 0.045,
    "sharpe_ratio": 0.82,
    "sortino_ratio": 1.15,
    "max_drawdown": 0.18,
    "max_drawdown_duration": 120,
    "calmar_ratio": 0.25,
    "win_rate": 0.55,
    "profit_loss_ratio": 1.4,
    "total_trades": 32,
    "avg_holding_days": 18.5
  },
  "equity_curve": [
    {"date": "20200102", "equity": 1000500},
    ...
  ],
  "trades": [
    {
      "date": "20200315",
      "symbol": "000001.SZ",
      "direction": "buy",
      "price": 12.30,
      "quantity": 8000,
      "commission": 29.52
    }
  ]
}
```

### 6. 选股

#### POST /api/screener/run
多因子选股

请求：
```json
{
  "filters": {
    "pe_max": 20,
    "pb_max": 3,
    "roe_min": 15,
    "momentum_days": 20,
    "momentum_min": 0.05
  }
}
```

响应：
```json
{
  "results": [
    {"symbol": "000001.SZ", "name": "平安银行", "score": 0.85, "pe": 8.5, "pb": 0.9, "roe": 16.2}
  ]
}
```

### 7. 信号

#### GET /api/signals/today
获取今日已生成的信号

#### POST /api/signals/run
触发信号生成（盘后调用）

响应：
```json
{
  "signals": [
    {
      "symbol": "000001.SZ",
      "strategy_name": "MA Cross (5/20)",
      "signal": "buy",
      "price": 12.45,
      "datetime": "2024-12-31T15:30:00",
      "reason": "MA Cross (5/20) generated buy signal"
    }
  ],
  "generated_at": "2024-12-31T16:30:00"
}
```

#### POST /api/signals/test-notify
测试通知渠道

请求参数：`channel=webhook` 或 `channel=email`

## 错误响应

所有错误使用标准 HTTP 状态码：

- 400: 请求参数错误
- 401: 未授权（缺失或无效 token）
- 404: 资源未找到
- 409: 冲突（如同步任务已在运行）
- 500: 服务器内部错误

错误格式：
```json
{"detail": "错误描述信息"}
```
