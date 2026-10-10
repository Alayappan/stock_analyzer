import { Injectable, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, Subject } from 'rxjs';
import { Portfolio, SubPortfolio, SubPortfolioDetail, MasterRollup } from '../models/portfolio.model';
import { Transaction, TransactionCreate } from '../models/transaction.model';
import { DividendSchedule } from '../models/market.model';

@Injectable({
  providedIn: 'root'
})
export class PortfolioService {
  private baseUrl = '/api';

  // Reactive state signals
  activePortfolioId = signal<number>(1);
  activeBaseCurrency = signal<string>('USD');
  selectedSubPortfolioId = signal<number | null>(null);

  // Event bus to trigger global UI re-fetching
  refreshTrigger$ = new Subject<void>();

  constructor(private http: HttpClient) {}

  getPortfolios(): Observable<Portfolio[]> {
    return this.http.get<Portfolio[]>(`${this.baseUrl}/portfolios`);
  }

  getPortfolio(id: number): Observable<Portfolio> {
    return this.http.get<Portfolio>(`${this.baseUrl}/portfolios/${id}`);
  }

  createPortfolio(data: { name: string; description?: string; base_currency: string }): Observable<Portfolio> {
    return this.http.post<Portfolio>(`${this.baseUrl}/portfolios`, data);
  }

  getPortfolioRollup(id: number, baseCurrency?: string): Observable<MasterRollup> {
    let params = new HttpParams();
    if (baseCurrency) {
      params = params.set('base_currency', baseCurrency);
    }
    return this.http.get<MasterRollup>(`${this.baseUrl}/portfolios/${id}/rollup`, { params });
  }

  createSubPortfolio(portfolioId: number, data: { name: string; country: string; currency: string; benchmark_ticker: string; cash_balance: number }): Observable<SubPortfolio> {
    return this.http.post<SubPortfolio>(`${this.baseUrl}/portfolios/${portfolioId}/sub-portfolios`, data);
  }

  getSubPortfolioDetail(subPortfolioId: number): Observable<SubPortfolioDetail> {
    return this.http.get<SubPortfolioDetail>(`${this.baseUrl}/sub-portfolios/${subPortfolioId}`);
  }

  updateCashWallet(subPortfolioId: number, type: 'CASH_DEPOSIT' | 'CASH_WITHDRAWAL', amount: number, notes?: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/sub-portfolios/${subPortfolioId}/cash`, {
      type,
      amount,
      notes
    });
  }

  editCashPool(subPortfolioId: number, new_cash_balance: number, notes?: string): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/sub-portfolios/${subPortfolioId}/cash-pool`, {
      new_cash_balance,
      notes
    });
  }

  updateSubPortfolio(subPortfolioId: number, data: { name?: string; country?: string; currency?: string; benchmark_ticker?: string; cash_balance?: number }): Observable<SubPortfolio> {
    return this.http.put<SubPortfolio>(`${this.baseUrl}/sub-portfolios/${subPortfolioId}`, data);
  }

  deleteSubPortfolio(subPortfolioId: number): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/sub-portfolios/${subPortfolioId}`);
  }

  getSubPortfolioDividends(subPortfolioId: number): Observable<DividendSchedule[]> {
    return this.http.get<DividendSchedule[]>(`${this.baseUrl}/sub-portfolios/${subPortfolioId}/dividends`);
  }

  getTransactions(subPortfolioId?: number, ticker?: string, type?: string, limit: number = 100): Observable<Transaction[]> {
    let params = new HttpParams().set('limit', limit.toString());
    if (subPortfolioId) params = params.set('sub_portfolio_id', subPortfolioId.toString());
    if (ticker) params = params.set('ticker', ticker);
    if (type) params = params.set('type', type);
    return this.http.get<Transaction[]>(`${this.baseUrl}/transactions`, { params });
  }

  createTransaction(tx: TransactionCreate): Observable<Transaction> {
    return this.http.post<Transaction>(`${this.baseUrl}/transactions`, tx);
  }

  deleteTransaction(id: number): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/transactions/${id}`);
  }

  importPortfolioFile(formData: FormData): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/portfolios/import`, formData);
  }

  deduplicateSubPortfolio(subPortfolioId: number): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/sub-portfolios/${subPortfolioId}/deduplicate`, {});
  }

  triggerRefresh() {
    this.refreshTrigger$.next();
  }
}
