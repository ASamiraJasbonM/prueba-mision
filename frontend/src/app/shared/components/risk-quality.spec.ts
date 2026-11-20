import { TestBed } from '@angular/core/testing';
import { RiskQualityComponent } from './risk-quality';
describe('Risk input transparency', () => {
  it('never describes missing provenance as verified', () => {
    const fixture = TestBed.createComponent(RiskQualityComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('no asumir datos verificados');
  });
  it('shows mixed sources and stale inputs independently of score completeness', () => {
    const fixture = TestBed.createComponent(RiskQualityComponent);
    fixture.componentRef.setInput('quality', {
      indicadores_externos: 4, indicadores_manuales: 1, indicadores_sinteticos: 1, indicadores_sin_origen: 0,
      tasas_externas: 1, tasas_sinteticas: 30, tasas_total: 31, indicadores_rezagados: ['DEUDA_PIB'],
      dias_desde_tasa: 4, dias_desde_calculo: 3, solo_fuentes_externas: false, datos_rezagados: true, requiere_revision: true,
    });
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('requiere revisión');
    expect(text).toContain('1 manuales/no verificados');
    expect(text).toContain('30 sintéticas');
    expect(text).toContain('DEUDA_PIB');
  });
});
