"""Backtest engine tests."""

import numpy as np
import pandas as pd
import pytest
from datetime import date

from core.backtest.portfolio import Portfolio
from core.backtest.metrics import calculate_metrics


def make_ohlcv(n=100, seed=42):
    """Generate synthetic OHLCV data."""
    np.random.seed(seed)
    close = 10 + np.cumsum(np.random.randn(n) * 0.1)
    return pd.DataFrame({
        "open": close + np.random.randn(n) * 0.05,
        "high": close + abs(np.random.randn(n) * 0.2),
        "low": close - abs(np.random.randn(n) * 0.2),
        "close": close,
        "volume": np.random.randint(100000, 1000000, n).astype(float),
    }, index=pd.date_range("2020-01-01", periods=n, name="date"))


def test_portfolio_buy_sell():
    """Test basic buy and sell operations."""
    p = Portfolio(initial_capital=100_000)
    ok = p.buy("000001.SZ", price=10.0, quantity=1000, date=date(2024, 1, 1))
    assert ok
    assert p.cash == pytest.approx(100_000 - 10_000 - 3.0, rel=1e-3)
    assert p.get_position("000001.SZ") is not None

    ok = p.sell("000001.SZ", price=11.0, quantity=1000, date=date(2024, 1, 2))
    assert ok
    assert p.get_position("000001.SZ") is None
    assert p.cash > 100_000  # profit


def test_portfolio_buy_insufficient_cash():
    """Test buy with insufficient cash returns False."""
    p = Portfolio(initial_capital=100)
    ok = p.buy("000001.SZ", price=10.0, quantity=1000, date=date(2024, 1, 1))
    assert not ok


def test_calculate_metrics_basic():
    """Test metrics calculation on synthetic equity curve."""
    dates = pd.date_range("2020-01-01", periods=100, name="date")
    # Equity grows from 1M to 1.2M
    equity = pd.Series(
        np.linspace(1_000_000, 1_200_000, 100), index=dates
    )

    metrics = calculate_metrics(equity, [])
    assert "total_return" in metrics
    assert "annual_return" in metrics
    assert "sharpe_ratio" in metrics
    assert "max_drawdown" in metrics
    assert metrics["total_return"] > 0
    assert metrics["max_drawdown"] >= 0  # Drawdown stored as positive fraction


def test_calculate_metrics_with_trades():
    """Test metrics with trade history."""
    from core.backtest.portfolio import Trade
    dates = pd.date_range("2020-01-01", periods=100, name="date")
    equity = pd.Series(
        np.linspace(1_000_000, 1_100_000, 100), index=dates
    )
    trades = [
        Trade(date=date(2020, 2, 1), symbol="X", direction="buy",
              price=10.0, quantity=1000, commission=3.0),
        Trade(date=date(2020, 3, 1), symbol="X", direction="sell",
              price=11.0, quantity=1000, commission=3.3, stamp_tax=11.0),
    ]
    metrics = calculate_metrics(equity, trades)
    assert metrics["total_trades"] == 2
