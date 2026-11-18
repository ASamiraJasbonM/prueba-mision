export type DecimalString = string;
export type Role = 'ADMIN' | 'ANALISTA' | 'VIEWER';
export type RiskLevel = 'BAJO' | 'MODERADO' | 'ALTO' | 'CRITICO';
export type IndicatorType =
  'PIB' | 'INFLACION' | 'DESEMPLEO' | 'BALANZA_COMERCIAL' | 'DEUDA_PIB' | 'PIB_PERCAPITA';
export type AssetType = 'RENTA_FIJA' | 'RENTA_VARIABLE' | 'COMMODITIES' | 'MONEDA';
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
export interface User {
  id: number;
  email: string;
  nombre_completo: string;
  rol: Role;
  activo: boolean;
  fecha_creacion: string;
}
export interface Tokens {
  access: string;
  refresh: string;
}
export interface Country {
  codigo_iso: string;
  nombre: string;
  moneda_codigo: string;
  moneda_nombre: string;
  region: string;
  latitud: DecimalString;
  longitud: DecimalString;
  poblacion: number;
  bandera_url: string;
  activo: boolean;
}
export interface Indicator {
  id: number;
  pais: string;
  tipo: IndicatorType;
  valor: DecimalString;
  unidad: string;
  anio: number;
  fuente: string;
  fecha_actualizacion: string;
}
export interface CountryDetail extends Country {
  indicadores: Indicator[];
}
export interface ExchangeRate {
  id: number;
  moneda_origen: string;
  moneda_destino: string;
  tasa: DecimalString;
  fecha: string;
  variacion_porcentual: DecimalString | null;
  fuente: string;
}
export interface Risk {
  id: number;
  pais: string;
  pais_nombre: string;
  fecha_calculo: string;
  score_economico: DecimalString;
  score_cambiario: DecimalString;
  score_estabilidad: DecimalString;
  indice_compuesto: DecimalString;
  nivel_riesgo: RiskLevel;
  variacion: DecimalString | null;
  tendencia: 'SUBE' | 'BAJA' | 'ESTABLE' | 'SIN_HISTORICO';
  clave_calculo: string | null;
  detalle_calculo: {
    parcial: boolean;
    faltantes: string[];
    fuentes?: Record<
      string,
      {
        anio: number;
        fuente: string;
        unidad?: string;
        valor?: string;
        valor_usd?: string;
        fecha: string;
      }
    >;
    factores_en_riesgo?: { factor: string; valor: string; penalizacion: string }[];
  };
}
export interface RiskDetail extends Risk {
  historico: Risk[];
  historico_url: string;
}
export interface MapCountry {
  codigo_iso: string;
  nombre: string;
  latitud: DecimalString;
  longitud: DecimalString;
  indice_compuesto: DecimalString | null;
  nivel_riesgo: RiskLevel | null;
  color: string;
  parcial: boolean;
}
export interface DashboardSummary {
  total_paises: number;
  alertas_activas: number;
  portafolios_usuario: number;
  promedio_irpc_region: DecimalString | null;
  paises_con_irpc: number;
  paises_irpc_parcial: number;
}
export interface TrendPoint {
  pais: string;
  tipo: IndicatorType;
  anio: number;
  valor: DecimalString | null;
  unidad: string;
  fuente: string | null;
}
export interface Portfolio {
  id: number;
  nombre: string;
  descripcion: string;
  usuario: number;
  es_publico: boolean;
  activo: boolean;
  fecha_creacion: string;
  fecha_modificacion: string;
  version: number;
}
export interface Position {
  id: number;
  portafolio: number;
  pais: string;
  tipo_activo: AssetType;
  monto_inversion_usd: DecimalString;
  fecha_entrada: string;
  fecha_salida: string | null;
  notas: string;
}
export interface Distribution {
  codigo: string;
  monto_usd: DecimalString;
  porcentaje: DecimalString;
}
export interface PortfolioSummary {
  total_invertido_usd: DecimalString;
  posiciones_activas: number;
  por_pais: Distribution[];
  por_tipo_activo: Distribution[];
  riesgo_promedio_ponderado: DecimalString | null;
  monto_con_riesgo_usd: DecimalString;
  paises_con_datos_faltantes: string[];
  version: number;
}
export interface PortfolioDetail extends Portfolio {
  posiciones: Position[];
  metricas: PortfolioSummary;
}
export interface PortfolioInput {
  nombre: string;
  descripcion: string;
  es_publico: boolean;
  version?: number;
}
export interface PositionInput {
  pais: string;
  tipo_activo: AssetType;
  monto_inversion_usd: DecimalString;
  fecha_entrada: string;
  notas: string;
  version: number;
}
export interface Alert {
  id: number;
  usuario: number | null;
  pais: string;
  tipo_alerta: string;
  severidad: 'INFO' | 'WARNING' | 'CRITICAL';
  titulo: string;
  mensaje: string;
  leida: boolean;
  fecha_creacion: string;
}
export interface AlertSummary {
  total: number;
  no_leidas: number;
  por_tipo: Record<string, number>;
  por_severidad: Record<string, number>;
}
export interface SyncReport {
  actualizados: number;
  paises_procesados?: number;
  errores: { pais: string; operacion: string; mensaje: string }[];
  riesgo?: { calculados: number; existentes: number };
}
export const INDICATORS: { value: IndicatorType; label: string }[] = [
  { value: 'PIB', label: 'PIB' },
  { value: 'INFLACION', label: 'Inflación' },
  { value: 'DESEMPLEO', label: 'Desempleo' },
  { value: 'BALANZA_COMERCIAL', label: 'Balanza comercial' },
  { value: 'DEUDA_PIB', label: 'Deuda / PIB' },
  { value: 'PIB_PERCAPITA', label: 'PIB per cápita' },
];
export const ASSETS: { value: AssetType; label: string }[] = [
  { value: 'RENTA_FIJA', label: 'Renta fija' },
  { value: 'RENTA_VARIABLE', label: 'Renta variable' },
  { value: 'COMMODITIES', label: 'Commodities' },
  { value: 'MONEDA', label: 'Moneda' },
];
export const RISK_LABELS: Record<RiskLevel, string> = {
  BAJO: 'Bajo',
  MODERADO: 'Moderado',
  ALTO: 'Alto',
  CRITICO: 'Crítico',
};
