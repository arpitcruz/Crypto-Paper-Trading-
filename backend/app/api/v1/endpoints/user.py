from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List
from uuid import UUID

from app.db.base import get_db
from app.models.user import User
from app.models.alert import PriceAlert, AlertCondition
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.trading import PriceAlertCreate
from app.api.v1.deps import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.username and payload.username != current_user.username:
        result = await db.execute(select(User).where(User.username == payload.username))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = payload.username

    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/me/alerts")
async def get_price_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PriceAlert)
        .where(and_(PriceAlert.user_id == current_user.id, PriceAlert.is_active == True))
        .order_by(desc(PriceAlert.created_at))
    )
    return result.scalars().all()


@router.post("/me/alerts", status_code=201)
async def create_price_alert(
    payload: PriceAlertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.core.config import settings
    if payload.symbol.upper() not in settings.SUPPORTED_PAIRS:
        raise HTTPException(status_code=400, detail="Unsupported trading pair")

    alert = PriceAlert(
        user_id=current_user.id,
        symbol=payload.symbol.upper(),
        target_price=payload.target_price,
        condition=AlertCondition(payload.condition),
        is_active=True,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.delete("/me/alerts/{alert_id}")
async def delete_price_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PriceAlert).where(
            and_(PriceAlert.id == alert_id, PriceAlert.user_id == current_user.id)
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.delete(alert)
    await db.commit()
    return {"message": "Alert deleted"}
