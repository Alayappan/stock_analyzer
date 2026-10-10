import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { MarketStatusItem, TickerDetail, MarketQuote, FxRate } from '../models/market.model';
import { PortfolioAllocations, BenchmarkGrowth } from '../models/analytics.model';

@Injectable({
  providedIn: 'root'
})
export class MarketService {
  private baseUrl = '/api';

  constructor(private http: HttpClient) {}

  getMarketStatus(): Observable<MarketStatusItem[]> {
    return this.http.get<MarketStatusItem[]>(`${this.baseUrl}/market/status`);
  }

  getTickerDetail(ticker: string): Observable<TickerDetail> {
    return this.http.get<TickerDetail>(`${this.baseUrl}/market/ticker/${encodeURIComponent(ticker)}`);
  }

  getQuotes(tickers?: string): Observable<MarketQuote[]> {
    let params = new HttpParams();
    if (tickers) {
      params = params.set('tickers', tickers);
    }
    return this.http.get<MarketQuote[]>(`${this.baseUrl}/market/quotes`, { params });
  }

  getFxRates(): Observable<FxRate[]> {
    return this.http.get<FxRate[]>(`${this.baseUrl}/market/fx-rates`);
  }

  refreshMarket(): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/market/refresh`, {});
  }

  getAllocations(portfolioId: number, subPortfolioId?: number): Observable<PortfolioAllocations> {
    let params = new HttpParams();
    if (subPortfolioId) {
      params = params.set('sub_portfolio_id', subPortfolioId.toString());
    }
    return this.http.get<PortfolioAllocations>(`${this.baseUrl}/analytics/allocations/${portfolioId}`, { params });
  }

  getBenchmarkGrowth(subPortfolioId: number, period: string = '6mo'): Observable<BenchmarkGrowth> {
    return this.http.get<BenchmarkGrowth>(`${this.baseUrl}/analytics/benchmark-growth/${subPortfolioId}?period=${period}`);
  }
}
