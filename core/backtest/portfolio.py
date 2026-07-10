"""Portfolio management for backtesting.

Provides a Portfolio class that tracks positions, cash, and trade history
with support for A-share market transaction costs (commission and stamp tax).
"""

from dataclasses import dataclass, field
from datetime import date as DateType
from typing import Any

from loguru import logger


@dataclass
class Position:
    """Represents a holding position for a single symbol.

    Attributes:
        symbol: Ticker symbol of the held instrument.
        quantity: Number of shares held.
        avg_cost: Average cost per share (including commission).
        current_price: Most recent market price.
    """

    symbol: str
    quantity: int
    avg_cost: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        """Current market value of the position."""
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit/loss based on current price vs average cost."""
        return (self.current_price - self.avg_cost) * self.quantity


@dataclass
class Trade:
    """Record of an executed trade.

    Attributes:
        date: Date of trade execution.
        symbol: Ticker symbol traded.
        direction: 'buy' or 'sell'.
        price: Execution price.
        quantity: Number of shares.
        commission: Commission paid.
        stamp_tax: Stamp tax paid (sell side only).
    """

    date: DateType
    symbol: str
    direction: str
    price: float
    quantity: int
    commission: float
    stamp_tax: float = 0.0


class Portfolio:
    """Portfolio manager that tracks positions, cash, and trade history.

    Handles order execution with A-share market transaction costs:
        - Commission: applied on both buy and sell (default 0.03%).
        - Stamp tax: applied on sell only (default 0.1%, A-share rule).

    Args:
        initial_capital: Starting cash amount.
        commission_rate: Commission rate per trade (default 0.0003).
        stamp_tax: Stamp tax rate on sell orders (default 0.001).

    Example:
        >>> portfolio = Portfolio(initial_capital=1_000_000)
        >>> portfolio.buy("000001.SZ", price=15.50, quantity=1000, date=today)
        >>> portfolio.sell("000001.SZ", price=16.20, quantity=1000, date=today)
        >>> print(portfolio.cash)
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000,
        commission_rate: float = 0.0003,
        stamp_tax: float = 0.001,
    ) -> None:
        self._initial_capital = initial_capital
        self._cash: float = initial_capital
        self._commission_rate = commission_rate
        self._stamp_tax = stamp_tax
        self._positions: dict[str, Position] = {}
        self._trade_history: list[Trade] = []

        logger.info(
            f"Portfolio initialized | Capital: {initial_capital:,.2f} | "
            f"Commission: {commission_rate:.4%} | Stamp tax: {stamp_tax:.4%}"
        )

    @property
    def cash(self) -> float:
        """Current available cash."""
        return self._cash

    @property
    def initial_capital(self) -> float:
        """Initial capital at portfolio creation."""
        return self._initial_capital

    @property
    def positions(self) -> dict[str, Position]:
        """Current open positions."""
        return self._positions

    @property
    def trade_history(self) -> list[Trade]:
        """History of all executed trades."""
        return self._trade_history

    def buy(
        self,
        symbol: str,
        price: float,
        quantity: int,
        date: DateType,
    ) -> bool:
        """Execute a buy order.

        Deducts the total cost (price * quantity + commission) from cash.
        If a position already exists for the symbol, the average cost is
        updated using a weighted average.

        Args:
            symbol: Ticker symbol to buy.
            price: Execution price per share.
            quantity: Number of shares to buy (must be positive).
            date: Date of the trade execution.

        Returns:
            True if the order was executed successfully, False otherwise.

        Raises:
            ValueError: If price or quantity is non-positive.
        """
        if price <= 0:
            raise ValueError(f"Price must be positive, got {price}.")
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}.")

        commission = price * quantity * self._commission_rate
        total_cost = price * quantity + commission

        if total_cost > self._cash:
            logger.warning(
                f"Insufficient cash for BUY {symbol} | "
                f"Required: {total_cost:,.2f} | Available: {self._cash:,.2f}"
            )
            return False

        self._cash -= total_cost

        # Update or create position
        if symbol in self._positions:
            pos = self._positions[symbol]
            total_quantity = pos.quantity + quantity
            pos.avg_cost = (
                (pos.avg_cost * pos.quantity + price * quantity) / total_quantity
            )
            pos.quantity = total_quantity
            pos.current_price = price
        else:
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_cost=price,
                current_price=price,
            )

        trade = Trade(
            date=date,
            symbol=symbol,
            direction="buy",
            price=price,
            quantity=quantity,
            commission=commission,
            stamp_tax=0.0,
        )
        self._trade_history.append(trade)

        logger.debug(
            f"BUY {symbol} | Qty: {quantity} | Price: {price:.4f} | "
            f"Commission: {commission:.2f} | Cash: {self._cash:,.2f}"
        )
        return True

    def sell(
        self,
        symbol: str,
        price: float,
        quantity: int,
        date: DateType,
    ) -> bool:
        """Execute a sell order.

        Adds the net proceeds (price * quantity - commission - stamp_tax)
        to cash. Stamp tax is applied only on the sell side (A-share rule).
        If the full quantity is sold, the position is removed.

        Args:
            symbol: Ticker symbol to sell.
            price: Execution price per share.
            quantity: Number of shares to sell (must be positive).
            date: Date of the trade execution.

        Returns:
            True if the order was executed successfully, False otherwise.

        Raises:
            ValueError: If price or quantity is non-positive.
        """
        if price <= 0:
            raise ValueError(f"Price must be positive, got {price}.")
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}.")

        position = self._positions.get(symbol)
        if position is None:
            logger.warning(f"No position to sell for {symbol}")
            return False

        if position.quantity < quantity:
            logger.warning(
                f"Insufficient position for SELL {symbol} | "
                f"Requested: {quantity} | Available: {position.quantity}"
            )
            return False

        commission = price * quantity * self._commission_rate
        stamp_tax_cost = price * quantity * self._stamp_tax
        net_proceeds = price * quantity - commission - stamp_tax_cost

        self._cash += net_proceeds

        # Update or remove position
        position.quantity -= quantity
        if position.quantity == 0:
            del self._positions[symbol]
        else:
            position.current_price = price

        trade = Trade(
            date=date,
            symbol=symbol,
            direction="sell",
            price=price,
            quantity=quantity,
            commission=commission,
            stamp_tax=stamp_tax_cost,
        )
        self._trade_history.append(trade)

        logger.debug(
            f"SELL {symbol} | Qty: {quantity} | Price: {price:.4f} | "
            f"Commission: {commission:.2f} | Stamp tax: {stamp_tax_cost:.2f} | "
            f"Cash: {self._cash:,.2f}"
        )
        return True

    def get_equity(self, prices: dict[str, float]) -> float:
        """Calculate total portfolio equity (cash + positions market value).

        Args:
            prices: Dictionary mapping symbol to current market price.

        Returns:
            Total portfolio value as cash plus sum of all position market values.
        """
        equity = self._cash

        for symbol, position in self._positions.items():
            current_price = prices.get(symbol, position.current_price)
            position.current_price = current_price
            equity += position.quantity * current_price

        return equity

    def get_position(self, symbol: str) -> Position | None:
        """Get the current position for a symbol.

        Args:
            symbol: Ticker symbol to look up.

        Returns:
            Position object if held, None otherwise.
        """
        return self._positions.get(symbol)
