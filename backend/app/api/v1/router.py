from fastapi import APIRouter
from app.api.v1.endpoints import auth, trading, market, user, admin

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(user.router)
api_router.include_router(trading.router)
api_router.include_router(market.router)
api_router.include_router(admin.router)
