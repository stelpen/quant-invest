"""Signal generation across a universe of symbols.

The :class:`SignalGenerator` loads historical data for each requested
symbol via an injected ``data_loader`` callable, runs one or more
strategies over that data, and captures the trade signals the strategies
emit on the most recent bar. Signals are returned as plain dictionaries
suitable for serialization, notification, or persistence.

Strategies interact with a *portfolio-like* object through ``buy`` /
``sell`` calls. Rather than executing real trades, the generator supplies a
lightweight recording adapter (:class:`_SignalRecorder`) that turns each
call into a structured signal record.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

import pandas as pd
from loguru import logger

from core.strategy.base import Strategy

# A data loader takes a symbol and returns its OHLCV DataFrame (or None).
DataLoader = Callable[[str], "pd.DataFrame | None"]


class _RecordedPosition:
    """Minimal position stub exposing the ``quantity`` attribute.

    Used so that strategies which call ``portfolio.get_position(symbol)``
    before selling see a non-empty position and therefore emit a sell
    signal during signal generation.
    """

    def __init__(self, symbol: str, quantity: int = 100) -> None:
        self.symbol = symbol
        self.quantity = quantity


class _SignalRecorder:
    """Portfolio-like adapter that records signals instead of trading.

    Implements the subset of the portfolio interface that strategies use:
    ``cash``, ``buy``, ``sell`` and ``get_position``. Every ``buy`` /
    ``sell`` call is captured as a pending signal for the active bar.
    """

    def __init__(self, cash: float = 1_000_000.0) -> None:
        self.cash = cash
        self.pending: list[dict[str, Any]] = []

    def get_position(self, symbol: str) -> _RecordedPosition:
        """Return a stub position so sell logic can trigger."""
        return _RecordedPosition(symbol)

    def buy(self, symbol: str, price: float, quantity: int, date: Any) -> bool:
        """Record a buy signal."""
        self.pending.append(
            {"symbol": symbol, "signal": "buy", "price": float(price), "datetime": date}
        )
        return True

    def sell(self, symbol: str, price: float, quantity: int, date: Any) -> bool:
        """Record a sell signal."""
        self.pending.append(
            {"symbol": symbol, "signal": "sell", "price": float(price), "datetime": date}
        )
        return True


class SignalGenerator:
    """Run strategies over a set of symbols and collect trade signals.

    Args:
        data_loader: Callable that, given a symbol, returns its historical
            OHLCV :class:`pandas.DataFrame` (indexed by date) or ``None``
            when data is unavailable.
        min_bars: Minimum number of bars required before a symbol is
            evaluated (default 2). Symbols with fewer bars are skipped.

    Example:
        >>> gen = SignalGenerator(data_loader=storage.load_ohlcv)
        >>> signals = gen.run_strategies(["000001.SZ"], [MACrossStrategy()])
    """

    def __init__(self, data_loader: DataLoader, min_bars: int = 2) -> None:
        if not callable(data_loader):
            raise ValueError("data_loader must be callable.")
        if min_bars < 1:
            raise ValueError("min_bars must be >= 1.")
        self._data_loader = data_loader
        self._min_bars = min_bars

    def run_strategies(
        self,
        symbols: list[str],
        strategies: list[Strategy],
    ) -> list[dict[str, Any]]:
        """Evaluate every strategy against every symbol's latest bar.

        For each symbol the data is loaded once and reused across all
        strategies. Each strategy is invoked on the final (most recent)
        bar; any resulting buy/sell order is recorded as a signal.

        Args:
            symbols: Ticker symbols to evaluate.
            strategies: Strategy instances to run.

        Returns:
            A list of signal dictionaries, each containing ``symbol``,
            ``strategy_name``, ``signal`` (``"buy"`` / ``"sell"``),
            ``price``, ``datetime`` and ``reason``.
        """
        if not symbols:
            logger.warning("run_strategies called with no symbols.")
            return []
        if not strategies:
            logger.warning("run_strategies called with no strategies.")
            return []

        results: list[dict[str, Any]] = []
        logger.info(
            f"Generating signals | Symbols: {len(symbols)} | "
            f"Strategies: {len(strategies)}"
        )

        for symbol in symbols:
            data = self._load(symbol)
            if data is None:
                continue

            for strategy in strategies:
                results.extend(self._run_one(symbol, data, strategy))

        logger.info(f"Signal generation complete | Signals: {len(results)}")
        return results

    # ----------------------------------------------------------------- #
    # Internal helpers
    # ----------------------------------------------------------------- #
    def _load(self, symbol: str) -> "pd.DataFrame | None":
        """Load and validate the OHLCV frame for a symbol."""
        try:
            data = self._data_loader(symbol)
        except Exception as exc:  # noqa: BLE001 - loader failures are per-symbol
            logger.error(f"Failed to load data for {symbol}: {exc}")
            return None

        if data is None or getattr(data, "empty", True):
            logger.warning(f"No data available for {symbol}; skipping.")
            return None
        if "close" not in data.columns:
            logger.warning(f"Data for {symbol} missing 'close' column; skipping.")
            return None
        if len(data) < self._min_bars:
            logger.debug(
                f"Insufficient bars for {symbol} "
                f"({len(data)} < {self._min_bars}); skipping."
            )
            return None
        return data

    def _run_one(
        self,
        symbol: str,
        data: pd.DataFrame,
        strategy: Strategy,
    ) -> list[dict[str, Any]]:
        """Run a single strategy on the latest bar of ``data``."""
        recorder = _SignalRecorder()
        last_index = len(data) - 1
        last_row = data.iloc[last_index]

        try:
            strategy.on_bar(last_index, last_row, data, recorder)
        except Exception as exc:  # noqa: BLE001 - one strategy must not break others
            logger.error(
                f"Strategy {strategy.name!r} failed on {symbol}: {exc}"
            )
            return []

        signals: list[dict[str, Any]] = []
        for record in recorder.pending:
            signals.append(
                {
                    "symbol": symbol,
                    "strategy_name": strategy.name,
                    "signal": record["signal"],
                    "price": record["price"],
                    "datetime": self._normalize_datetime(record["datetime"]),
                    "reason": f"{strategy.name} generated {record['signal']} signal",
                }
            )

        if signals:
            logger.debug(
                f"{strategy.name} produced {len(signals)} signal(s) for {symbol}."
            )
        return signals

    @staticmethod
    def _normalize_datetime(value: Any) -> str:
        """Convert a bar timestamp into an ISO-8601 string."""
        if value is None:
            return datetime.now().isoformat()
        if isinstance(value, str):
            return value
        try:
            return pd.Timestamp(value).isoformat()
        except (ValueError, TypeError):
            return str(value)
