import { Component, Input, OnInit, OnChanges, SimpleChanges, Output, EventEmitter, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PortfolioService } from '../../services/portfolio.service';
import { MarketService } from '../../services/market.service';
import { ToastService } from '../../services/toast.service';
import { SubPortfolioDetail, Holding } from '../../models/portfolio.model';
import { PortfolioAllocations, BenchmarkGrowth } from '../../models/analytics.model';
import { DividendSchedule } from '../../models/market.model';
import { AllocationChartComponent } from '../charts/allocation-chart.component';
import { BenchmarkChartComponent } from '../charts/benchmark-chart.component';
import { DividendsScheduleComponent } from '../dividends-schedule/dividends-schedule.component';

@Component({
  selector: 'app-sub-portfolio',
  standalone: true,
  imports: [
    CommonModule, 
    FormsModule,
    AllocationChartComponent, 
    BenchmarkChartComponent, 
    DividendsScheduleComponent
  ],
  templateUrl: './sub-portfolio.component.html'
})
export class SubPortfolioComponent implements OnInit, OnChanges {
  @Input({ required: true }) subPortfolioId!: number;
  @Output() back = new EventEmitter<void>();
  @Output() openTrade = new EventEmitter<{ ticker?: string; type?: 'BUY' | 'SELL' | 'CASH_DEPOSIT' | 'CASH_WITHDRAWAL' }>();
  @Output() viewStockDetail = new EventEmitter<string>();

  portfolioService = inject(PortfolioService);
  marketService = inject(MarketService);
  toastService = inject(ToastService);

  isLoading = signal<boolean>(true);
  detail = signal<SubPortfolioDetail | null>(null);
  allocations = signal<PortfolioAllocations | null>(null);
  benchmarkGrowth = signal<BenchmarkGrowth | null>(null);
  dividends = signal<DividendSchedule[]>([]);

  activeTab = signal<'holdings' | 'performance' | 'allocations' | 'dividends'>('holdings');
  benchmarkPeriod = signal<string>('6mo');

  // Edit Cash Pool State
  showEditCashModal = signal<boolean>(false);
  newCashPoolBalance: number = 0;
  cashPoolEditNotes: string = '';
  isSavingCashPool = signal<boolean>(false);

  // Edit Sub-Portfolio State
  showEditSubModal = signal<boolean>(false);
  editSubName: string = '';
  editSubCountry: string = 'US';
  editSubCurrency: string = 'USD';
  editSubBenchmark: string = '^GSPC';
  isSavingSub = signal<boolean>(false);

  // Delete Sub-Portfolio State
  showDeleteConfirmModal = signal<boolean>(false);
  isDeletingSub = signal<boolean>(false);

