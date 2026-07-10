# QuantInvest 架构文档

## 系统概览

QuantInvest 是一个面向 A 股市场的个人量化投资分析平台，采用前后端分离架构，部署在 Linux 云服务器上。

## 分层架构

```
┌─────────────────────────────────────────────────────────┐
│  浏览器 (Vue 3 SPA)                                       │
│  Element Plus + KLineCharts + ECharts                    │
│  /login / / /stocks /kline/:sym /screener /backtest     │
│  /signals /settings                                      │
└────────────────────────┬────────────────────────────────┘
                         │ REST API (/api/*, JWT Bearer)
┌────────────────────────▼────────────────────────────────┐
│  FastAPI 应用层 (main.py)                                │
│  CORS, startup, routers mount                            │
├─────────────────────────────────────────────────────────┤
│  API 路由 (api/routes/*.py)                              │
│  /auth /stocks /data /indicators /backtest              │
│  /screener /signals                                      │
├─────────────────────────────────────────────────────────┤
│  核心引擎层 (core/)                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ data/    │ │indicators│ │ backtest │ │ strategy │  │
│  │ fetcher  │ │ MA/EMA   │ │ engine   │ │ base     │  │
│  │ storage  │ │ MACD/RSI │ │ portfolio│ │ ma_cross │  │
│  │ updater  │ │ KDJ/BOLL │ │ metrics  │ │ screener │  │
│  │          │ │ ATR/OBV  │ │          │ │          │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────────┐ ┌──────────┐                          │
│  │ signals/     │ │scheduler │                          │
│  │ generator    │ │APSched   │                          │
│  │ notifier     │ │          │                          │
│  └──────────────┘ └──────────┘                          │
├─────────────────────────────────────────────────────────┤
│  存储层                                                  │
│  SQLite (stock_list, daily_update_log) + Parquet (K线)  │
└─────────────────────────────────────────────────────────┘
```

## 核心模块说明

### data/ - 数据采集与存储

- **fetcher.py** - 封装 AKShare，从东方财富/同花顺等数据源拉取
- **storage.py** - SQLite 存元数据，Parquet 存时序 K 线
- **updater.py** - 增量更新、复权处理

### indicators/ - 技术指标

所有指标函数都是纯函数：`pd.Series -> pd.Series`，便于组合和向量化计算。

- ma.py: SMA, EMA, WMA
- momentum.py: MACD (DIF/DEA/HIST), RSI, KDJ
- volatility.py: BOLL (UPPER/MID/LOWER), ATR
- volume.py: OBV, VWAP

### backtest/ - 回测引擎

两个互补的实现：

- **engine.BacktestEngine** - 事件驱动协议风格，要求策略实现 `on_bar(idx, row, engine) -> Signal`
- **portfolio.Portfolio** - 实用主义风格，要求策略实现 `on_bar(idx, row, data, portfolio)` 并通过 portfolio.buy/sell 直接下单

API 层使用 Portfolio 风格（更接近真实交易流程）。

### strategy/ - 策略框架

`base.Strategy` 是抽象基类，`ma_cross.MACrossStrategy` 是示例实现。

### signals/ - 信号与通知

- **generator** - 盘后扫描，对所有股票运行策略，生成买卖信号
- **notifier** - 通过 Webhook（飞书/钉钉/企业微信/通用）或邮件发送通知

## 数据流

### 同步流程

```
用户/调度器 -> POST /api/data/sync
              -> BackgroundTask 触发
              -> DataUpdater.update_all
              -> AKShareFetcher.get_daily_kline
              -> DataStorage.save_daily_kline (Parquet)
              -> 更新 daily_update_log
```

### 回测流程

```
用户 -> POST /api/backtest/run {strategy, symbol, dates, params}
       -> DataStorage.load_daily_kline (Parquet)
       -> 构建 Strategy 实例
       -> Portfolio 逐 bar 迭代
          -> strategy.on_bar(idx, row, df, portfolio)
          -> portfolio.buy/sell (执行订单)
          -> portfolio.get_equity (记录权益)
       -> calculate_metrics (收益/夏普/回撤)
       -> 返回 BacktestResponse
```

### 信号生成流程

```
调度器 (16:30) -> SignalGenerator.run_strategies
                 -> 对每只股票加载数据
                 -> 调用 strategy.on_bar(最后一条)
                 -> _SignalRecorder 收集 buy/sell
                 -> 构造信号字典列表
                 -> Notifier.notify (webhook + email)
```

## 扩展点

1. **新增策略**：继承 `core.strategy.base.Strategy`，在 `api/routes/backtest.py` 的 `_build_strategy` 注册
2. **新增指标**：在 `core/indicators/*.py` 添加，在 `api/routes/data.py` 的 KLine 处理中注册
3. **新增数据源**：在 `core/data/fetcher.py` 添加新数据源类
4. **新增通知渠道**：在 `core/signals/notifier.py` 的 `notify()` 中添加分发
5. **新增 API 路由**：在 `api/routes/` 创建新文件，在 `main.py` include

## 安全模型

- JWT 认证 (HS256, 默认 24h 有效期)
- 单用户管理，账号密码在 .env 中配置
- CORS 默认允许所有源（生产环境应限制）
- 关键操作（同步、信号生成）需登录
- 系统未实现细粒度权限控制 (适用个人使用)
