"""QuantInvest FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config.settings import ensure_dirs, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    ensure_dirs()

    # Initialize database
    from api.dependencies import get_storage
    get_storage()

    logger.info(f"Server running on {settings.HOST}:{settings.PORT}")
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="个人量化投资分析平台 API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — 当允许所有来源(*)时，凭证必须关闭（Starlette 规则）
_cors_origins = settings.cors_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from api.routes.auth import router as auth_router
from api.routes.stocks import router as stocks_router
from api.routes.data import router as data_router
from api.routes.indicators import router as indicators_router
from api.routes.backtest import router as backtest_router
from api.routes.screener import router as screener_router
from api.routes.signals import router as signals_router

app.include_router(auth_router)
app.include_router(stocks_router)
app.include_router(data_router)
app.include_router(indicators_router)
app.include_router(backtest_router)
app.include_router(screener_router)
app.include_router(signals_router)


@app.get("/")
async def root():
    """应用信息。"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
async def health():
    """健康检查。"""
    return {"status": "ok"}
