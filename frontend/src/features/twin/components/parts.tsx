/** Piezas del módulo del gemelo, armadas con las clases y el lenguaje del kit (@/shared/ui). */
import type { ReactNode } from "react";
import { CheckIcon, Heading, Pill, Stack, Text } from "@/shared/ui";
import type { Dim } from "../types";

const LETTERS = "ABCDEFGH";

/** Encabezado de sección: pastilla, título grande y bajada. */
export function SectionIntro({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) {
  return (
    <Stack gap={10}>
      <div><Pill>{eyebrow}</Pill></div>
      <Heading level={1}>{title}</Heading>
      {children && <Text>{children}</Text>}
    </Stack>
  );
}

/**
 * Lista de elección única con tarjetas del kit (vd-opcion). En vez de ilustración lleva una letra.
 * `extra` agrega una opción punteada al final (p. ej. "Ninguna me representa").
 */
export function ChoiceList({
  options,
  value,
  onChange,
  label,
  extra,
  disabled,
}: {
  options: string[];
  value: number | null;
  onChange: (i: number) => void;
  label: string;
  extra?: { value: number; label: string };
  disabled?: boolean;
}) {
  return (
    <div className="tw-choices" role="group" aria-label={label}>
      {options.map((o, i) => (
        <button
          key={i}
          type="button"
          className="vd-opcion tw-choice"
          aria-pressed={value === i}
          onClick={() => onChange(i)}
          disabled={disabled}
        >
          <span className="tw-choice-key" aria-hidden="true">{LETTERS[i]}</span>
          <span className="vd-opcion-texto">
            <span className="vd-opcion-titulo tw-choice-text">{o}</span>
          </span>
          <span className="vd-opcion-check"><CheckIcon /></span>
        </button>
      ))}
      {extra && (
        <button
          type="button"
          className="vd-opcion tw-choice tw-choice--extra"
          aria-pressed={value === extra.value}
          onClick={() => onChange(extra.value)}
          disabled={disabled}
        >
          <span className="tw-choice-key tw-choice-key--extra" aria-hidden="true">?</span>
          <span className="vd-opcion-texto">
            <span className="vd-opcion-titulo tw-choice-text">{extra.label}</span>
          </span>
          <span className="vd-opcion-check"><CheckIcon /></span>
        </button>
      )}
    </div>
  );
}

/** Rasgo medido: posición (rayita) con su margen de duda (banda). 50 = promedio. */
export function DimBar({ nombre, dim, previous, hint }: { nombre: string; dim: Dim; previous?: number; hint?: string }) {
  const lo = Math.max(0, dim.m - dim.sd);
  const hi = Math.min(100, dim.m + dim.sd);
  const measured = dim.n > 0 || dim.sd < 30;
  return (
    <div className="tw-dim" title={hint}>
      <div className="tw-dim-top">
        <span className="vd-ind-n">{nombre}</span>
        <span className="tw-dim-val">{measured ? `${Math.round(dim.m)} ±${Math.round(dim.sd)}` : "sin medir"}</span>
      </div>
      <span className="tw-track" role="img" aria-label={`${nombre}: ${Math.round(dim.m)} más o menos ${Math.round(dim.sd)}`}>
        <span className="tw-mid" />
        <span className="tw-band" style={{ left: `${lo}%`, width: `${hi - lo}%` }} />
        {previous !== undefined && <span className="tw-prev" style={{ left: `${previous}%` }} />}
        <span className="tw-mark" style={{ left: `${dim.m}%` }} />
      </span>
    </div>
  );
}

/** Barra simple de 0–100 con etiqueta y valor (acierto por tema, calibración). */
export function Meter({ label, value, display, tone = "acento", marker }: {
  label: ReactNode;
  value: number;
  display?: ReactNode;
  tone?: "acento" | "sol" | "control";
  /** Línea de referencia (p. ej. el azar). */
  marker?: number;
}) {
  return (
    <div className="tw-meter">
      <div className="tw-dim-top">
        <span className="vd-ind-n">{label}</span>
        <span className="tw-dim-val">{display ?? `${Math.round(value)}%`}</span>
      </div>
      <span className="tw-meter-track">
        <i className={`tw-meter-fill tw-meter-fill--${tone}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
        {marker !== undefined && <b style={{ left: `${marker}%` }} />}
      </span>
    </div>
  );
}

/** Claridad del perfil, misma fórmula que el backend (spec §5.4). */
export function clarityOf(dims: Record<string, Dim>) {
  const list = Object.values(dims);
  const vals = list.map((d) => Math.min(1, Math.max(0, 1 - (d.sd - 8) / 22)));
  return {
    pct: Math.round((100 * vals.reduce((a, b) => a + b, 0)) / list.length),
    measured: list.filter((d) => d.sd <= 12 && d.n >= 2).length,
    total: list.length,
  };
}
