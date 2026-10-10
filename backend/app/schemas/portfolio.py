from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class SubPortfolioBase(BaseModel):
    name: str
    country: str = "US"
    currency: str = "USD"
    benchmark_ticker: str = "^GSPC"
    cash_balance: Decimal = Field(default=Decimal("0.0000"), ge=0)

class SubPortfolioCreate(SubPortfolioBase):
    portfolio_id: int

class SubPortfolioUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    benchmark_ticker: Optional[str] = None
    cash_balance: Optional[Decimal] = Field(default=None, ge=0)

class CashPoolEdit(BaseModel):
    new_cash_balance: Decimal = Field(ge=0)
    notes: Optional[str] = None

class HoldingOut(BaseModel):
    ticker: str
    name: str
    shares: Decimal
    cost_basis: Decimal
    current_price: Decimal
    current_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    daily_pnl: Decimal
    daily_pnl_percent: Decimal
    sector: Optional[str] = "Other"
    currency: str

class SubPortfolioOut(SubPortfolioBase):
    id: int
    portfolio_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SubPortfolioDetailOut(SubPortfolioOut):
    total_invested_value: Decimal = Decimal("0.0000")
    total_market_value: Decimal = Decimal("0.0000")
    total_portfolio_value: Decimal = Decimal("0.0000") # cash + market value
    total_unrealized_pnl: Decimal = Decimal("0.0000")
    total_unrealized_pnl_percent: Decimal = Decimal("0.0000")
    total_daily_pnl: Decimal = Decimal("0.0000")
    total_daily_pnl_percent: Decimal = Decimal("0.0000")
    holdings: List[HoldingOut] = []

class PortfolioBase(BaseModel):
    name: str
    description: Optional[str] = None
    base_currency: str = "USD"

class PortfolioCreate(PortfolioBase):
    pass

class PortfolioOut(PortfolioBase):
    id: int
    created_at: datetime
    updated_at: datetime
    sub_portfolios: List[SubPortfolioOut] = []
    model_config = ConfigDict(from_attributes=True)

class SubPortfolioSummaryConverted(BaseModel):
    id: int
    name: str
    country: str
    local_currency: str
    benchmark_ticker: str
    local_cash_balance: Decimal
    local_market_value: Decimal
    local_total_value: Decimal
    local_daily_pnl: Decimal
    local_unrealized_pnl: Decimal
    # Converted into Master Base Currency:
    base_fx_rate: Decimal
    converted_cash_balance: Decimal
    converted_market_value: Decimal
    converted_total_value: Decimal
    converted_daily_pnl: Decimal
    converted_unrealized_pnl: Decimal

class MasterRollupOut(BaseModel):
    portfolio_id: int
    portfolio_name: str
    base_currency: str
    total_net_worth: Decimal
    total_cash: Decimal
    total_market_value: Decimal
    total_invested: Decimal
    total_unrealized_pnl: Decimal
    total_unrealized_pnl_percent: Decimal
    total_daily_pnl: Decimal
    total_daily_pnl_percent: Decimal
    sub_portfolios: List[SubPortfolioSummaryConverted]

class CashWalletUpdate(BaseModel):
    type: str # CASH_DEPOSIT, CASH_WITHDRAWAL
    amount: Decimal = Field(gt=0)
    notes: Optional[str] = None
