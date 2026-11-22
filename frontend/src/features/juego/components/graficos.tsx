import { useId, useState, type ReactNode } from "react";
import { cssVars, cx } from "@/shared/ui";
import { GEMELOS } from "../api";
import { minuscula, mundos, plata } from "../textos";
import type { Rango, Tono } from "../types";
import { RangoSueldo } from "./piezas";

export const sinMovimiento = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Una explicación que se abre al tocar el "?": información extra sin ocupar la pantalla. */
export function Info({ pregunta, children }: { pregunta: string; children: ReactNode }) {
  const [abierta, setAbierta] = useState(false);
  const id = useId();
  return (
    <span className="jg-info">
      <button type="button" className="jg-info-boton" aria-expanded={abierta} aria-controls={id} onClick={(e) => { e.stopPropagation(); setAbierta((a) => !a); }}>
        <i aria-hidden="true">?</i>
        {pregunta}
      </button>
      {abierta && (
        <span id={id} className="jg-info-caja" role="note">
          {children}
        </span>
      )}
    </span>
  );
}

export type Reparto = { mas: number; igual: number; menos: number };

/**
 * Medidas comunes de los gráficos de sueldo año a año (abanico, todas tus opciones, tu sueldo, tus dos vidas):
 * el mismo ancho y el mismo tramo para las líneas, con los rótulos del final a la derecha de X1.
 */
export const LIENZO = { W: 320, X0: 8, X1: 236 } as const;

/** Un sueldo en un rótulo de gráfico. Terminar sin trabajo cuenta $0, igual que en el pie de los gráficos. */
export const rotuloSueldo = (n: number) => plata(Math.max(0, n));

/**
 * La escala vertical de todos los gráficos de sueldo: si algún valor toca $0 (mundos sin trabajo), el eje parte
 * en $0 para que esa caída se lea como $0; si no, se acerca al tramo de los sueldos (80% del más bajo) para que se
 * vean las diferencias. Arriba deja 6% de aire. Devuelve la función que lleva un sueldo a su altura en el SVG.
 */
export function escalaSueldo(valores: number[], y0: number, y1: number) {
  const tope = Math.max(...valores, 1) * 1.06;
  const min = Math.min(...valores);
  const piso = min <= 0 ? 0 : min * 0.8;
  return (n: number) => y1 - ((Math.max(piso, n) - piso) / Math.max(1, tope - piso)) * (y1 - y0);
}

/**
 * El eje de abajo, igual en todos los gráficos de sueldo: la línea base y, debajo, a la izquierda la edad del
 * primer punto con su sueldo ("hoy" si ese punto es hoy) y a la derecha la edad final.
 */
export function EjeX({ alto, y1, e0, e1, sueldo0, hoy = true }: { alto: number; y1: number; e0: number; e1: number; sueldo0?: number; hoy?: boolean }) {
  const { X0, X1 } = LIENZO;
  return (
    <>
      <line className="jg-abanico-eje" x1={X0} x2={X1} y1={y1} y2={y1} />
      <text x={X0} y={alto - 6} className="jg-abanico-sub">
        {[hoy && "hoy", `${e0} años`, sueldo0 !== undefined && rotuloSueldo(sueldo0)].filter(Boolean).join(" · ")}
      </text>
      <text x={X1} y={alto - 6} textAnchor="end" className="jg-abanico-sub">{e1} años</text>
    </>
  );
}

export type PuntoAbanico = { edad: number; p10: number; p50: number; p90: number };

/**
 * Sueldo año a año: la franja contiene a 8 de cada 10 gemelos de la opción y la línea gruesa es el del medio.
 * `referencia` dibuja el gemelo del medio de otra opción (punteado) y `tu` la vida que jugaste (línea amarilla).
 */
