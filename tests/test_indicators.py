"""Tests for technical indicators."""

import numpy as np
import pandas as pd
import pytest

from core.indicators.ma import sma, ema, wma
from core.indicators.momentum import macd, rsi, kdj
from core.indicators.volatility import bollinger_bands, atr
from core.indicators.volume import obv, vwap


class TestMA:
    """Moving average tests."""

    def test_sma_basic(self):
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
        result = sma(data, 3)
        assert len(result) == len(data)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert result.iloc[2] == pytest.approx(2.0)
        assert result.iloc[3] == pytest.approx(3.0)
        assert result.iloc[9] == pytest.approx(9.0)

    def test_ema_basic(self):
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
        result = ema(data, 3)
        assert len(result) == len(data)
        # EMA should follow the trend upward
        assert result.iloc[-1] > result.iloc[-2]

    def test_wma_basic(self):
        data = pd.Series([1, 2, 3, 4, 5], dtype=float)
        result = wma(data, 3)
        assert len(result) == len(data)
        # WMA(3) at index 2: (1*1 + 2*2 + 3*3) / (1+2+3) = 14/6
        assert result.iloc[2] == pytest.approx(14 / 6, rel=1e-4)

    def test_sma_single_period(self):
        data = pd.Series([5, 10, 15], dtype=float)
        result = sma(data, 1)
        # SMA with period 1 = the data itself
        pd.testing.assert_series_equal(result, data, check_names=False)


class TestMomentum:
    """Momentum indicator tests."""

    @pytest.fixture
    def price_data(self):
        np.random.seed(42)
        return pd.Series(
            100 + np.cumsum(np.random.randn(100) * 2), dtype=float
        )

    def test_macd_output_shapes(self, price_data):
        dif, dea, hist = macd(price_data)
        assert len(dif) == len(price_data)
        assert len(dea) == len(price_data)
        assert len(hist) == len(price_data)

    def test_macd_histogram(self, price_data):
        dif, dea, hist = macd(price_data)
        # MACD histogram = (DIF - DEA) * 2
        valid = ~(dif.isna() | dea.isna())
        expected = (dif[valid] - dea[valid]) * 2
        pd.testing.assert_series_equal(hist[valid], expected, check_names=False)

    def test_rsi_range(self, price_data):
        result = rsi(price_data)
        valid = result.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_kdj_output(self, price_data):
        high = price_data + 2
        low = price_data - 2
        k, d, j = kdj(high, low, price_data)
        assert len(k) == len(price_data)
        assert len(d) == len(price_data)
        assert len(j) == len(price_data)


class TestVolatility:
    """Volatility indicator tests."""

    @pytest.fixture
    def ohlcv(self):
        np.random.seed(42)
        close = pd.Series(100 + np.cumsum(np.random.randn(50) * 2), dtype=float)
        high = close + abs(np.random.randn(50))
        low = close - abs(np.random.randn(50))
        return high, low, close

    def test_bollinger_bands(self, ohlcv):
        _, _, close = ohlcv
        upper, mid, lower = bollinger_bands(close, 20, 2)
        assert len(upper) == len(close)
        valid = ~upper.isna()
        assert (upper[valid] >= mid[valid]).all()
        assert (mid[valid] >= lower[valid]).all()

    def test_atr_positive(self, ohlcv):
        high, low, close = ohlcv
        result = atr(high, low, close, 14)
        valid = result.dropna()
        assert (valid >= 0).all()


class TestVolume:
    """Volume indicator tests."""

    def test_obv_direction(self):
        close = pd.Series([10, 11, 10.5, 12, 11.5], dtype=float)
        volume = pd.Series([100, 200, 150, 300, 100], dtype=float)
        result = obv(close, volume)
        assert len(result) == len(close)
        # When price goes up, OBV adds volume
        assert result.iloc[1] > result.iloc[0]

    def test_vwap_basic(self):
        high = pd.Series([11, 12, 13], dtype=float)
        low = pd.Series([9, 10, 11], dtype=float)
        close = pd.Series([10, 11, 12], dtype=float)
        volume = pd.Series([100, 200, 150], dtype=float)
        result = vwap(high, low, close, volume)
        assert len(result) == len(close)
        assert result.iloc[-1] > 0
