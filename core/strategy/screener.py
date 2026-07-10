"""Fundamental and basic stock screener.

Applies a configurable set of filters (valuation, profitability, momentum,
and liquidity) to a universe of stocks and returns a ranked
:class:`pandas.DataFrame` with a composite score. The screener is tolerant
of missing data: a stock missing the columns a particular filter needs
simply fails that filter, while the remaining filters still operate.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from loguru import logger


# Maps each numeric filter key to (metric_name, comparison_direction).
# direction "max" -> value must be <= limit; "min" -> value must be >= limit.
_NUMERIC_FILTERS: dict[str, tuple[str, str]] = {
    "pe_max": ("pe", "max"),
    "pe_min": ("pe", "min"),
    "pb_max": ("pb", "max"),
    "pb_min": ("pb", "min"),
    "roe_min": ("roe", "min"),
    "volume_min": ("latest_volume", "min"),
}
_MOMENTUM_KEYS: tuple[str, ...] = ("momentum_days", "momentum_min")

# Columns exposed in the output DataFrame (in addition to ``score``).
_OUTPUT_COLUMNS: tuple[str, ...] = (
    "pe",
    "pb",
    "roe",
    "latest_close",
    "latest_volume",
    "momentum",
)


class StockScreener:
    """Stock screener supporting fundamental + basic technical filters.

    The screener operates on a mapping ``{symbol: DataFrame}``. Each
    DataFrame is expected to contain price fields (``close``, ``volume``)
    and may also include fundamental ratios (``pe``, ``pb``, ``roe``).

    Supported filter keys:

    * ``pe_max`` / ``pe_min`` — bounds on the trailing P/E ratio.
    * ``pb_max`` / ``pb_min`` — bounds on the price-to-book ratio.
    * ``roe_min`` — minimum return on equity (e.g. ``0.10`` == 10%).
    * ``momentum_days`` + ``momentum_min`` — minimum trailing return over
      ``momentum_days`` trading days (e.g. ``0.05`` for a 5% move). Both
      keys must be supplied together.
    * ``volume_min`` — minimum latest-bar volume threshold.

    The composite ``score`` is the fraction of active filters a stock
    passes, in ``[0, 1]``.

    Args:
        min_score: Minimum composite score a stock must reach to remain in
            the output. Default ``0.0`` keeps every evaluated stock.

    Example:
        >>> filters = {"pe_max": 20, "roe_min": 0.10,
        ...            "momentum_days": 20, "momentum_min": 0.05}
        >>> results = StockScreener().screen(stock_data, filters)
    """

    def __init__(self, min_score: float = 0.0) -> None:
        if not 0.0 <= min_score <= 1.0:
            raise ValueError(f"min_score must be in [0, 1], got {min_score}.")
        self.min_score = min_score

    # ----------------------------------------------------------------- #
    # Public API
    # ----------------------------------------------------------------- #
    def screen(
        self,
        stock_data: dict[str, pd.DataFrame],
        filters: dict[str, Any],
    ) -> pd.DataFrame:
        """Screen a universe of stocks against the supplied filters.

        Args:
            stock_data: Mapping of ticker symbol to its price/fundamental
                :class:`pandas.DataFrame`.
            filters: Filter specification (see class docstring).

        Returns:
            A :class:`pandas.DataFrame` indexed by symbol, sorted by
            ``score`` descending, with the ``score`` column plus any
            available metric columns. Returns an empty DataFrame if no
            stock qualifies.

        Raises:
            ValueError: If ``stock_data`` is empty or ``filters`` is
                malformed.
        """
        if not stock_data:
            raise ValueError("stock_data must not be empty.")
        if not isinstance(filters, dict):
            raise ValueError("filters must be a dict.")
        self._validate_filters(filters)

        active_total = self._active_filter_count(filters)
        rows: list[dict[str, Any]] = []

        for symbol, df in stock_data.items():
            try:
                metrics = self._compute_metrics(df, filters)
            except Exception as exc:  # noqa: BLE001 - skip malformed symbols
                logger.warning(f"Screener skipped {symbol}: {exc}")
                continue

            passed = self._count_passes(metrics, filters)
            score = (passed / active_total) if active_total else 0.0
            if score < self.min_score:
                continue

            row: dict[str, Any] = {"symbol": symbol, "score": round(score, 4)}
            for col in _OUTPUT_COLUMNS:
                row[col] = metrics.get(col)
            rows.append(row)

        if not rows:
            logger.info("Screener found no qualifying symbols.")
            return pd.DataFrame(columns=["score", *_OUTPUT_COLUMNS])

        result = pd.DataFrame(rows).set_index("symbol")
        result.sort_values("score", ascending=False, inplace=True)
        logger.info(
            f"Screen complete | Universe: {len(stock_data)} | "
            f"Qualified: {len(result)} | Filters: {sorted(filters)}"
        )
        return result

    # ----------------------------------------------------------------- #
    # Validation
    # ----------------------------------------------------------------- #
    @staticmethod
    def _validate_filters(filters: dict[str, Any]) -> None:
        """Validate filter keys and value types."""
        momentum_present = [k for k in _MOMENTUM_KEYS if k in filters]
        if momentum_present and len(momentum_present) != len(_MOMENTUM_KEYS):
            missing = set(_MOMENTUM_KEYS) - set(momentum_present)
            raise ValueError(
                f"Momentum filter requires all of {list(_MOMENTUM_KEYS)}; "
                f"missing {sorted(missing)}."
            )

        for key, value in filters.items():
            if key == "momentum_days":
                if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                    raise ValueError(f"'momentum_days' must be a positive int, got {value}.")
            elif key == "momentum_min":
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise ValueError(f"'momentum_min' must be numeric, got {value}.")
            elif key in _NUMERIC_FILTERS:
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise ValueError(
                        f"Filter {key!r} must be numeric, got {type(value).__name__}."
                    )
            else:
                raise ValueError(f"Unknown filter key: {key!r}.")

    @staticmethod
    def _active_filter_count(filters: dict[str, Any]) -> int:
        """Count the number of active filters (momentum counts once)."""
        count = sum(1 for k in filters if k in _NUMERIC_FILTERS)
        if all(k in filters for k in _MOMENTUM_KEYS):
            count += 1
        return count

    # ----------------------------------------------------------------- #
    # Metric extraction
    # ----------------------------------------------------------------- #
    @staticmethod
    def _compute_metrics(
        df: pd.DataFrame, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract the metric values needed to evaluate ``filters``."""
        if df is None or df.empty:
            return {}

        metrics: dict[str, Any] = {}
        latest = df.iloc[-1]

        for col in ("pe", "pb", "roe"):
            if col in df.columns:
                value = pd.to_numeric(latest[col], errors="coerce")
                metrics[col] = None if pd.isna(value) else float(value)

        if "volume" in df.columns:
            volume = pd.to_numeric(latest["volume"], errors="coerce")
            metrics["latest_volume"] = None if pd.isna(volume) else float(volume)

        if "close" in df.columns:
            closes = pd.to_numeric(df["close"], errors="coerce").dropna()
            if not closes.empty:
                metrics["latest_close"] = float(closes.iloc[-1])

            if all(k in filters for k in _MOMENTUM_KEYS):
                days = int(filters["momentum_days"])
                if len(closes) >= days + 1:
                    past = float(closes.iloc[-(days + 1)])
                    latest_close = float(closes.iloc[-1])
                    if past > 0:
                        metrics["momentum"] = (latest_close / past) - 1.0

        return metrics

    # ----------------------------------------------------------------- #
    # Filter evaluation
    # ----------------------------------------------------------------- #
    @staticmethod
    def _count_passes(metrics: dict[str, Any], filters: dict[str, Any]) -> int:
        """Return how many active filters the stock's metrics satisfy."""
        passes = 0

        for key, limit in filters.items():
            spec = _NUMERIC_FILTERS.get(key)
            if spec is None:
                continue
            metric_name, direction = spec
            value = metrics.get(metric_name)
            if value is None:
                continue
            if direction == "max" and value <= limit:
                passes += 1
            elif direction == "min" and value >= limit:
                passes += 1

        if all(k in filters for k in _MOMENTUM_KEYS):
            momentum = metrics.get("momentum")
            if momentum is not None and momentum >= filters["momentum_min"]:
                passes += 1

        return passes
