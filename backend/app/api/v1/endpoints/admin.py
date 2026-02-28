from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from uuid import UUID

from app.db.base import get_db
from app.models.user import User, UserRole
from app.models.wallet import Wallet, WalletType, Transaction, TransactionType
from app.models.order import Order
from app.models.position import Position
from app.models.alert import AdminLog
from app.schemas.user import UserResponse, AdminUserUpdate
from app.services.wallet_service import get_wallet, record_transaction
from app.api.v1.deps import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    is_blocked: Optional[bool] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)
    if search:
        query = query.where(
            (User.email.ilike(f"%{search}%")) | (User.username.ilike(f"%{search}%"))
        )
    if role:
        query = query.where(User.role == role)
    if is_blocked is not None:
        query = query.where(User.is_blocked == is_blocked)
    query = query.order_by(desc(User.created_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/users/stats")
async def get_system_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(select(func.count(User.id)).where(User.is_active == True))
    blocked_users = await db.scalar(select(func.count(User.id)).where(User.is_blocked == True))
    total_orders = await db.scalar(select(func.count(Order.id)))
    open_positions = await db.scalar(
        select(func.count(Position.id)).where(Position.status == "open")
    )

    return {
        "total_users": total_users,
        "active_users": active_users,
        "blocked_users": blocked_users,
        "total_orders": total_orders,
        "open_positions": open_positions,
    }


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}")
async def update_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes = []

    if payload.is_active is not None:
        user.is_active = payload.is_active
        changes.append(f"is_active={payload.is_active}")

    if payload.is_blocked is not None:
        user.is_blocked = payload.is_blocked
        changes.append(f"is_blocked={payload.is_blocked}")

    if payload.role is not None:
        user.role = payload.role
        changes.append(f"role={payload.role}")

    if payload.wallet_adjustment and payload.wallet_type:
        wallet_type = WalletType(payload.wallet_type)
        wallet = await get_wallet(db, user_id, wallet_type)
        old_balance = wallet.balance
        wallet.balance = max(0.0, wallet.balance + payload.wallet_adjustment)
        await record_transaction(
            db, user_id, wallet,
            TransactionType.ADMIN_ADJUSTMENT,
            payload.wallet_adjustment,
            f"Admin adjustment by {admin.username}",
            str(admin.id),
        )
        changes.append(f"wallet_adjustment={payload.wallet_adjustment}")

    # Log admin action
    log = AdminLog(
        admin_id=admin.id,
        action="update_user",
        target_user_id=user_id,
        details=", ".join(changes),
    )
    db.add(log)
    await db.commit()

    return {"message": "User updated", "changes": changes}


@router.get("/logs")
async def get_admin_logs(
    limit: int = Query(default=100, le=500),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AdminLog).order_by(desc(AdminLog.created_at)).limit(limit)
    )
    return result.scalars().all()


@router.get("/positions")
async def get_all_positions(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Position)
    if symbol:
        query = query.where(Position.symbol == symbol)
    if status:
        query = query.where(Position.status == status)
    query = query.order_by(desc(Position.opened_at)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
