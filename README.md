# QuantInvest - 个人量化投资平台

<p align="center">
  <strong>面向 A 股市场的个人量化投资分析工具</strong>
</p>

---

## 主要功能

- **数据采集** — 基于 AKShare 自动获取沪深两市日线/分钟线行情，增量更新
- **技术分析** — 内置 MA/EMA/MACD/RSI/KDJ/布林带/ATR/OBV/VWAP 等指标
- **策略回测** — 事件驱动回测引擎，支持手续费/滑点/印花税，避免未来函数
- **多因子选股** — PE/PB/ROE/动量等因子筛选，自定义权重排序
- **信号推送** — 策略盘后自动扫描，通过企业微信/飞书/钉钉/邮件推送买卖信号
- **Web 面板** — Vue3 交互式界面，含 K 线图、回测报告、选股器

## 系统架构

```
┌──────────────────────────────────────────────────────┐
│                  浏览器 (Vue3 SPA)                     │
│  仪表盘 │ K线图 │ 选股器 │ 回测 │ 信号 │ 设置        │
└───────────────────────┬──────────────────────────────┘
                        │ HTTP / WebSocket
┌───────────────────────▼──────────────────────────────┐
│                FastAPI 后端 (REST API)                 │
│  /auth │ /stocks │ /data │ /backtest │ /screener     │
├──────────────────────────────────────────────────────┤
│  核心引擎层                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ 数据采集  │ │ 指标计算  │ │ 回测引擎  │ │ 策略库 │  │
│  │ AKShare  │ │ pandas   │ │ 事件驱动  │ │ MA/Mom │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘  │
├──────────────────────────────────────────────────────┤
│  存储层                                              │
│  SQLite (元数据/股票列表)  │  Parquet (K线时序数据)    │
└──────────────────────────────────────────────────────┘
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Element Plus + KLineCharts + ECharts |
| 后端 | FastAPI + SQLAlchemy + Pydantic v2 |
| 数据源 | AKShare (免费开源) |
| 存储 | SQLite + Parquet (PyArrow) |
| 认证 | JWT (python-jose) |
| 调度 | APScheduler |
| 日志 | loguru |

## 快速开始

### 系统要求

- Python 3.10+
- Node.js 18+
- 2GB+ 可用磁盘空间（存储行情数据）

### 安装

```bash
# 克隆项目
cd /path/to/quant-invest

# 后端
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 前端
cd frontend
npm install
cd ..

# 配置
cp .env.example .env
# 编辑 .env 修改 SECRET_KEY 和管理员密码
```

### 初始化数据

```bash
# 首次运行需拉取股票列表和历史数据（约需10分钟）
python -c "
from core.data.fetcher import AKShareFetcher
from core.data.storage import DataStorage
from core.data.updater import DataUpdater
storage = DataStorage()
storage.init_db()
updater = DataUpdater(AKShareFetcher(), storage)
updater.init_data()
"
```

### 启动

```bash
# 启动后端 (默认 http://localhost:8000)
python run.py

# 另一个终端，启动前端开发服务器 (默认 http://localhost:5173)
cd frontend
npm run dev
```

访问 http://localhost:5173 ，使用 admin / admin123 登录（生产环境请修改 .env）。

### 生产部署

```bash
# 构建前端
cd frontend && npm run build && cd ..

# 后端直接启动（前端静态文件可由 Nginx 托管）
python run.py --host 0.0.0.0 --port 8000
```

详细部署指南见 [DEPLOY.md](DEPLOY.md)。

## 配置说明

所有配置通过环境变量或 `.env` 文件管理：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| SECRET_KEY | JWT 签名密钥 | change-me-in-production |
| ADMIN_USERNAME | 管理员用户名 | admin |
| ADMIN_PASSWORD | 管理员密码 | admin123 |
| DATA_DIR | 数据存储目录 | ./data |
| DB_URL | 数据库连接 | sqlite:///./data/market.db |
| AKSHARE_RATE_LIMIT | AKShare 请求间隔(秒) | 0.5 |
| NOTIFY_WEBHOOK_URL | Webhook 通知地址 | - |
| NOTIFY_EMAIL_TO | 通知邮箱 | - |
| SMTP_HOST/PORT/USER/PASSWORD | SMTP 配置 | - |
| CORS_ORIGINS | CORS 允许域 | * |

## 目录结构

```
quant-invest/
├── api/                   # FastAPI 路由层
│   ├── auth.py            # JWT 认证
│   ├── schemas.py         # Pydantic 模型
│   ├── database.py        # 数据库连接
│   ├── dependencies.py    # 依赖注入
│   └── routes/            # API 路由
├── core/                  # 核心引擎
│   ├── data/              # 数据采集与存储
│   ├── indicators/        # 技术指标库
│   ├── backtest/          # 回测引擎
│   ├── strategy/          # 策略框架
│   └── signals/           # 信号生成与通知
├── frontend/              # Vue3 前端
├── config/                # 配置管理
├── data/                  # 运行时数据
├── deploy/                # 部署文件
├── tests/                 # 测试
└── docs/                  # 文档
```

## 内置策略

| 策略 | 说明 | 参数 |
|------|------|------|
| MA Cross | 双均线交叉 | fast_period(5), slow_period(20) |

自定义策略开发指南见 [docs/STRATEGY_GUIDE.md](docs/STRATEGY_GUIDE.md)。

## 路线图

- [x] 数据采集与存储
- [x] 技术指标库
- [x] 回测引擎
- [x] 双均线策略
- [x] 多因子选股
- [x] Web 管理面板
- [x] 信号通知推送
- [ ] 更多内置策略（布林突破、动量反转）
- [ ] 实盘交易对接（QMT/MiniQMT）
- [ ] 机器学习因子
- [ ] 组合优化（均值方差 / 风险平价）
- [ ] 多市场支持

## 安全注意

⚠️ 本系统仅供个人学习和研究使用。投资有风险，入市需谨慎。

- 生产环境务必修改 SECRET_KEY 和 ADMIN_PASSWORD
- 建议配置 HTTPS（参考 deploy/nginx.conf.example）
- 不要将 .env 文件提交到版本控制
- 自动交易功能风险极高，请充分测试后谨慎使用

## License

MIT
