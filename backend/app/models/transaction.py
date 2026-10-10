from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

class TransactionType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    CASH_DEPOSIT = "CASH_DEPOSIT"
    CASH_WITHDRAWAL = "CASH_WITHDRAWAL"
    DIVIDEND = "DIVIDEND"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    sub_portfolio_id = Column(Integer, ForeignKey("sub_portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(20), nullable=False) # BUY, SELL, CASH_DEPOSIT, CASH_WITHDRAWAL, DIVIDEND
    ticker = Column(String(50), nullable=True, index=True)
    shares = Column(Numeric(15, 4), nullable=True)
    price_per_share = Column(Numeric(15, 4), nullable=True)
    fees = Column(Numeric(15, 4), nullable=False, default=0.0000)
    total_amount = Column(Numeric(15, 4), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    executed_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sub_portfolio = relationship("SubPortfolio", back_populates="transactions")
