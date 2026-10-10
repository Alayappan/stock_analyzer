import { Component, Input, OnChanges, SimpleChanges, ViewChild, ElementRef, AfterViewInit, OnDestroy, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, registerables } from 'chart.js';
import { BenchmarkGrowth } from '../../models/analytics.model';

Chart.register(...registerables);

@Component({
  selector: 'app-benchmark-chart',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="w-full flex flex-col">
      <!-- Period controls -->
      <div class="flex items-center justify-between mb-3">
        <div class="text-xs text-finance-muted font-medium">
          Relative Performance: <span class="text-emerald-400 font-semibold">Portfolio Growth</span> vs <span class="text-cyan-400 font-semibold">{{ growthData?.benchmark_name || 'Benchmark' }}</span>
        </div>
        <div class="flex items-center gap-1 bg-finance-bg border border-finance-border rounded-lg p-0.5 text-xs">
          @for (p of periods; track p) {
            <button 
              (click)="onPeriodChange(p)"
              [class.bg-finance-card]="currentPeriod === p"
              [class.text-white]="currentPeriod === p"
              [class.font-semibold]="currentPeriod === p"
              [class.text-finance-muted]="currentPeriod !== p"
              class="px-2.5 py-1 rounded transition hover:text-white">
              {{ p.toUpperCase() }}
            </button>
          }
        </div>
      </div>

      <!-- Canvas container -->
      <div class="w-full h-72 relative">
        <canvas #chartCanvas></canvas>
        @if (!growthData || !growthData.points || growthData.points.length === 0) {
          <div class="absolute inset-0 flex items-center justify-center text-xs text-finance-muted">
            Loading benchmark comparison data...
          </div>
        }
      </div>
    </div>
  `
})
export class BenchmarkChartComponent implements AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('chartCanvas') chartCanvas!: ElementRef<HTMLCanvasElement>;
  @Input() growthData: BenchmarkGrowth | null = null;
  @Input() currentPeriod: string = '6mo';
  @Output() periodChange = new EventEmitter<string>();

  periods = ['1mo', '3mo', '6mo', '1y'];
  private chart: Chart | null = null;

  ngAfterViewInit() {
    this.createOrUpdateChart();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['growthData'] && this.chartCanvas) {
      this.createOrUpdateChart();
    }
  }

  ngOnDestroy() {
    if (this.chart) {
      this.chart.destroy();
    }
  }

  onPeriodChange(period: string) {
    this.currentPeriod = period;
    this.periodChange.emit(period);
  }

  private createOrUpdateChart() {
    if (!this.chartCanvas) return;
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }

    if (!this.growthData || !this.growthData.points || this.growthData.points.length === 0) return;

    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (!ctx) return;

    const points = this.growthData.points;
    const labels = points.map(p => p.date);
    const portfolioReturns = points.map(p => p.portfolio_return_pct);
    const benchmarkReturns = points.map(p => p.benchmark_return_pct);

    // Gradient for portfolio line
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(16, 185, 129, 0.25)');
    gradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Portfolio Return (%)',
            data: portfolioReturns,
            borderColor: '#10b981',
            backgroundColor: gradient,
            fill: true,
            tension: 0.3,
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHoverBackgroundColor: '#10b981'
          },
          {
            label: `${this.growthData.benchmark_name || 'Benchmark'} (%)`,
            data: benchmarkReturns,
            borderColor: '#06b6d4',
            backgroundColor: 'transparent',
            borderDash: [5, 5],
            fill: false,
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointHoverBackgroundColor: '#06b6d4'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        scales: {
          x: {
            grid: {
              color: 'rgba(31, 41, 55, 0.5)',
            },
            ticks: {
              color: '#9ca3af',
              font: { size: 10 },
              maxTicksLimit: 8
            }
          },
          y: {
            grid: {
              color: 'rgba(31, 41, 55, 0.5)',
            },
            ticks: {
              color: '#9ca3af',
              font: { size: 10 },
              callback: (val) => `${val}%`
            }
          }
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: '#111827',
            titleColor: '#f3f4f6',
            bodyColor: '#e5e7eb',
            borderColor: '#374151',
            borderWidth: 1,
            padding: 10,
            callbacks: {
              label: (context) => {
                const val = Number(context.raw);
                const prefix = val >= 0 ? '+' : '';
                return ` ${context.dataset.label}: ${prefix}${val.toFixed(2)}%`;
              }
            }
          }
        }
      }
    });
  }
}