export function Abanico({
  puntos, hoy, referencia, nombreReferencia, tu, alto = 170, color, colorReferencia,
}: {
  /** El color de la opción, para que la línea sea la misma que en su tarjeta y en la nube. */
  color?: string;
  colorReferencia?: string;
  puntos: PuntoAbanico[];
  /** Punto de partida común: edad y sueldo de hoy. */
  hoy: { edad: number; sueldo: number };
  referencia?: PuntoAbanico[];
  nombreReferencia?: string;
  tu?: { edad: number; sueldo: number }[];
  alto?: number;
}) {
  if (puntos.length === 0) return null;
  const { W, X0, X1 } = LIENZO;
  const Y0 = 14;
  const Y1 = alto - 22;
  const inicio = { edad: hoy.edad, p10: hoy.sueldo, p50: hoy.sueldo, p90: hoy.sueldo };
  const serie = [inicio, ...puntos];
  const ref = referencia ? [inicio, ...referencia] : null;
  const e0 = hoy.edad;
  const e1 = serie[serie.length - 1].edad;
  const x = (edad: number) => X0 + ((edad - e0) / Math.max(1, e1 - e0)) * (X1 - X0);
  const y = escalaSueldo([...serie.flatMap((p) => [p.p10, p.p90]), ...(ref ?? []).map((p) => p.p50), ...(tu ?? []).map((t) => t.sueldo)], Y0, Y1);
  const linea = (ps: { edad: number; v: number }[]) => ps.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.edad).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");
  const franja = `${linea(serie.map((p) => ({ edad: p.edad, v: p.p90 })))} ${[...serie].reverse().map((p) => `L${x(p.edad).toFixed(1)},${y(p.p10).toFixed(1)}`).join(" ")} Z`;
  const fin = serie[serie.length - 1];
  // etiquetas del final: se separan si quedan encima
  const etiquetas = [
    { k: "p90", v: fin.p90, t: rotuloSueldo(fin.p90), s: "90%" },
    { k: "p50", v: fin.p50, t: rotuloSueldo(fin.p50), s: "mediana" },
    { k: "p10", v: fin.p10, t: rotuloSueldo(fin.p10), s: "10%" },
  ].map((e) => ({ ...e, y: y(e.v) }));
  for (let i = 1; i < etiquetas.length; i++) if (etiquetas[i].y - etiquetas[i - 1].y < 27) etiquetas[i].y = etiquetas[i - 1].y + 27;
  const exceso = etiquetas[2].y - (Y1 + 4);
  if (exceso > 0) for (const e of etiquetas) e.y -= exceso;

  return (
    <svg
      className="jg-abanico"
      viewBox={`0 0 ${W} ${alto}`}
      role="img"
      aria-label={`Sueldo año a año, de los ${e0} a los ${e1} años. A los ${e1}: 10% ${plata(fin.p10)}, mediana ${plata(fin.p50)}, 90% ${plata(fin.p90)}.`}
    >
      <EjeX alto={alto} y1={Y1} e0={e0} e1={e1} sueldo0={hoy.sueldo} />
      <path className="jg-abanico-franja" style={color ? { fill: `color-mix(in srgb, ${color} 16%, transparent)` } : undefined} d={franja} />
      {ref && <path className="jg-abanico-ref" style={colorReferencia ? { stroke: colorReferencia } : undefined} pathLength={1} d={linea(ref.map((p) => ({ edad: p.edad, v: p.p50 })))} />}
      <path className="jg-abanico-medio" style={color ? { stroke: color } : undefined} pathLength={1} d={linea(serie.map((p) => ({ edad: p.edad, v: p.p50 })))} />
      {tu && tu.length > 1 && (
        <>
          <path className="jg-abanico-tu-borde" pathLength={1} d={linea(tu.map((t) => ({ edad: t.edad, v: t.sueldo })))} />
          <path className="jg-abanico-tu" pathLength={1} d={linea(tu.map((t) => ({ edad: t.edad, v: t.sueldo })))} />
          <circle className="jg-abanico-tu-punto" cx={x(tu[tu.length - 1].edad)} cy={y(tu[tu.length - 1].sueldo)} r={5.5} />
          <text className="jg-abanico-num jg-abanico-tu-nombre" x={x(tu[tu.length - 1].edad) - 9} y={y(tu[tu.length - 1].sueldo) + (y(tu[tu.length - 1].sueldo) < 30 ? 18 : -9)} textAnchor="end">
            tú · {GEMELOS + 1}
          </text>
        </>
      )}
      <circle className="jg-abanico-hoy" cx={x(e0)} cy={y(hoy.sueldo)} r={4.5} />
      {etiquetas.map((e) => (
        <g key={e.k} className="jg-abanico-etiqueta">
          <text x={X1 + 8} y={e.y + 1} className="jg-abanico-num">{e.t}</text>
          <text x={X1 + 8} y={e.y + 11} className="jg-abanico-sub">{e.s}</text>
        </g>
      ))}
      {ref && nombreReferencia && (
        <text x={X0} y={10} className="jg-abanico-sub">- - - si eligieras {minuscula(nombreReferencia)}</text>
      )}
    </svg>
  );
}

