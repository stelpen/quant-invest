"""Market data fetching via AKShare.

Wraps AKShare API calls with rate limiting, logging, and graceful error
handling. All methods return an empty ``pandas.DataFrame`` on failure so that
callers can rely on a consistent return type.
"""

from __future__ import annotations

import time
from typing import Any

import akshare as ak
import pandas as pd
from loguru import logger

from config.settings import settings


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

        Returns:
            DataFrame containing the realtime spot data for all A-share
            instruments. On error an empty DataFrame is returned.
        """
        self._sleep()
        try:
            df = ak.stock_zh_a_spot_em()
            logger.info("Fetched A-share stock list: {} rows", len(df))
            return df
        except Exception as exc:
            logger.error("Failed to fetch stock list: {}", exc)
            return self._empty_df()

    def get_daily_kline(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """Fetch daily K-line data for a single symbol.

        Args:
            symbol: 6-digit stock code, e.g. ``"000001"``.
            start_date: Start date in ``YYYYMMDD`` format.
            end_date: End date in ``YYYYMMDD`` format.
            adjust: Price adjustment type. One of ``"qfq"``, ``"hfq"``,
                ``""`` (none). Default ``"qfq"``.

        Returns:
            DataFrame with English column names: ``date``, ``open``,
            ``high``, ``low``, ``close``, ``volume``, ``amount``,
            ``amplitude``, ``pct_change``, ``change``, ``turnover``.
            Returns an empty DataFrame on error.
        """
        self._sleep()
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
            if df is None or df.empty:
                logger.warning(
                    "Empty daily K-line for {} between {} and {}",
                    symbol,
                    start_date,
                    end_date,
                )
                return self._empty_df()
            df = df.rename(columns=self._DAILY_COLUMN_MAP)
            logger.info(
                "Fetched daily K-line for {}: {} rows", symbol, len(df)
            )
            return df
        except Exception as exc:
            logger.error(
                "Failed to fetch daily K-line for {}: {}", symbol, exc
            )
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