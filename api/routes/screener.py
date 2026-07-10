"""Screener routes."""

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from api.auth import get_current_user
from api.dependencies import get_storage
from api.schemas import ScreenRequest, ScreenResponse

router = APIRouter(prefix="/api/screener", tags=["选股"])


@router.post("/run", response_model=ScreenResponse)
async def run_screener(
    request: ScreenRequest,
    _user: dict = Depends(get_current_user),
):
    """运行多因子选股筛选。

    支持的过滤器:
    - pe_max / pe_min: 市盈率范围
    - pb_max / pb_min: 市净率范围
    - roe_min: 最低 ROE
    - momentum_days: 动量计算天数
    - momentum_min / momentum_max: 动量范围
    - volume_min: 最低日均成交量
    """
    storage = get_storage()
    symbols = storage.get_all_symbols()

    if not symbols:
        raise HTTPException(status_code=404, detail="暂无股票数据，请先同步")

    from core.strategy.screener import StockScreener

    # 加载各股票数据
    stock_data = {}
    # 限制选股范围避免超时（默认扫描前500只）
    scan_limit = request.filters.get("_limit", 500)
    for sym in symbols[:scan_limit]:
        df = storage.load_daily_kline(sym)
        if not df.empty:
            stock_data[sym] = df

    if not stock_data:
        return ScreenResponse(results=[])

    screener = StockScreener()
    try:
        result_df = screener.screen(stock_data, request.filters)
    except Exception as e:
        logger.error(f"Screener error: {e}")
        raise HTTPException(status_code=500, detail=f"选股失败: {e}")

    if result_df is None or result_df.empty:
        return ScreenResponse(results=[])

    # 转换为字典列表
    results = result_df.head(100).to_dict(orient="records")
    return ScreenResponse(results=results)
