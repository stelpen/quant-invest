# 策略开发指南

## 策略基类

所有策略继承 `core.strategy.base.Strategy`，需实现两个抽象成员：

```python
from core.strategy.base import Strategy
import pandas as pd
from typing import Any


class MyStrategy(Strategy):

    @property
    def name(self) -> str:
        """策略名称，用于展示和日志。"""
        return "My Strategy"

    def on_bar(
        self,
        index: int,
        row: pd.Series,
        data: pd.DataFrame,
        portfolio: Any,
    ) -> None:
        """每根 K 线调用一次，在此实现买卖逻辑。"""
        ...

    def get_params(self) -> dict[str, Any]:
        """（可选）暴露可调参数。"""
        return {}
```

## on_bar 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| index | int | 当前 bar 在 data 中的整数位置 |
| row | pd.Series | 当前 bar，含 open/high/low/close/volume |
| data | pd.DataFrame | 完整历史数据（可用于计算指标） |
| portfolio | Portfolio | 组合对象，用 buy/sell 下单 |

## Portfolio 接口

```python
# 买入
portfolio.buy(symbol, price, quantity, date) -> bool

# 卖出
portfolio.sell(symbol, price, quantity, date) -> bool

# 查询持仓
position = portfolio.get_position(symbol)  # 返回 Position 或 None
if position:
    print(position.quantity, position.avg_cost)

# 可用现金
cash = portfolio.cash
```

## 完整示例：RSI 超买超卖策略

```python
from typing import Any
import pandas as pd
from core.strategy.base import Strategy
from core.indicators.momentum import rsi


class RSIStrategy(Strategy):
    """RSI < 30 买入，RSI > 70 卖出。"""

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    @property
    def name(self) -> str:
        return f"RSI ({self.period})"

    def get_params(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "oversold": self.oversold,
            "overbought": self.overbought,
        }

    def on_bar(self, index, row, data, portfolio):
        # 需要足够数据计算 RSI
        if index < self.period:
            return

        window = data["close"].iloc[: index + 1]
        rsi_val = rsi(window, self.period).iloc[-1]

        if pd.isna(rsi_val):
            return

        symbol = data.attrs.get("symbol", "UNKNOWN")
        price = float(row["close"])
        bar_date = data.index[index]

        position = portfolio.get_position(symbol)

        # 超卖买入
        if rsi_val < self.oversold and position is None:
            qty = (int(portfolio.cash / price) // 100) * 100
            if qty > 0:
                portfolio.buy(symbol, price, qty, bar_date)

        # 超买卖出
        elif rsi_val > self.overbought and position is not None:
            portfolio.sell(symbol, price, position.quantity, bar_date)
```

## 注册策略

在 `api/routes/backtest.py` 中注册以便前端调用：

```python
AVAILABLE_STRATEGIES = {
    "ma_cross": {...},
    "rsi": {
        "name": "RSI 超买超卖",
        "description": "RSI<30 买入, RSI>70 卖出",
        "params": {"period": 14, "oversold": 30, "overbought": 70},
    },
}

def _build_strategy(name: str, params: dict):
    if name == "ma_cross":
        ...
    elif name == "rsi":
        from core.strategy.rsi import RSIStrategy
        return RSIStrategy(
            period=params.get("period", 14),
            oversold=params.get("oversold", 30),
            overbought=params.get("overbought", 70),
        )
```

## 最佳实践

1. **避免未来函数** - 只使用 `data.iloc[:index+1]` 范围内的数据，不要用未来的 bar
2. **检查数据充足性** - 计算指标前确认 `index` 足够大
3. **处理 NaN** - 指标在初期会返回 NaN，需 `pd.isna()` 检查
4. **仓位管理** - A 股按 100 股整数倍下单
5. **异常隔离** - on_bar 抛异常会被引擎捕获，但应尽量避免

## 回测验证

```python
from core.backtest.portfolio import Portfolio
from core.backtest.metrics import calculate_metrics
import pandas as pd

# 加载数据
df = storage.load_daily_kline("000001.SZ", "20200101", "20241231")
df = df.set_index("date")
df.attrs["symbol"] = "000001.SZ"

# 运行
strategy = RSIStrategy()
portfolio = Portfolio(initial_capital=1_000_000)
equity = {}
for idx in range(len(df)):
    row = df.iloc[idx]
    strategy.on_bar(idx, row, df, portfolio)
    equity[df.index[idx]] = portfolio.get_equity({"000001.SZ": row["close"]})

# 评估
metrics = calculate_metrics(pd.Series(equity), portfolio.trade_history)
print(metrics)
```
