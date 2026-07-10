"""Stock list routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import text

from api.auth import get_current_user
from api.database import get_db
from api.schemas import StockInfo, StockListResponse

router = APIRouter(prefix="/api/stocks", tags=["股票"])


@router.get("", response_model=StockListResponse)
async def list_stocks(
    q: str = Query("", description="搜索关键词（代码或名称）"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    _user: dict = Depends(get_current_user),
):
    """获取股票列表，支持搜索和分页。"""
    db = next(get_db())
    try:
        offset = (page - 1) * size
        if q:
            query = text(
                "SELECT symbol, name, market, industry, list_date "
                "FROM stock_list WHERE symbol LIKE :q OR name LIKE :q "
                "ORDER BY symbol LIMIT :limit OFFSET :offset"
            )
            count_query = text(
                "SELECT COUNT(*) FROM stock_list WHERE symbol LIKE :q OR name LIKE :q"
            )
            params = {"q": f"%{q}%", "limit": size, "offset": offset}
        else:
            query = text(
                "SELECT symbol, name, market, industry, list_date "
                "FROM stock_list ORDER BY symbol LIMIT :limit OFFSET :offset"
            )
            count_query = text("SELECT COUNT(*) FROM stock_list")
            params = {"limit": size, "offset": offset}

        rows = db.execute(query, params).fetchall()
        total = db.execute(
            count_query, {"q": f"%{q}%"} if q else {}
        ).scalar()

        items = [
            StockInfo(
                symbol=r[0],
                name=r[1],
                market=r[2],
                industry=r[3],
                list_date=r[4],
            )
            for r in rows
        ]
        return StockListResponse(items=items, total=total or 0)
    except Exception as e:
        logger.error(f"List stocks error: {e}")
        raise HTTPException(status_code=500, detail="查询股票列表失败")
    finally:
        db.close()


@router.get("/search")
async def search_stocks(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    _user: dict = Depends(get_current_user),
):
    """快速搜索股票（返回前20条匹配）。"""
    db = next(get_db())
    try:
        rows = db.execute(
            text(
                "SELECT symbol, name, market, industry FROM stock_list "
                "WHERE symbol LIKE :q OR name LIKE :q "
                "ORDER BY symbol LIMIT 20"
            ),
            {"q": f"%{q}%"},
        ).fetchall()
        return [
            {"symbol": r[0], "name": r[1], "market": r[2], "industry": r[3]}
            for r in rows
        ]
    finally:
        db.close()


@router.get("/{symbol}", response_model=StockInfo)
async def get_stock(
    symbol: str,
    _user: dict = Depends(get_current_user),
):
    """获取单个股票详情。"""
    db = next(get_db())
    try:
        row = db.execute(
            text(
                "SELECT symbol, name, market, industry, list_date "
                "FROM stock_list WHERE symbol = :s"
            ),
            {"s": symbol},
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"股票 {symbol} 未找到")
        return StockInfo(
            symbol=row[0], name=row[1], market=row[2],
            industry=row[3], list_date=row[4],
        )
    finally:
        db.close()
