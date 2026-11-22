import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { cssVars, cx } from "@/shared/ui";
import { GEMELOS } from "../api";
import { minuscula, plata } from "../textos";
import type { Tono } from "../types";

const sinMovimiento = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Reparte `total` puntos según las proporciones, sin que el redondeo sume de más o de menos. */
export function repartir(partes: number[], total = 100): number[] {
  const suma = partes.reduce((a, b) => a + b, 0) || 1;
  const exactos = partes.map((p) => (p / suma) * total);
  const enteros = exactos.map(Math.floor);
  let faltan = total - enteros.reduce((a, b) => a + b, 0);
  const orden = exactos.map((e, i) => ({ i, resto: e - Math.floor(e) })).sort((a, b) => b.resto - a.resto);
  for (const { i } of orden) {
    if (faltan-- <= 0) break;
    enteros[i]++;
  }
  return enteros;
}

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
 * Los gemelos de una opción, de a 100: cada punto son 5 gemelos. Verde terminó ganando más que su par
 * de la opción base, gris igual, naranjo menos. Sin `reparto` (la opción base) son todos neutros.
 */
export function NubeGemelos({ reparto, etiqueta }: { reparto: Reparto | null; etiqueta: string }) {
  const [mas, igual] = reparto ? repartir([reparto.mas, reparto.igual, reparto.menos]) : [0, 100];
  return (
    <span className="jg-nube" role="img" aria-label={etiqueta}>
      {Array.from({ length: 100 }, (_, i) => (
        <i
          key={i}
          data-tipo={!reparto ? "base" : i < mas ? "mas" : i < mas + igual ? "igual" : "menos"}
          style={cssVars({ "--jg-i": (i % 10) + Math.floor(i / 10) })}
        />
      ))}
    </span>
  );
}

export function LeyendaNube({ reparto, nombre, contra }: { reparto: Reparto; nombre: string; contra: string }) {
  const [mas, igual, menos] = repartir([reparto.mas, reparto.igual, reparto.menos]);
  return (
    <span className="jg-leyenda">
      <span><i data-tipo="mas" />en <b>{mas}</b> ganas más con «{nombre}»</span>
      <span><i data-tipo="igual" />en <b>{igual}</b> terminas igual</span>
      <span><i data-tipo="menos" />en <b>{menos}</b> ganas más con «{contra}»</span>
    </span>
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
  const W = 320;
  const X0 = 8;
  const X1 = 250;
  const Y0 = 14;
  const Y1 = alto - 24;
  const inicio = { edad: hoy.edad, p10: hoy.sueldo, p50: hoy.sueldo, p90: hoy.sueldo };
  const serie = [inicio, ...puntos];
  const ref = referencia ? [inicio, ...referencia] : null;
  const e0 = hoy.edad;
  const e1 = serie[serie.length - 1].edad;
  const tope = Math.max(...serie.map((p) => p.p90), ...(ref ?? []).map((p) => p.p50), ...(tu ?? []).map((t) => t.sueldo), 1) * 1.06;
  const x = (edad: number) => X0 + ((edad - e0) / Math.max(1, e1 - e0)) * (X1 - X0);
  // el eje no parte de cero: se acerca al tramo donde están los sueldos para que se vean las diferencias
  const piso = Math.min(...serie.map((p) => p.p10), ...(tu ?? []).map((t) => t.sueldo)) * 0.8;
  const y = (n: number) => Y1 - ((Math.max(piso, n) - piso) / Math.max(1, tope - piso)) * (Y1 - Y0);
  const linea = (ps: { edad: number; v: number }[]) => ps.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.edad).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");
  const franja = `${linea(serie.map((p) => ({ edad: p.edad, v: p.p90 })))} ${[...serie].reverse().map((p) => `L${x(p.edad).toFixed(1)},${y(p.p10).toFixed(1)}`).join(" ")} Z`;
  const fin = serie[serie.length - 1];
  // etiquetas del final: se separan si quedan encima
  const etiquetas = [
    { k: "p90", v: fin.p90, t: `${plata(fin.p90)}`, s: "90%" },
    { k: "p50", v: fin.p50, t: `${plata(fin.p50)}`, s: "mediana" },
    { k: "p10", v: fin.p10, t: `${plata(fin.p10)}`, s: "10%" },
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
      <line className="jg-abanico-eje" x1={X0} x2={X1} y1={Y1} y2={Y1} />
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
      <text x={X0} y={alto - 6} className="jg-abanico-sub">hoy · {e0} años</text>
      <text x={X1} y={alto - 6} textAnchor="end" className="jg-abanico-sub">{e1} años</text>
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
    <span className="jg-progreso" role="img" aria-label={`Año ${actual} de ${total}`}>
      {Array.from({ length: total }, (_, i) => (
        <i key={i} data-estado={i + 1 < actual ? "vivido" : i + 1 === actual ? "ahora" : "falta"} />
      ))}
    </span>
  );
}

