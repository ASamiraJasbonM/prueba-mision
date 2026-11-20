import { TestBed } from '@angular/core/testing';
import { Chart, CartesianScaleOptions } from 'chart.js';
import { DataChart, formatChartTick } from './data-chart';
describe('DataChart', () => {
  it('keeps tiny exchange-rate ticks distinct from zero', () => {
    expect(formatChartTick(0.00025)).toContain('E-4');
    expect(formatChartTick(0)).toBe('0');
  });
  it('names both axes and exposes exact point values with the keyboard, including missing data', async () => {
    await TestBed.configureTestingModule({ imports: [DataChart] }).compileComponents();
    const fixture = TestBed.createComponent(DataChart);
    fixture.componentRef.setInput('labels', ['2024', '2025']);
    fixture.componentRef.setInput('series', [{ label: 'Colombia', data: [0, null] }]);
    fixture.componentRef.setInput('xLabel', 'Año');
    fixture.componentRef.setInput('yLabel', 'USD');
    fixture.detectChanges();
    const canvas = fixture.nativeElement.querySelector('canvas') as HTMLCanvasElement;
    const chart = Chart.getChart(canvas)!;
    expect((chart.scales['x']!.options as CartesianScaleOptions).title.text).toBe('Año');
    expect((chart.scales['y']!.options as CartesianScaleOptions).title.text).toBe('USD');
    expect(chart.options.interaction?.intersect).toBeFalse();
    canvas.dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true }));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.chart-readout').textContent).toContain('USD: 0');
    expect(chart.getActiveElements()[0].index).toBe(0);
    canvas.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.chart-readout').textContent).toContain('Sin dato');
    expect(fixture.nativeElement.querySelector('.chart-readout').textContent).toContain('2025');
    fixture.destroy();
    expect(Chart.getChart(canvas)).toBeUndefined();
  });
  for (const kind of ['pie', 'doughnut'] as const) {
    it(`exposes the selected ${kind} category and amount without inventing Cartesian axes`, async () => {
      await TestBed.configureTestingModule({ imports: [DataChart] }).compileComponents();
      const fixture = TestBed.createComponent(DataChart);
      fixture.componentRef.setInput('kind', kind);
      fixture.componentRef.setInput('labels', ['CO', 'BR']);
      fixture.componentRef.setInput('series', [{ label: 'Inversión', data: [1234.56, 2000] }]);
      fixture.componentRef.setInput('xLabel', 'País');
      fixture.componentRef.setInput('yLabel', 'USD');
      fixture.detectChanges();
      fixture.nativeElement
        .querySelector('canvas')
        .dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true }));
      fixture.detectChanges();
      const text = fixture.nativeElement.querySelector('.chart-readout').textContent;
      expect(text).toContain('País: CO');
      expect(text).toContain('1.234,56');
      const chart = Chart.getChart(fixture.nativeElement.querySelector('canvas'))!;
      expect('type' in chart.config ? chart.config.type : undefined).toBe(kind);
      expect(chart.scales['x']).toBeUndefined();
      expect(chart.data.datasets[0].backgroundColor instanceof Array).toBeTrue();
      fixture.destroy();
    });
  }
});
