import { Component, Input, Output, EventEmitter, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PortfolioService } from '../../services/portfolio.service';
import { ToastService } from '../../services/toast.service';
import { SubPortfolio, SubPortfolioDetail } from '../../models/portfolio.model';
import { TransactionType } from '../../models/transaction.model';

@Component({
  selector: 'app-transaction-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './transaction-modal.component.html'
})
export class TransactionModalComponent implements OnInit {
  portfolioService = inject(PortfolioService);
  toastService = inject(ToastService);

  @Input() subPortfolios: SubPortfolio[] = [];
  @Input() initialSubPortfolioId: number | null = null;
  @Input() initialTicker: string = '';
  @Input() initialType: TransactionType = 'BUY';

  @Output() close = new EventEmitter<void>();
  @Output() transactionSuccess = new EventEmitter<void>();

  // Form Fields
  selectedSubPortfolioId: number = 1;
  txType: TransactionType = 'BUY';
  ticker: string = '';
  shares: number | null = 10;
  pricePerShare: number | null = 150;
  fees: number = 0;
  cashAmount: number | null = 1000;
  notes: string = '';

  isSubmitting = signal<boolean>(false);
  errorMessage = signal<string | null>(null);
  currentSubDetail = signal<SubPortfolioDetail | null>(null);

  // Common quick ticker suggestions
  popularTickers = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'RELIANCE.NS', 'TCS.NS', 'INFY.NS', '7203.T', '6758.T'];

  ngOnInit() {
    if (this.initialSubPortfolioId) {
      this.selectedSubPortfolioId = this.initialSubPortfolioId;
    } else if (this.subPortfolios.length > 0) {
      this.selectedSubPortfolioId = this.subPortfolios[0].id;
    }

    if (this.initialTicker) {
      this.ticker = this.initialTicker;
    }
    if (this.initialType) {
      this.txType = this.initialType;
    }

    this.loadSubPortfolioDetail();
  }

  onSubPortfolioChange() {
    this.loadSubPortfolioDetail();
  }

  loadSubPortfolioDetail() {
    if (!this.selectedSubPortfolioId) return;
    this.portfolioService.getSubPortfolioDetail(this.selectedSubPortfolioId).subscribe({
      next: (detail) => this.currentSubDetail.set(detail),
      error: (err) => console.error(err)
    });
  }

  selectTicker(t: string) {
    this.ticker = t;
    // Auto adjust sub-portfolio if ticker belongs to India (.NS) or Japan (.T)
    if (t.endsWith('.NS')) {
      const match = this.subPortfolios.find(s => s.country === 'IN' || s.currency === 'INR');
      if (match) this.selectedSubPortfolioId = match.id;
    } else if (t.endsWith('.T')) {
      const match = this.subPortfolios.find(s => s.country === 'JP' || s.currency === 'JPY');
      if (match) this.selectedSubPortfolioId = match.id;
    }
    this.loadSubPortfolioDetail();
  }

  calculateTotal(): number {
    if (this.txType === 'CASH_DEPOSIT' || this.txType === 'CASH_WITHDRAWAL' || this.txType === 'DIVIDEND') {
      return Number(this.cashAmount) || 0;
    }
    const s = Number(this.shares) || 0;
    const p = Number(this.pricePerShare) || 0;
    const f = Number(this.fees) || 0;
    if (this.txType === 'BUY') {
      return (s * p) + f;
    } else if (this.txType === 'SELL') {
      return Math.max(0, (s * p) - f);
    }
    return 0;
  }

  isWalletInsufficient(): boolean {
    const detail = this.currentSubDetail();
    if (!detail) return false;
    const total = this.calculateTotal();

    if (this.txType === 'BUY' || this.txType === 'CASH_WITHDRAWAL') {
      return total > detail.cash_balance;
    }
    return false;
  }

  getOwnedShares(): number {
    const detail = this.currentSubDetail();
    if (!detail || !this.ticker) return 0;
    const h = detail.holdings.find(x => x.ticker.toUpperCase() === this.ticker.trim().toUpperCase());
    return h ? Number(h.shares) : 0;
  }

  isSellExceeded(): boolean {
    if (this.txType !== 'SELL') return false;
    const owned = this.getOwnedShares();
    const req = Number(this.shares) || 0;
    return req > owned;
  }

  submitTransaction() {
    this.errorMessage.set(null);

    // Validations
    if (this.isWalletInsufficient()) {
      const detail = this.currentSubDetail();
      this.errorMessage.set(`Insufficient cash wallet balance! Available: ${detail?.currency} ${detail?.cash_balance.toFixed(2)}, Required: ${detail?.currency} ${this.calculateTotal().toFixed(2)}.`);
      return;
    }

    if (this.isSellExceeded()) {
      this.errorMessage.set(`Cannot sell ${this.shares} shares. You only own ${this.getOwnedShares()} shares of ${this.ticker}.`);
      return;
    }

    this.isSubmitting.set(true);

    if (this.txType === 'CASH_DEPOSIT' || this.txType === 'CASH_WITHDRAWAL') {
      const amount = Number(this.cashAmount) || 0;
      this.portfolioService.updateCashWallet(this.selectedSubPortfolioId, this.txType, amount, this.notes).subscribe({
        next: () => {
          this.isSubmitting.set(false);
          this.toastService.success(`Cash wallet updated successfully!`, 'Transaction Recorded');
          this.portfolioService.triggerRefresh();
          this.transactionSuccess.emit();
          this.close.emit();
        },
        error: (err) => {
          this.isSubmitting.set(false);
          this.errorMessage.set(err.error?.detail || 'Transaction failed');
        }
      });
    } else {
      const payload = {
        sub_portfolio_id: this.selectedSubPortfolioId,
        type: this.txType,
        ticker: this.ticker.trim().toUpperCase(),
        shares: Number(this.shares),
        price_per_share: Number(this.pricePerShare),
        fees: Number(this.fees) || 0,
        notes: this.notes
      };

      this.portfolioService.createTransaction(payload).subscribe({
        next: () => {
          this.isSubmitting.set(false);
          this.toastService.success(`${this.txType} ${payload.shares} shares of ${payload.ticker} recorded!`, 'Trade Executed');
          this.portfolioService.triggerRefresh();
          this.transactionSuccess.emit();
          this.close.emit();
        },
        error: (err) => {
          this.isSubmitting.set(false);
          this.errorMessage.set(err.error?.detail || 'Transaction execution failed');
        }
      });
    }
  }
}
