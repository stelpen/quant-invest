"""Volatility indicators.

Provides Bollinger Bands and Average True Range calculations for
measuring market volatility.
"""

import pandas as pd


def bollinger_bands(
    close: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands.

    Bollinger Bands consist of a middle band (SMA) and upper/lower bands
    placed a specified number of standard deviations away from the middle.

    Args:
        close: Closing price series.
        period: Lookback period for SMA and standard deviation (default 20).
        std_dev: Number of standard deviations for band width (default 2.0).

    Returns:
        A tuple of (upper, middle, lower):
            - upper: Middle band + std_dev * rolling standard deviation.
            - middle: Simple moving average of close.
            - lower: Middle band - std_dev * rolling standard deviation.

    Raises:
        ValueError: If period is less than 1, std_dev is negative, or
            close is empty.
    """
    if close.empty:
        raise ValueError("Input series must not be empty.")
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}.")
    if std_dev < 0:
        raise ValueError(f"std_dev must be >= 0, got {std_dev}.")

    middle = close.rolling(window=period, min_periods=period).mean()
    rolling_std = close.rolling(window=period, min_periods=period).std(ddof=0)

    upper = middle + std_dev * rolling_std
    lower = middle - std_dev * rolling_std

    return upper, middle, lower


def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Calculate Average True Range (ATR).

    True Range is the greatest of:
        - Current high minus current low
        - Absolute value of current high minus previous close
        - Absolute value of current low minus previous close

    ATR is smoothed using Wilder's method (EMA with alpha = 1/period).

    Args:
        high: High price series.
        low: Low price series.
        close: Closing price series.
        period: Smoothing period for ATR (default 14).

    Returns:
        A pandas Series containing ATR values.

    Raises:
        ValueError: If period is less than 1 or any input series is empty.
    """
    if close.empty or high.empty or low.empty:
        raise ValueError("Input series must not be empty.")
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}.")

    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Wilder's smoothing: alpha = 1/period
    atr_values = true_range.ewm(
        alpha=1.0 / period, min_periods=period, adjust=False
    ).mean()

    return atr_values
