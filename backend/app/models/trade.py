import uuid
from sqlalchemy import Column, String, Float, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.models.order import OrderSide, MarketType
import enum


class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    position_id = Column(UUID(as_uuid=True), nullable=True)
    symbol = Column(String(20), nullable=False, index=True)
    market_type = Column(Enum(MarketType), nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    value = Column(Float, nullable=False)  # price * quantity
    fee = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="trades")
    order = relationship("Order", back_populates="trades")
