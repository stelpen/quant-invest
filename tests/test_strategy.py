"""Strategy tests."""

import numpy as np
import pandas as pd
import pytest
from datetime import date

from core.strategy.base import Strategy
from core.strategy.ma_cross import MACrossStrategy
from core.backtest.portfolio import Portfolio


def test_strategy_is_abstract():
    """Strategy base class cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Strategy()  # type: ignore


def test_ma_cross_init():
    """MACrossStrategy initializes with valid params."""
    s = MACrossStrategy(fast_period=5, slow_period=20)
    assert s.fast_period == 5
    assert s.slow_period == 20
    assert "5" in s.name and "20" in s.name


def test_ma_cross_invalid_params():
    """MACrossStrategy rejects invalid period combinations."""
    with pytest.raises(ValueError):
        MACrossStrategy(fast_period=20, slow_period=5)  # fast >= slow
    with pytest.raises(ValueError):
        MACrossStrategy(fast_period=0, slow_period=20)  # non-positive


def test_ma_cross_get_params():
    """get_params returns the configured parameters."""
    s = MACrossStrategy(fast_period=10, slow_period=30)
    params = s.get_params()
    assert params["fast_period"] == 10
    assert params["slow_period"] == 30


def test_ma_cross_generates_trades():
    """MACrossStrategy generates trades on trending data."""
    # Create data with a clear uptrend then downtrend
    n = 100
    up = np.linspace(10, 20, 50)
    down = np.linspace(20, 10, 50)
    close = np.concatenate([up, down])
    df = pd.DataFrame({
        "open": close,
        "high": close + 0.1,
        "low": close - 0.1,
        "close": close,
        "volume": np.full(n, 100000.0),
    }, index=pd.date_range("2020-01-01", periods=n, name="date"))
    df.attrs["symbol"] = "TEST"

    strategy = MACrossStrategy(fast_period=5, slow_period=20)
    portfolio = Portfolio(initial_capital=1_000_000)

    for idx in range(len(df)):
        row = df.iloc[idx]
        strategy.on_bar(idx, row, df, portfolio)

    # Should have generated at least one trade over the trend reversal
    assert len(portfolio.trade_history) >= 1
