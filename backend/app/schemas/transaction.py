from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum

class TransactionTypeEnum(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    CASH_DEPOSIT = "CASH_DEPOSIT"
    CASH_WITHDRAWAL = "CASH_WITHDRAWAL"
    DIVIDEND = "DIVIDEND"

class TransactionCreate(BaseModel):
    sub_portfolio_id: int
    type: TransactionTypeEnum
    ticker: Optional[str] = None
    shares: Optional[Decimal] = Field(default=None, ge=0)
    price_per_share: Optional[Decimal] = Field(default=None, ge=0)
    fees: Decimal = Field(default=Decimal("0.0000"), ge=0)
    total_amount: Optional[Decimal] = None # Calculated if not provided
    executed_at: Optional[datetime] = None
    notes: Optional[str] = None

class TransactionOut(BaseModel):
    id: int
    sub_portfolio_id: int
    type: str
    ticker: Optional[str] = None
    shares: Optional[Decimal] = None
    price_per_share: Optional[Decimal] = None
    fees: Decimal
    total_amount: Decimal
    currency: str
    executed_at: datetime
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
