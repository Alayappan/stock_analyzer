from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Date, PrimaryKeyConstraint, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class MarketCache(Base):
    __tablename__ = "market_cache"

    ticker = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    current_price = Column(Numeric(15, 4), nullable=False)
    previous_close = Column(Numeric(15, 4), nullable=False)
    day_change = Column(Numeric(15, 4), nullable=False, default=0.0000)
    day_change_percent = Column(Numeric(15, 4), nullable=False, default=0.0000)
    pe_ratio = Column(Numeric(15, 4), nullable=True)
    market_cap = Column(Numeric(20, 2), nullable=True)
    dividend_yield = Column(Numeric(15, 4), nullable=True)
    fifty_two_week_high = Column(Numeric(15, 4), nullable=True)
    fifty_two_week_low = Column(Numeric(15, 4), nullable=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FxRate(Base):
    __tablename__ = "fx_rates"

    from_currency = Column(String(10), nullable=False)
    to_currency = Column(String(10), nullable=False)
    rate = Column(Numeric(15, 6), nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        PrimaryKeyConstraint("from_currency", "to_currency", name="pk_fx_rates"),
    )


class DividendSchedule(Base):
    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True, index=True)
    sub_portfolio_id = Column(Integer, ForeignKey("sub_portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(50), nullable=False, index=True)
    ex_date = Column(Date, nullable=True)
    record_date = Column(Date, nullable=True)
    payment_date = Column(Date, nullable=True)
    dividend_per_share = Column(Numeric(15, 4), nullable=False)
    projected_payout = Column(Numeric(15, 4), nullable=False)
    currency = Column(String(10), nullable=False)
    status = Column(String(50), nullable=False, default="ANNOUNCED") # ANNOUNCED, PROJECTED, PAID
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sub_portfolio = relationship("SubPortfolio", back_populates="dividends")
