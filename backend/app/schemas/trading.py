from pydantic import BaseModel, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.order import OrderSide, OrderType, MarketType, PositionSide, MarginMode, OrderStatus
from app.models.position import PositionStatus
from app.models.wallet import WalletType


class PlaceOrderRequest(BaseModel):
    symbol: str
    market_type: MarketType
    order_type: OrderType
    side: OrderSide
    quantity: float
    price: Optional[float] = None         # For limit orders
    stop_price: Optional[float] = None    # For stop orders
    leverage: Optional[int] = 1           # Futures only
    margin_mode: Optional[MarginMode] = MarginMode.CROSS
    position_side: Optional[PositionSide] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("leverage")
    @classmethod
    def validate_leverage(cls, v):
        if v and (v < 1 or v > 100):
            raise ValueError("Leverage must be between 1 and 100")
        return v


class OrderResponse(BaseModel):
    id: UUID
    user_id: UUID
    symbol: str
    market_type: MarketType
    order_type: OrderType
    side: OrderSide
    status: OrderStatus
    price: Optional[float]
    stop_price: Optional[float]
    avg_fill_price: Optional[float]
    quantity: float
    filled_quantity: float
    remaining_quantity: float
    leverage: int
    margin_mode: Optional[MarginMode]
    position_side: Optional[PositionSide]
    take_profit: Optional[float]
    stop_loss: Optional[float]
    fee_amount: float
    created_at: datetime
    filled_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PositionResponse(BaseModel):
    id: UUID
    user_id: UUID
    symbol: str
    side: PositionSide
    status: PositionStatus
    margin_mode: MarginMode
    quantity: float
    entry_price: float
    current_price: Optional[float]
    leverage: int
    initial_margin: float
    maintenance_margin: float
    unrealized_pnl: float
    realized_pnl: float
    total_fee: float
    funding_fee: float
    liquidation_price: Optional[float]
    take_profit: Optional[float]
    stop_loss: Optional[float]
    margin_ratio: float
    roe_percent: Optional[float] = None
    opened_at: datetime
    closed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ClosePositionRequest(BaseModel):
    position_id: UUID
    quantity: Optional[float] = None  # None = close all


class UpdatePositionRiskRequest(BaseModel):
    position_id: UUID
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None


class TradeResponse(BaseModel):
    id: UUID
    symbol: str
    market_type: MarketType
    side: OrderSide
    price: float
    quantity: float
    value: float
    fee: float
    realized_pnl: float
    executed_at: datetime

    model_config = {"from_attributes": True}


class WalletResponse(BaseModel):
    id: UUID
    wallet_type: WalletType
    balance: float
    locked_balance: float
    available_balance: float
    total_deposited: float

    model_config = {"from_attributes": True}


class TransferRequest(BaseModel):
    amount: float
    from_wallet: WalletType
    to_wallet: WalletType

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class PriceAlertCreate(BaseModel):
    symbol: str
    target_price: float
    condition: str  # "above" or "below"

    @field_validator("target_price")
    @classmethod
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError("Target price must be positive")
        return v


class MarketDataResponse(BaseModel):
    symbol: str
    price: float
    change_24h: float
    change_percent_24h: float
    high_24h: float
    low_24h: float
    volume_24h: float
    market_cap: Optional[float] = None
