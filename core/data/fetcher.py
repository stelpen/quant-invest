"""Market data fetching via AKShare.

Wraps AKShare API calls with rate limiting, logging, graceful error
handling, and exponential-backoff retries for transient network failures.
All methods return an empty ``pandas.DataFrame`` on failure so that callers
can rely on a consistent return type.
"""

from __future__ import annotations

import random
import time
from typing import Any, Callable

import akshare as ak
import pandas as pd
from loguru import logger

from config.settings import settings


# Exception substrings that indicate a retryable (transient) failure.
_RETRYABLE_KEYWORDS = (
    "RemoteDisconnected",
    "Connection aborted",
    "ConnectionReset",
    "ConnectionError",
    "timeout",
    "Timeout",
    "Too Many Requests",
    "503",
    "502",
    "ChunkedEncodingError",
)


def _is_retryable(exc: Exception) -> bool:
    """Check if the exception is a transient network error worth retrying."""
    exc_str = str(exc)
    exc_type = type(exc).__name__
    for kw in _RETRYABLE_KEYWORDS:
        if kw in exc_str or kw in exc_type:
            return True
    return False


def _retry(
    func: Callable[[], pd.DataFrame],
    max_attempts: int = 3,
    base_delay: float = 3.0,
    label: str = "",
) -> pd.DataFrame:
    """Execute ``func`` with exponential backoff retries on transient errors.

    Args:
        func: Zero-arg callable that returns a DataFrame.
        max_attempts: Total attempts (including the first try).
        base_delay: Initial delay in seconds (doubled each retry with jitter).
        label: Description for log messages.

    Returns:
        DataFrame from successful call, or empty DataFrame after all retries fail.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as exc:
            if attempt < max_attempts and _is_retryable(exc):
                delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                logger.warning(
                    "{} attempt {}/{} failed ({}), retrying in {:.1f}s...",
                    label, attempt, max_attempts, exc, delay,
                )
                time.sleep(delay)
            else:
                raise
    return pd.DataFrame()  # unreachable but satisfies type checker


class AKShareFetcher:
    """Fetch A-share market data from AKShare.

    A small ``time.sleep`` is applied before each request to respect the
    configured rate limit and avoid being throttled by the upstream provider.
    """

    #: Mapping from AKShare Chinese column names to English for daily K-line.
    _DAILY_COLUMN_MAP: dict[str, str] = {
        "日期": "date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
        "成交额": "amount",
        "振幅": "amplitude",
        "涨跌幅": "pct_change",
        "涨跌额": "change",
        "换手率": "turnover",
    }

    def __init__(self, rate_limit: float | None = None) -> None:
        """Initialize the fetcher.

        Args:
            rate_limit: Seconds to wait between requests. Falls back to
                ``settings.AKSHARE_RATE_LIMIT`` when not provided.
        """
        self.rate_limit: float = (
            rate_limit if rate_limit is not None else settings.AKSHARE_RATE_LIMIT
        )

    def _sleep(self) -> None:
        """Sleep between requests to respect rate limits."""
        if self.rate_limit and self.rate_limit > 0:
            time.sleep(self.rate_limit)

    @staticmethod
    def _empty_df() -> pd.DataFrame:
        return pd.DataFrame()

    def get_stock_list(self) -> pd.DataFrame:
        """Fetch the full A-share stock list.

        Tries multiple AKShare endpoints in order:
            1. ``stock_zh_a_spot_em`` (East Money, primary)
            2. ``stock_info_a_code_name`` (Tushare-style fallback)

        Returns:
            DataFrame containing the realtime spot data for all A-share
            instruments. Returns an empty DataFrame if all sources fail.
        """
        # Primary: East Money realtime spot (has total market cap for ranking)
        def _primary() -> pd.DataFrame:
            self._sleep()
            df = ak.stock_zh_a_spot_em()
            return df if df is not None else self._empty_df()

        try:
            df = _retry(_primary, max_attempts=3, base_delay=3.0, label="stock_list(em)")
            if df is not None and not df.empty:
                logger.info("Fetched A-share stock list: {} rows", len(df))
                return df
        except Exception as exc:
            logger.error("Primary source failed: {}", exc)

        # Fallback: simpler symbol/name list (no market cap)
        def _fallback() -> pd.DataFrame:
            self._sleep()
            df = ak.stock_info_a_code_name()
            return df if df is not None else self._empty_df()

        try:
            df = _retry(_fallback, max_attempts=3, base_delay=5.0, label="stock_list(fb)")
            if df is not None and not df.empty:
                df = df.rename(columns={"code": "symbol", "name": "name"})
                logger.info("Fetched A-share stock list (fallback): {} rows", len(df))
                return df
        except Exception as exc:
            logger.error("Fallback source also failed: {}", exc)

        return self._empty_df()

    def get_daily_kline(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """Fetch daily K-line data for a single symbol (with retry).

        Args:
            symbol: 6-digit stock code, e.g. ``"000001"``.
            start_date: Start date in ``YYYYMMDD`` format.
            end_date: End date in ``YYYYMMDD`` format.
            adjust: Price adjustment type. One of ``"qfq"``, ``"hfq"``,
                ``""`` (none). Default ``"qfq"``.

        Returns:
            DataFrame with English column names. Returns empty DataFrame on error.
        """
        def _fetch() -> pd.DataFrame:
            self._sleep()
            return ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )

        try:
            df = _retry(_fetch, max_attempts=3, base_delay=2.0, label=f"kline({symbol})")
            if df is None or df.empty:
                logger.warning(
                    "Empty daily K-line for {} between {} and {}",
                    symbol, start_date, end_date,
                )
                return self._empty_df()
            df = df.rename(columns=self._DAILY_COLUMN_MAP)
            logger.info("Fetched daily K-line for {}: {} rows", symbol, len(df))
            return df
        except Exception as exc:
            logger.error("Failed to fetch daily K-line for {}: {}", symbol, exc)
            return self._empty_df()

    def get_minute_kline(self, symbol: str, period: str = "5") -> pd.DataFrame:
        """Fetch intraday minute K-line data.

        Args:
            symbol: 6-digit stock code.
            period: Minute period, e.g. ``"1"``, ``"5"``, ``"15"``,
                ``"30"``, ``"60"``. Default ``"5"``.

        Returns:
            DataFrame with the raw AKShare columns. Returns an empty
            DataFrame on error.
        """
        self._sleep()
        try:
            df = ak.stock_zh_a_hist_min_em(symbol=symbol, period=period)
            if df is None or df.empty:
                logger.warning("Empty minute K-line for {}", symbol)
                return self._empty_df()
            logger.info(
                "Fetched minute K-line for {} (period={}): {} rows",
                symbol,
                period,
                len(df),
            )
            return df
        except Exception as exc:
            logger.error(
                "Failed to fetch minute K-line for {}: {}", symbol, exc
            )
            return self._empty_df()

    def get_financial_data(self, symbol: str) -> pd.DataFrame:
        """Fetch basic financial indicators.

        Args:
            symbol: 6-digit stock code.

        Returns:
            DataFrame with THS financial abstract data. Returns an empty
            DataFrame on error.
        """
        self._sleep()
        try:
            df = ak.stock_financial_abstract_ths(symbol=symbol)
            if df is None or df.empty:
                logger.warning("Empty financial data for {}", symbol)
                return self._empty_df()
            logger.info(
                "Fetched financial data for {}: {} rows", symbol, len(df)
            )
            return df
        except Exception as exc:
            logger.error(
                "Failed to fetch financial data for {}: {}", symbol, exc
            )
            return self._empty_df()

    def get_index_daily(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Fetch daily index data.

        Args:
            symbol: Index code (e.g. ``"000300"`` for HS300).
            start_date: Start date in ``YYYYMMDD`` format.
            end_date: End date in ``YYYYMMDD`` format.

        Returns:
            DataFrame with daily index bars. Returns an empty DataFrame
            on error.
        """
        self._sleep()
        try:
            df = ak.index_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
            )
            if df is None or df.empty:
                logger.warning(
                    "Empty index data for {} between {} and {}",
                    symbol,
                    start_date,
                    end_date,
                )
                return self._empty_df()
            logger.info(
                "Fetched index daily for {}: {} rows", symbol, len(df)
            )
            return df
        except Exception as exc:
            logger.error(
                "Failed to fetch index daily for {}: {}", symbol, exc
            )
            return self._empty_df()