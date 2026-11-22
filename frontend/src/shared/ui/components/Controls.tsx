import { useId, type ReactNode } from "react";
import { cx } from "../tokens";

/** Chip que se marca y desmarca (gustos, rasgos). */
export function Chip({ pressed, onToggle, children }: { pressed: boolean; onToggle: () => void; children: ReactNode }) {
  return (
    <button type="button" className="vd-chip" aria-pressed={pressed} onClick={onToggle}>
      {children}
    </button>
  );
}

/** Selector de dos (o más) opciones excluyentes. */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
  /** Descripción accesible del grupo. */
  label: string;
}) {
  return (
    <div
      className="vd-seg"
      role="group"
      aria-label={label}
      style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}
    >
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={o.value === value} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Deslizador con etiqueta y valor a la derecha (p. ej. reparto de prioridades). */
export function Slider({
  label,
  value,
  onChange,
  min = 0,
  max = 10,
  step = 1,
  color,
  display,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  /** Color del riel, p. ej. `var(--dinero)`. */
  color?: string;
  /** Lo que se muestra a la derecha; por defecto el valor. */
  display?: ReactNode;
}) {
  const id = useId();
  return (
    <div className="vd-rango-campo">
      <div className="vd-ind-fila">
        <label htmlFor={id} className="vd-ind-n">
          {label}
        </label>
        <span className="vd-ind-v">{display ?? value}</span>
      </div>
      <input
        id={id}
        className="vd-rango"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={color ? { accentColor: color } : undefined}
      />
    </div>
  );
}

/** Etiqueta chica de efecto: "+ Carrera", "− Familia", "Para ti". */
export function Tag({
  tone = "default",
  children,
  className,
}: {
  /** `minus` = algo que pierdes (borde punteado). */
  tone?: "default" | "minus" | "accent" | "sol";
  children: ReactNode;
  className?: string;
}) {
  const t = { default: undefined, minus: "vd-tag--menos", accent: "vd-tag--acento", sol: "vd-tag--sol" }[tone];
  return <span className={cx("vd-tag", t, className)}>{children}</span>;
}
