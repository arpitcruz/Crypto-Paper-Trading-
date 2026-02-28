import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class WalletType(str, enum.Enum):
    SPOT = "spot"
    FUTURES = "futures"


class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRADE_FEE = "trade_fee"
    REALIZED_PNL = "realized_pnl"
    FUNDING_FEE = "funding_fee"
    LIQUIDATION = "liquidation"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    TRANSFER = "transfer"


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wallet_type = Column(Enum(WalletType), nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    locked_balance = Column(Float, default=0.0, nullable=False)  # In open orders/positions
    total_deposited = Column(Float, default=0.0)
    total_withdrawn = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="wallets")

    @property
    def available_balance(self) -> float:
        return max(0.0, self.balance - self.locked_balance)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wallet_type = Column(Enum(WalletType), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    reference_id = Column(String(255), nullable=True)  # Order ID / Trade ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="transactions")
