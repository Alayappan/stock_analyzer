import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PortfolioService } from './services/portfolio.service';
import { ToastService } from './services/toast.service';
import { SubPortfolio } from './models/portfolio.model';
import { TransactionType } from './models/transaction.model';

import { NavbarComponent } from './components/navbar/navbar.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { SubPortfolioComponent } from './components/sub-portfolio/sub-portfolio.component';
import { ImportModalComponent } from './components/import-modal/import-modal.component';
import { TransactionModalComponent } from './components/transaction-modal/transaction-modal.component';
import { StockDetailModalComponent } from './components/stock-detail-modal/stock-detail-modal.component';
import { TransactionHistoryComponent } from './components/transaction-history/transaction-history.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    NavbarComponent,
    DashboardComponent,
    SubPortfolioComponent,
    ImportModalComponent,
    TransactionModalComponent,
    StockDetailModalComponent,
    TransactionHistoryComponent
  ],
  templateUrl: './app.component.html'
})
export class AppComponent implements OnInit {
  portfolioService = inject(PortfolioService);
  toastService = inject(ToastService);

  subPortfolios = signal<SubPortfolio[]>([]);

  // Modal display states
  showImportModal = signal<boolean>(false);
  showTransactionModal = signal<boolean>(false);
  showLedgerModal = signal<boolean>(false);
  detailTicker = signal<string | null>(null);

  // Initial params for Transaction modal
  tradeInitialTicker: string = '';
  tradeInitialType: TransactionType = 'BUY';
  tradeInitialSubId: number | null = null;

  ngOnInit() {
    this.loadSubPortfolios();
    this.portfolioService.refreshTrigger$.subscribe(() => {
      this.loadSubPortfolios();
    });
  }

  loadSubPortfolios() {
    const pId = this.portfolioService.activePortfolioId();
    this.portfolioService.getPortfolio(pId).subscribe({
      next: (p) => {
        this.subPortfolios.set(p.sub_portfolios || []);
      },
      error: (err) => console.error('Error loading sub-portfolios:', err)
    });
  }

  openTradeModal(params?: { ticker?: string; type?: TransactionType; subPortfolioId?: number }) {
    this.tradeInitialTicker = params?.ticker || '';
    this.tradeInitialType = params?.type || 'BUY';
    this.tradeInitialSubId = params?.subPortfolioId || this.portfolioService.selectedSubPortfolioId();
    this.showTransactionModal.set(true);
  }

  openStockDetail(ticker: string) {
    this.detailTicker.set(ticker);
  }

  onTradeFromDetail(ticker: string) {
    this.detailTicker.set(null);
    this.openTradeModal({ ticker, type: 'BUY' });
  }
}
