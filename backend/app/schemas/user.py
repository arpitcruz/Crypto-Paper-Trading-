from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.user import UserRole, AuthProvider


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    role: UserRole
    auth_provider: AuthProvider
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None


class UserStats(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    best_trade: float
    worst_trade: float
    total_volume: float

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_blocked: Optional[bool] = None
    role: Optional[UserRole] = None
    wallet_adjustment: Optional[float] = None
    wallet_type: Optional[str] = None
