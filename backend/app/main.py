from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog

from app.core.config import settings
from app.db.base import engine, Base
from app.db.redis import init_redis, close_redis
from app.api.v1.router import api_router
from app.websocket.routes import router as ws_router
from app.websocket.manager import manager

logger = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Crypto Paper Trading API")

    # Initialize Redis
    await init_redis()
    logger.info("Redis connected")

    # Create database tables
    from app.models import (
        User, Wallet, Transaction, Order, Position, Trade,
        PriceAlert, UserSession, AdminLog
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")

    # Start Binance WebSocket stream
    stream_task = manager.start_background_stream()
    logger.info("Binance WebSocket stream started")

    yield

    # Cleanup
    stream_task.cancel()
    await close_redis()
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Crypto Paper Trading API

    Professional-grade paper trading platform with:
    - **Real live market data** from Binance
    - **Spot & Futures trading** simulation
    - **WebSocket** real-time price streaming
    - **Leverage** up to 100x with liquidation simulation
    - **PnL tracking** with ROE calculation
    - **Price alerts** and notifications
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("Request", method=request.method, path=request.url.path)
    response = await call_next(request)
    logger.info("Response", status_code=response.status_code)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Include routers
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
