# 🪙 CryptoPaper — Professional Crypto Paper Trading Platform

A production-grade crypto paper trading platform with **real live market data** from Binance,
supporting Spot + Futures simulation with leverage up to 100x.

---

## 🏗️ Architecture

```
CryptoPaper/
├── backend/          # FastAPI Python backend
├── admin/            # React admin dashboard (web)
├── mobile/           # Flutter Android/iOS app
├── nginx/            # Reverse proxy configuration
└── docker-compose.yml
```

## 🔧 Tech Stack

| Layer        | Technology                                    |
|--------------|-----------------------------------------------|
| Backend      | FastAPI, SQLAlchemy (async), Alembic           |
| Database     | PostgreSQL 15                                 |
| Cache        | Redis 7                                       |
| Queue        | Celery + Redis broker                         |
| Real-time    | WebSocket (Binance stream + custom WS server) |
| Mobile       | Flutter (Dart)                                |
| Admin Panel  | React 18 + TypeScript + TailwindCSS + Vite    |
| Proxy        | Nginx                                         |
| Container    | Docker + Docker Compose                       |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Flutter SDK (for mobile)
- Node.js 18+ (for admin panel dev)

### 1. Clone and configure
```bash
git clone <repo-url>
cd Crypto-Paper-Trading-
cp .env.example .env
# Edit .env with your values
```

### 2. Start all services
```bash
docker-compose up -d
```

### 3. Verify it's running
```
API:    http://localhost:8000
Docs:   http://localhost:8000/docs
Admin:  http://localhost:3001 (run separately)
```

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint                  | Description              |
|--------|---------------------------|--------------------------|
| POST   | `/api/v1/auth/register`   | Register new user        |
| POST   | `/api/v1/auth/login`      | Email/password login     |
| POST   | `/api/v1/auth/google`     | Google OAuth login       |
| POST   | `/api/v1/auth/refresh`    | Refresh access token     |
| POST   | `/api/v1/auth/logout`     | Logout / revoke session  |
| POST   | `/api/v1/auth/forgot-password` | Request password reset |
| POST   | `/api/v1/auth/reset-password`  | Reset password          |

### Market Data
| Method | Endpoint                      | Description              |
|--------|-------------------------------|--------------------------|
| GET    | `/api/v1/market/tickers`      | All 15+ live tickers     |
| GET    | `/api/v1/market/ticker/{sym}` | 24h ticker for symbol    |
| GET    | `/api/v1/market/price/{sym}`  | Current price            |
| GET    | `/api/v1/market/klines/{sym}` | Candlestick OHLCV data   |
| GET    | `/api/v1/market/orderbook/{sym}` | Order book depth      |

### Trading
| Method | Endpoint                         | Description               |
|--------|----------------------------------|---------------------------|
| POST   | `/api/v1/trading/orders`         | Place order (spot/futures) |
| GET    | `/api/v1/trading/orders`         | Get order history          |
| DELETE | `/api/v1/trading/orders/{id}`    | Cancel open order          |
| GET    | `/api/v1/trading/positions`      | Get open/closed positions  |
| POST   | `/api/v1/trading/positions/close` | Close futures position    |
| PUT    | `/api/v1/trading/positions/risk` | Update TP/SL               |
| GET    | `/api/v1/trading/trades`         | Trade execution history    |
| GET    | `/api/v1/trading/wallet`         | Get wallet balances        |
| POST   | `/api/v1/trading/wallet/transfer` | Transfer between wallets  |
| POST   | `/api/v1/trading/wallet/reset`   | Reset wallet to default    |
| GET    | `/api/v1/trading/stats`          | Trading statistics         |

### Admin (requires admin role)
| Method | Endpoint                    | Description                  |
|--------|-----------------------------|------------------------------|
| GET    | `/api/v1/admin/users`       | List all users (with search) |
| GET    | `/api/v1/admin/users/stats` | System statistics            |
| PUT    | `/api/v1/admin/users/{id}`  | Update user / adjust wallet  |
| GET    | `/api/v1/admin/logs`        | Admin audit logs             |
| GET    | `/api/v1/admin/positions`   | All user positions           |

---

## 🔌 WebSocket Streams

### Market prices (public)
```
ws://localhost:8000/ws/market          # All supported pairs
ws://localhost:8000/ws/market/BTCUSDT  # Specific symbol
```

**Message format:**
```json
{
  "type": "ticker",
  "symbol": "BTCUSDT",
  "price": 67234.50,
  "change_24h": 2.34,
  "high_24h": 68000.0,
  "low_24h": 65000.0,
  "volume_24h": 12345.67
}
```

