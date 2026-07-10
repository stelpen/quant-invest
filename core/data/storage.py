"""Data storage layer for QuantInvest.

Persists stock metadata and incremental K-line data using SQLite (for
metadata and update logs) and Parquet files (for time-series bars).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import pandas as pd
from loguru import logger
from sqlalchemy import (
    Column,
    DateTime,
    String,
    create_engine,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class StockList(Base):
    """A-share stock metadata."""

    __tablename__ = "stock_list"

    symbol = Column(String(16), primary_key=True)
    name = Column(String(64), nullable=True)
    market = Column(String(16), nullable=True)
    industry = Column(String(64), nullable=True)
    list_date = Column(String(16), nullable=True)


class DailyUpdateLog(Base):
    """Per-symbol incremental update log."""

    __tablename__ = "daily_update_log"

    symbol = Column(String(16), primary_key=True)
    last_date = Column(String(16), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class DataStorage:
    """Persist and retrieve market data.

    Combines a SQLite database (for reference data and bookkeeping) with
    Parquet files (for efficient time-series storage).
    """

    def __init__(self, db_url: Optional[str] = None, data_dir: Optional[str] = None) -> None:
        """Initialize storage.

        Args:
            db_url: SQLAlchemy database URL. Defaults to
                ``settings.DB_URL``.
            data_dir: Directory for Parquet files. Defaults to
                ``settings.DATA_DIR``.
        """
        from config.settings import settings  # local import to avoid cycles

        self.db_url: str = db_url or settings.DB_URL
        self.data_dir: str = data_dir or settings.DATA_DIR

        self.parquet_dir: str = os.path.join(self.data_dir, "parquet", "daily")
        os.makedirs(self.parquet_dir, exist_ok=True)

        self.engine: Engine = create_engine(
            self.db_url,
            echo=False,
            future=True,
        )
        self.SessionLocal = sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False, future=True
        )

    def init_db(self) -> None:
        """Create all tables if they do not already exist."""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database initialized at {}", self.db_url)
        except Exception as exc:
            logger.error("Failed to initialize database: {}", exc)
            raise

    def _parquet_path(self, symbol: str) -> str:
        return os.path.join(self.parquet_dir, f"{symbol}.parquet")

    def save_stock_list(self, df: pd.DataFrame) -> None:
        """Upsert stock list rows from a DataFrame.

        Expected columns (best-effort): ``symbol``/``代码``,
        ``name``/``名称``, ``market`` (optional),
        ``industry`` (optional), ``list_date`` (optional).

        Args:
            df: Stock list DataFrame from the fetcher.
        """
        if df is None or df.empty:
            logger.warning("save_stock_list called with empty DataFrame")
            return

        rename_map = {
            "代码": "symbol",
            "名称": "name",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        if "symbol" not in df.columns:
            logger.error("save_stock_list: 'symbol' column missing after rename")
            return

        rows = []
        for _, row in df.iterrows():
            rows.append(
                {
                    "symbol": str(row.get("symbol", "")).strip(),
                    "name": str(row.get("name", "")).strip() or None,
                    "market": str(row.get("market", "")).strip() or None,
                    "industry": str(row.get("industry", "")).strip() or None,
                    "list_date": str(row.get("list_date", "")).strip() or None,
                }
            )

        try:
            with self.engine.begin() as conn:
                for r in rows:
                    if not r["symbol"]:
                        continue
                    conn.execute(
                        text(
                            """
                            INSERT INTO stock_list (symbol, name, market, industry, list_date)
                            VALUES (:symbol, :name, :market, :industry, :list_date)
                            ON CONFLICT(symbol) DO UPDATE SET
                                name=excluded.name,
                                market=excluded.market,
                                industry=excluded.industry,
                                list_date=excluded.list_date
                            """
                        ),
                        r,
                    )
            logger.info("Upserted {} stock rows", len(rows))
        except Exception as exc:
            logger.error("Failed to save stock list: {}", exc)

    def save_daily_kline(self, symbol: str, df: pd.DataFrame) -> None:
        """Append-merge daily K-line data into the per-symbol Parquet file.

        Existing rows are read, the new frame is concatenated, duplicates by
        ``date`` are removed keeping the latest, then the result is sorted
        by ``date`` and written back atomically.

        Args:
            symbol: Stock code.
            df: New K-line rows to persist.
        """
        if df is None or df.empty:
            logger.warning("save_daily_kline({}): empty DataFrame", symbol)
            return

        path = self._parquet_path(symbol)
        try:
            if os.path.exists(path):
                existing = pd.read_parquet(path)
                combined = pd.concat([existing, df], ignore_index=True)
            else:
                combined = df.copy()

            if "date" in combined.columns:
                combined["date"] = combined["date"].astype(str)
                combined = combined.drop_duplicates(
                    subset=["date"], keep="last"
                ).sort_values("date").reset_index(drop=True)
            else:
                combined = combined.reset_index(drop=True)

            combined.to_parquet(path, index=False)
            logger.info(
                "Saved daily K-line for {}: {} rows -> {}", symbol, len(combined), path
            )
        except Exception as exc:
            logger.error("Failed to save daily K-line for {}: {}", symbol, exc)

    def load_daily_kline(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Load daily K-line data from Parquet with optional date filtering.

        Args:
            symbol: Stock code.
            start_date: Inclusive lower bound (string comparable to ``date``).
            end_date: Inclusive upper bound (string comparable to ``date``).

        Returns:
            Filtered DataFrame; empty if the file does not exist.
        """
        path = self._parquet_path(symbol)
        if not os.path.exists(path):
            logger.warning("load_daily_kline({}): parquet not found", symbol)
            return pd.DataFrame()

        try:
            df = pd.read_parquet(path)
        except Exception as exc:
            logger.error("Failed to read parquet for {}: {}", symbol, exc)
            return pd.DataFrame()

        if df.empty:
            return df

        if "date" not in df.columns:
            return df

        df["date"] = df["date"].astype(str)
        if start_date:
            df = df[df["date"] >= str(start_date)]
        if end_date:
            df = df[df["date"] <= str(end_date)]
        return df.reset_index(drop=True)

    def get_last_update_date(self, symbol: str) -> Optional[str]:
        """Return the last persisted ``date`` for ``symbol``, or ``None``."""
        try:
            with self.engine.connect() as conn:
                row = conn.execute(
                    text("SELECT last_date FROM daily_update_log WHERE symbol=:s"),
                    {"s": symbol},
                ).fetchone()
            if row is None:
                return None
            value = row[0]
            return str(value) if value is not None else None
        except Exception as exc:
            logger.error("get_last_update_date failed for {}: {}", symbol, exc)
            return None

    def update_log(self, symbol: str, last_date: str) -> None:
        """Upsert the ``daily_update_log`` row for ``symbol``."""
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO daily_update_log (symbol, last_date, updated_at)
                        VALUES (:symbol, :last_date, :updated_at)
                        ON CONFLICT(symbol) DO UPDATE SET
                            last_date=excluded.last_date,
                            updated_at=excluded.updated_at
                        """
                    ),
                    {
                        "symbol": symbol,
                        "last_date": last_date,
                        "updated_at": datetime.utcnow(),
                    },
                )
            logger.debug("Updated log {} -> {}", symbol, last_date)
        except Exception as exc:
            logger.error("update_log failed for {}: {}", symbol, exc)

    def get_all_symbols(self) -> list[str]:
        """Return all symbols stored in the ``stock_list`` table."""
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(
                    text("SELECT symbol FROM stock_list ORDER BY symbol")
                ).fetchall()
            return [r[0] for r in rows if r and r[0]]
        except Exception as exc:
            logger.error("get_all_symbols failed: {}", exc)
            return []