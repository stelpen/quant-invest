"""Signal generation and notification routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from api.auth import get_current_user
from api.dependencies import get_notifier, get_storage
from api.schemas import SignalItem, SignalsResponse

router = APIRouter(prefix="/api/signals", tags=["信号"])

_today_signals: list[dict] = []
_last_generated: str = ""


@router.get("/today", response_model=SignalsResponse)
async def get_today_signals(_user: dict = Depends(get_current_user)):
    """获取今日已生成的信号。"""
    return SignalsResponse(
        signals=[SignalItem(**s) for s in _today_signals],
        generated_at=_last_generated,
    )


@router.post("/run", response_model=SignalsResponse)
async def run_signals(_user: dict = Depends(get_current_user)):
    """运行所有启用的策略，生成今日信号。"""
    global _today_signals, _last_generated

    storage = get_storage()
    symbols = storage.get_all_symbols()
    if not symbols:
        raise HTTPException(status_code=404, detail="暂无股票数据")

    from core.signals.generator import SignalGenerator
    from core.strategy.ma_cross import MACrossStrategy

    def data_loader(symbol: str):
        return storage.load_daily_kline(symbol)

    generator = SignalGenerator(data_loader=data_loader, min_bars=30)

    strategies = [MACrossStrategy(fast_period=5, slow_period=20)]
    signals = generator.run_strategies(symbols[:200], strategies)

    _today_signals = signals
    _last_generated = datetime.now().isoformat()

    # 自动通知
    notifier = get_notifier()
    if signals:
        results = notifier.notify(signals)
        logger.info(f"Signals generated: {len(signals)}, notify results: {results}")

    return SignalsResponse(
        signals=[SignalItem(**s) for s in signals],
        generated_at=_last_generated,
    )


@router.post("/test-notify")
async def test_notify(
    channel: str = "webhook",  # or "email"
    _user: dict = Depends(get_current_user),
):
    """测试通知渠道是否正常。"""
    notifier = get_notifier()
    test_signals = [
        {
            "symbol": "000001.SZ",
            "strategy_name": "Test",
            "signal": "buy",
            "price": 12.34,
            "datetime": datetime.now().isoformat(),
            "reason": "Test notification",
        }
    ]

    if channel == "webhook":
        ok = notifier.send_webhook(test_signals)
        return {"channel": "webhook", "ok": ok}
    elif channel == "email":
        ok = notifier.send_email(test_signals)
        return {"channel": "email", "ok": ok}
    else:
        results = notifier.notify(test_signals)
        return {"channel": "all", "results": results}
