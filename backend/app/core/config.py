from pydantic_settings import BaseSettings
from typing import List, Dict, Any
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Multi-Currency Global Portfolio Management System"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://portfolio_user:portfolio_pass@db:5432/portfolio_db"
    )
    # Sync fallback for Alembic or sync utilities if needed
    DATABASE_SYNC_URL: str = os.getenv(
        "DATABASE_SYNC_URL", 
        "postgresql://portfolio_user:portfolio_pass@db:5432/portfolio_db"
    )

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:80",
        "http://localhost:4200",
        "http://127.0.0.1",
        "http://127.0.0.1:4200",
        "*"
    ]

    # Market Polling Interval in minutes
    MARKET_POLL_INTERVAL_MINUTES: int = 5

    # Benchmark mappings by country
    DEFAULT_BENCHMARKS: Dict[str, Dict[str, str]] = {
        "US": {"ticker": "^GSPC", "name": "S&P 500", "currency": "USD"},
        "IN": {"ticker": "^NSEI", "name": "NIFTY 50", "currency": "INR"},
        "JP": {"ticker": "^N225", "name": "Nikkei 225", "currency": "JPY"},
        "GB": {"ticker": "^FTSE", "name": "FTSE 100", "currency": "GBP"},
        "EU": {"ticker": "^STOXX50E", "name": "Euro Stoxx 50", "currency": "EUR"},
        "CA": {"ticker": "^GSPTSE", "name": "S&P/TSX Composite", "currency": "CAD"},
        "HK": {"ticker": "^HSI", "name": "Hang Seng Index", "currency": "HKD"},
    }

    # Regional Market Trading Hours (Local time, 24-hr format)
    MARKET_SCHEDULES: Dict[str, Dict[str, Any]] = {
        "NYSE": {
            "name": "New York Stock Exchange",
            "timezone": "America/New_York",
            "open": "09:30",
            "close": "16:00",
            "country": "US",
            "currency": "USD"
        },
        "NSE": {
            "name": "National Stock Exchange of India",
            "timezone": "Asia/Kolkata",
            "open": "09:15",
            "close": "15:30",
            "country": "IN",
            "currency": "INR"
        },
        "TSE": {
            "name": "Tokyo Stock Exchange",
            "timezone": "Asia/Tokyo",
            "open": "09:00",
            "close": "15:00",
            "country": "JP",
            "currency": "JPY"
        },
        "LSE": {
            "name": "London Stock Exchange",
            "timezone": "Europe/London",
            "open": "08:00",
            "close": "16:30",
            "country": "GB",
            "currency": "GBP"
        },
        "EURONEXT": {
            "name": "Euronext Paris / Frankfurt",
            "timezone": "Europe/Paris",
            "open": "09:00",
            "close": "17:30",
            "country": "EU",
            "currency": "EUR"
        }
    }

    class Config:
        case_sensitive = True

settings = Settings()
