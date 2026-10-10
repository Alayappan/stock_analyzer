export type TransactionType = 'BUY' | 'SELL' | 'CASH_DEPOSIT' | 'CASH_WITHDRAWAL' | 'DIVIDEND';

export interface Transaction {
  id: number;
  sub_portfolio_id: number;
  type: TransactionType;
  ticker?: string;
  shares?: number;
  price_per_share?: number;
  fees: number;
  total_amount: number;
  currency: string;
  executed_at: string;
  notes?: string;
  created_at: string;
}

export interface TransactionCreate {
  sub_portfolio_id: number;
  type: TransactionType;
  ticker?: string;
  shares?: number;
  price_per_share?: number;
  fees?: number;
  total_amount?: number;
  executed_at?: string;
  notes?: string;
}