  ngOnInit() {
    this.loadSubPortfolio();
    this.portfolioService.refreshTrigger$.subscribe(() => {
      this.loadSubPortfolio();
    });
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['subPortfolioId']) {
      this.loadSubPortfolio();
    }
  }

  loadSubPortfolio() {
    if (!this.subPortfolioId) return;
    this.isLoading.set(true);

    this.portfolioService.getSubPortfolioDetail(this.subPortfolioId).subscribe({
      next: (d) => {
        this.detail.set(d);
        this.isLoading.set(false);
        this.loadAllocations();
        this.loadBenchmarkGrowth(this.benchmarkPeriod());
        this.loadDividends();
      },
      error: (err) => {
        console.error('Error loading sub-portfolio:', err);
        this.isLoading.set(false);
      }
    });
  }

  loadAllocations() {
    const pId = this.portfolioService.activePortfolioId();
    this.marketService.getAllocations(pId, this.subPortfolioId).subscribe({
      next: (alloc) => this.allocations.set(alloc),
      error: (err) => console.warn('Could not load allocations:', err)
    });
  }

  loadBenchmarkGrowth(period: string) {
    this.benchmarkPeriod.set(period);
    this.marketService.getBenchmarkGrowth(this.subPortfolioId, period).subscribe({
      next: (bg) => this.benchmarkGrowth.set(bg),
      error: (err) => console.warn('Could not load benchmark growth:', err)
    });
  }

  loadDividends() {
    this.portfolioService.getSubPortfolioDividends(this.subPortfolioId).subscribe({
      next: (divs) => this.dividends.set(divs),
      error: (err) => console.warn('Could not load dividends:', err)
    });
  }

  quickDeposit() {
    this.openTrade.emit({ type: 'CASH_DEPOSIT' });
  }

  quickWithdraw() {
    this.openTrade.emit({ type: 'CASH_WITHDRAWAL' });
  }

  tradeHolding(ticker: string, action: 'BUY' | 'SELL') {
    this.openTrade.emit({ ticker, type: action });
  }

  // --- Cash Pool Edit Handlers ---
  openEditCashPool() {
    const curr = this.detail()?.cash_balance || 0;
    this.newCashPoolBalance = Number(curr);
    this.cashPoolEditNotes = '';
    this.showEditCashModal.set(true);
  }

  saveCashPool() {
    if (this.newCashPoolBalance < 0) {
      this.toastService.error('Cash balance cannot be negative', 'Validation Error');
      return;
    }

    this.isSavingCashPool.set(true);
    this.portfolioService.editCashPool(this.subPortfolioId, Number(this.newCashPoolBalance), this.cashPoolEditNotes).subscribe({
      next: (res) => {
        this.isSavingCashPool.set(false);
        this.showEditCashModal.set(false);
        this.toastService.success(`Cash pool adjusted to ${res.currency} ${Number(res.new_cash_balance).toLocaleString()}`, 'Cash Pool Updated');
        this.loadSubPortfolio();
        this.portfolioService.triggerRefresh();
      },
      error: (err) => {
        this.isSavingCashPool.set(false);
        this.toastService.error(err.error?.detail || 'Failed to update cash pool', 'Error');
      }
    });
  }

  // --- Sub-Portfolio Edit Handlers ---
  openEditSubPortfolio() {
    const d = this.detail();
    if (!d) return;
    this.editSubName = d.name;
    this.editSubCountry = d.country;
    this.editSubCurrency = d.currency;
    this.editSubBenchmark = d.benchmark_ticker;
    this.showEditSubModal.set(true);
  }

  saveSubPortfolio() {
    if (!this.editSubName.trim()) {
      this.toastService.error('Sub-portfolio name cannot be empty', 'Validation Error');
      return;
    }

    this.isSavingSub.set(true);
    const payload = {
      name: this.editSubName.trim(),
      country: this.editSubCountry,
      currency: this.editSubCurrency.toUpperCase(),
      benchmark_ticker: this.editSubBenchmark.toUpperCase()
    };

    this.portfolioService.updateSubPortfolio(this.subPortfolioId, payload).subscribe({
      next: (sp) => {
        this.isSavingSub.set(false);
        this.showEditSubModal.set(false);
        this.toastService.success(`Sub-portfolio '${sp.name}' updated!`, 'Saved');
        this.loadSubPortfolio();
        this.portfolioService.triggerRefresh();
      },
      error: (err) => {
        this.isSavingSub.set(false);
        this.toastService.error(err.error?.detail || 'Failed to update sub-portfolio', 'Error');
      }
    });
  }

  // --- Sub-Portfolio Delete Handlers ---
  openDeleteModal() {
    this.showDeleteConfirmModal.set(true);
  }

  confirmDeleteSubPortfolio() {
    this.isDeletingSub.set(true);
    this.portfolioService.deleteSubPortfolio(this.subPortfolioId).subscribe({
      next: () => {
        this.isDeletingSub.set(false);
        this.showDeleteConfirmModal.set(false);
        this.toastService.success('Sub-portfolio deleted successfully', 'Deleted');
        this.portfolioService.selectedSubPortfolioId.set(null);
        this.portfolioService.triggerRefresh();
        this.back.emit();
      },
      error: (err) => {
        this.isDeletingSub.set(false);
        this.toastService.error(err.error?.detail || 'Failed to delete sub-portfolio', 'Error');
      }
    });
  }
}