### User stream (authenticated)
```
ws://localhost:8000/ws/user?token=<access_token>
```

**Receives:**
- Real-time PnL updates for open positions
- Price alert triggers
- Order fill notifications

---

## 📈 Trading Engine

### Spot Trading
- Market, Limit, Stop-Limit orders
- SL/TP support
- Fee simulation (0.1%)
- Trade history

### Futures Trading
- Leverage: 1x–100x
- Long/Short positions
- Cross & Isolated margin
- Liquidation simulation
- Funding fee every 8h (0.01%)
- Real-time unrealized PnL

**PnL Formula:**
```
Long PnL  = (currentPrice - entryPrice) × quantity × leverage
Short PnL = (entryPrice - currentPrice) × quantity × leverage
ROE%      = PnL / initialMargin × 100
```

**Liquidation Price:**
```
Long Liq  = entryPrice × (1 - 1/leverage + 0.005)
Short Liq = entryPrice × (1 + 1/leverage - 0.005)
```

---

## 🔐 Security

- JWT access tokens (60min) + refresh tokens (30 days)
- Bcrypt password hashing
- Per-route rate limiting via SlowAPI
- Nginx rate limiting (60 req/min API, 10 req/min auth)
- SQL injection protection via SQLAlchemy ORM
- Input validation via Pydantic v2
- Admin audit logs for all actions

---

## 📱 Mobile App (Flutter)

### Screens
- **Markets** — Live prices for all 15+ pairs, WebSocket-updated
- **Trade** — Spot & Futures order placement with leverage slider
- **Positions** — Real-time PnL updates, close positions
- **Wallet** — Balance overview, statistics, wallet reset
- **Profile** — User info, logout

### Building APK
```bash
cd mobile
flutter pub get
flutter build apk --release \
  --dart-define=API_URL=http://your-server:8000/api/v1 \
  --dart-define=WS_URL=ws://your-server:8000
```

---

## 🖥️ Admin Panel (React)

### Features
- System stats dashboard with charts
- User management (block/unblock, role management)
- Wallet adjustments (add/remove virtual funds)
- Live position monitoring
- Admin action audit logs

### Development
```bash
cd admin
npm install
npm run dev   # http://localhost:3001
```

### Production build
```bash
npm run build
# Serve dist/ from any static host
```

---

## ⚙️ Configuration

Key environment variables (see `.env.example`):

| Variable                  | Default     | Description                 |
|---------------------------|-------------|-----------------------------|
| `SECRET_KEY`              | required    | JWT signing secret          |
| `DATABASE_URL`            | see compose | PostgreSQL connection string |
| `REDIS_URL`               | see compose | Redis connection string      |
| `DEFAULT_WALLET_BALANCE`  | 10000.0     | Starting virtual balance    |
| `MAX_LEVERAGE`            | 100         | Maximum allowed leverage    |
| `TRADING_FEE_SPOT`        | 0.001       | Spot fee (0.1%)             |
| `TRADING_FEE_FUTURES`     | 0.0004      | Futures fee (0.04%)         |
| `GOOGLE_CLIENT_ID`        | optional    | For Google OAuth            |

---

## 🗄️ Database Schema

### Core Tables
- **users** — Auth info, role, provider
- **wallets** — Spot + Futures balances per user
- **orders** — All orders with status tracking
- **positions** — Open/closed futures positions
- **trades** — Executed trade records
- **transactions** — Full wallet transaction log
- **price_alerts** — User-configured price alerts
- **user_sessions** — Refresh token tracking
- **admin_logs** — Audit trail for admin actions

---

## 🐳 Deployment

### Docker Compose (recommended)
```bash
docker-compose up -d --build
docker-compose logs -f backend
```

### Manual migrations
```bash
cd backend
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### Cloud deployment
- **AWS**: ECS + RDS + ElastiCache + ALB
- **DigitalOcean**: App Platform + Managed DB
- **VPS**: Docker Compose + Caddy/Nginx

---

## 📊 Supported Trading Pairs

BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT,
DOGEUSDT, AVAXUSDT, LINKUSDT, DOTUSDT, MATICUSDT, LTCUSDT,
UNIUSDT, ATOMUSDT, FTMUSDT

*(Add more by updating `SUPPORTED_PAIRS` in `config.py`)*

---

## 🔮 Roadmap

- [ ] Leaderboard system
- [ ] Copy trading simulation
- [ ] Backtesting module
- [ ] AI trade analysis
- [ ] Strategy builder
- [ ] Multi-language support
- [ ] iOS build (already Flutter-ready)
- [ ] TradingView chart integration
- [ ] Order book depth chart