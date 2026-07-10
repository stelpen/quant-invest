"""Abstract base class for trading strategies.

Defines the minimal interface every strategy must implement to be used
with the backtest engine or signal generator. Concrete strategies (for
example :class:`~core.strategy.ma_cross.MACrossStrategy`) subclass
:class:`Strategy` and supply the actual entry / exit logic.
"""

from __future__ import annotations

import abc
from typing import Any

import pandas as pd


class Strategy(abc.ABC):
    """Abstract base for all trading strategies.

    Subclasses must override the abstract :attr:`name` property and the
    abstract :meth:`on_bar` method. :meth:`get_params` may be overridden
    to expose tunable parameters for external tooling (optimizers, CLI,
    dashboards).
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable name of the strategy.

        Returns:
            A short identifier (e.g. ``"MA Cross (5/20)"``).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def on_bar(
        self,
        index: int,
        row: pd.Series,
        data: pd.DataFrame,
        portfolio: Any,
    ) -> None:
        """React to a single bar of market data.

        Called once per bar by the backtest engine or live runner. The
        implementation should inspect the current ``row`` (and optionally
        the rolling ``data`` history) and place orders through
        ``portfolio`` when an entry / exit condition is met.

        Args:
            index: Integer position of the bar inside ``data``.
            row: The current row (``pd.Series``) with at minimum OHLCV
                fields.
            data: The full historical :class:`pandas.DataFrame` seen so
                far, useful for computing indicators.
            portfolio: The executing portfolio / engine instance. Use
                ``portfolio.buy(...)`` / ``portfolio.sell(...)`` (or the
                equivalent engine method) to submit orders.
        """
        raise NotImplementedError

    def get_params(self) -> dict[str, Any]:
        """Return the strategy's configurable parameters.

        Default implementation returns an empty dictionary. Concrete
        strategies should override this to expose their tunable knobs.

        Returns:
            Mapping of parameter name to value.
        """
        return {}
