"""Seed script: creates admin + demo users, wallets, orders, positions, trades."""
import asyncio
import sys
sys.path.insert(0, '/home/user/Crypto-Paper-Trading-/backend')

from datetime import datetime, timezone, timedelta
from uuid import uuid4
from app.db.base import AsyncSessionLocal, engine
from app.models import User, Wallet, Transaction, Order, Position, Trade, AdminLog
from app.models.user import UserRole, AuthProvider
from app.models.wallet import WalletType, TransactionType
from app.models.order import OrderSide, OrderType, OrderStatus, MarketType, PositionSide, MarginMode
from app.models.position import PositionStatus
from app.core.security import get_password_hash


async def seed():
    async with AsyncSessionLocal() as db:
        # === Admin user ===
        admin = User(
            id=uuid4(), email="admin@cryptopaper.com", username="admin",
            hashed_password=get_password_hash("admin123"),
            full_name="System Admin", role=UserRole.ADMIN,
            auth_provider=AuthProvider.EMAIL, is_active=True, is_verified=True,
            last_login=datetime.now(timezone.utc),
        )
        db.add(admin)

        # === Demo users ===
        users = []
        demo_data = [
            ("trader_alex", "alex@demo.com", "Alex Turner", False),
            ("crypto_james", "james@demo.com", "James Wu", False),
            ("hodl_sara", "sara@demo.com", "Sara Khan", False),
            ("spammer99", "spammer@bad.io", "Spam Bot", True),
        ]
        for username, email, name, blocked in demo_data:
            u = User(
                id=uuid4(), email=email, username=username,
                hashed_password=get_password_hash("demo123"),
                full_name=name, role=UserRole.USER,
                auth_provider=AuthProvider.EMAIL, is_active=True,
                is_verified=True, is_blocked=blocked,
                last_login=datetime.now(timezone.utc) - timedelta(minutes=len(users) * 20 + 2),
                created_at=datetime.now(timezone.utc) - timedelta(days=30 - len(users) * 5),
            )
            db.add(u)
            users.append(u)
        await db.flush()

        # === Wallets ===
        def make_wallets(user, spot_balance, futures_balance):
            spot = Wallet(id=uuid4(), user_id=user.id, wallet_type=WalletType.SPOT,
                         balance=spot_balance, locked_balance=0.0, total_deposited=10000.0)
            fut = Wallet(id=uuid4(), user_id=user.id, wallet_type=WalletType.FUTURES,
                        balance=futures_balance, locked_balance=futures_balance * 0.08, total_deposited=0.0)
            return spot, fut

        admin_spot, admin_fut = make_wallets(admin, 10000.0, 0.0)
        alex_spot, alex_fut = make_wallets(users[0], 8760.50, 1239.50)
        james_spot, james_fut = make_wallets(users[1], 9200.0, 800.0)
        sara_spot, sara_fut = make_wallets(users[2], 12450.0, 550.0)
        spam_spot, spam_fut = make_wallets(users[3], 10000.0, 0.0)

        for w in [admin_spot, admin_fut, alex_spot, alex_fut,
                  james_spot, james_fut, sara_spot, sara_fut, spam_spot, spam_fut]:
            db.add(w)
        await db.flush()

        # === Orders for alex ===
        now = datetime.now(timezone.utc)
        orders_data = [
            ("BTCUSDT", MarketType.FUTURES, OrderType.MARKET, OrderSide.BUY, OrderStatus.FILLED,
             67234.50, 0.1, 10, 67234.50),
            ("ETHUSDT", MarketType.FUTURES, OrderType.MARKET, OrderSide.SELL, OrderStatus.FILLED,
             3521.80, 0.5, 20, 3521.80),
            ("SOLUSDT", MarketType.FUTURES, OrderType.LIMIT, OrderSide.BUY, OrderStatus.OPEN,
             170.00, 5, 15, None),
            ("BTCUSDT", MarketType.SPOT, OrderType.MARKET, OrderSide.BUY, OrderStatus.FILLED,
             66500.0, 0.05, 1, 66500.0),
            ("ETHUSDT", MarketType.SPOT, OrderType.LIMIT, OrderSide.BUY, OrderStatus.CANCELLED,
             3400.0, 0.3, 1, None),
        ]
        for sym, mtype, otype, side, status, price, qty, lev, fill in orders_data:
            o = Order(
                id=uuid4(), user_id=users[0].id, symbol=sym, market_type=mtype,
                order_type=otype, side=side, status=status, price=price,
                avg_fill_price=fill, quantity=qty, filled_quantity=qty if fill else 0,
                remaining_quantity=0 if fill else qty, leverage=lev,
                margin_mode=MarginMode.CROSS, fee_rate=0.001, fee_amount=price*qty*0.001 if fill else 0,
                created_at=now - timedelta(hours=len(orders_data)),
                filled_at=now - timedelta(hours=len(orders_data)-1) if fill else None,
            )
            db.add(o)
        await db.flush()

        # === Positions for alex ===
        pos_data = [
            ("BTCUSDT", PositionSide.LONG, 0.1, 66811.35, 67234.50, 10, 668.11),
            ("ETHUSDT", PositionSide.SHORT, 0.5, 3434.50, 3521.80, 20, 88.05),
            ("SOLUSDT", PositionSide.LONG, 5.0, 171.15, 178.42, 15, 57.05),
        ]
        for sym, side, qty, entry, current, lev, margin in pos_data:
            liq = entry * (1 - 1/lev + 0.005) if side == PositionSide.LONG else entry * (1 + 1/lev - 0.005)
            if side == PositionSide.LONG:
                upnl = (current - entry) * qty * lev
            else:
                upnl = (entry - current) * qty * lev
            p = Position(
                id=uuid4(), user_id=users[0].id, symbol=sym, side=side,
                status=PositionStatus.OPEN, margin_mode=MarginMode.CROSS,
                quantity=qty, entry_price=entry, current_price=current,
                leverage=lev, initial_margin=margin, maintenance_margin=margin*0.05,
                unrealized_pnl=upnl, realized_pnl=0.0, total_fee=margin*0.001,
                liquidation_price=liq, take_profit=entry*1.1, stop_loss=entry*0.95,
                opened_at=now - timedelta(hours=6),
            )
            db.add(p)

        # === Trades for all users ===
        for i, user in enumerate(users):
            for j in range(10):
                side = OrderSide.BUY if j % 2 == 0 else OrderSide.SELL
                price = 65000 + j * 500
                qty = 0.01 + j * 0.005
                pnl = (j - 4) * 25.0
                t = Trade(
                    id=uuid4(), user_id=user.id, symbol="BTCUSDT",
                    market_type=MarketType.FUTURES, side=side, price=price,
                    quantity=qty, value=price * qty, fee=price * qty * 0.001,
                    realized_pnl=pnl,
                    executed_at=now - timedelta(days=j, hours=i*2),
                )
                db.add(t)

        # === Admin log ===
        log = AdminLog(
            id=uuid4(), admin_id=admin.id, action="update_user",
            target_user_id=users[3].id, details="is_blocked=True",
            created_at=now - timedelta(hours=2),
        )
        db.add(log)

        await db.commit()
        print("Seed data inserted successfully!")
        print(f"Admin login: admin@cryptopaper.com / admin123")


asyncio.run(seed())
