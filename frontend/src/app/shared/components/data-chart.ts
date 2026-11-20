import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  input,
  signal,
  untracked,
  effect,
  OnDestroy,
  viewChild,
} from '@angular/core';
import { Chart, Plugin, registerables } from 'chart.js';
Chart.register(...registerables);
const chartValue = (value: number | null | undefined): string =>
  value === null || value === undefined
    ? 'Sin dato'
    : new Intl.NumberFormat('es-CO', { maximumFractionDigits: 12 }).format(value);
export function formatChartTick(value: string | number): string {
  const number = Number(value);
  if (number !== 0 && Math.abs(number) < 0.01)
    return new Intl.NumberFormat('es-CO', {
      notation: 'scientific',
      maximumFractionDigits: 3,
    }).format(number);
  return new Intl.NumberFormat('es-CO', {
    notation: Math.abs(number) >= 1000000 ? 'compact' : 'standard',
    maximumFractionDigits: 6,
  }).format(number);
}
export interface ChartSeries {
  label: string;
  data: (number | null)[];
}
@Component({
  selector: 'app-data-chart',
  template: `<div class="chart-wrap">
      <canvas
        #canvas
        role="img"
        tabindex="0"
        [attr.aria-label]="
          title() + '. Usa las flechas izquierda y derecha para consultar valores.'
        "
        (keydown)="moveCursor($event)"
      ></canvas>
    </div>
    <p class="chart-instruction">
      {{
        kind() === 'line'
          ? 'Mueve el cursor, toca un punto o usa ← → para consultar sus valores.'
          : 'Toca un segmento o usa ← → para consultar su valor.'
      }}
    </p>
    <div class="chart-readout" aria-live="polite" aria-atomic="true">
      @if (selectedIndex(); as selection) {
        <strong>{{ xLabel() }}: {{ labels()[selection.index] }}</strong>
        @for (item of series(); track item.label) {
          <span
            >{{ item.label }} · {{ yLabel() }}:
            <b>{{ formatValue(item.data[selection.index]) }}</b></span
          >
        }
      } @else {
        <span
          >Selecciona un {{ kind() === 'line' ? 'punto' : 'segmento' }} para ver el valor
          específico.</span
        >
      }
    </div>
    <details class="chart-data">
      <summary>Ver datos del gráfico · huecos = sin dato</summary>
      <div class="table-scroll">
        <table>
          <caption>
            {{
              title()
            }}
          </caption>
          <thead>
            <tr>
              <th>{{ xLabel() }}</th>
              @for (s of series(); track s.label) {
                <th>{{ s.label }}</th>
              }
            </tr>
          </thead>
          <tbody>
            @for (label of labels(); track $index; let i = $index) {
              <tr>
                <th>{{ label }}</th>
                @for (s of series(); track s.label) {
                  <td>{{ formatValue(s.data[i]) }}</td>
                }
              </tr>
            }
          </tbody>
        </table>
      </div>
    </details>`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DataChart implements AfterViewInit, OnDestroy {
  readonly title = input('Serie histórica');
  readonly labels = input<string[]>([]);
  readonly series = input<ChartSeries[]>([]);
  readonly xLabel = input('Periodo');
  readonly yLabel = input('Valor');
  readonly selectedIndex = signal<{ index: number } | null>(null);
  readonly formatValue = chartValue;
  private cursorIndex: number | null = null;
  readonly kind = input<'line' | 'pie' | 'doughnut'>('line');
  private canvas = viewChild<ElementRef<HTMLCanvasElement>>('canvas');
  private chart: Chart | null = null;
  private ready = false;
  constructor() {
    effect(() => {
      this.labels();
      this.series();
      this.kind();
      this.xLabel();
      this.yLabel();
      if (this.ready) untracked(() => this.draw());
    });
  }
  ngAfterViewInit(): void {
    this.ready = true;
    this.draw();
  }
  ngOnDestroy(): void {
    this.chart?.destroy();
  }
  moveCursor(event: KeyboardEvent): void {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key) || !this.labels().length)
      return;
    event.preventDefault();
    const last = this.labels().length - 1;
    const index =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? last
          : this.cursorIndex === null
            ? 0
            : Math.max(0, Math.min(last, this.cursorIndex + (event.key === 'ArrowLeft' ? -1 : 1)));
    this.select(index);
    const chart = this.chart;
    if (!chart) return;
    const active = this.series().flatMap((s, datasetIndex) =>
      s.data[index] === null || s.data[index] === undefined ? [] : [{ datasetIndex, index }],
    );
    chart.setActiveElements(active);
    const point = active.length ? chart.getDatasetMeta(active[0].datasetIndex).data[index] : null;
    chart.tooltip?.setActiveElements(active, point ? { x: point.x, y: point.y } : { x: 0, y: 0 });
    chart.update('none');
  }
  private select(index: number): void {
    this.cursorIndex = index;
    this.selectedIndex.set({ index });
  }
  private draw(): void {
    const element = this.canvas()?.nativeElement;
    if (!element) return;
    this.chart?.destroy();
    this.cursorIndex = null;
    this.selectedIndex.set(null);
    const colors = ['#19634e', '#c7923e', '#547a9e', '#c47764', '#8d72a4', '#609a83'];
    const cursor: Plugin = {
      id: 'value-cursor',
      afterDatasetsDraw: (chart) => {
        if (this.kind() !== 'line' || this.cursorIndex === null) return;
        const { ctx, chartArea, scales } = chart;
        const x = scales['x'].getPixelForValue(this.cursorIndex);
        const active = chart.getActiveElements()[0];
        const y = active?.element.y;
        ctx.save();
        ctx.strokeStyle = '#24634e';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(x, chartArea.top);
        ctx.lineTo(x, chartArea.bottom);
        if (y !== undefined) {
          ctx.moveTo(chartArea.left, y);
          ctx.lineTo(chartArea.right, y);
        }
        ctx.stroke();
        ctx.restore();
      },
    };
    this.chart = new Chart(element, {
      plugins: [cursor],
      type: this.kind(),
      data: {
        labels: this.labels(),
        datasets: this.series().map((s, i) => ({
          label: s.label,
          data: s.data,
          borderColor: colors[i % colors.length],
          backgroundColor: this.kind() !== 'line' ? colors : colors[i % colors.length] + '18',
          spanGaps: false,
          tension: 0,
          pointRadius: 3,
          pointHoverRadius: 6,
          pointHitRadius: 18,
          borderWidth: 2,
          fill: false,
        })),
      },
      options: {
        responsive: true,
        locale: 'es-CO',
        interaction: {
          mode: this.kind() === 'line' ? 'index' : 'nearest',
          intersect: this.kind() !== 'line',
        },
        onHover: (event, active, chart) => {
          if (active.length) {
            this.select(active[0].index);
            chart.canvas.style.cursor = 'crosshair';
          } else chart.canvas.style.cursor = 'default';
        },
        onClick: (_event, active) => {
          if (active.length) this.select(active[0].index);
        },
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8, padding: 20 } },
          tooltip: {
            backgroundColor: '#123c31',
            padding: 12,
            displayColors: true,
            callbacks: {
              title: (items) =>
                this.xLabel() + ': ' + (this.labels()[items[0]?.dataIndex ?? 0] ?? ''),
              afterTitle: () => this.yLabel(),
              label: (c) =>
                c.dataset.label + ': ' + chartValue(typeof c.raw === 'number' ? c.raw : null),
            },
          },
        },
        ...(this.kind() === 'line'
          ? {
              scales: {
                x: {
                  title: { display: true, text: this.xLabel(), color: '#4f6256' },
                  ticks: { autoSkip: true, maxTicksLimit: 6, maxRotation: 0 },
                  grid: { display: false },
                },
                y: {
                  title: { display: true, text: this.yLabel(), color: '#4f6256' },
                  ticks: {
                    maxTicksLimit: 6,
                    callback: formatChartTick,
                  },
                  grid: { color: '#edf0eb' },
                },
              },
            }
          : {}),
      },
    });
  }
}
