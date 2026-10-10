import { Component, OnInit, Output, EventEmitter, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PortfolioService } from '../../services/portfolio.service';
import { MarketService } from '../../services/market.service';
import { ToastService } from '../../services/toast.service';
import { MasterRollup, SubPortfolioSummaryConverted, SubPortfolio } from '../../models/portfolio.model';
import { PortfolioAllocations } from '../../models/analytics.model';
import { AllocationChartComponent } from '../charts/allocation-chart.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, AllocationChartComponent],
  templateUrl: './dashboard.component.html'
})
export class DashboardComponent implements OnInit {
  portfolioService = inject(PortfolioService);
  marketService = inject(MarketService);
  toastService = inject(ToastService);

  @Output() selectSubPortfolio = new EventEmitter<number>();
  @Output() openImport = new EventEmitter<void>();
  @Output() openTrade = new EventEmitter<void>();

  isLoading = signal<boolean>(true);
  rollup = signal<MasterRollup | null>(null);
  allocations = signal<PortfolioAllocations | null>(null);

  // New sub-portfolio modal state
  showNewSubModal = signal<boolean>(false);
  newSubName = '';
  newSubCountry = 'EU';
  newSubCurrency = 'EUR';
  newSubBenchmark = '^STOXX50E';
  newSubCash = 10000;

  // Edit sub-portfolio modal state
  showEditSubModal = signal<boolean>(false);
  editSubId: number | null = null;
  editSubName = '';
  editSubCountry = 'US';
  editSubCurrency = 'USD';
  editSubBenchmark = '^GSPC';
  isSavingSub = signal<boolean>(false);

  // Delete sub-portfolio modal state
  showDeleteSubModal = signal<boolean>(false);
  subToDelete: SubPortfolioSummaryConverted | null = null;
  isDeletingSub = signal<boolean>(false);

  ngOnInit() {
    this.loadDashboardData();
    this.portfolioService.refreshTrigger$.subscribe(() => {
      this.loadDashboardData();
    });
  }

  loadDashboardData() {
    this.isLoading.set(true);
    const pId = this.portfolioService.activePortfolioId();
    const baseCurr = this.portfolioService.activeBaseCurrency();

    this.portfolioService.getPortfolioRollup(pId, baseCurr).subscribe({
      next: (data) => {
        this.rollup.set(data);
        this.isLoading.set(false);
        this.loadMasterAllocations(pId);
      },
      error: (err) => {
        console.error('Error loading rollup:', err);
        this.isLoading.set(false);
      }
    });
  }

  loadMasterAllocations(pId: number) {
    this.marketService.getAllocations(pId).subscribe({
      next: (data) => this.allocations.set(data),
      error: (err) => console.warn('Could not load master allocations:', err)
    });
  }

  createSubPortfolio() {
    const pId = this.portfolioService.activePortfolioId();
    const payload = {
      name: this.newSubName.trim() || `${this.newSubCountry} Equities`,
      country: this.newSubCountry,
      currency: this.newSubCurrency,
      benchmark_ticker: this.newSubBenchmark,
      cash_balance: Number(this.newSubCash) || 0
    };

    this.portfolioService.createSubPortfolio(pId, payload).subscribe({
      next: (sp) => {
        this.showNewSubModal.set(false);
        this.toastService.success(`Created ${sp.name} sub-portfolio!`, 'Sub-Portfolio Added');
        this.loadDashboardData();
      },
      error: (err) => {
        this.toastService.error(err.error?.detail || 'Failed to create sub-portfolio', 'Error');
      }
    });
  }

  openEditSub(sp: SubPortfolioSummaryConverted, event: Event) {
    event.stopPropagation();
    this.editSubId = sp.id;
    this.editSubName = sp.name;
    this.editSubCountry = sp.country;
    this.editSubCurrency = sp.local_currency;
    this.editSubBenchmark = sp.benchmark_ticker;
    this.showEditSubModal.set(true);
  }

  saveSubPortfolio() {
    if (!this.editSubId || !this.editSubName.trim()) {
      this.toastService.error('Sub-portfolio name cannot be empty', 'Validation Error');
      return;
    }
    this.isSavingSub.set(true);
    this.portfolioService.updateSubPortfolio(this.editSubId, {
      name: this.editSubName.trim(),
      country: this.editSubCountry,
      currency: this.editSubCurrency.toUpperCase(),
      benchmark_ticker: this.editSubBenchmark.toUpperCase()
    }).subscribe({
      next: (res) => {
        this.isSavingSub.set(false);
        this.showEditSubModal.set(false);
        this.toastService.success(`Sub-portfolio '${res.name}' updated!`, 'Saved');
        this.loadDashboardData();
        this.portfolioService.triggerRefresh();
      },
      error: (err) => {
        this.isSavingSub.set(false);
        this.toastService.error(err.error?.detail || 'Failed to update sub-portfolio', 'Error');
      }
    });
  }

  openDeleteSub(sp: SubPortfolioSummaryConverted, event: Event) {
    event.stopPropagation();
    this.subToDelete = sp;
    this.showDeleteSubModal.set(true);
  }

  confirmDeleteSub() {
    if (!this.subToDelete) return;
    this.isDeletingSub.set(true);
    this.portfolioService.deleteSubPortfolio(this.subToDelete.id).subscribe({
      next: () => {
        this.isDeletingSub.set(false);
        this.showDeleteSubModal.set(false);
        this.toastService.success('Sub-portfolio deleted successfully', 'Deleted');
        this.subToDelete = null;
        this.loadDashboardData();
        this.portfolioService.triggerRefresh();
      },
      error: (err) => {
        this.isDeletingSub.set(false);
        this.toastService.error(err.error?.detail || 'Failed to delete sub-portfolio', 'Error');
      }
    });
  }

  getCountryFlag(country: string): string {
    const map: Record<string, string> = {
      'US': '🇺🇸',
      'IN': '🇮🇳',
      'JP': '🇯🇵',
      'GB': '🇬🇧',
      'EU': '🇪🇺',
      'CA': '🇨🇦',
      'HK': '🇭🇰',
      'AU': '🇦🇺'
    };
    return map[country] || '🌐';
  }
}
