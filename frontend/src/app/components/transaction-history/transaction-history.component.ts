import { Component, OnInit, Output, EventEmitter, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PortfolioService } from '../../services/portfolio.service';
import { ToastService } from '../../services/toast.service';
import { Transaction } from '../../models/transaction.model';

@Component({
  selector: 'app-transaction-history',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './transaction-history.component.html'
})
export class TransactionHistoryComponent implements OnInit {
  portfolioService = inject(PortfolioService);
  toastService = inject(ToastService);

  @Output() close = new EventEmitter<void>();

  transactions = signal<Transaction[]>([]);
  isLoading = signal<boolean>(true);

  // Filters
  filterType: string = '';
  searchTicker: string = '';

  ngOnInit() {
    this.loadTransactions();
  }

  loadTransactions() {
    this.isLoading.set(true);
    this.portfolioService.getTransactions(
      undefined,
      this.searchTicker ? this.searchTicker.trim().toUpperCase() : undefined,
      this.filterType || undefined,
      200
    ).subscribe({
      next: (list) => {
        this.transactions.set(list);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Error loading transactions:', err);
        this.isLoading.set(false);
      }
    });
  }

  deleteTx(id: number) {
    if (confirm(`Delete transaction #${id}? This will remove it from the historical ledger.`)) {
      this.portfolioService.deleteTransaction(id).subscribe({
        next: () => {
          this.toastService.success(`Transaction #${id} deleted`, 'Ledger Updated');
          this.portfolioService.triggerRefresh();
          this.loadTransactions();
        },
        error: (err) => {
          this.toastService.error(err.error?.detail || 'Failed to delete transaction', 'Error');
        }
      });
    }
  }
}
