import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DividendSchedule } from '../../models/market.model';

@Component({
  selector: 'app-dividends-schedule',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dividends-schedule.component.html'
})
export class DividendsScheduleComponent {
  @Input() dividends: DividendSchedule[] = [];
  @Input() currency: string = 'USD';

  getTotalProjected(): number {
    return this.dividends.reduce((acc, d) => acc + (Number(d.projected_payout) || 0), 0);
  }
}