/** Barra apilada con sus partes y una leyenda corta. */
export function BarraPartes({ partes, sinLeyenda }: { partes: { nombre: string; prob: number; tono?: string }[]; sinLeyenda?: boolean }) {
  const visibles = partes.filter((p) => p.prob >= 0.005);
  return (
    <span className="jg-partes">
      <span className="jg-partes-barra" aria-hidden="true">
        {visibles.map((p, i) => (
          <i key={p.tono ?? p.nombre} data-n={p.tono ?? i} style={{ flexGrow: p.prob }} />
        ))}
      </span>
      {!sinLeyenda && <span className="jg-partes-leyenda">
        {visibles.map((p, i) => (
          <span key={p.nombre}>
            <i data-n={p.tono ?? i} />
            {p.nombre} <b>{Math.round(p.prob * 100)}</b>
          </span>
        ))}
      </span>}
    </span>
  );
}

/** Los años de la partida como puntos: los vividos llenos, el actual marcado. */
export function ProgresoAnios({ actual, total }: { actual: number; total: number }) {
  return (
    <span
      className="jg-progreso"
      role="progressbar"
      aria-label="Años de la partida"
      aria-valuemin={1}
      aria-valuemax={total}
      aria-valuenow={actual}
      aria-valuetext={`Año ${actual} de ${total}`}
    >
      {Array.from({ length: total }, (_, i) => (
        <i key={i} data-estado={i + 1 < actual ? "vivido" : i + 1 === actual ? "ahora" : "falta"} />
      ))}
    </span>
  );
}

export type Casilla = { id: string; texto: string; prob: number; tono: Tono };

/**
 * El dado, a la vista: la barra es todo lo que podía pasar con la opción elegida (cada tramo, su probabilidad)
 * y la ficha queda quieta en lo que te tocó a ti (el sorteo ya se vio en la espera).
 */
