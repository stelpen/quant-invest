"""Volume-based indicators.

Provides On-Balance Volume (OBV) and Volume Weighted Average Price (VWAP)
calculations for analyzing volume-price relationships.
"""

import numpy as np
import pandas as pd


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Calculate On-Balance Volume (OBV).

    OBV accumulates volume based on price direction:
        - If close > previous close: OBV += volume
        - If close < previous close: OBV -= volume
        - If close == previous close: OBV unchanged

    Args:
        close: Closing price series.
        volume: Trading volume series.

    Returns:
        A pandas Series containing cumulative OBV values.

    Raises:
        ValueError: If close or volume is empty, or lengths do not match.
    """
    if close.empty or volume.empty:
        raise ValueError("Input series must not be empty.")
    if len(close) != len(volume):
        raise ValueError(
            f"Series length mismatch: close ({len(close)}) vs volume ({len(volume)})."
        )

    direction = np.sign(close.diff())
    # First value has no previous close; set direction to 0
    direction.iloc[0] = 0.0

    obv_values = (direction * volume).cumsum()

    return obv_values


def vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """Calculate Volume Weighted Average Price (VWAP).

    VWAP is calculated as the cumulative sum of (typical price * volume)
    divided by cumulative volume. Typical price = (high + low + close) / 3.

    Note: This implementation computes a running VWAP from the start of the
    series. For intraday VWAP that resets daily, pre-filter data by session.

    Args:
        high: High price series.
        low: Low price series.
        close: Closing price series.
        volume: Trading volume series.

    Returns:
        A pandas Series containing VWAP values.

    Raises:
        ValueError: If any input series is empty or lengths do not match.
    """
    if close.empty or high.empty or low.empty or volume.empty:
        raise ValueError("Input series must not be empty.")
    lengths = {len(high), len(low), len(close), len(volume)}
    if len(lengths) > 1:
        raise ValueError("All input series must have the same length.")

    typical_price = (high + low + close) / 3.0
    cumulative_tp_volume = (typical_price * volume).cumsum()
    cumulative_volume = volume.cumsum()

    # Avoid division by zero where cumulative volume is 0
    vwap_values = cumulative_tp_volume / cumulative_volume.replace(0, np.nan)

    return vwap_values
