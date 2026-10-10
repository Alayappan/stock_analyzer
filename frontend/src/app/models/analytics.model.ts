export interface AllocationItem {
  label: string;
  ticker?: string;
  value: number;
  percentage: number;
  currency: string;
}

export interface PortfolioAllocations {
  total_value: number;
  currency: string;
  by_company: AllocationItem[];
  by_sector: AllocationItem[];
  by_asset_class: AllocationItem[];
}

export interface BenchmarkGrowthPoint {
  date: string;
  portfolio_return_pct: number;
  benchmark_return_pct: number;
  portfolio_value: number;
  benchmark_value: number;
}

export interface BenchmarkGrowth {
  sub_portfolio_id: number;
  sub_portfolio_name: string;
  benchmark_ticker: string;
  benchmark_name: string;
  period: string;
  points: BenchmarkGrowthPoint[];
}
