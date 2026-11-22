import type { CSSProperties } from "react";

/** Los cuatro indicadores del gemelo. El orden es el que usan todas las pantallas. */
export type IndicatorKey = "dinero" | "carrera" | "bienestar" | "vida";

export const INDICATORS: { key: IndicatorKey; label: string }[] = [
  { key: "dinero", label: "Dinero" },
  { key: "carrera", label: "Carrera" },
  { key: "bienestar", label: "Bienestar" },
  { key: "vida", label: "Vida personal" },
];

export const indicatorLabel = (k: IndicatorKey) => INDICATORS.find((i) => i.key === k)!.label;

/** Color de un indicador como variable CSS (cambia con el tema). */
export const indicatorColor = (k: IndicatorKey) => `var(--${k})`;

/** Valores de los cuatro indicadores, 0 a 100. */
export type IndicatorValues = Record<IndicatorKey, number>;

/** Permite pasar variables CSS (--algo) en `style` sin pelear con los tipos. */
export const cssVars = (vars: Record<string, string | number>) => vars as CSSProperties;

/** Signo con menos tipográfico: +17, −18, 0. */
export const signed = (n: number) => (n > 0 ? `+${n}` : n < 0 ? `−${Math.abs(n)}` : "0");

export const clamp01 = (n: number) => Math.min(1, Math.max(0, n));

export const cx = (...xs: (string | false | null | undefined)[]) => xs.filter(Boolean).join(" ");
