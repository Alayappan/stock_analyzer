export interface MarketQuote {
  ticker: string;
  name: string;
  currency: string;
  current_price: number;
  previous_close: number;
  day_change: number;
  day_change_percent: number;
  pe_ratio?: number;
  market_cap?: number;
  dividend_yield?: number;
  fifty_two_week_high?: number;
  fifty_two_week_low?: number;
  sector?: string;
  industry?: string;
  last_updated: string;
}

export interface NewsArticle {
  title: string;
  publisher?: string;
  link?: string;
  published_time?: string;
  summary?: string;
  sentiment_label: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  sentiment_score: number;
}

export interface DividendSchedule {
  id: number;
  sub_portfolio_id: number;
  ticker: string;
  ex_date?: string;
  record_date?: string;
  payment_date?: string;
  dividend_per_share: number;
  projected_payout: number;
  currency: string;
  status: string;
  created_at: string;
}

export interface TickerDetail {
  quote: MarketQuote;
  news: NewsArticle[];
  dividends: DividendSchedule[];
}

export interface MarketStatusItem {
  exchange_id: string;
  name: string;
  country: string;
  currency: string;
  timezone: string;
  is_open: boolean;
  local_time: string;
  open_time: string;
  close_time: string;
}

export interface FxRate {
  from_currency: string;
  to_currency: string;
  rate: number;
  last_updated: string;
}
