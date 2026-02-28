import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.models.order import PositionSide, MarginMode
import enum


class PositionStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"


class Position(Base):
    __tablename__ = "positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(PositionSide), nullable=False)
    status = Column(Enum(PositionStatus), default=PositionStatus.OPEN, nullable=False, index=True)
    margin_mode = Column(Enum(MarginMode), default=MarginMode.CROSS, nullable=False)

    # Position sizing
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    leverage = Column(Integer, default=1, nullable=False)

    # Margin
    initial_margin = Column(Float, nullable=False)
    maintenance_margin = Column(Float, nullable=False)
    margin_ratio = Column(Float, default=0.0)

    # PnL
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    total_fee = Column(Float, default=0.0)
    funding_fee = Column(Float, default=0.0)

    # Risk
    liquidation_price = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    bankruptcy_price = Column(Float, nullable=True)

    # Timestamps
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Close info
    close_price = Column(Float, nullable=True)
    close_reason = Column(String(50), nullable=True)  # manual, liquidation, tp, sl

    # Relationships
    user = relationship("User", back_populates="positions")

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        if self.side == PositionSide.LONG:
            return (current_price - self.entry_price) * self.quantity * self.leverage
        else:
            return (self.entry_price - current_price) * self.quantity * self.leverage

    def calculate_roe(self, current_price: float) -> float:
        pnl = self.calculate_unrealized_pnl(current_price)
        if self.initial_margin > 0:
            return (pnl / self.initial_margin) * 100
        return 0.0

    def calculate_liquidation_price(self) -> float:
        maintenance_margin_rate = 0.005  # 0.5%
        if self.side == PositionSide.LONG:
            liq_price = self.entry_price * (1 - (1 / self.leverage) + maintenance_margin_rate)
        else:
            liq_price = self.entry_price * (1 + (1 / self.leverage) - maintenance_margin_rate)
        return max(0.0, liq_price)
