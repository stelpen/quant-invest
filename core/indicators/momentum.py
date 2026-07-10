"""Momentum indicators.

Provides MACD, RSI, and KDJ oscillator calculations for trend and
momentum analysis.
"""

import pandas as pd


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Moving Average Convergence Divergence (MACD).

    Args:
        close: Closing price series.
        fast: Period for the fast EMA (default 12).
        slow: Period for the slow EMA (default 26).
        signal: Period for the signal line EMA (default 9).

    Returns:
        A tuple of (DIF, DEA, MACD_histogram):
            - DIF: Difference between fast and slow EMA.
            - DEA: Signal line (EMA of DIF).
            - MACD_histogram: 2 * (DIF - DEA), bar chart values.

    Raises:
        ValueError: If any period is less than 1 or close is empty.
    """
    if close.empty:
        raise ValueError("Input series must not be empty.")
    if fast < 1 or slow < 1 or signal < 1:
        raise ValueError("All period parameters must be >= 1.")
    if fast >= slow:
        raise ValueError(
            f"Fast period ({fast}) must be less than slow period ({slow})."
        )

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_hist = 2.0 * (dif - dea)

    return dif, dea, macd_hist


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI).

    Uses Wilder's smoothing method (exponential moving average with
    alpha = 1/period) for average gain and average loss calculations.

    Args:
        close: Closing price series.
        period: Lookback period for RSI calculation (default 14).

    Returns:
        A pandas Series with RSI values ranging from 0 to 100.

    Raises:
        ValueError: If period is less than 1 or close is empty.
    """
    if close.empty:
        raise ValueError("Input series must not be empty.")
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}.")

    delta = close.diff()

    gains = delta.clip(lower=0.0)
    losses = (-delta).clip(lower=0.0)

    # Wilder's smoothing: alpha = 1/period
    avg_gain = gains.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi_values = 100.0 - (100.0 / (1.0 + rs))

    return rsi_values


def kdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate KDJ stochastic oscillator.

    Commonly used in A-share markets. RSV is smoothed into K and D lines
    using an exponential-like SMA smoothing, and J is derived from K and D.

    Args:
        high: High price series.
        low: Low price series.
        close: Closing price series.
        n: Lookback period for highest high / lowest low (default 9).
        m1: Smoothing period for K line (default 3).
        m2: Smoothing period for D line (default 3).

    Returns:
        A tuple of (K, D, J):
            - K: Fast stochastic line.
            - D: Slow stochastic line (smoothed K).
            - J: 3*K - 2*D, indicating overbought/oversold extremes.

    Raises:
        ValueError: If any period is less than 1 or input series are empty.
    """
    if close.empty or high.empty or low.empty:
        raise ValueError("Input series must not be empty.")
    if n < 1 or m1 < 1 or m2 < 1:
        raise ValueError("All period parameters must be >= 1.")

    lowest_low = low.rolling(window=n, min_periods=n).min()
    highest_high = high.rolling(window=n, min_periods=n).max()

    # RSV: Raw Stochastic Value (0-100 scale)
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100.0
    # Handle division by zero when highest_high == lowest_low
    rsv = rsv.fillna(50.0)

    # SMA-style smoothing: K(t) = (m1-1)/m1 * K(t-1) + 1/m1 * RSV(t)
    # This is equivalent to ewm with alpha = 1/m1
    k_values = rsv.ewm(alpha=1.0 / m1, adjust=False).mean()
    d_values = k_values.ewm(alpha=1.0 / m2, adjust=False).mean()
    j_values = 3.0 * k_values - 2.0 * d_values

    return k_values, d_values, j_values