/** Un número que sube o baja hasta su valor en vez de aparecer de golpe. */
export function Contador({ desde, hasta, formato, espera = 0, ms = 900 }: { desde: number; hasta: number; formato: (n: number) => string; espera?: number; ms?: number }) {
  const [n, setN] = useState(sinMovimiento() ? hasta : desde);
  const cuadro = useRef(0);
  useEffect(() => {
    if (sinMovimiento() || desde === hasta) {
      setN(hasta);
      return;
    }
    setN(desde);
    let inicio = 0;
    const paso = (t: number) => {
      if (!inicio) inicio = t + espera;
      const k = Math.min(1, Math.max(0, (t - inicio) / ms));
      const suave = 1 - Math.pow(1 - k, 3);
      setN(desde + (hasta - desde) * suave);
      if (k < 1) cuadro.current = requestAnimationFrame(paso);
    };
    cuadro.current = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(cuadro.current);
  }, [desde, hasta, espera, ms]);
  return <span style={{ fontVariantNumeric: "tabular-nums" }}>{formato(n)}</span>;
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
    <div className="jg-ruleta" role="img" aria-label={`El dado: ${tramos.map((t) => `${t.texto} ${Math.round(t.ancho * 100)} de cada 100`).join("; ")}. A ti te tocó: ${tocado.texto}`}>
      <div className="jg-ruleta-pista">
        {tramos.map((t) => (
          <span key={t.id} className={cx("jg-ruleta-tramo", t.id === salio && "jg-ruleta-tramo--tuyo")} data-tono={t.tono} style={{ flexGrow: t.ancho }}>
            {t.ancho >= 0.12 ? `${Math.round(t.ancho * 100)}` : ""}
          </span>
        ))}
        <span className="jg-ruleta-ficha" style={cssVars({ "--jg-meta": `${meta}%` })} aria-hidden="true">⚄</span>
      </div>
      <div className="jg-ruleta-leyenda" aria-hidden="true">
        {tramos.map((t) => (
          <span key={t.id} className={cx(t.id === salio && "jg-ruleta-tuyo")}>
            <i data-tono={t.tono} />
            {t.texto} <b>{Math.round(t.ancho * 100)} de 100 mundos</b>
          </span>
        ))}
      </div>
    </div>
  );
}

/** Tu sueldo año a año hasta ahora: una línea con el último punto marcado. */
export function LineaSueldo({ puntos }: { puntos: { edad: number; sueldo: number }[] }) {
  if (puntos.length < 2) return null;
  const W = 320;
  const H = 96;
  const X0 = 8;
  const X1 = 250;
  const Y0 = 14;
  const Y1 = H - 22;
  const tope = Math.max(...puntos.map((p) => p.sueldo), 1) * 1.1;
  const e0 = puntos[0].edad;
  const e1 = puntos[puntos.length - 1].edad;
  const x = (edad: number) => X0 + ((edad - e0) / Math.max(1, e1 - e0)) * (X1 - X0);
  const y = (n: number) => Y1 - (Math.max(0, n) / tope) * (Y1 - Y0);
  const d = puntos.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.edad).toFixed(1)},${y(p.sueldo).toFixed(1)}`).join(" ");
  const fin = puntos[puntos.length - 1];
  return (
    <svg className="jg-abanico" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Tu sueldo desde los ${e0} hasta los ${e1} años: de ${plata(puntos[0].sueldo)} a ${plata(fin.sueldo)}`}>
      <line className="jg-abanico-eje" x1={X0} x2={X1} y1={Y1} y2={Y1} />
      <path className="jg-abanico-medio" pathLength={1} d={d} />
      {puntos.slice(0, -1).map((p) => (
        <circle key={p.edad} className="jg-abanico-hoy" cx={x(p.edad)} cy={y(p.sueldo)} r={3} />
      ))}
      <circle className="jg-abanico-tu-punto" style={{ animationDelay: "1.3s" }} cx={x(fin.edad)} cy={y(fin.sueldo)} r={5.5} />
      <text x={X1 + 10} y={y(fin.sueldo) + 4} className="jg-abanico-num">{fin.sueldo > 0 ? plata(fin.sueldo) : "sin sueldo"}</text>
      <text x={X0} y={H - 6} className="jg-abanico-sub">{e0} años · {plata(puntos[0].sueldo)}</text>
      <text x={X1} y={H - 6} textAnchor="end" className="jg-abanico-sub">{e1} años</text>
    </svg>
  );
}
