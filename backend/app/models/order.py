import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class OrderSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LIMIT = "stop_limit"
    STOP_MARKET = "stop_market"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class MarketType(str, enum.Enum):
    SPOT = "spot"
    FUTURES = "futures"


class PositionSide(str, enum.Enum):
    LONG = "long"
    SHORT = "short"


class MarginMode(str, enum.Enum):
    CROSS = "cross"
    ISOLATED = "isolated"


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    market_type = Column(Enum(MarketType), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)

    # Pricing
    price = Column(Float, nullable=True)       # Limit price
    stop_price = Column(Float, nullable=True)   # Stop trigger price
    avg_fill_price = Column(Float, nullable=True)

    # Quantity
    quantity = Column(Float, nullable=False)
    filled_quantity = Column(Float, default=0.0)
    remaining_quantity = Column(Float, nullable=False)

    # Futures specific
    leverage = Column(Integer, default=1)
    margin_mode = Column(Enum(MarginMode), default=MarginMode.CROSS, nullable=True)
    position_side = Column(Enum(PositionSide), nullable=True)
    margin_used = Column(Float, default=0.0)

    # Risk management
    take_profit = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)

    # Fees
    fee_rate = Column(Float, default=0.001)
    fee_amount = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    filled_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="orders")
    trades = relationship("Trade", back_populates="order")
