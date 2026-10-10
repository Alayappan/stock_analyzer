import asyncio
from contextlib import asynccontextmanager
from decimal import Decimal
from datetime import datetime
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.models.portfolio import Portfolio, SubPortfolio
from app.models.transaction import Transaction
from app.models.market import MarketCache, FxRate
from app.services.scheduler import start_scheduler, stop_scheduler, sync_all_markets
from app.routers import (
    portfolios_router,
    transactions_router,
    import_router,
    market_router,
    analytics_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("portfolio_system")

async def seed_initial_data_if_empty():
    """Seed initial master portfolio and starter holdings if database is fresh."""
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(Portfolio).where(Portfolio.id == 1)
            res = await session.execute(stmt)
            existing_p = res.scalar_one_or_none()
            
            if not existing_p:
                logger.info("Database is empty. Seeding initial master portfolio and demo sub-portfolios...")
                master = Portfolio(
                    id=1,
                    name="Global Wealth Master",
                    description="Multi-currency global diversified portfolio tracking US, India, and Japan markets",
                    base_currency="USD"
                )
                session.add(master)
                await session.flush()

                # Sub-portfolios
                us_sub = SubPortfolio(
                    id=1,
                    portfolio_id=1,
                    name="US Bluechips & Tech",
                    country="US",
                    currency="USD",
                    benchmark_ticker="^GSPC",
                    cash_balance=Decimal("25000.0000")
                )
                in_sub = SubPortfolio(
                    id=2,
                    portfolio_id=1,
                    name="India Growth Equities",
                    country="IN",
                    currency="INR",
                    benchmark_ticker="^NSEI",
                    cash_balance=Decimal("500000.0000")
                )
                jp_sub = SubPortfolio(
                    id=3,
                    portfolio_id=1,
                    name="Japan High-Tech & Auto",
                    country="JP",
                    currency="JPY",
                    benchmark_ticker="^N225",
                    cash_balance=Decimal("1500000.0000")
                )
                session.add_all([us_sub, in_sub, jp_sub])
                await session.flush()

                # Seed realistic starter transactions
                initial_transactions = [
                    # US Holdings
                    Transaction(sub_portfolio_id=1, type="BUY", ticker="AAPL", shares=Decimal("40"), price_per_share=Decimal("185.50"), fees=Decimal("0.00"), total_amount=Decimal("7420.00"), currency="USD", notes="Core holding"),
                    Transaction(sub_portfolio_id=1, type="BUY", ticker="MSFT", shares=Decimal("25"), price_per_share=Decimal("402.10"), fees=Decimal("0.00"), total_amount=Decimal("10052.50"), currency="USD", notes="Cloud & AI"),
                    Transaction(sub_portfolio_id=1, type="BUY", ticker="NVDA", shares=Decimal("20"), price_per_share=Decimal("118.00"), fees=Decimal("0.00"), total_amount=Decimal("2360.00"), currency="USD", notes="Semiconductors"),
                    # India Holdings
                    Transaction(sub_portfolio_id=2, type="BUY", ticker="RELIANCE.NS", shares=Decimal("100"), price_per_share=Decimal("2850.00"), fees=Decimal("50.00"), total_amount=Decimal("285050.00"), currency="INR", notes="Energy & Retail"),
                    Transaction(sub_portfolio_id=2, type="BUY", ticker="TCS.NS", shares=Decimal("60"), price_per_share=Decimal("4120.00"), fees=Decimal("30.00"), total_amount=Decimal("247230.00"), currency="INR", notes="IT Leader"),
                    # Japan Holdings
                    Transaction(sub_portfolio_id=3, type="BUY", ticker="7203.T", shares=Decimal("300"), price_per_share=Decimal("2850.00"), fees=Decimal("500.00"), total_amount=Decimal("855500.00"), currency="JPY", notes="Automotive world leader"),
                    Transaction(sub_portfolio_id=3, type="BUY", ticker="6758.T", shares=Decimal("100"), price_per_share=Decimal("12600.00"), fees=Decimal("500.00"), total_amount=Decimal("1260500.00"), currency="JPY", notes="Electronics & Gaming"),
                ]
                session.add_all(initial_transactions)
                await session.commit()
                logger.info("Successfully seeded demo data.")
        except Exception as e:
            logger.warning(f"Seed data check note: {e}")
            await session.rollback()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed initial demo data if empty
    await seed_initial_data_if_empty()

    # Pre-populate FX rates and quotes
    try:
        await sync_all_markets(force=True)
    except Exception as e:
        logger.warning(f"Initial market sync note: {e}")

    # Start APScheduler background worker
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Containerized Multi-Currency Global Portfolio Management System with FastAPI, Angular, PostgreSQL, and Docker Compose.",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers under /api
app.include_router(portfolios_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(import_router, prefix="/api")
app.include_router(market_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")

@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker container monitoring."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }
