import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RiskQuality } from '../models/dto';

@Component({
  selector: 'app-risk-quality',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `@if (quality(); as q) {
    <div class="quality" [class.warning]="q.requiere_revision">
      <strong>Calidad de datos: {{ q.requiere_revision ? 'requiere revisión' : 'fuentes externas recientes' }}</strong>
      <span>Indicadores: {{ q.indicadores_externos }}/6 externos · {{ q.indicadores_manuales }} manuales/no verificados ·
        {{ q.indicadores_sinteticos }} sintéticos · {{ q.indicadores_sin_origen }} sin origen.</span>
      @if (!compact()) {
        <span>Cambio: {{ q.tasas_externas }}/{{ q.tasas_total }} observaciones externas · {{ q.tasas_sinteticas }} sintéticas.</span>
        <span>Antigüedad: cálculo {{ q.dias_desde_calculo }} día(s) · última tasa
          {{ q.dias_desde_tasa === null ? 'sin fecha' : q.dias_desde_tasa + ' día(s)' }}.</span>
        @if (q.indicadores_rezagados.length) {
          <span>Indicadores de años anteriores al umbral: {{ q.indicadores_rezagados.join(', ') }}.</span>
        }
        @if (q.indicadores_sin_fecha?.length) {
          <span>Indicadores sin año válido: {{ q.indicadores_sin_fecha?.join(', ') }}.</span>
        }
        <small>Un cálculo completo puede contener datos demo o manuales. Se señala rezago económico de más de dos años,
          tasa de más de dos días o cálculo de más de un día. La procedencia no certifica la exactitud del proveedor.</small>
      } @else {
        <span>Cambio sintético: {{ q.tasas_sinteticas }}/{{ q.tasas_total }} · {{ q.datos_rezagados ? 'Hay datos rezagados o sin fecha' : 'Sin rezago detectado' }}.</span>
      }
    </div>
  } @else { <small>Calidad de datos no disponible; no asumir datos verificados.</small> }`,
  styles: [`
    .quality { display: grid; gap: 5px; padding: 10px; margin-top: 8px; border-left: 3px solid #15803d; font-size: 12px; line-height: 1.5; }
    .warning { border-color: #a16207; background: #fffbeb; color: #713f12; }
  `],
})
export class RiskQualityComponent {
  readonly quality = input<RiskQuality>();
  readonly compact = input(false);
}
