"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ----- Auth -----
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


# ----- Stocks -----
class StockInfo(BaseModel):
    symbol: str
    name: Optional[str] = None
    market: Optional[str] = None
    industry: Optional[str] = None
    list_date: Optional[str] = None


class StockListResponse(BaseModel):
    items: list[StockInfo]
    total: int


# ----- Data -----
class KLineRequest(BaseModel):
    symbol: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    indicators: list[str] = Field(default_factory=list)


class KLineResponse(BaseModel):
    symbol: str
    dates: list[str]
    opens: list[float]
    highs: list[float]
    lows: list[float]
    closes: list[float]
    volumes: list[float]
    indicators: dict[str, dict[str, list[Optional[float]]]] = Field(default_factory=dict)


class SyncRequest(BaseModel):
    symbols: Optional[list[str]] = None


class SyncStatus(BaseModel):
    running: bool
    progress: str
    total_symbols: int
    synced_symbols: int
    last_update: Optional[str] = None


# ----- Backtest -----
class BacktestRequest(BaseModel):
    strategy: str = "ma_cross"
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 1_000_000
    params: dict[str, Any] = Field(default_factory=dict)


class TradeRecord(BaseModel):
    date: str
    symbol: str
    direction: str
    price: float
    quantity: int
    commission: float


class EquityPoint(BaseModel):
    date: str
    equity: float


class BacktestResponse(BaseModel):
    metrics: dict[str, Any]
    equity_curve: list[EquityPoint]
    trades: list[TradeRecord]


class StrategyInfo(BaseModel):
    name: str
    description: str
    params: dict[str, Any]


# ----- Screener -----
class ScreenRequest(BaseModel):
    filters: dict[str, Any] = Field(default_factory=dict)


class ScreenResponse(BaseModel):
    results: list[dict[str, Any]]


# ----- Signals -----
class SignalItem(BaseModel):
    symbol: str
    strategy_name: str
    signal: str
    price: float
    datetime: str
    reason: str


class SignalsResponse(BaseModel):
    signals: list[SignalItem]
    generated_at: str