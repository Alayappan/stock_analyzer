import { Component, OnInit, Output, EventEmitter, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PortfolioService } from '../../services/portfolio.service';
import { MarketService } from '../../services/market.service';
import { ToastService } from '../../services/toast.service';
import { MarketStatusItem } from '../../models/market.model';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './navbar.component.html'
})
export class NavbarComponent implements OnInit {
  portfolioService = inject(PortfolioService);
  marketService = inject(MarketService);
  toastService = inject(ToastService);

  @Output() openImport = new EventEmitter<void>();
  @Output() openTransaction = new EventEmitter<void>();
  @Output() openLedger = new EventEmitter<void>();

  isRefreshing = signal<boolean>(false);
  lastRefreshed = signal<string>('Just now');
  marketStatuses = signal<MarketStatusItem[]>([]);

  currencies = [
    { code: 'USD', symbol: '$', name: 'US Dollar', flag: '🇺🇸' },
    { code: 'INR', symbol: '₹', name: 'Indian Rupee', flag: '🇮🇳' },
    { code: 'EUR', symbol: '€', name: 'Euro', flag: '🇪🇺' },
    { code: 'GBP', symbol: '£', name: 'British Pound', flag: '🇬🇧' },
    { code: 'JPY', symbol: '¥', name: 'Japanese Yen', flag: '🇯🇵' },
  ];

  ngOnInit() {
    this.loadMarketStatuses();
  }

  loadMarketStatuses() {
    this.marketService.getMarketStatus().subscribe({
      next: (statuses) => this.marketStatuses.set(statuses),
      error: () => console.warn('Could not load market statuses')
    });
  }

  onCurrencyChange(code: string) {
    this.portfolioService.activeBaseCurrency.set(code);
    this.portfolioService.triggerRefresh();
    this.toastService.info(`Display base currency changed to ${code}`, 'Currency Updated');
  }

  onRefreshNow() {
    this.isRefreshing.set(true);
    this.marketService.refreshMarket().subscribe({
      next: (res) => {
        this.isRefreshing.set(false);
        this.lastRefreshed.set(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
        this.loadMarketStatuses();
        this.portfolioService.triggerRefresh();
        this.toastService.success(`Live quotes & FX rates synced (${res.count || 0} symbols)`, 'Market Refreshed');
      },
      error: (err) => {
        this.isRefreshing.set(false);
        this.portfolioService.triggerRefresh();
        this.toastService.warning('Market data refreshed with cached baselines', 'Market Refresh');
      }
    });
  }
}
