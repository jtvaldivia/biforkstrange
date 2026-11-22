import type { CSSProperties } from "react";
import { INDICATORS, indicatorColor, indicatorLabel, type IndicatorKey } from "../tokens";

/* ───────── Evolución: cuatro líneas a lo largo de los años ───────── */

const X0 = 20;
const X1 = 300;
const Y0 = 180; // valor 0
const YS = 1.6; // px por punto (100 → 20)

const shortLabel: Record<IndicatorKey, string> = { dinero: "Dinero", carrera: "Carrera", bienestar: "Bienestar", vida: "Vida" };

/**
 * Gráfico "Diez años en cuatro líneas". Cada serie es un valor 0–100 por año (o por turno).
 * `band` sombrea un tramo (p. ej. el túnel) y `marker` marca un momento (p. ej. "Agosto 2031").
 * Las posiciones de `band` y `marker` son índices de la serie (pueden ser fraccionarios).
 */
export function LinesChart({
  series,
  startYear,
  endYear,
  band,
  marker,
  label,
}: {
  series: Partial<Record<IndicatorKey, number[]>>;
  startYear: number;
  endYear: number;
  band?: { from: number; to: number; label?: string };
  marker?: { at: number; label?: string };
  /** Descripción accesible de lo que muestra el gráfico. */
  label: string;
}) {
  const keys = INDICATORS.map((i) => i.key).filter((k) => series[k]?.length);
  const n = Math.max(...keys.map((k) => series[k]!.length), 2);
  const x = (i: number) => X0 + ((X1 - X0) * i) / (n - 1);
  const y = (v: number) => Y0 - v * YS;

  // etiquetas al final de cada línea, separadas al menos 12px
  const ends = keys
    .map((k) => ({ k, y: y(series[k]![series[k]!.length - 1]) + 4 }))
    .sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) ends[i].y = Math.max(ends[i].y, ends[i - 1].y + 12);

  const mid = Math.round((startYear + endYear) / 2);

  return (
    <svg viewBox="0 0 370 210" width="100%" role="img" aria-label={label} style={{ display: "block", maxWidth: 370 }}>
      {band && <rect x={x(band.from)} y={18} width={x(band.to) - x(band.from)} height={162} fill="var(--niebla)" />}
      <path d={`M${X0} ${Y0} H${X1}`} stroke="var(--linea)" strokeWidth={2} strokeLinecap="round" />
      {marker && (
        <path d={`M${x(marker.at)} 18 V${Y0}`} stroke="var(--tinta)" strokeWidth={1.5} strokeDasharray="2 4" strokeLinecap="round" />
      )}
      {band?.label && (
        <text className="vd-svg-s" x={(x(band.from) + x(band.to)) / 2} y={12} textAnchor="middle">
          {band.label}
        </text>
      )}
      {marker?.label && (
        <text className="vd-svg-s" x={x(marker.at) + 2} y={12}>
          {marker.label}
        </text>
      )}
      {keys.map((k, i) => (
        <polyline
          key={k}
          className="vd-trazo"
          points={series[k]!.map((v, j) => `${x(j)},${y(v)}`).join(" ")}
          fill="none"
          stroke={indicatorColor(k)}
          strokeWidth={3.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          pathLength={360}
          style={{ animationDelay: `${0.2 + i * 0.3}s` } as CSSProperties}
        />
      ))}
      {ends.map((e) => (
        <text key={e.k} className="vd-svg-t" x={308} y={e.y}>
          {shortLabel[e.k]}
        </text>
      ))}
      <text className="vd-svg-s" x={X0} y={198}>
        {startYear}
      </text>
      <text className="vd-svg-s" x={(X0 + X1) / 2} y={198} textAnchor="middle">
        {mid}
      </text>
      <text className="vd-svg-s" x={X1} y={198} textAnchor="end">
        {endYear}
      </text>
    </svg>
  );
}

/* ───────── Rangos lado a lado: esta vida contra otra ───────── */

export type Range = { low: number; high: number; median: number };

/**
 * Rango de resultados de dos caminos en un indicador (0–100).
 * Barra angosta: camino seguro. Barra ancha: apuesta. La rayita es la mediana.
 */
/** `colorA` y `colorB` pisan los colores por defecto (A: el del indicador; B: solo el borde). */
export function RangeCompare({ indicator, a, b, label, colorA, colorB }: { indicator: IndicatorKey; a: Range; b: Range; label?: string; colorA?: string; colorB?: string }) {
  const bar = (r: Range, fill: string) => (
    <span className="vd-rango-pista">
      <i style={{ left: `${r.low}%`, width: `${r.high - r.low}%`, background: fill }} />
      <b style={{ left: `${r.median}%` }} />
    </span>
  );
  return (
    <div className="vd-pila" style={{ gap: 5 }}>
      <span className="vd-ind-n">{label ?? indicatorLabel(indicator)}</span>
      <div
        className="vd-rangos"
        role="img"
        aria-label={`${label ?? indicatorLabel(indicator)}: A entre ${a.low} y ${a.high}, B entre ${b.low} y ${b.high}`}
      >
        <em>A</em>
        {bar(a, colorA ?? indicatorColor(indicator))}
        <em>B</em>
        {bar(b, colorB ?? "var(--papel)")}
      </div>
    </div>
  );
}

/* ───────── Línea de visitas: cuántas veces viste a alguien ───────── */

/**
 * Línea de tiempo con visitas (punto lleno), invitaciones perdidas (punto punteado)
 * y un final (rombo). Las fechas van en años con decimales (2029.5 = mediados de 2029).
 */
export function VisitsTimeline({
  startYear,
  endYear,
  seen,
  missed,
  end,
  label,
}: {
  startYear: number;
  endYear: number;
  seen: number[];
  missed: number[];
  end?: number;
  label: string;
}) {
  const span = Math.max(endYear - startYear, 1);
  const x = (t: number) => 10 + ((t - startYear) / span) * 258;
  const lineEnd = end !== undefined ? x(end) : 306;
  const ticks = [startYear, Math.round((startYear + endYear) / 2), endYear];
  return (
    <svg viewBox="0 0 342 70" width="100%" role="img" aria-label={label} style={{ display: "block", maxWidth: 342 }}>
      <path d={`M10 30 H${lineEnd}`} stroke="var(--control)" strokeWidth={2} strokeLinecap="round" />
      <path d={`M${lineEnd} 30 H332`} stroke="var(--control)" strokeWidth={2} strokeLinecap="round" strokeDasharray="1 6" />
      <path d={ticks.map((t) => `M${x(t)} 44 V50`).join(" ")} stroke="var(--control)" strokeWidth={1.5} strokeLinecap="round" />
      {missed.map((t, i) => (
        <circle key={`m${i}`} cx={x(t)} cy={30} r={6} fill="var(--papel)" stroke="var(--suave)" strokeWidth={1.5} strokeDasharray="3 3" />
      ))}
      {seen.map((t, i) => (
        <circle key={`s${i}`} cx={x(t)} cy={30} r={7} fill="var(--tinta)" />
      ))}
      {end !== undefined && (
        <path
          d={`M${lineEnd} 20 L${lineEnd + 8} 30 L${lineEnd} 40 L${lineEnd - 8} 30Z`}
          fill="var(--papel)"
          stroke="var(--tinta)"
          strokeWidth={2}
          strokeLinejoin="round"
        />
      )}
      {ticks.map((t, i) => (
        <text key={t} className="vd-svg-s" x={x(t)} y={64} textAnchor={i === 0 ? "start" : "middle"}>
          {t}
        </text>
      ))}
    </svg>
  );
}
