from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.db.base import get_db
from app.models.user import User, AuthProvider
from app.models.alert import UserSession
from app.schemas.auth import (
    UserRegister, UserLogin, GoogleLogin, TokenResponse,
    RefreshTokenRequest, ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
)
from app.schemas.user import UserResponse
from app.core.security import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, verify_token, create_password_reset_token
)
from app.core.config import settings
from app.services.wallet_service import get_or_create_wallets
from app.api.v1.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        auth_provider=AuthProvider.EMAIL,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()

    # Create wallets for new user
    await get_or_create_wallets(db, user.id)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Account is blocked")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # Store session
    session = UserSession(
        user_id=user.id,
        refresh_token=refresh_token,
        device_info=request.headers.get("User-Agent", "Unknown"),
        ip_address=request.client.host if request.client else "Unknown",
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)

    user.last_login = datetime.utcnow()
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/google", response_model=TokenResponse)
async def google_login(payload: GoogleLogin, db: AsyncSession = Depends(get_db)):
    # Verify Google token
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={payload.token}"
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Google token")
        google_data = resp.json()

    email = google_data.get("email")
    google_id = google_data.get("sub")
    full_name = google_data.get("name")
    avatar_url = google_data.get("picture")

    if not email or not google_id:
        raise HTTPException(status_code=400, detail="Unable to extract user info from Google token")

    # Find or create user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        username = email.split("@")[0]
        # Ensure unique username
        base_username = username
        counter = 1
        while True:
            result = await db.execute(select(User).where(User.username == username))
            if not result.scalar_one_or_none():
                break
            username = f"{base_username}{counter}"
            counter += 1

        user = User(
            email=email,
            username=username,
            full_name=full_name,
            avatar_url=avatar_url,
            google_id=google_id,
            auth_provider=AuthProvider.GOOGLE,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()
        await get_or_create_wallets(db, user.id)

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    user.last_login = datetime.utcnow()
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    token_data = verify_token(payload.refresh_token)
    if not token_data or token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(
        select(UserSession).where(
            UserSession.refresh_token == payload.refresh_token,
            UserSession.is_active == True,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=401, detail="Session not found or expired")

    user_id = token_data["sub"]
    new_access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)

    session.refresh_token = new_refresh_token
    session.expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserSession).where(UserSession.refresh_token == payload.refresh_token)
    )
    session = result.scalar_one_or_none()
    if session:
        session.is_active = False
        await db.commit()
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    # Don't reveal if user exists
    if user:
        token = create_password_reset_token(payload.email)
        # In production, send email with token
        # await send_password_reset_email(user.email, token)
    return {"message": "If the email is registered, you will receive a reset link"}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    token_data = verify_token(payload.token)
    if not token_data or token_data.get("type") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    email = token_data["sub"]
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(payload.new_password)
    await db.commit()
    return {"message": "Password reset successfully"}


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(payload.new_password)
    await db.commit()
    return {"message": "Password changed successfully"}
