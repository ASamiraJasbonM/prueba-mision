import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RiskLevel, RISK_LABELS } from '../models/dto';
@Component({
  selector: 'app-risk-badge',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span class="risk-badge" [attr.data-risk]="level()"
    ><span class="risk-dot"></span>{{ level() ? labels[level()!] : 'Sin cálculo' }}</span
  >`,
})
export class RiskBadgeComponent {
  readonly level = input<RiskLevel | null>(null);
  readonly labels = RISK_LABELS;
}
