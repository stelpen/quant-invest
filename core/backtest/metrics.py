"""Performance metrics for backtest evaluation.

Calculates standard portfolio metrics including returns, risk-adjusted
performance (Sharpe, Sortino, Calmar), drawdown statistics, and trade
statistics (win rate, profit/loss ratio).
"""

from typing import Any

import numpy as np
import pandas as pd

# Trading days per year for annualization
TRADING_DAYS_PER_YEAR = 252


def calculate_metrics(
    equity_curve: pd.Series,
    trades: list[Any],
    risk_free_rate: float = 0.03,
) -> dict[str, Any]:
    """Calculate a comprehensive set of backtest performance metrics.

    Handles edge cases gracefully:
        - Empty trade list: trade metrics returned as 0 or NaN.
        - Short equity curves: returns NaN for risk-adjusted metrics.
        - Zero or negative drawdowns: Calmar ratio handled with inf/NaN.
        - All losses or all wins: profit_loss_ratio handled with inf/NaN.

    Args:
        equity_curve: Time series of portfolio equity values (daily).
        trades: List of Trade objects from the backtest.
        risk_free_rate: Annual risk-free rate for Sharpe/Sortino (default 0.03).

    Returns:
        Dictionary with the following keys:
            - total_return: Total cumulative return as a fraction.
            - annual_return: Annualized return as a fraction.
            - sharpe_ratio: Risk-adjusted return (excess return / volatility).
            - sortino_ratio: Like Sharpe but uses downside deviation.
            - max_drawdown: Maximum peak-to-trough decline as a positive fraction.
            - max_drawdown_duration: Longest drawdown duration in days.
            - calmar_ratio: Annual return / max drawdown.
            - win_rate: Fraction of profitable round-trip trades.
            - profit_loss_ratio: Average win / average loss.
            - total_trades: Total number of trades executed.
            - avg_holding_days: Average holding period for round-trip trades.
    """
    metrics: dict[str, Any] = {
        "total_return": 0.0,
        "annual_return": 0.0,
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "max_drawdown": 0.0,
        "max_drawdown_duration": 0,
        "calmar_ratio": 0.0,
        "win_rate": 0.0,
        "profit_loss_ratio": 0.0,
        "total_trades": len(trades),
        "avg_holding_days": 0.0,
    }

    if equity_curve is None or equity_curve.empty or len(equity_curve) < 2:
        metrics["sharpe_ratio"] = float("nan")
        metrics["sortino_ratio"] = float("nan")
        metrics["max_drawdown"] = float("nan")
        metrics["max_drawdown_duration"] = 0
        metrics["calmar_ratio"] = float("nan")
        metrics["annual_return"] = float("nan")
        _calculate_trade_metrics(trades, metrics)
        return metrics

    equity = equity_curve.astype(float).dropna()

    initial_equity = equity.iloc[0]
    final_equity = equity.iloc[-1]

    if initial_equity <= 0:
        metrics["annual_return"] = float("nan")
        metrics["total_return"] = float("nan")
        metrics["sharpe_ratio"] = float("nan")
        metrics["sortino_ratio"] = float("nan")
        metrics["max_drawdown"] = float("nan")
        metrics["max_drawdown_duration"] = 0
        metrics["calmar_ratio"] = float("nan")
        _calculate_trade_metrics(trades, metrics)
        return metrics

    # Total return
    total_return = (final_equity - initial_equity) / initial_equity
    metrics["total_return"] = float(total_return)

    # Annualized return
    n_periods = len(equity)
    if n_periods > 1:
        years = n_periods / TRADING_DAYS_PER_YEAR
        if years > 0:
            if final_equity > 0 and initial_equity > 0:
                annual_return = (final_equity / initial_equity) ** (1.0 / years) - 1.0
            else:
                annual_return = float("nan")
        else:
            annual_return = float("nan")
    else:
        annual_return = float("nan")
    metrics["annual_return"] = float(annual_return)

    # Daily returns
    daily_returns = equity.pct_change().dropna()

    if len(daily_returns) < 2:
        metrics["sharpe_ratio"] = float("nan")
        metrics["sortino_ratio"] = float("nan")
    else:
        # Sharpe ratio: (annual_return - risk_free_rate) / annual_volatility
        daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
        excess_returns = daily_returns - daily_rf

        annual_vol = float(daily_returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))
        if annual_vol > 0 and not np.isnan(annual_return):
            sharpe = (annual_return - risk_free_rate) / annual_vol
            metrics["sharpe_ratio"] = float(sharpe)
        else:
            metrics["sharpe_ratio"] = float("nan")

        # Sortino ratio: uses downside deviation only
        downside_returns = excess_returns.copy()
        downside_returns[downside_returns > 0] = 0.0
        downside_dev = float(
            np.sqrt((downside_returns ** 2).mean()) * np.sqrt(TRADING_DAYS_PER_YEAR)
        )
        if downside_dev > 0 and not np.isnan(annual_return):
            sortino = (annual_return - risk_free_rate) / downside_dev
            metrics["sortino_ratio"] = float(sortino)
        else:
            metrics["sortino_ratio"] = float("nan")

    # Maximum drawdown and duration
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    max_dd = float(drawdown.min())  # Negative value
    metrics["max_drawdown"] = abs(max_dd) if not np.isnan(max_dd) else float("nan")

    # Max drawdown duration in days
    in_drawdown = drawdown < 0
    if in_drawdown.any():
        duration = _max_consecutive_true(in_drawdown.values)
        metrics["max_drawdown_duration"] = int(duration)
    else:
        metrics["max_drawdown_duration"] = 0

    # Calmar ratio: annual_return / |max_drawdown|
    if not np.isnan(annual_return) and max_dd < 0:
        metrics["calmar_ratio"] = float(annual_return / abs(max_dd))
    else:
        metrics["calmar_ratio"] = float("nan")

    # Trade-based metrics
    _calculate_trade_metrics(trades, metrics)

    return metrics


