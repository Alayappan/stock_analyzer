import { Component, Output, EventEmitter, inject, signal, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PortfolioService } from '../../services/portfolio.service';
import { ToastService } from '../../services/toast.service';
import { SubPortfolio } from '../../models/portfolio.model';

@Component({
  selector: 'app-import-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './import-modal.component.html'
})
export class ImportModalComponent {
  portfolioService = inject(PortfolioService);
  toastService = inject(ToastService);

  @Input() subPortfolios: SubPortfolio[] = [];
  @Output() close = new EventEmitter<void>();
  @Output() importSuccess = new EventEmitter<void>();

  selectedFile: File | null = null;
  targetSubPortfolioId: number | null = null;
  autoFundCash: boolean = true;
  skipDuplicates: boolean = true;
  replaceExisting: boolean = false;
  isUploading = signal<boolean>(false);
  importResult = signal<any | null>(null);
  errorMessage = signal<string | null>(null);

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.selectedFile = file;
      this.errorMessage.set(null);
      this.importResult.set(null);
    }
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
      this.selectedFile = event.dataTransfer.files[0];
      this.errorMessage.set(null);
      this.importResult.set(null);
    }
  }

  downloadSampleCsv() {
    const sample = `Symbol,Trade Date,Purchase Price,Quantity,Commission,Comment
AAPL,2024-01-15,185.5000,25,0.0000,US Tech core holding
MSFT,2024-02-10,405.2000,15,0.0000,AI & Cloud leader
NVDA,2024-03-01,820.0000,10,0.0000,Semiconductor GPU play
RELIANCE.NS,2024-01-20,2750.0000,50,20.0000,India Energy & Retail giant
TCS.NS,2024-02-15,3950.0000,30,20.0000,India IT services
INFY.NS,2024-03-10,1580.0000,75,15.0000,India Digital Transformation
7203.T,2024-01-25,2900.0000,200,500.0000,Toyota Motor Corporation
6758.T,2024-02-28,12800.0000,50,500.0000,Sony Group Japan`;

    const blob = new Blob([sample], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'yahoo_portfolio_template.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  }

  submitImport() {
    if (!this.selectedFile) {
      this.errorMessage.set('Please select a Yahoo Finance export file (CSV or Excel)');
      return;
    }

    this.isUploading.set(true);
    this.errorMessage.set(null);
    this.importResult.set(null);

    const formData = new FormData();
    formData.append('file', this.selectedFile);
    formData.append('portfolio_id', this.portfolioService.activePortfolioId().toString());
    if (this.targetSubPortfolioId) {
      formData.append('target_sub_portfolio_id', this.targetSubPortfolioId.toString());
    }
    formData.append('auto_fund_cash', this.autoFundCash.toString());
    formData.append('skip_duplicates', this.skipDuplicates.toString());
    formData.append('replace_existing', this.replaceExisting.toString());

    this.portfolioService.importPortfolioFile(formData).subscribe({
      next: (res) => {
        this.isUploading.set(false);
        this.importResult.set(res);
        let msg = `Imported ${res.transactions_imported} transactions across ${res.sub_portfolios_affected} sub-portfolios!`;
        if (res.duplicates_skipped > 0) {
          msg += ` (${res.duplicates_skipped} duplicates skipped)`;
        }
        this.toastService.success(msg, 'Import Completed');
        this.portfolioService.triggerRefresh();
        this.importSuccess.emit();
      },
      error: (err) => {
        this.isUploading.set(false);
        const detail = err.error?.detail || 'Failed to parse and import portfolio file.';
        this.errorMessage.set(detail);
        this.toastService.error(detail, 'Import Failed');
      }
    });
  }
}
