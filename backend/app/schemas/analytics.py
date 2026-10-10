from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

class AllocationItem(BaseModel):
    label: str
    ticker: Optional[str] = None
    value: Decimal
    percentage: Decimal
    currency: str

class PortfolioAllocationsOut(BaseModel):
    total_value: Decimal
    currency: str
    by_company: List[AllocationItem]
    by_sector: List[AllocationItem]
    by_asset_class: List[AllocationItem]

class BenchmarkGrowthPoint(BaseModel):
    date: str
    portfolio_return_pct: float
    benchmark_return_pct: float
    portfolio_value: float
    benchmark_value: float

class BenchmarkGrowthOut(BaseModel):
    sub_portfolio_id: int
    sub_portfolio_name: str
    benchmark_ticker: str
    benchmark_name: str
    period: str
    points: List[BenchmarkGrowthPoint]
