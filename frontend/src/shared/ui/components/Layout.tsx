import type { CSSProperties, HTMLAttributes, ReactNode } from "react";
import { sceneClass, type SceneMode } from "../scene";
import { cssVars, cx } from "../tokens";

type ScreenProps = HTMLAttributes<HTMLDivElement> & {
  /** `noche` para oficina, túnel y momentos duros: un tinte frío del mismo tema, no un fondo invertido. */
  tone?: "dia" | "noche";
  /**
   * Activa el reloj de escena (ver scene.ts) para pantallas con <TravelScene>, <OfficeScene>
   * o elementos con `revealAt`. Cambia la `key` del Screen para volver a correrla.
   */
  scene?: SceneMode;
  /** Separación vertical entre bloques (px). */
  gap?: number;
  /** Más margen lateral (pantallas de relato, como "Lo que no vuelve"). */
  wide?: boolean;
};

/** Pantalla completa de la app: columna de teléfono, fondo y tipografía del kit. */
export function Screen({ tone = "dia", gap = 20, wide, scene, className, style, ...rest }: ScreenProps) {
  return (
    <div
      className={cx("vd", "vd-pantalla", tone === "noche" && "vd-noche", wide && "vd-pantalla--ancha", sceneClass(scene), className)}
      style={{ ...cssVars({ "--vd-gap": `${gap}px` }), ...style }}
      {...rest}
    />
  );
}

/** Fila superior: pastilla o botón atrás a la izquierda, meta a la derecha. */
export function ScreenHeader({ left, right }: { left?: ReactNode; right?: ReactNode }) {
  return (
    <header className="vd-cabecera">
      {left}
      {right}
    </header>
  );
}

/** Pie pegado al fondo de la pantalla, para la acción principal. */
export function ScreenFooter({ children }: { children: ReactNode }) {
  return <div className="vd-pie">{children}</div>;
}

type StackProps = HTMLAttributes<HTMLDivElement> & { gap?: number; as?: "div" | "section" };

/** Columna con separación. */
export function Stack({ gap = 8, as: Tag = "div", className, style, ...rest }: StackProps) {
  return <Tag className={cx("vd-pila", className)} style={{ ...cssVars({ "--vd-gap": `${gap}px` }), ...style }} {...rest} />;
}

/** Fila que envuelve (tags, chips). */
export function Row({ gap = 8, className, style, ...rest }: HTMLAttributes<HTMLDivElement> & { gap?: number }) {
  return <div className={cx("vd-fila", className)} style={{ ...cssVars({ "--vd-gap": `${gap}px` }), ...style }} {...rest} />;
}

/** Caja gris suave (niebla) para agrupar controles. */
export function Panel({ className, ...rest }: HTMLAttributes<HTMLElement>) {
  return <section className={cx("vd-caja", className)} {...rest} />;
}

/** Tarjeta amarilla de momento (p. ej. "Tu felicidad"). */
export function SunCard({ className, ...rest }: HTMLAttributes<HTMLElement>) {
  return <section className={cx("vd-sol", "vd-tarjeta-sol", className)} {...rest} />;
}

/** Banda con el tinte de noche del tema (p. ej. "Lo que te perdiste"): se distingue del fondo sin invertirlo. */
export function NightBand({ className, ...rest }: HTMLAttributes<HTMLElement>) {
  return <section className={cx("vd-banda-noche", className)} {...rest} />;
}

/** Aparece lento, en secuencia: para relatos que se leen de a uno. */
export function SlowReveal({ delay = 0, style, className, ...rest }: HTMLAttributes<HTMLDivElement> & { delay?: number }) {
  return <div className={cx("vd-lento", className)} style={{ animationDelay: `${delay}s`, ...style } as CSSProperties} {...rest} />;
}