export function Ruleta({ casillas, salio }: { casillas: Casilla[]; salio: string }) {
  const total = casillas.reduce((a, c) => a + c.prob, 0) || 1;
  let acumulado = 0;
  const tramos = casillas.map((c) => {
    const desde = acumulado / total;
    acumulado += c.prob;
    return { ...c, desde, ancho: c.prob / total };
  });
  const tocado = tramos.find((t) => t.id === salio);
  if (!tocado || tramos.length < 2) return null;
  const meta = (tocado.desde + tocado.ancho / 2) * 100;
  return (
    <div className="jg-ruleta" role="img" aria-label={`El dado: ${tramos.map((t) => `${t.texto} ${mundos(t.ancho)} de ${GEMELOS} mundos`).join("; ")}. A ti te tocó: ${tocado.texto}`}>
      <div className="jg-ruleta-pista">
        {tramos.map((t) => (
          <span key={t.id} className={cx("jg-ruleta-tramo", t.id === salio && "jg-ruleta-tramo--tuyo")} data-tono={t.tono} style={{ flexGrow: t.ancho }}>
            {t.ancho >= 0.12 ? `${mundos(t.ancho)}` : ""}
          </span>
        ))}
        <span className="jg-ruleta-ficha" style={cssVars({ "--jg-meta": `${meta}%` })} aria-hidden="true">⚄</span>
      </div>
      <div className="jg-ruleta-leyenda" aria-hidden="true">
        {tramos.map((t) => (
          <span key={t.id} className={cx(t.id === salio && "jg-ruleta-tuyo")}>
            <i data-tono={t.tono} />
            {t.texto} <b>{mundos(t.ancho)} de {GEMELOS} mundos</b>
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * Lo que te juegas, mientras se tira tu dado: los resultados posibles de la opción que elegiste, con sus chances,
 * y la ficha buscando dónde caer. Sin resultados que sortear (una opción segura) es solo una espera corta.
 * Es la misma pista que la ruleta del resultado: ahí la ficha cae donde te tocó.
 */
export function DadoEnJuego({ casillas, titulo, texto, onSalir }: { casillas: Casilla[]; titulo: string; texto?: string; onSalir?: () => void }) {
  const total = casillas.reduce((a, c) => a + c.prob, 0) || 1;
  const hay = casillas.length > 1;
  return (
    <div className="jg-dado-pantalla" data-sorteo={hay} role="status" aria-live="polite">
      {/* si el motor tarda o no responde, siempre hay una salida: la partida queda guardada */}
      {onSalir && (
        <button type="button" className="jg-ayuda jg-dado-salir" onClick={onSalir}>
          Salir
        </button>
      )}
      <span className="ap-titulo">{titulo}</span>
      {hay ? (
        <div className="jg-dado-cuerpo">
          <span className="jg-dado-eti">Te juegas</span>
          <div className="jg-ruleta" aria-label={`Te juegas: ${casillas.map((c) => `${c.texto}, ${mundos(c.prob / total)} de ${GEMELOS} mundos`).join("; ")}`}>
            <div className="jg-ruleta-pista">
              {casillas.map((c) => (
                <span key={c.id} className="jg-ruleta-tramo" data-tono={c.tono} style={{ flexGrow: c.prob / total }}>
                  {c.prob / total >= 0.12 ? `${mundos(c.prob / total)}` : ""}
                </span>
              ))}
              <span className="jg-ruleta-ficha jg-ficha-busca" aria-hidden="true">⚄</span>
            </div>
            <div className="jg-ruleta-leyenda" aria-hidden="true">
              {casillas.map((c) => (
                <span key={c.id}>
                  <i data-tono={c.tono} />
                  {c.texto} <b>{mundos(c.prob / total)} de {GEMELOS}</b>
                </span>
              ))}
            </div>
          </div>
          <p className="ap-texto">{texto ?? "Tirando tu dado…"}</p>
        </div>
      ) : (
        <div className="jg-cargando">
          <i aria-hidden="true" />
          <span>{texto ?? "Viviendo el año…"}</span>
        </div>
      )}
    </div>
  );
}

/** Tu sueldo año a año hasta ahora: una línea con el último punto marcado. */
export function LineaSueldo({ puntos }: { puntos: { edad: number; sueldo: number }[] }) {
  if (puntos.length < 2) return null;
  const { W, X0, X1 } = LIENZO;
  const H = 96;
  const Y0 = 14;
  const Y1 = H - 22;
  const e0 = puntos[0].edad;
  const e1 = puntos[puntos.length - 1].edad;
  const x = (edad: number) => X0 + ((edad - e0) / Math.max(1, e1 - e0)) * (X1 - X0);
  const y = escalaSueldo(puntos.map((p) => p.sueldo), Y0, Y1);
  const d = puntos.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.edad).toFixed(1)},${y(p.sueldo).toFixed(1)}`).join(" ");
  const fin = puntos[puntos.length - 1];
  return (
    <svg className="jg-abanico" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Tu sueldo desde los ${e0} hasta los ${e1} años: de ${plata(puntos[0].sueldo)} a ${plata(fin.sueldo)}`}>
      <EjeX alto={H} y1={Y1} e0={e0} e1={e1} sueldo0={puntos[0].sueldo} hoy={false} />
      <path className="jg-abanico-tu-borde" pathLength={1} d={d} />
      <path className="jg-abanico-tu" pathLength={1} d={d} />
      {puntos.slice(0, -1).map((p) => (
        <circle key={p.edad} className="jg-abanico-hoy" cx={x(p.edad)} cy={y(p.sueldo)} r={3} />
      ))}
      <circle className="jg-abanico-tu-punto" style={{ animationDelay: "1.3s" }} cx={x(fin.edad)} cy={y(fin.sueldo)} r={5.5} />
      <text x={X1 + 8} y={y(fin.sueldo) + 4} className="jg-abanico-num">{rotuloSueldo(fin.sueldo)}</text>
    </svg>
  );
}

/**
 * El sueldo final de cada opción en una sola escala: del 10% al 90% de sus mundos, con la mediana marcada y los
 * extremos en pesos. `tu` marca tu sueldo una sola vez, con una raya que cruza todas las opciones.
 */
export function RangosOpciones({ opciones, tu }: { opciones: { id: string; nombre: string; rango: Rango; color?: string; nota?: string }[]; tu?: number }) {
  if (opciones.length === 0) return null;
  const tope = Math.max(tu ?? 0, ...opciones.map((o) => o.rango.p90), 1) * 1.05;
  const enPct = (n: number) => Math.min(100, Math.max(0, (n / tope) * 100));
  return (
    <div style={{ position: "relative", display: "grid", gap: 14 }}>
      {opciones.map((o) => (
        <div key={o.id} style={{ display: "grid", gap: 4 }}>
          <span className="jg-chico">
            <i className="jg-color" style={{ background: o.color }} aria-hidden="true" /> {o.nombre}
            {o.nota && ` · ${o.nota}`}
          </span>
          <RangoSueldo rango={o.rango} tope={tope} color={o.color} />
        </div>
      ))}
      {tu !== undefined && (
        <span
          aria-label={`Tu sueldo: ${plata(tu)}`}
          role="img"
          style={{ position: "absolute", top: 0, bottom: 18, left: `${enPct(tu)}%`, width: 4, marginLeft: -2, borderRadius: 2, background: "var(--sol)", boxShadow: "0 0 0 1.5px var(--tinta)", pointerEvents: "none" }}
        >
          <span className="jg-chico" style={{ position: "absolute", top: -16, transform: enPct(tu) > 85 ? "translateX(-100%)" : "translateX(-50%)", whiteSpace: "nowrap", fontWeight: 700 }}>
            tú
          </span>
        </span>
      )}
    </div>
  );
}
