"""Moving average indicators.

Provides Simple, Exponential, and Weighted Moving Average calculations.
All functions accept a pandas Series and return a pandas Series of the same length.
"""

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average.

    Args:
        series: Input price series.
        period: Number of periods for the moving average window.

    Returns:
        A pandas Series containing the SMA values. The first (period - 1)
        values will be NaN.

    Raises:
        ValueError: If period is less than 1 or series is empty.
    """
    if series.empty:
        raise ValueError("Input series must not be empty.")
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}.")

    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average.

    Uses the exponentially weighted moving average with span equal to the
    specified period. The smoothing factor alpha = 2 / (period + 1).

    Args:
        series: Input price series.
        period: Span for the EMA calculation.

    Returns:
        A pandas Series containing the EMA values.

    Raises:
        ValueError: If period is less than 1 or series is empty.
    """
    if series.empty:
        raise ValueError("Input series must not be empty.")
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}.")

    return series.ewm(span=period, adjust=False).mean()


def wma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Weighted Moving Average.

    Assigns linearly increasing weights from 1 (oldest) to period (newest).
    Weight for position i in the window is (i + 1), so the most recent
    observation has the highest weight.

    Args:
        series: Input price series.
        period: Number of periods for the weighted window.

    Returns:
        A pandas Series containing the WMA values. The first (period - 1)
        values will be NaN.

    Raises:
        ValueError: If period is less than 1 or series is empty.
    """
    if series.empty:
        raise ValueError("Input series must not be empty.")
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}.")

    weights = np.arange(1, period + 1, dtype=np.float64)
    weight_sum = weights.sum()

    def _weighted_mean(window: np.ndarray) -> float:
        return np.dot(window, weights) / weight_sum

    return series.rolling(window=period, min_periods=period).apply(
        _weighted_mean, raw=True
    )
