import { Component, Input, OnChanges, SimpleChanges, ViewChild, ElementRef, AfterViewInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, registerables } from 'chart.js';
import { AllocationItem } from '../../models/analytics.model';

Chart.register(...registerables);

@Component({
  selector: 'app-allocation-chart',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="relative w-full flex flex-col items-center">
      <div class="w-full h-64 relative">
        <canvas #chartCanvas></canvas>
      </div>
      @if (!items || items.length === 0) {
        <div class="absolute inset-0 flex items-center justify-center text-xs text-finance-muted">
          No allocation data available
        </div>
      }
    </div>
  `
})
export class AllocationChartComponent implements AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('chartCanvas') chartCanvas!: ElementRef<HTMLCanvasElement>;
  @Input() items: AllocationItem[] = [];
  @Input() title: string = 'Allocations';

  private chart: Chart | null = null;

  ngAfterViewInit() {
    this.createOrUpdateChart();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['items'] && this.chartCanvas) {
      this.createOrUpdateChart();
    }
  }

  ngOnDestroy() {
    if (this.chart) {
      this.chart.destroy();
    }
  }

  private createOrUpdateChart() {
    if (!this.chartCanvas) return;
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }

    if (!this.items || this.items.length === 0) return;

    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (!ctx) return;

    const labels = this.items.map(i => i.label);
    const data = this.items.map(i => Number(i.value));

    // Vibrant modern palette for financial charts
    const backgroundColors = [
      '#10b981', '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899',
      '#f59e0b', '#14b8a6', '#6366f1', '#f97316', '#84cc16'
    ];

    this.chart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: backgroundColors.slice(0, data.length),
          borderColor: '#111827',
          borderWidth: 2,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 10,
              padding: 12,
              color: '#9ca3af',
              font: {
                size: 11,
                family: 'Inter'
              }
            }
          },
          tooltip: {
            backgroundColor: '#1f2937',
            titleColor: '#fff',
            bodyColor: '#e5e7eb',
            borderColor: '#374151',
            borderWidth: 1,
            padding: 10,
            callbacks: {
              label: (context) => {
                const val = context.raw as number;
                const total = (context.dataset.data as number[]).reduce((a, b) => a + b, 0);
                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : '0';
                return ` ${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (${pct}%)`;
              }
            }
          }
        },
        cutout: '68%'
      }
    });
  }
}
