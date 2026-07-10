"""Incremental data update orchestration.

Combines :class:`AKShareFetcher` and :class:`DataStorage` to keep the
local cache in sync with upstream data sources.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from loguru import logger

from config.settings import settings
from core.data.fetcher import AKShareFetcher
from core.data.storage import DataStorage


class DataUpdater:
    """Coordinate incremental data updates.

    Attributes:
        fetcher: Underlying AKShare client.
        storage: Persistence layer.
    """

    def __init__(
        self,
        fetcher: Optional[AKShareFetcher] = None,
        storage: Optional[DataStorage] = None,
    ) -> None:
        """Initialize the updater.

        Args:
            fetcher: Optional pre-built fetcher. A new one is created if
                not supplied.
            storage: Optional pre-built storage. A new one is created if
                not supplied.
        """
        self.fetcher: AKShareFetcher = fetcher or AKShareFetcher()
        self.storage: DataStorage = storage or DataStorage()

        try:
            self.storage.init_db()
        except Exception as exc:
            logger.error("DataUpdater: init_db failed: {}", exc)

    @staticmethod
    def _today_str() -> str:
        return datetime.now().strftime("%Y%m%d")

    @staticmethod
    def _next_day_str(yyyymmdd: str) -> str:
        dt = datetime.strptime(yyyymmdd, "%Y%m%d") + timedelta(days=1)
        return dt.strftime("%Y%m%d")

    def update_stock_list(self) -> pd.DataFrame:
        """Refresh the cached stock list.

        Returns:
            The freshly fetched DataFrame (also persisted).
        """
        logger.info("Updating stock list...")
        df = self.fetcher.get_stock_list()
        if df is None or df.empty:
            logger.warning("Stock list fetch returned no rows")
            return df

        self.storage.save_stock_list(df)
        logger.info("Stock list updated: {} rows", len(df))
        return df

    def update_daily_kline(self, symbol: str) -> bool:
        """Incrementally update one symbol's daily K-line.

        Computes the next day after the last persisted ``date`` (or falls
        back to one year back when no log exists) and fetches the missing
        range.

        Args:
            symbol: 6-digit stock code.

        Returns:
            ``True`` if new rows were saved, ``False`` otherwise.
        """
        last = self.storage.get_last_update_date(symbol)

        if last and len(last) == 8 and last.isdigit():
            start_date = self._next_day_str(last)
        else:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        end_date = self._today_str()

        if start_date > end_date:
            logger.info("{}: already up to date (last={})", symbol, last)
            return False

        logger.info("Fetching {} from {} to {}", symbol, start_date, end_date)
        df = self.fetcher.get_daily_kline(symbol, start_date, end_date)
        if df is None or df.empty:
            logger.warning("No new rows for {}", symbol)
            return False

        self.storage.save_daily_kline(symbol, df)

        if "date" in df.columns:
            new_last = max(str(d) for d in df["date"].tolist())
            self.storage.update_log(symbol, new_last)
        return True

    def update_all(self, max_symbols: Optional[int] = None) -> dict[str, int]:
        """Update daily K-line for all cached symbols.

        Args:
            max_symbols: Cap on number of symbols to update (useful for
                smoke tests). ``None`` means no cap.

        Returns:
            Mapping ``{"success": n_ok, "failed": n_fail, "skipped": n_skip}``.
        """
        symbols = self.storage.get_all_symbols()
        if not symbols:
            logger.warning("update_all: stock list is empty")
            return {"success": 0, "failed": 0, "skipped": 0}

        if max_symbols is not None:
            symbols = symbols[:max_symbols]

        total = len(symbols)
        logger.info("Starting bulk update for {} symbols", total)

        ok = fail = skip = 0
        for i, sym in enumerate(symbols, 1):
            try:
                updated = self.update_daily_kline(sym)
                if updated:
                    ok += 1
                else:
                    skip += 1
            except Exception as exc:
                fail += 1
                logger.error("update_daily_kline({}) crashed: {}", sym, exc)

            if i % 50 == 0 or i == total:
                logger.info(
                    "Progress {}/{}: ok={} skip={} fail={}",
                    i,
                    total,
                    ok,
                    skip,
                    fail,
                )

        logger.info(
            "Bulk update finished: success={} failed={} skipped={}",
            ok,
            fail,
            skip,
        )
        return {"success": ok, "failed": fail, "skipped": skip}

    def init_data(self) -> dict[str, int]:
        """First-time setup.

        Refreshes the stock list and seeds daily K-line for the top 500
        symbols by market cap (using the ``market_cap`` column from the
        spot feed if available).

        Returns:
            Counters returned by :meth:`update_all`.
        """
        logger.info("Running first-time initialization...")
        df = self.update_stock_list()
        if df is None or df.empty:
            logger.error("init_data: stock list fetch failed")
            return {"success": 0, "failed": 0, "skipped": 0}

        # Sort by market cap if present, otherwise leave as-is.
        if "总市值" in df.columns:
            df = df.sort_values(by="总市值", ascending=False)

        symbols = (
            df["symbol"].astype(str).head(500).tolist()
            if "symbol" in df.columns
            else []
        )
        if not symbols:
            logger.error("init_data: no symbols available after fetch")
            return {"success": 0, "failed": 0, "skipped": 0}

        ok = fail = skip = 0
        total = len(symbols)
        for i, sym in enumerate(symbols, 1):
            try:
                # Force a one-year backfill by clearing any prior log row.
                self.storage.update_log(sym, "")
                updated = self.update_daily_kline(sym)
                if updated:
                    ok += 1
                else:
                    skip += 1
            except Exception as exc:
                fail += 1
                logger.error("init_data {} crashed: {}", sym, exc)

            if i % 50 == 0 or i == total:
                logger.info(
                    "Init progress {}/{}: ok={} skip={} fail={}",
                    i,
                    total,
                    ok,
                    skip,
                    fail,
                )

        logger.info(
            "Init finished: success={} failed={} skipped={}",
            ok,
            fail,
            skip,
        )
        return {"success": ok, "failed": fail, "skipped": skip}