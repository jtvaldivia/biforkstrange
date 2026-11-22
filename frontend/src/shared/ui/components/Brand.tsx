import type { SVGAttributes } from "react";

/** Las trayectorias finas del abanico: cada una es una vida posible que sale del mismo origen. */
const VIDAS = [6, 19, 25.5, 32, 38.5, 45, 51.5, 58].map((y) => `M13 32 C30 32 36 ${y} 55 ${y}`).join(" ");

/**
 * Isotipo de Bifurca ("abanico de vidas"): un origen que se abre en muchas trayectorias, como las vidas
 * de la simulación, y una sola en trazo grueso que termina en el nodo del camino que eliges.
 * Por defecto toma la tinta y el acento del tema, así que en oscuro es la versión clara sobre fondo oscuro.
 * Para una imagen con colores fijos (la tarjeta para compartir) se pasan `color` y `acento`.
 */
export function BifurcaMark({
  size = 32,
  color = "currentColor",
  acento = "var(--acento)",
  title,
  ...rest
}: Omit<SVGAttributes<SVGSVGElement>, "color"> & { size?: number; color?: string; acento?: string; title?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      {...rest}
    >
      <path d={VIDAS} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" opacity={0.3} />
      <path d="M13 32 C30 32 36 12.5 52 12.5" fill="none" stroke={color} strokeWidth={4.5} strokeLinecap="round" />
      <circle cx={11} cy={32} r={7} fill={color} />
      <circle cx={53} cy={12.5} r={6.5} fill={acento} />
    </svg>
  );
}

/** Isotipo + nombre ("bifurca" en minúscula, Sora 700). El tamaño del texto define el del isotipo. */
export function BifurcaLogo({
  size = 20,
  color,
  acento,
  className,
}: {
  /** Tamaño de la letra, en px. */
  size?: number;
  color?: string;
  acento?: string;
  className?: string;
}) {
  return (
    <span className={["vd-marca", className].filter(Boolean).join(" ")} style={{ fontSize: size, color }} aria-label="Bifurca" role="img">
      <BifurcaMark size={Math.round(size * 1.35)} color={color} acento={acento} />
      <span aria-hidden="true">bifurca</span>
    </span>
  );
}
