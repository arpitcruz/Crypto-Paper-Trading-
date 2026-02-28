from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.wallet import Wallet, Transaction, WalletType, TransactionType
from app.core.config import settings
import structlog

logger = structlog.get_logger()


async def get_or_create_wallets(db: AsyncSession, user_id: UUID) -> dict:
    """Get both wallets for a user, creating them if not exist."""
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallets = {w.wallet_type: w for w in result.scalars().all()}

    for wtype in [WalletType.SPOT, WalletType.FUTURES]:
        if wtype not in wallets:
            wallet = Wallet(
                user_id=user_id,
                wallet_type=wtype,
                balance=settings.DEFAULT_WALLET_BALANCE if wtype == WalletType.SPOT else 0.0,
                total_deposited=settings.DEFAULT_WALLET_BALANCE if wtype == WalletType.SPOT else 0.0,
            )
            db.add(wallet)
            wallets[wtype] = wallet
    await db.flush()
    return wallets


async def get_wallet(db: AsyncSession, user_id: UUID, wallet_type: WalletType) -> Wallet:
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user_id, Wallet.wallet_type == wallet_type)
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        wallets = await get_or_create_wallets(db, user_id)
        wallet = wallets[wallet_type]
    return wallet


async def record_transaction(
    db: AsyncSession,
    user_id: UUID,
    wallet: Wallet,
    transaction_type: TransactionType,
    amount: float,
    description: str = None,
    reference_id: str = None,
) -> Transaction:
    tx = Transaction(
        user_id=user_id,
        wallet_type=wallet.wallet_type,
        transaction_type=transaction_type,
        amount=amount,
        balance_before=wallet.balance,
        balance_after=wallet.balance + amount,
        description=description,
        reference_id=reference_id,
    )
    db.add(tx)
    return tx


async def debit_wallet(
    db: AsyncSession,
    user_id: UUID,
    wallet_type: WalletType,
    amount: float,
    transaction_type: TransactionType,
    description: str = None,
    reference_id: str = None,
    lock_balance: bool = False,
) -> Wallet:
    wallet = await get_wallet(db, user_id, wallet_type)

    available = wallet.balance - wallet.locked_balance
    if available < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance. Available: ${available:.2f}, Required: ${amount:.2f}"
        )

    wallet.balance -= amount
    if lock_balance:
        wallet.locked_balance += amount

    await record_transaction(
        db, user_id, wallet, transaction_type, -amount, description, reference_id
    )
    await db.flush()
    return wallet


async def credit_wallet(
    db: AsyncSession,
    user_id: UUID,
    wallet_type: WalletType,
    amount: float,
    transaction_type: TransactionType,
    description: str = None,
    reference_id: str = None,
    unlock_balance: float = 0.0,
) -> Wallet:
    wallet = await get_wallet(db, user_id, wallet_type)
    wallet.balance += amount

    if unlock_balance > 0:
        wallet.locked_balance = max(0.0, wallet.locked_balance - unlock_balance)

    await record_transaction(
        db, user_id, wallet, transaction_type, amount, description, reference_id
    )
    await db.flush()
    return wallet


async def lock_balance(db: AsyncSession, user_id: UUID, wallet_type: WalletType, amount: float) -> Wallet:
    wallet = await get_wallet(db, user_id, wallet_type)
    available = wallet.balance - wallet.locked_balance
    if available < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance to lock. Available: ${available:.2f}"
        )
    wallet.locked_balance += amount
    await db.flush()
    return wallet


async def unlock_balance(db: AsyncSession, user_id: UUID, wallet_type: WalletType, amount: float) -> Wallet:
    wallet = await get_wallet(db, user_id, wallet_type)
    wallet.locked_balance = max(0.0, wallet.locked_balance - amount)
    await db.flush()
    return wallet


async def transfer_between_wallets(
    db: AsyncSession,
    user_id: UUID,
    from_type: WalletType,
    to_type: WalletType,
    amount: float,
) -> dict:
    if from_type == to_type:
        raise HTTPException(status_code=400, detail="Cannot transfer to same wallet")

    from_wallet = await get_wallet(db, user_id, from_type)
    available = from_wallet.balance - from_wallet.locked_balance
    if available < amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: ${available:.2f}"
        )

    from_wallet.balance -= amount
    await record_transaction(
        db, user_id, from_wallet, TransactionType.TRANSFER,
        -amount, f"Transfer to {to_type.value} wallet"
    )

    to_wallet = await get_wallet(db, user_id, to_type)
    to_wallet.balance += amount
    await record_transaction(
        db, user_id, to_wallet, TransactionType.TRANSFER,
        amount, f"Transfer from {from_type.value} wallet"
    )

    await db.flush()
    return {"from_wallet": from_wallet, "to_wallet": to_wallet}


async def reset_wallet(db: AsyncSession, user_id: UUID) -> dict:
    """Reset both wallets to default balance."""
    wallets = await get_or_create_wallets(db, user_id)
    for wallet in wallets.values():
        old_balance = wallet.balance
        wallet.balance = settings.DEFAULT_WALLET_BALANCE if wallet.wallet_type == WalletType.SPOT else 0.0
        wallet.locked_balance = 0.0
        await record_transaction(
            db, user_id, wallet, TransactionType.ADMIN_ADJUSTMENT,
            wallet.balance - old_balance, "Wallet reset"
        )
    await db.flush()
    return wallets
