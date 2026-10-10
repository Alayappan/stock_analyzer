export interface SubPortfolio {
  id: number;
  portfolio_id: number;
  name: string;
  country: string;
  currency: string;
  benchmark_ticker: string;
  cash_balance: number;
  created_at: string;
  updated_at: string;
}

export interface Holding {
  ticker: string;
  name: string;
  shares: number;
  cost_basis: number;
  current_price: number;
  current_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  daily_pnl: number;
  daily_pnl_percent: number;
  sector: string;
  currency: string;
}

export interface SubPortfolioDetail extends SubPortfolio {
  total_invested_value: number;
  total_market_value: number;
  total_portfolio_value: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_percent: number;
  total_daily_pnl: number;
  total_daily_pnl_percent: number;
  holdings: Holding[];
}

export interface SubPortfolioSummaryConverted {
  id: number;
  name: string;
  country: string;
  local_currency: string;
  benchmark_ticker: string;
  local_cash_balance: number;
  local_market_value: number;
  local_total_value: number;
  local_daily_pnl: number;
  local_unrealized_pnl: number;
  base_fx_rate: number;
  converted_cash_balance: number;
  converted_market_value: number;
  converted_total_value: number;
  converted_daily_pnl: number;
  converted_unrealized_pnl: number;
}

export interface MasterRollup {
  portfolio_id: number;
  portfolio_name: string;
  base_currency: string;
  total_net_worth: number;
  total_cash: number;
  total_market_value: number;
  total_invested: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_percent: number;
  total_daily_pnl: number;
  total_daily_pnl_percent: number;
  sub_portfolios: SubPortfolioSummaryConverted[];
}

export interface Portfolio {
  id: number;
  name: string;
  description?: string;
  base_currency: string;
  created_at: string;
  updated_at: string;
  sub_portfolios: SubPortfolio[];
}
