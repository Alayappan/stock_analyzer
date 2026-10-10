from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

class MarketQuoteOut(BaseModel):
    ticker: str
    name: str
    currency: str
    current_price: Decimal
    previous_close: Decimal
    day_change: Decimal
    day_change_percent: Decimal
    pe_ratio: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None
    fifty_two_week_high: Optional[Decimal] = None
    fifty_two_week_low: Optional[Decimal] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)

class NewsArticleOut(BaseModel):
    title: str
    publisher: Optional[str] = "Yahoo Finance"
    link: Optional[str] = "#"
    published_time: Optional[str] = None
    summary: Optional[str] = None
    sentiment_label: str = "NEUTRAL" # BULLISH, BEARISH, NEUTRAL
    sentiment_score: float = 0.0

class DividendScheduleOut(BaseModel):
    id: int
    sub_portfolio_id: int
    ticker: str
    ex_date: Optional[date] = None
    record_date: Optional[date] = None
    payment_date: Optional[date] = None
    dividend_per_share: Decimal
    projected_payout: Decimal
    currency: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TickerDetailOut(BaseModel):
    quote: MarketQuoteOut
    news: List[NewsArticleOut] = []
    dividends: List[DividendScheduleOut] = []

class MarketStatusItem(BaseModel):
    exchange_id: str
    name: str
    country: str
    currency: str
    timezone: str
    is_open: bool
    local_time: str
    open_time: str
    close_time: str

class FxRateOut(BaseModel):
    from_currency: str
    to_currency: str
    rate: Decimal
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)
