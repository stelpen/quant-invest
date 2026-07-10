"""Moving-average crossover strategy.

A classic trend-following strategy: go long when a fast exponential moving
average (EMA) crosses above a slow EMA (golden cross) and exit when the fast
EMA crosses back below the slow EMA (death cross).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from loguru import logger

from core.indicators.ma import ema

from .base import Strategy


class MACrossStrategy(Strategy):
    """Exponential moving-average crossover strategy.

    Generates a *buy* when the fast EMA crosses above the slow EMA and a
    *sell* when the fast EMA crosses below the slow EMA. Crossovers are
    detected by comparing the fast-vs-slow relationship on the current bar
    with the previous bar, so a signal fires only on the transition.

    Args:
        fast_period: Span of the fast EMA (default 5).
        slow_period: Span of the slow EMA (default 20).

    Raises:
        ValueError: If ``fast_period`` or ``slow_period`` is not positive,
            or if ``fast_period`` is not strictly less than ``slow_period``.
    """

    def __init__(self, fast_period: int = 5, slow_period: int = 20) -> None:
        if fast_period <= 0 or slow_period <= 0:
            raise ValueError("Periods must be positive integers.")
        if fast_period >= slow_period:
            raise ValueError(
                f"fast_period ({fast_period}) must be < slow_period ({slow_period})."
            )

        self.fast_period = fast_period
        self.slow_period = slow_period

    @property
    def name(self) -> str:
        """Human-readable strategy name including its periods."""
        return f"MA Cross ({self.fast_period}/{self.slow_period})"

    def get_params(self) -> dict[str, Any]:
        """Return the configurable parameters for this strategy."""
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
        }

    def on_bar(
        self,
        index: int,
        row: pd.Series,
        data: pd.DataFrame,
        portfolio: Any,
    ) -> None:
        """Evaluate the crossover condition for the current bar.

        Computes the fast and slow EMA over the close prices up to and
        including the current bar, then places an order through
        ``portfolio`` when a crossover is detected.

        Args:
            index: Integer position of the current bar in ``data``.
            row: Current bar as a :class:`pandas.Series` (needs a ``close``
                field; a ``symbol`` field is used when present).
            data: Full historical price frame with a ``close`` column.
            portfolio: Executing portfolio / engine exposing ``buy`` and
                ``sell`` methods.
        """
        # Need at least slow_period + 1 bars to detect a crossover.
        if index < self.slow_period:
            return

        window = data["close"].iloc[: index + 1]
        fast_ema = ema(window, self.fast_period)
        slow_ema = ema(window, self.slow_period)

        fast_now, fast_prev = fast_ema.iloc[-1], fast_ema.iloc[-2]
        slow_now, slow_prev = slow_ema.iloc[-1], slow_ema.iloc[-2]

        if pd.isna(fast_prev) or pd.isna(slow_prev):
            return

        symbol = self._resolve_symbol(row, data)
        price = float(row["close"])
        bar_date = self._resolve_date(index, row, data)

        crossed_up = fast_prev <= slow_prev and fast_now > slow_now
        crossed_down = fast_prev >= slow_prev and fast_now < slow_now

        if crossed_up:
            self._buy(portfolio, symbol, price, bar_date)
        elif crossed_down:
            self._sell(portfolio, symbol, price, bar_date)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _buy(self, portfolio: Any, symbol: str, price: float, bar_date: Any) -> None:
        """Submit a buy order, sizing to affordable lots of 100 shares."""
        cash = getattr(portfolio, "cash", 0.0)
        if price <= 0 or cash <= 0:
            return
        quantity = (int(cash / price) // 100) * 100
        if quantity <= 0:
            logger.debug(f"{self.name}: insufficient cash to buy {symbol}.")
            return
        try:
            portfolio.buy(symbol, price, quantity, bar_date)
        except Exception as exc:  # noqa: BLE001 - strategy must not crash loop
            logger.error(f"{self.name}: buy {symbol} failed: {exc}")

    def _sell(self, portfolio: Any, symbol: str, price: float, bar_date: Any) -> None:
        """Submit a sell order liquidating the full existing position."""
        get_position = getattr(portfolio, "get_position", None)
        if not callable(get_position):
            return
        position = get_position(symbol)
        if position is None or getattr(position, "quantity", 0) <= 0:
            return
        try:
            portfolio.sell(symbol, price, position.quantity, bar_date)
        except Exception as exc:  # noqa: BLE001 - strategy must not crash loop
            logger.error(f"{self.name}: sell {symbol} failed: {exc}")

    @staticmethod
    def _resolve_symbol(row: pd.Series, data: pd.DataFrame) -> str:
        """Best-effort extraction of the traded symbol."""
        for source in (row, data.attrs):
            try:
                value = source.get("symbol")  # type: ignore[union-attr]
            except AttributeError:
                value = None
            if value:
                return str(value)
        return "UNKNOWN"

    @staticmethod
    def _resolve_date(index: int, row: pd.Series, data: pd.DataFrame) -> Any:
        """Best-effort extraction of the bar's date/timestamp."""
        name = getattr(row, "name", None)
        if name is not None:
            return name
        try:
            return data.index[index]
        except (IndexError, KeyError):
            return None