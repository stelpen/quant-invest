"""Data sync and K-line query routes."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from loguru import logger

from api.auth import get_current_user
from api.dependencies import get_storage, get_updater
from api.schemas import KLineRequest, KLineResponse, SyncRequest, SyncStatus

router = APIRouter(prefix="/api/data", tags=["数据"])

_sync_state = {
    "running": False,
    "progress": "未运行",
    "total_symbols": 0,
    "synced_symbols": 0,
    "last_update": None,
}


@router.post("/kline", response_model=KLineResponse)
async def get_kline(
    request: KLineRequest,
    _user: dict = Depends(get_current_user),
):
    """获取 K 线数据，可选叠加技术指标。"""
    storage = get_storage()
    df = storage.load_daily_kline(request.symbol, request.start_date, request.end_date)
    if df.empty:
        # 本地无数据，尝试从数据源拉取并保存
        logger.info(f"No local data for {request.symbol}, fetching from source...")
        from api.dependencies import get_fetcher
        df = get_fetcher().get_daily_kline(
            symbol=request.symbol,
            start_date=request.start_date or "20200101",
            end_date=request.end_date or datetime.now().strftime("%Y%m%d"),
        )
        if df is not None and not df.empty:
            storage.save_daily_kline(request.symbol, df)
        else:
            raise HTTPException(status_code=404, detail=f"未找到 {request.symbol} 的数据")

    if "date" not in df.columns:
        raise HTTPException(status_code=500, detail="数据格式错误，缺少日期列")

    indicators_result: dict = {}
    if request.indicators:
        from core.indicators.ma import sma, ema
        from core.indicators.momentum import macd, rsi, kdj
        from core.indicators.volatility import bollinger_bands, atr

        for ind in request.indicators:
            ind_lower = ind.lower()
            try:
                if ind_lower == "ma":
                    sma5 = sma(df["close"], 5)
                    sma10 = sma(df["close"], 10)
                    sma20 = sma(df["close"], 20)
                    indicators_result["MA"] = {
                        "MA5": _to_list(sma5),
                        "MA10": _to_list(sma10),
                        "MA20": _to_list(sma20),
                    }
                elif ind_lower == "ema":
                    ema5 = ema(df["close"], 5)
                    ema12 = ema(df["close"], 12)
                    ema26 = ema(df["close"], 26)
                    indicators_result["EMA"] = {
                        "EMA5": _to_list(ema5),
                        "EMA12": _to_list(ema12),
                        "EMA26": _to_list(ema26),
                    }
                elif ind_lower == "macd":
                    dif, dea, hist = macd(df["close"])
                    indicators_result["MACD"] = {
                        "DIF": _to_list(dif),
                        "DEA": _to_list(dea),
                        "HIST": _to_list(hist),
                    }
                elif ind_lower == "rsi":
                    rsi6 = rsi(df["close"], 6)
                    rsi12 = rsi(df["close"], 12)
                    rsi24 = rsi(df["close"], 24)
                    indicators_result["RSI"] = {
                        "RSI6": _to_list(rsi6),
                        "RSI12": _to_list(rsi12),
                        "RSI24": _to_list(rsi24),
                    }
                elif ind_lower == "kdj":
                    k, d, j = kdj(df["high"], df["low"], df["close"])
                    indicators_result["KDJ"] = {
                        "K": _to_list(k),
                        "D": _to_list(d),
                        "J": _to_list(j),
                    }
                elif ind_lower == "boll":
                    upper, mid, lower = bollinger_bands(df["close"])
                    indicators_result["BOLL"] = {
                        "UPPER": _to_list(upper),
                        "MID": _to_list(mid),
                        "LOWER": _to_list(lower),
                    }
                elif ind_lower == "atr":
                    a = atr(df["high"], df["low"], df["close"], 14)
                    indicators_result["ATR"] = {"ATR14": _to_list(a)}
            except Exception as e:
                logger.warning(f"Indicator {ind} calculation failed: {e}")

    return KLineResponse(
        symbol=request.symbol,
        dates=[str(d) for d in df["date"].tolist()],
        opens=df["open"].tolist(),
        highs=df["high"].tolist(),
        lows=df["low"].tolist(),
        closes=df["close"].tolist(),
        volumes=df["volume"].tolist(),
        indicators=indicators_result,
    )


@router.get("/index/{symbol}")
async def get_index(
    symbol: str,
    start_date: str = "20200101",
    end_date: Optional[str] = None,
    _user: dict = Depends(get_current_user),
):
    """获取指数数据。"""
    from api.dependencies import get_fetcher
    end_date = end_date or datetime.now().strftime("%Y%m%d")
    df = get_fetcher().get_index_daily(symbol, start_date, end_date)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"未找到指数 {symbol} 数据")
    return {
        "symbol": symbol,
        "dates": [str(d) for d in df["date"].tolist()],
        "closes": df["close"].tolist(),
    }


@router.post("/sync")
async def sync_data(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    _user: dict = Depends(get_current_user),
):
    """触发数据同步（后台任务）。"""
    if _sync_state["running"]:
        raise HTTPException(status_code=409, detail="同步任务已在运行中")

    _sync_state["running"] = True
    _sync_state["progress"] = "启动中..."
    background_tasks.add_task(_run_sync, request.symbols)
    return {"status": "started", "message": "数据同步任务已启动"}


@router.get("/sync/status", response_model=SyncStatus)
async def sync_status(_user: dict = Depends(get_current_user)):
    """获取同步状态。"""
    return SyncStatus(**_sync_state)


def _run_sync(symbols: Optional[list[str]] = None) -> None:
    """后台执行数据同步。"""
    try:
        updater = get_updater()
        if symbols:
            _sync_state["total_symbols"] = len(symbols)
            _sync_state["synced_symbols"] = 0
            for sym in symbols:
                _sync_state["progress"] = f"同步 {sym}"
                updater.update_daily_kline(sym)
                _sync_state["synced_symbols"] += 1
        else:
            _sync_state["progress"] = "同步股票列表..."
            updater.update_stock_list()
            all_symbols = updater.storage.get_all_symbols()
            _sync_state["total_symbols"] = len(all_symbols)
            _sync_state["synced_symbols"] = 0
            for i, sym in enumerate(all_symbols):
                _sync_state["progress"] = f"[{i+1}/{len(all_symbols)}] 同步 {sym}"
                updater.update_daily_kline(sym)
                _sync_state["synced_symbols"] += 1
        _sync_state["last_update"] = datetime.now().isoformat()
        _sync_state["progress"] = "完成"
    except Exception as e:
        logger.error(f"Sync task failed: {e}")
        _sync_state["progress"] = f"失败: {e}"
    finally:
        _sync_state["running"] = False


def _to_list(s) -> list[Optional[float]]:
    """Convert Series to list, replacing NaN with None."""
    return [None if pd_isna(v) else float(v) for v in s.tolist()]


def pd_isna(v):
    """NaN check that's safe for non-float."""
    try:
        import math
        if v is None:
            return True
        if isinstance(v, float):
            return math.isnan(v)
        return False
    except Exception:
        return False