from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "CryptoPaper Trading"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://cryptouser:cryptopass@localhost:5432/cryptopaper"

    # Redis
    REDIS_URL: str = "redis://:redispass@localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://:redispass@localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://:redispass@localhost:6379/2"

    # Binance
    BINANCE_WS_URL: str = "wss://stream.binance.com:9443/ws"
    BINANCE_REST_URL: str = "https://api.binance.com"

    # Wallet
    DEFAULT_WALLET_BALANCE: float = 10000.0
    TRADING_FEE_SPOT: float = 0.001  # 0.1%
    TRADING_FEE_FUTURES: float = 0.0004  # 0.04%

    # Leverage
    MAX_LEVERAGE: int = 100
    DEFAULT_LEVERAGE: int = 1

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # Mail
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: str = "noreply@cryptopaper.com"
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587

    # Supported Trading Pairs
    SUPPORTED_PAIRS: list = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
        "MATICUSDT", "LTCUSDT", "UNIUSDT", "ATOMUSDT", "FTMUSDT"
    ]

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
