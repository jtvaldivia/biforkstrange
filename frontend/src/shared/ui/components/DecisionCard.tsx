import type { ReactNode } from "react";
import { cx } from "../tokens";
import { CheckIcon } from "./Icon";
import { Tag } from "./Controls";

export type DecisionTag = { label: string; tone?: "default" | "minus" | "accent" | "sol" };

/**
 * Tarjeta de un camino posible en la decisión del año. Se hunde al elegirla.
 * `detail` solo se ve en la elegida: lo que hace falta para decidir va a la vista, el resto se abre al tocar.
 * `tile` es la versión de grilla, con el dibujo grande arriba.
 */
export function DecisionCard({
  art,
  title,
  subtitle,
  tags = [],
  detail,
  tile = false,
  selected,
  onSelect,
}: {
  /** Ilustración, p. ej. <DecisionArt kind="viaje" />. En `tile`, con `llenar`. */
  art: ReactNode;
  title: ReactNode;
  subtitle?: string;
  tags?: DecisionTag[];
  detail?: ReactNode;
  tile?: boolean;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button type="button" className={cx("vd-opcion", tile && "vd-opcion--tile", detail != null && "vd-opcion--abre")} aria-pressed={selected} onClick={onSelect}>
      <span className="vd-opcion-dibujo">{art}</span>
      <span className="vd-opcion-texto">
        <span className="vd-opcion-titulo">{title}</span>
        {subtitle && <span className="vd-opcion-sub">{subtitle}</span>}
        {tags.length > 0 && (
          <span className="vd-opcion-tags">
            {tags.map((t) => (
              <Tag key={t.label} tone={t.tone}>
                {t.label}
              </Tag>
            ))}
          </span>
        )}
      </span>
      {selected && detail != null && <span className="vd-opcion-detalle">{detail}</span>}
      <span className="vd-opcion-check">
        <CheckIcon />
      </span>
    </button>
  );
}

/** Lista de caminos con selección única. `tile`: grilla de dos columnas con dibujos grandes. */
export function DecisionList<T extends string>({
  options,
  value,
  onChange,
  label,
  tile = false,
}: {
  options: ({ id: T } & Omit<Parameters<typeof DecisionCard>[0], "selected" | "onSelect" | "tile">)[];
  value: T | null;
  onChange: (id: T) => void;
  label: string;
  tile?: boolean;
}) {
  return (
    <div className={tile ? "vd-rejilla" : "vd-pila"} role="group" aria-label={label} style={tile ? undefined : { gap: 14 }}>
      {options.map(({ id, ...o }) => (
        <DecisionCard key={id} {...o} tile={tile} selected={value === id} onSelect={() => onChange(id)} />
      ))}
    </div>
  );
}