def _calculate_trade_metrics(
    trades: list[Any], metrics: dict[str, Any]
) -> None:
    """Calculate win rate, profit/loss ratio, and average holding days.

    Pairs buy trades with subsequent sell trades to form round-trip trades.
    Holding period is measured in days between paired trades.

    Args:
        trades: List of Trade objects.
        metrics: Metrics dictionary to update in place.
    """
    if not trades:
        return

    round_trips = _pair_round_trips(trades)

    if not round_trips:
        metrics["total_trades"] = len(trades)
        metrics["avg_holding_days"] = float("nan")
        metrics["win_rate"] = float("nan")
        metrics["profit_loss_ratio"] = float("nan")
        return

    profits = [p["pnl"] for p in round_trips]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]

    # Win rate
    if round_trips:
        metrics["win_rate"] = float(len(wins) / len(round_trips))
    else:
        metrics["win_rate"] = 0.0

    # Profit/loss ratio
    if wins and losses:
        avg_win = float(np.mean(wins))
        avg_loss = float(abs(np.mean(losses)))
        metrics["profit_loss_ratio"] = avg_win / avg_loss if avg_loss > 0 else float("nan")
    elif wins and not losses:
        metrics["profit_loss_ratio"] = float("inf")
    else:
        metrics["profit_loss_ratio"] = 0.0

    # Average holding days
    holding_days = [p["holding_days"] for p in round_trips]
    if holding_days:
        metrics["avg_holding_days"] = float(np.mean(holding_days))
    else:
        metrics["avg_holding_days"] = 0.0

    metrics["total_trades"] = len(trades)


def _pair_round_trips(trades: list[Any]) -> list[dict[str, Any]]:
    """Pair buy and sell trades into round-trip trade records.

    Uses FIFO matching: the earliest open buy is matched against the next sell.

    Args:
        trades: List of Trade objects with date, direction, price, quantity.

    Returns:
        List of dicts with keys: pnl, holding_days.
    """
    round_trips: list[dict[str, Any]] = []
    open_buys: list[dict[str, Any]] = []

    for trade in trades:
        direction = getattr(trade, "direction", None)
        price = getattr(trade, "price", 0.0)
        quantity = getattr(trade, "quantity", 0)
        trade_date = getattr(trade, "date", None)

        if direction == "buy":
            open_buys.append(
                {"price": price, "quantity": quantity, "date": trade_date}
            )
        elif direction == "sell" and open_buys:
            # FIFO: match against earliest open buy
            buy = open_buys.pop(0)
            matched_qty = min(buy["quantity"], quantity)

            pnl = (price - buy["price"]) * matched_qty

            holding_days = 0.0
            if buy["date"] is not None and trade_date is not None:
                try:
                    holding_days = abs((trade_date - buy["date"]).days)
                except (TypeError, AttributeError):
                    holding_days = 0.0

            round_trips.append({"pnl": pnl, "holding_days": holding_days})

            # If sell quantity exceeds buy quantity, leftover is unused
            # If buy quantity exceeds sell, put remainder back
            if buy["quantity"] > matched_qty:
                open_buys.insert(
                    0,
                    {
                        "price": buy["price"],
                        "quantity": buy["quantity"] - matched_qty,
                        "date": buy["date"],
                    },
                )

    return round_trips


def _max_consecutive_true(arr: np.ndarray) -> int:
    """Find the longest run of consecutive True values in a boolean array.

    Args:
        arr: Boolean numpy array.

    Returns:
        Length of the longest consecutive True run.
    """
    if len(arr) == 0:
        return 0

    max_run = 0
    current_run = 0
    for value in arr:
        if value:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0
    return max_run