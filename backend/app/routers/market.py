from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.core.database import get_db
from app.models.market import MarketCache, FxRate
from app.schemas.market import MarketQuoteOut, TickerDetailOut, MarketStatusItem, FxRateOut
from app.services.market_data import MarketDataService
from app.services.portfolio_engine import PortfolioEngine
from app.services.scheduler import get_all_market_statuses, sync_all_markets

router = APIRouter(prefix="/market", tags=["Market Data"])

@router.get("/status", response_model=List[MarketStatusItem])
async def get_market_trading_status():
    """Get live trading hours and open/closed status for NYSE, NSE, TSE, LSE, and Euronext."""
    return get_all_market_statuses()

@router.post("/refresh")
async def trigger_market_refresh():
    """On-demand trigger to force immediate update of stock quotes, dividends, and FX rates."""
    result = await sync_all_markets(force=True)
    return result

@router.get("/ticker/{ticker}", response_model=TickerDetailOut)
async def get_ticker_details(ticker: str, db: AsyncSession = Depends(get_db)):
    """Fetch real-time quote, valuation stats (P/E, Market Cap, 52w range), and live RSS news with sentiment analysis."""
    ticker_clean = ticker.strip().upper()
    
    # 1. Get Quote (from cache or fetch)
    cache_obj = await PortfolioEngine.get_or_update_market_cache(ticker_clean, db)
    quote_out = MarketQuoteOut.model_validate(cache_obj)
    
    # 2. Get News with Sentiment
    news_items = MarketDataService.get_ticker_news(ticker_clean)
    
    # 3. Get Upcoming Dividends
    div_items = MarketDataService.get_dividend_declarations(ticker_clean)
    
    return {
        "quote": quote_out,
        "news": news_items,
        "dividends": []
    }

@router.get("/quotes", response_model=List[MarketQuoteOut])
async def list_cached_quotes(
    tickers: Optional[str] = Query(None, description="Comma-separated ticker list, or all if empty"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve current market cache for tickers."""
    stmt = select(MarketCache)
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        stmt = stmt.where(MarketCache.ticker.in_(ticker_list))
        
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/fx-rates", response_model=List[FxRateOut])
async def list_fx_rates(db: AsyncSession = Depends(get_db)):
    """Retrieve live foreign exchange rates table."""
    stmt = select(FxRate).order_by(FxRate.from_currency, FxRate.to_currency)
    res = await db.execute(stmt)
    return res.scalars().all()
