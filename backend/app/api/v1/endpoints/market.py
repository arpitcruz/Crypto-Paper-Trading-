from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.services.market_data import (
    fetch_current_price, fetch_ticker_24h, fetch_all_tickers,
    fetch_klines, fetch_orderbook
)
from app.core.config import settings

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get("/pairs")
async def get_supported_pairs():
    return {"pairs": settings.SUPPORTED_PAIRS}


@router.get("/tickers")
async def get_all_tickers():
    tickers = await fetch_all_tickers()
    return {"tickers": tickers, "count": len(tickers)}


@router.get("/ticker/{symbol}")
async def get_ticker(symbol: str):
    symbol = symbol.upper()
    if symbol not in settings.SUPPORTED_PAIRS:
        raise HTTPException(status_code=400, detail=f"Unsupported pair: {symbol}")
    data = await fetch_ticker_24h(symbol)
    if not data:
        raise HTTPException(status_code=503, detail="Failed to fetch market data")
    return data


@router.get("/price/{symbol}")
async def get_price(symbol: str):
    symbol = symbol.upper()
    price = await fetch_current_price(symbol)
    if not price:
        raise HTTPException(status_code=503, detail="Failed to fetch price")
    return {"symbol": symbol, "price": price}


@router.get("/klines/{symbol}")
async def get_klines(
    symbol: str,
    interval: str = Query(default="1h"),
    limit: int = Query(default=200, le=1000),
):
    symbol = symbol.upper()
    if symbol not in settings.SUPPORTED_PAIRS:
        raise HTTPException(status_code=400, detail=f"Unsupported pair: {symbol}")
    klines = await fetch_klines(symbol, interval, limit)
    return {"symbol": symbol, "interval": interval, "data": klines}


@router.get("/orderbook/{symbol}")
async def get_orderbook(symbol: str, limit: int = Query(default=20, le=100)):
    symbol = symbol.upper()
    if symbol not in settings.SUPPORTED_PAIRS:
        raise HTTPException(status_code=400, detail=f"Unsupported pair: {symbol}")
    data = await fetch_orderbook(symbol, limit)
    if not data:
        raise HTTPException(status_code=503, detail="Failed to fetch order book")
    return data
