import { Component, Input, Output, EventEmitter, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MarketService } from '../../services/market.service';
import { TickerDetail } from '../../models/market.model';

@Component({
  selector: 'app-stock-detail-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './stock-detail-modal.component.html'
})
export class StockDetailModalComponent implements OnInit {
  @Input({ required: true }) ticker: string = '';
  @Output() close = new EventEmitter<void>();
  @Output() trade = new EventEmitter<string>();

  marketService = inject(MarketService);

  isLoading = signal<boolean>(true);
  tickerDetail = signal<TickerDetail | null>(null);

  ngOnInit() {
    this.fetchData();
  }

  fetchData() {
    this.isLoading.set(true);
    this.marketService.getTickerDetail(this.ticker).subscribe({
      next: (detail) => {
        this.tickerDetail.set(detail);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Error fetching stock detail:', err);
        this.isLoading.set(false);
      }
    });
  }

  getRangeProgress(quote: any): number {
    if (!quote.fifty_two_week_low || !quote.fifty_two_week_high) return 50;
    const low = Number(quote.fifty_two_week_low);
    const high = Number(quote.fifty_two_week_high);
    const curr = Number(quote.current_price);
    if (high <= low) return 50;
    const progress = ((curr - low) / (high - low)) * 100;
    return Math.max(0, Math.min(100, Math.round(progress)));
  }

  formatMarketCap(val?: number): string {
    if (!val) return 'N/A';
    if (val >= 1e12) return (val / 1e12).toFixed(2) + ' T';
    if (val >= 1e9) return (val / 1e9).toFixed(2) + ' B';
    if (val >= 1e6) return (val / 1e6).toFixed(2) + ' M';
    return val.toLocaleString();
  }
}
