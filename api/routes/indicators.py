"""Indicator calculation routes."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from api.auth import get_current_user
from api.dependencies import get_storage

router = APIRouter(prefix="/api/indicators", tags=["指标"])


@router.post("/calculate")
async def calculate_indicators(
    symbol: str,
    indicators: list[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    params: dict[str, Any] = {},
    _user: dict = Depends(get_current_user),
):
    """计算技术指标。

    支持的指标: ma, ema, macd, rsi, kdj, boll, atr, obv, vwap
    """
    storage = get_storage()
    df = storage.load_daily_kline(symbol, start_date, end_date)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的数据")

    from core.indicators.ma import sma, ema
    from core.indicators.momentum import macd, rsi, kdj
    from core.indicators.volatility import bollinger_bands, atr
    from core.indicators.volume import obv, vwap

    results: dict[str, Any] = {"symbol": symbol, "dates": df["date"].tolist()}

    for ind in indicators:
        ind_lower = ind.lower()
        try:
            if ind_lower == "sma":
                period = params.get("sma_period", 20)
                results["SMA"] = _safe(sma(df["close"], period))
            elif ind_lower == "ema":
                period = params.get("ema_period", 20)
                results["EMA"] = _safe(ema(df["close"], period))
            elif ind_lower == "macd":
                fast = params.get("macd_fast", 12)
                slow = params.get("macd_slow", 26)
                signal = params.get("macd_signal", 9)
                dif, dea, hist = macd(df["close"], fast, slow, signal)
                results["MACD"] = {
                    "DIF": _safe(dif), "DEA": _safe(dea), "HIST": _safe(hist)
                }
            elif ind_lower == "rsi":
                period = params.get("rsi_period", 14)
                results["RSI"] = _safe(rsi(df["close"], period))
            elif ind_lower == "kdj":
                n = params.get("kdj_n", 9)
                k, d, j = kdj(df["high"], df["low"], df["close"], n)
                results["KDJ"] = {"K": _safe(k), "D": _safe(d), "J": _safe(j)}
            elif ind_lower == "boll":
                period = params.get("boll_period", 20)
                std_dev = params.get("boll_std", 2)
                upper, mid, lower = bollinger_bands(df["close"], period, std_dev)
                results["BOLL"] = {
                    "UPPER": _safe(upper), "MID": _safe(mid), "LOWER": _safe(lower)
                }
            elif ind_lower == "atr":
                period = params.get("atr_period", 14)
                results["ATR"] = _safe(atr(df["high"], df["low"], df["close"], period))
            elif ind_lower == "obv":
                results["OBV"] = _safe(obv(df["close"], df["volume"]))
            elif ind_lower == "vwap":
                results["VWAP"] = _safe(vwap(df["high"], df["low"], df["close"], df["volume"]))
            else:
                logger.warning(f"Unknown indicator: {ind}")
        except Exception as e:
            logger.error(f"Indicator {ind} calculation error: {e}")
            results[ind.upper()] = {"error": str(e)}

    return results


def _safe(series) -> list:
    """Convert a pandas Series to a JSON-safe list."""
    import math
    return [None if (v is None or (isinstance(v, float) and math.isnan(v))) else float(v)
            for v in series.tolist()]
