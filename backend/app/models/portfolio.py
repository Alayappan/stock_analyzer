from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    base_currency = Column(String(10), nullable=False, default="USD")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sub_portfolios = relationship("SubPortfolio", back_populates="portfolio", cascade="all, delete-orphan", lazy="selectin")


class SubPortfolio(Base):
    __tablename__ = "sub_portfolios"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    country = Column(String(10), nullable=False, default="US")
    currency = Column(String(10), nullable=False, default="USD")
    benchmark_ticker = Column(String(50), nullable=False, default="^GSPC")
    cash_balance = Column(Numeric(15, 4), nullable=False, default=0.0000)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    portfolio = relationship("Portfolio", back_populates="sub_portfolios")
    transactions = relationship("Transaction", back_populates="sub_portfolio", cascade="all, delete-orphan", lazy="selectin")
    dividends = relationship("DividendSchedule", back_populates="sub_portfolio", cascade="all, delete-orphan", lazy="selectin")
