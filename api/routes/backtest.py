"""Backtest routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from api.auth import get_current_user
from api.dependencies import get_storage
from api.schemas import (
    BacktestRequest,
    BacktestResponse,
    EquityPoint,
    StrategyInfo,
    TradeRecord,
)

router = APIRouter(prefix="/api/backtest", tags=["回测"])


AVAILABLE_STRATEGIES = {
    "ma_cross": {
        "name": "MA Cross (双均线交叉)",
        "description": "快速 EMA 上穿慢速 EMA 买入，下穿卖出",
        "params": {"fast_period": 5, "slow_period": 20},
    },
}


@router.get("/strategies", response_model=list[StrategyInfo])
async def list_strategies(_user: dict = Depends(get_current_user)):
    """列出所有可用回测策略及其参数。"""
    return [
        StrategyInfo(name=k, description=v["description"], params=v["params"])
        for k, v in AVAILABLE_STRATEGIES.items()
    ]


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest,
    _user: dict = Depends(get_current_user),
):
    """运行策略回测。

    使用 Portfolio + Strategy 手动迭代方式（兼容策略基类接口）。
    """
    if request.strategy not in AVAILABLE_STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的策略: {request.strategy}. "
                   f"可选: {list(AVAILABLE_STRATEGIES.keys())}",
        )

    storage = get_storage()
    df = storage.load_daily_kline(request.symbol, request.start_date, request.end_date)
    if df.empty:
        # 尝试从远程拉取
        from api.dependencies import get_fetcher
        df = get_fetcher().get_daily_kline(
            request.symbol, request.start_date, request.end_date
        )
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"未找到 {request.symbol} 的数据")
        storage.save_daily_kline(request.symbol, df)

    if len(df) < 30:
        raise HTTPException(status_code=400, detail="数据不足（至少需要30根K线）")

    # 确保日期索引，并记录 symbol 供策略解析
    if "date" in df.columns:
        df = df.set_index("date")
    df.attrs["symbol"] = request.symbol

    # 创建策略
    strategy = _build_strategy(request.strategy, request.params)

    # 使用 Portfolio 运行回测
    from core.backtest.portfolio import Portfolio
    from core.backtest.metrics import calculate_metrics

    portfolio = Portfolio(
        initial_capital=request.initial_capital,
        commission_rate=0.0003,
        stamp_tax=0.001,
    )

    equity_curve = {}
    for idx in range(len(df)):
        row = df.iloc[idx]
        bar_date = df.index[idx]
        try:
            strategy.on_bar(idx, row, df, portfolio)
        except Exception as e:
            logger.debug(f"Strategy error at bar {idx}: {e}")

        equity = portfolio.get_equity({request.symbol: row["close"]})
        equity_curve[bar_date] = equity

    # 构建结果
    import pandas as pd
    equity_series = pd.Series(equity_curve, dtype=float)

    metrics = calculate_metrics(equity_series, portfolio.trade_history)

    # 格式化输出
    equity_points = [
        EquityPoint(date=str(d), equity=float(v))
        for d, v in equity_curve.items()
    ]

    trades = [
        TradeRecord(
            date=str(t.date),
            symbol=t.symbol,
            direction=t.direction,
            price=t.price,
            quantity=t.quantity,
            commission=t.commission,
        )
        for t in portfolio.trade_history
    ]

    return BacktestResponse(
        metrics=metrics,
        equity_curve=equity_points,
        trades=trades,
    )


def _build_strategy(name: str, params: dict):
    """Build a strategy instance from name and params."""
    if name == "ma_cross":
        from core.strategy.ma_cross import MACrossStrategy
        fast = params.get("fast_period", 5)
        slow = params.get("slow_period", 20)
        return MACrossStrategy(fast_period=fast, slow_period=slow)
    raise HTTPException(status_code=400, detail=f"未知策略: {name}")
