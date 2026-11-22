import { useEffect, useRef, useState } from "react";
import {
  Button, DecisionArt, DecisionCard, DecisionList, Heading, Meta, Pill, Row, Screen, ScreenHeader, Stack, Text, cssVars, type DecisionTag,
} from "@/shared/ui";
import { CALIDAD, EMPRESA_EJEMPLO, TIPO_EMPLEADOR, arteOpcion, conSigno, plata, primeraFrase, sinSueldo, situacion } from "../textos";
import type { ContraBase, Eleccion, EmpresaOferta, EscenarioIA, PorQue, MundoDetalle, Narrado, OpcionComparada, OpcionPendiente, ParametrosComparar, Partida, Respaldo, SinNovedad, Suceso, Vista } from "../types";
import { useNarracion } from "../hooks/useNarracion";
import { Logo } from "./Logo";
import { BarraPartes, Info, ProgresoAnios, sinMovimiento, type Reparto } from "./graficos";
import { PesoDelCv } from "./PesoDelCv";
import { HojaEleccion } from "./HojaEleccion";
import { AvisoPerfil, CalidadTag, Cargando, ErrorCaja, FranjaSinNovedad, Hoy, Pensando, RangoSueldo, Salir } from "./piezas";
import { GEMELOS, textoError } from "../api";

type Internas = Record<string, string | number>;

/** El veredicto en una frase. Si casi todos empatan, eso va primero: no se anuncia "mejor" por una diferencia que casi nadie ve. */
function veredictoDe(r: Reparto, que: string): string {
  if (r.igual >= 0.995) return `Da lo mismo que ${que} para tu sueldo.`;
  if (r.igual >= 0.9) return `Casi no cambia tu sueldo frente a ${que}.`;
  if (r.igual >= 0.6) {
    const hacia = r.mas > r.menos * 1.5 ? " Cuando cambia, suele ser para mejor." : r.menos > r.mas * 1.5 ? " Cuando cambia, suele ser para peor." : "";
    return `Casi siempre da lo mismo que ${que}.${hacia}`;
  }
  if (r.mas - r.menos > 0.15) return `Suele salir mejor que ${que}.`;
  if (r.menos - r.mas > 0.15) return `Suele salir peor que ${que}.`;
  return `Es una apuesta: puede salir mejor o peor que ${que}.`;
}

/**
 * Cómo le va a esta opción frente a la base, con la misma suerte: en cuántos mundos ganas más, menos o igual,
 * y de cuánta plata se trata. Si casi todo es empate se dice directo; si la diferencia es chica, también.
 */
export function contraBase(c: ContraBase, base: OpcionComparada | undefined, conBase = true): { frase: string; magnitud: string | null } | null {
  if (!base || c.gana_mas_que_base === null || c.gana_menos_que_base === null) return null;
  const mas = c.gana_mas_que_base;
  const menos = c.gana_menos_que_base;
  const igual = c.igual_que_base ?? Math.max(0, 1 - mas - menos);
  if (igual >= 0.995) return { frase: "No cambia tu sueldo en ningún mundo.", magnitud: null };
  if (igual >= 0.9) return { frase: "Casi no cambia tu sueldo.", magnitud: null };

  const que = conBase ? `«${base.nombre}»` : "la otra opción";
  const frase = veredictoDe({ mas, igual, menos }, que);

  // Con muchos empates, la diferencia típica de todos los mundos es cero y tapa lo que pasa
  // cuando la opción sí cambia algo: ahí se muestra la diferencia solo entre esos mundos.
  const conEmpates = igual >= 0.2 && c.diferencia_si_cambia !== null && c.diferencia_si_cambia !== undefined;
  const d = conEmpates ? (c.diferencia_si_cambia as number) : c.diferencia_tipica;
  const cuando = conEmpates ? "Cuando cambia, la diferencia típica" : "La diferencia típica";
  let magnitud: string | null = null;
  if (d !== null) {
    const chica = Math.abs(d) < 0.03 * base.sueldo.p50;
    if (Math.abs(d) < 1000) magnitud = `${cuando} es casi cero.`;
    else if (chica) magnitud = `${cuando} es chica: ${conSigno(d)} al mes.`;
    else magnitud = `${cuando} es de ${conSigno(d)} al mes.`;
  }
  return { frase, magnitud };
}

/** Por qué te tocó esta decisión, en dos o tres palabras: va junto al nombre de la carta. */
function porQueCorto(p: PorQue | undefined): string | null {
  if (!p) return null;
  if (p.tipo === "obligada") return "por tu situación";
  if (p.tipo === "elegida") return "la elegiste tú";
  if (p.tipo === "llega") return "te llegó sin buscarla";
  if (p.tipo === "buscada") return "la buscaste tú";
  return "por algo que te pasó";
}

/** La explicación larga de por qué te tocó esta decisión, para el "?" junto a su nombre. */
function porQueLargo(p: PorQue | undefined, primerAnio: boolean): string | null {
  if (!p) return null;
  if (p.tipo === "llega") {
    const base = "Cada año el juego mira qué le pasa a gente en tu situación: tu edad, tu trabajo y tu rubro. Esto te llegó sin buscarlo.";
    // el primer año siempre llega algo: ahí la chance de esta carta en particular confunde más de lo que explica
    const chance = p.prob !== undefined && !primerAnio ? Math.round(p.prob * 100) : null;
    const cuanto = chance === null ? "" : chance < 1 ? " Entre todo lo que podía pasarte este año, esto tenía menos de 1 de 100 chances." : ` Entre todo lo que podía pasarte este año, esto tenía unas ${chance} de 100 chances.`;
    return base + cuanto + (primerAnio ? " El primer año siempre te llega algo para decidir." : "");
  }
  if (p.tipo === "obligada") return "Te pasó algo que no se puede dejar pasar, como quedar sin trabajo. Cuando eso ocurre, hay que decidir qué hacer.";
  if (p.tipo === "elegida") return "La elegiste tú al empezar, como la duda que querías probar.";
  if (p.tipo === "buscada") return "No te llegó nada este año y decidiste mirar esto por tu cuenta.";
  if (p.tipo === "consecuencia") return "Viene de algo que pasó o elegiste antes: por ejemplo, después de aceptar una oferta toca ver dónde entras.";
  return null;
}

/** Una sola ayuda para la tarjeta: qué es cada número y de dónde salen las probabilidades. */
function ComoLeer({ o, total, edadFinal, respaldo }: { o: OpcionComparada; base: OpcionComparada | undefined; total: number; edadFinal: number; respaldo?: Respaldo[] }) {
  const de = total || 100;
  const sorteo = respaldo && respaldo.length > 1 ? respaldo : null;
  return (
    <Info pregunta="¿De dónde salen estos números?">
      <span style={{ display: "block", marginBottom: 6 }}>
        En cada uno de los {de} mundos tu copia vivió todas las opciones con la misma suerte. <strong>Tu mejor opción en X de {de}:</strong> en esos mundos, «{o.nombre}» es con la que
        más ganas a los {edadFinal}.
      </span>
      <span style={{ display: "block", marginBottom: 6 }}>
        <strong>Si te va bien</strong> es lo que superan solo 1 de cada 10 mundos; <strong>si te va mal</strong>, lo que no alcanzan 1 de cada 10; <strong>lo típico</strong>,
        el mundo del medio.
      </span>
      {sorteo &&
        sorteo.map((r) => (
          <span key={r.resultado} style={{ display: "block", marginBottom: 6 }}>
            <strong>{r.texto}:</strong> {r.valor !== null ? `${Math.round(r.valor * 100)} de 100.` : "depende de tu situación."}{" "}
            {r.fuentes.length > 0 ? `Fuente: ${r.fuentes.join("; ")}.` : ""}
          </span>
        ))}
    </Info>
  );
}

type Narrar = (que: "pendiente" | "historia" | "mundo", signal: AbortSignal, mundo?: number) => Promise<{ items: Narrado[] }>;

function nivelIA(x: number): string {
  return x >= 0.35 ? "alta" : x >= 0.2 ? "media" : "baja";
}

export function ofertaTexto(e: EmpresaOferta): string {
  return e.cargo ? `Te ofrecen ser ${e.cargo} en ${e.nombre}.` : `Te ofrecen entrar a ${e.nombre}.`;
}

/**
 * La empresa real y el cargo que trae la opción. Sus cifras de sueldo, despidos, ascensos y cierre son sintéticas
 * (salen de su rubro y tamaño), así que no se muestran como si fueran de la empresa: solo la exposición a IA, que
 * es la de la ocupación del cargo.
 */
function EmpresaLinea({ empresa, texto }: { empresa: EmpresaOferta; texto?: string }) {
  const c = empresa.cifras;
  const cifras = [nivelIA(c.exposicion_ia) !== "baja" && `Exposición a IA del cargo ${nivelIA(c.exposicion_ia)}`]
    .filter((x): x is string => !!x);
  return (
    <span className="jg-empresa">
      <span className="jg-empresa-cabeza">
        <Logo carpeta="empresas" id={empresa.empresa_id} nombre={empresa.nombre} grupo={empresa.rubro} hay={empresa.logo} tamano={44} />
        <span className="jg-empresa-texto">
          <span className="jg-fuerte">{texto ?? ofertaTexto(empresa)}</span>
          <span className="jg-chico">
            {empresa.rubro} · {TIPO_EMPLEADOR[empresa.tipo] ?? empresa.tipo}
            {empresa.pais && empresa.pais !== "Chile" ? ` · ${empresa.pais}` : ""}
          </span>
        </span>
      </span>
      {cifras.length > 0 && (
        <span className="jg-empresa-cifras">
          {cifras.map((t) => (
            <span key={t}>{t}</span>
          ))}
        </span>
      )}
      <span className="jg-chico">{EMPRESA_EJEMPLO}</span>
    </span>
  );
}

const ESCENARIO_IA: Record<EscenarioIA["escenario"], string> = { lento: "lenta", medio: "a ritmo medio", rapido: "rápida" };

/** La opción para elegir: qué es, en cuántos mundos gana y el sueldo típico. La simulación va aparte, más abajo. */
/**
 * La frase de una línea bajo el nombre: qué es la opción, sin números. El único número de la tarjeta es
 * "Mejor opción en X de 100"; el dado del primer año va en "¿Por qué sale así?", para no poner dos cifras
 * parecidas que miden cosas distintas.
 */
function fraseCorta(o: OpcionComparada, detalle: string): string | undefined {
  const corta = detalle ? primeraFrase(detalle) : "";
  if (corta && corta.length <= 60 && !/\d/.test(corta)) return corta;
  const seguro = o.por_resultado.length === 1 ? o.por_resultado[0].texto : "";
  return seguro || undefined;
}

/**
 * La opción para elegir, corta: dibujo, nombre, una frase y en cuántos mundos es la mejor. Al elegirla se abre
 * solo con el sueldo (mediana y 10% · 90%) y, si hay, lo que se supuso dentro. El resto va más abajo.
 */
function OpcionConGemelos({
  o, decision, categoria, base, tope, selected, onSelect, supuesto, cambiable, edadFinal, color, ganadas, total, lider, empresa, textoEmpresa, respaldo,
}: {
  respaldo?: Respaldo[];
  /** Tiene algo que elegir dentro (rubro, región): tocarla de nuevo abre la hoja. */
  cambiable: boolean;
  o: OpcionComparada;
  decision: string;
  categoria: string;
  base: OpcionComparada | undefined;
  tope: number;
  selected: boolean;
  onSelect: () => void;
  /** Lo que se supuso dentro de la opción, ya con nombre ("Valparaíso"), no con código. */
  supuesto: string;
  edadFinal: number;
  color: string;
  /** En cuántos mundos esta opción es la que más gana (el mismo número que la nube). */
  ganadas: number | null;
  total: number;
  /** Es la que gana en más mundos. */
  lider: boolean;
  empresa?: EmpresaOferta | null;
  textoEmpresa?: string;
}) {
  // Un solo número en todas partes: en cuántos mundos esta es la mejor opción, el mismo que la grilla de
  // "Tus 100 mundos". Así la tarjeta y la grilla nunca dicen cosas distintas, y con los empates suman 100.
  const de = total || 100;
  const veredicto = !o.es_base ? contraBase(o, base)?.frase : null;
  const cesantia = Math.round(o.paso_por_cesantia * 100);
  const sube = Math.round((o.sube_de_cargo ?? 0) * 100);
  return (
    <DecisionCard
      art={<DecisionArt kind={arteOpcion(decision, o.opcion, categoria)} />}
      title={
        <span className="jg-opcion-titulo">
          <span className="jg-opcion-nombre">
            <i className="jg-color" style={{ background: color }} aria-hidden="true" />
            {o.nombre}
          </span>
          {ganadas !== null && (
            <span className="jg-marcador" data-lider={lider}>
              <span className="jg-marcador-num">
                {ganadas === 0 ? "En ningún mundo es la mejor" : <><b>{ganadas}</b> de {de} mundos es la mejor</>}
              </span>
              <MiniMundos ganadas={ganadas} total={de} color={color} />
            </span>
          )}
          {/* lo típico a la vista sin abrirla, para comparar las opciones de un vistazo; abierta, va en el detalle */}
          {!selected && (
            <span className="jg-tipico">
              Lo típico a los {edadFinal}: <b>{plata(o.sueldo.p50)}</b>
            </span>
          )}
        </span>
      }
      subtitle={fraseCorta(o, o.detalle)}
      tags={o.es_base ? [{ label: "Seguir como vas", tone: "minus" }] : []}
      selected={selected}
      onSelect={onSelect}
      detail={
        <>
          <span className="jg-escenarios" role="list" aria-label={`Sueldo a los ${edadFinal}`}>
            <span role="listitem">
              <span>Si te va bien</span>
              <b>{plata(o.sueldo.p90)}</b>
            </span>
            <span role="listitem" data-fuerte="true">
              <span>Lo típico a los {edadFinal}, en pesos de hoy</span>
              <b>{plata(o.sueldo.p50)}</b>
            </span>
            <span role="listitem">
              <span>Si te va mal</span>
              <b>{plata(o.sueldo.p10)}</b>
            </span>
            <span role="listitem">
              <span>Cierras algún año buscando trabajo</span>
              <b>{cesantia === 0 ? "en ningún mundo" : `en ${cesantia} de 100`}</b>
            </span>
            <span role="listitem">
              <span>Terminas en un cargo más alto</span>
              <b>{sube === 0 ? "en ningún mundo" : `en ${sube} de 100`}</b>
            </span>
          </span>
          {veredicto && <span className="jg-frase">{veredicto}</span>}
          {o.es_base && <span className="jg-frase">Es seguir como vas: las otras opciones se comparan con esta.</span>}
          {supuesto && (
            <span className="vd-opcion-sub">
              Supone: <strong>{supuesto}</strong>
              {cambiable && " · toca para cambiar"}
            </span>
          )}
          {empresa && <EmpresaLinea empresa={empresa} texto={textoEmpresa} />}
        </>
      }
    />
  );
}

/** Una tira de 100 puntitos: los primeros `ganadas` del color de la opción. La misma idea que la grilla, en chico. */
function MiniMundos({ ganadas, total, color }: { ganadas: number; total: number; color: string }) {
  return (
    <span className="jg-minimundos" aria-hidden="true">
      {Array.from({ length: total }, (_, i) => (
        <i key={i} style={i < ganadas ? { background: color } : undefined} />
      ))}
    </span>
  );
}

/** Un color por opción: la base siempre naranja; las demás en este orden. El gris es el empate. Sin azul: es el de la interfaz y la mediana. */
const COLORES = ["var(--jg-mas)", "var(--vida)", "var(--violeta)", "var(--turquesa)"];
export function coloresDe(comparadas: OpcionComparada[]): Record<string, string> {
  const salida: Record<string, string> = {};
  let i = 0;
  for (const o of comparadas) salida[o.opcion] = o.es_base ? "var(--jg-menos)" : COLORES[i++ % COLORES.length];
  return salida;
}

const tonoSuceso = (t: string) => (t === "bueno" ? "bueno" : t === "malo" ? "malo" : "neutro");


const claveSuceso = (x: Suceso) => `${x.nombre}|${x.texto}`;

/** Sin repetir el mismo texto dos veces seguidas en un año. */
function sinRepetir(sucesos: Suceso[]): Suceso[] {
  return sucesos.filter((x, i) => i === 0 || claveSuceso(x) !== claveSuceso(sucesos[i - 1]));
}

/**
 * Un mundo, todas las vidas en un solo gráfico: una línea por opción y los años de recesión sombreados.
 * Se ve de un vistazo que la misma suerte les pega a todas y que lo que separa las líneas es la decisión.
 */
function DueloMundo({
  vidas, hoy, recesiones, ganador,
}: {
  vidas: { opcion: string; nombre: string; color: string; puntos: { edad: number; sueldo: number }[] }[];
  hoy: { edad: number; sueldo: number };
  /** Edades al cerrar un año con recesión en este mundo. */
  recesiones: number[];
  ganador: string | null;
}) {
  if (vidas.length === 0 || vidas[0].puntos.length === 0) return null;
  const W = 320;
  const H = 150;
  const X0 = 8;
  const X1 = 236;
  const Y0 = 16;
  const Y1 = H - 22;
  const series = vidas.map((v) => ({ ...v, serie: [hoy, ...v.puntos] }));
  const e0 = hoy.edad;
  const e1 = Math.max(...series.map((s) => s.serie[s.serie.length - 1].edad));
  const tope = Math.max(...series.flatMap((s) => s.serie.map((p) => p.sueldo)), 1) * 1.08;
  const x = (edad: number) => X0 + ((edad - e0) / Math.max(1, e1 - e0)) * (X1 - X0);
  // si alguna vida queda sin sueldo, el eje parte en cero para que la caída se vea de verdad;
  // si no, se acerca al tramo de los sueldos para que se vea en qué se separan las vidas
  const todos = series.flatMap((s) => s.serie.map((p) => p.sueldo));
  const piso = Math.min(...todos) <= 0 ? 0 : Math.min(...todos) * 0.8;
  const y = (n: number) => Y1 - ((Math.max(piso, n) - piso) / Math.max(1, tope - piso)) * (Y1 - Y0);
  const linea = (ps: { edad: number; sueldo: number }[]) => ps.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.edad).toFixed(1)},${y(p.sueldo).toFixed(1)}`).join(" ");
  // la ganadora se dibuja al final, encima
  const orden = [...series].sort((a, b) => Number(a.opcion === ganador) - Number(b.opcion === ganador));
  const etiquetas = series
    .map((s) => {
      const fin = s.serie[s.serie.length - 1];
      return { opcion: s.opcion, color: s.color, texto: fin.sueldo > 0 ? plata(fin.sueldo) : "sin sueldo", y: y(fin.sueldo) };
    })
    .sort((a, b) => a.y - b.y);
  for (let i = 1; i < etiquetas.length; i++) if (etiquetas[i].y - etiquetas[i - 1].y < 14) etiquetas[i].y = etiquetas[i - 1].y + 14;
  const exceso = etiquetas[etiquetas.length - 1].y - (Y1 + 2);
  if (exceso > 0) for (const e of etiquetas) e.y -= exceso;

  return (
    <svg
      className="jg-abanico jg-duelo-mundo"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`Sueldo año a año en este mundo, de los ${e0} a los ${e1} años: ${series
        .map((s) => `${s.nombre} termina en ${plata(s.serie[s.serie.length - 1].sueldo)}`)
        .join("; ")}.${recesiones.length > 0 ? ` Hay recesión a los ${recesiones.join(", ")} años con cualquier opción.` : ""}`}
    >
      {recesiones.map((edad, i) => (
        <g key={edad}>
          <rect className="jg-duelo-recesion" x={x(edad - 1)} y={Y0 - 6} width={Math.max(2, x(edad) - x(edad - 1))} height={Y1 - Y0 + 6} />
          {(i === 0 || recesiones[i - 1] !== edad - 1) && (
            <text className="jg-abanico-sub" x={x(edad - 1) + 3} y={Y0 + 2}>
              recesión
            </text>
          )}
        </g>
      ))}
      <line className="jg-abanico-eje" x1={X0} x2={X1} y1={Y1} y2={Y1} />
      {orden.map((s) => (
        <path
          key={s.opcion}
          className="jg-abanico-medio"
          data-gana={s.opcion === ganador}
          style={{ stroke: s.color, strokeWidth: s.opcion === ganador ? 3.5 : 2.25, opacity: ganador && s.opcion !== ganador ? 0.75 : 1 }}
          pathLength={1}
          d={linea(s.serie)}
        />
      ))}
      <circle className="jg-abanico-hoy" cx={x(e0)} cy={y(hoy.sueldo)} r={4.5} />
      {etiquetas.map((e) => (
        <text key={e.opcion} x={X1 + 8} y={e.y + 4} className="jg-abanico-num" style={{ fill: e.color }}>
          {e.texto}
        </text>
      ))}
      <text x={X0} y={H - 6} className="jg-abanico-sub">hoy · {e0} años</text>
      <text x={X1} y={H - 6} textAnchor="end" className="jg-abanico-sub">{e1} años</text>
    </svg>
  );
}

/**
 * Todas las opciones en un solo gráfico: la línea de lo típico de cada una y, de la que estás mirando, la franja
 * donde terminan 8 de cada 10 mundos. Tocar una opción en la leyenda la destaca.
 */
function TodasAnioAnio({
  comparadas, colores, hoy, foco,
}: {
  comparadas: OpcionComparada[];
  colores: Record<string, string>;
  hoy: { edad: number; sueldo: number };
  foco: string;
}) {
  const [elegida, setElegida] = useState<string | null>(null);
  useEffect(() => setElegida(null), [foco]);
  const activa = elegida ?? foco;
  const series = comparadas.filter((o) => o.trayectoria.length > 0);
  if (series.length === 0) return null;
  const W = 320;
  const H = 180;
  const X0 = 8;
  const X1 = 236;
  const Y0 = 12;
  const Y1 = H - 22;
  const inicio = { edad: hoy.edad, p10: hoy.sueldo, p50: hoy.sueldo, p90: hoy.sueldo, sin_trabajo: 0 };
  const conInicio = (o: OpcionComparada) => [inicio, ...o.trayectoria];
  const act = series.find((o) => o.opcion === activa) ?? series[0];
  const e0 = hoy.edad;
  const e1 = Math.max(...series.map((o) => o.trayectoria[o.trayectoria.length - 1].edad));
  const valores = [...series.flatMap((o) => o.trayectoria.map((p) => p.p50)), ...act.trayectoria.flatMap((p) => [p.p10, p.p90]), hoy.sueldo];
  const tope = Math.max(...valores, 1) * 1.06;
  const piso = Math.max(0, Math.min(...valores) * 0.85);
  const x = (edad: number) => X0 + ((edad - e0) / Math.max(1, e1 - e0)) * (X1 - X0);
  const y = (n: number) => Y1 - ((Math.max(piso, n) - piso) / Math.max(1, tope - piso)) * (Y1 - Y0);
  const linea = (ps: { edad: number; v: number }[]) => ps.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.edad).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");
  const serieAct = conInicio(act);
  const franja = `${linea(serieAct.map((p) => ({ edad: p.edad, v: p.p90 })))} ${[...serieAct].reverse().map((p) => `L${x(p.edad).toFixed(1)},${y(p.p10).toFixed(1)}`).join(" ")} Z`;
  const orden = [...series].sort((a, b) => Number(a.opcion === act.opcion) - Number(b.opcion === act.opcion));
  const etiquetas = series
    .map((o) => {
      const fin = o.trayectoria[o.trayectoria.length - 1];
      return { opcion: o.opcion, color: colores[o.opcion], texto: plata(fin.p50), y: y(fin.p50) };
    })
    .sort((a, b) => a.y - b.y);
  for (let i = 1; i < etiquetas.length; i++) if (etiquetas[i].y - etiquetas[i - 1].y < 14) etiquetas[i].y = etiquetas[i - 1].y + 14;
  const exceso = etiquetas[etiquetas.length - 1].y - (Y1 + 2);
  if (exceso > 0) for (const e of etiquetas) e.y -= exceso;
  const finAct = act.trayectoria[act.trayectoria.length - 1];
  // si lo típico de todas queda cerca y la franja es ancha, eso es lo que hay que decir: pesa más la suerte que la decisión
  const finales = series.map((o) => o.trayectoria[o.trayectoria.length - 1].p50);
  const separacion = (Math.max(...finales) - Math.min(...finales)) / Math.max(1, finAct.p50);
  const ancho = (finAct.p90 - finAct.p10) / Math.max(1, finAct.p50);
  const pesaLaSuerte = series.length > 1 && separacion < 0.08 && ancho > 0.5;

  return (
    <Stack gap={8}>
      <svg
        className="jg-abanico"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Lo típico de cada opción, de los ${e0} a los ${e1} años: ${series.map((o) => `${o.nombre} ${plata(o.trayectoria[o.trayectoria.length - 1].p50)}`).join("; ")}.`}
      >
        <line className="jg-abanico-eje" x1={X0} x2={X1} y1={Y1} y2={Y1} />
        <path className="jg-abanico-franja" key={`franja:${act.opcion}`} style={{ fill: `color-mix(in srgb, ${colores[act.opcion]} 16%, transparent)` }} d={franja} />
        {orden.map((o) => (
          <path
            key={o.opcion}
            className="jg-abanico-medio"
            style={{ stroke: colores[o.opcion], strokeWidth: o.opcion === act.opcion ? 3.5 : 2, opacity: o.opcion === act.opcion ? 1 : 0.7 }}
            pathLength={1}
            d={linea(conInicio(o).map((p) => ({ edad: p.edad, v: p.p50 })))}
          />
        ))}
        <circle className="jg-abanico-hoy" cx={x(e0)} cy={y(hoy.sueldo)} r={4.5} />
        {etiquetas.map((e) => (
          <text key={e.opcion} x={X1 + 8} y={e.y + 4} className="jg-abanico-num" style={{ fill: e.color }}>
            {e.texto}
          </text>
        ))}
        <text x={X0} y={H - 6} className="jg-abanico-sub">hoy · {e0} años</text>
        <text x={X1} y={H - 6} textAnchor="end" className="jg-abanico-sub">{e1} años</text>
      </svg>
      <span className="jg-leyenda jg-leyenda-fila" role="group" aria-label="Destacar una opción">
        {series.map((o) => (
          <button type="button" key={o.opcion} className="jg-leyenda-boton" aria-pressed={o.opcion === act.opcion} onClick={() => setElegida(o.opcion)}>
            <i style={{ background: colores[o.opcion] }} />
            {o.nombre}
          </button>
        ))}
      </span>
      {pesaLaSuerte && (
        <span className="jg-destacado">Lo típico casi no cambia entre opciones, pero la franja es ancha: aquí tu suerte mueve más tu sueldo que lo que elijas.</span>
      )}
      <span className="jg-chico">
        La línea es lo típico de cada opción. La franja: con «{act.nombre}», 8 de cada 10 mundos terminan entre {plata(finAct.p10)} y {plata(finAct.p90)}.
      </span>
    </Stack>
  );
}

/**
 * Un mundo abierto. Arriba, el duelo: las vidas en un solo gráfico. Lo que le pasa en él con todas las opciones
 * (la recesión, una oferta que llega) va una sola vez; la historia de cada vida, año a año, queda plegada.
 */
function MundoAbierto({
  mundo, comparadas, colores, anioInicial, hoy, onCerrar, onOtro, onNarrar,
}: {
  mundo: MundoDetalle;
  onNarrar?: Narrar;
  comparadas: OpcionComparada[];
  colores: Record<string, string>;
  /** El año de la partida en que se toma la decisión: los años del mundo se cuentan desde ahí. */
  anioInicial: number;
  hoy: { edad: number; sueldo: number };
  onCerrar: () => void;
  /** Tira otro mundo al azar. */
  onOtro?: () => void;
}) {
  // mismo orden que las tarjetas
  const vidas = comparadas.map((c) => mundo.opciones.find((o) => o.opcion === c.opcion)).filter((o): o is MundoDetalle["opciones"][number] => !!o);
  const porSueldo = [...vidas].sort((a, b) => b.sueldo_final - a.sueldo_final);
  const ganadora = vidas.find((o) => o.opcion === mundo.ganador);
  const segunda = porSueldo.find((o) => o.opcion !== ganadora?.opcion);
  const empatadas = mundo.ganador === null ? porSueldo.filter((o) => o.sueldo_final >= porSueldo[0].sueldo_final * 0.995) : [];
  const largo = Math.max(...vidas.map((v) => v.anios.length));

  // lo que pasa igual en todas las vidas ese año es del mundo; la primera decisión siempre es distinta
  const comunes: Suceso[][] = [];
  for (let i = 0; i < largo; i++) {
    const listas = vidas.map((v) => (v.anios[i]?.sucesos ?? []).filter((_, j) => !(i === 0 && j === 0)));
    comunes.push(sinRepetir(listas[0] ?? []).filter((x) => listas.every((l) => l.some((y) => claveSuceso(y) === claveSuceso(x)))));
  }
  // lo que se muestra como "del mundo" son solo los eventos: que dos copias decidan lo mismo un año no es suerte compartida
  // la recesión no viene como suceso sino como marca del año: se suma aquí para que la lista diga lo mismo que el gráfico
  const RECESION: Suceso = { tipo: "evento", nombre: "Recesión", texto: "Recesión en el país.", tono: "malo" };
  const eventosDelMundo: Suceso[][] = comunes.map((l, i) => {
    const eventos = l.filter((x) => x.tipo === "evento");
    const recesion = vidas.some((v) => v.anios[i]?.recesion) && !eventos.some((x) => x.nombre === RECESION.nombre);
    return recesion ? [RECESION, ...eventos] : eventos;
  });
  const esComun = (i: number, x: Suceso) => eventosDelMundo[i].some((y) => claveSuceso(y) === claveSuceso(x));
  const anioDe = (i: number) => anioInicial + i;
  const delMundo = eventosDelMundo.map((l, i) => ({ i, l })).filter((x) => x.l.length > 0);
  const { textos: historias } = useNarracion(onNarrar ? (signal) => onNarrar("mundo", signal, mundo.mundo) : null, `mundo:${mundo.mundo}`);
  const lineas = vidas.map((v) => ({
    opcion: v.opcion,
    nombre: v.nombre,
    color: colores[v.opcion],
    // la edad al cerrar el año, como en el resto del juego: con la de partida el último punto quedaba en 39 y no en 40
    puntos: v.anios.filter((a) => a.fin).map((a) => ({ edad: a.fin!.edad, sueldo: a.fin!.estado === "buscando" ? 0 : a.fin!.sueldo })),
  }));
  const recesiones = (vidas[0]?.anios ?? []).filter((a) => a.recesion).map((a) => a.fin?.edad ?? a.edad + 1);

  return (
    <div className="jg-mundo" role="region" aria-label={`Mundo ${mundo.mundo + 1}`} key={mundo.mundo}>
      <div className="jg-mundo-cabeza">
        <span className="jg-fuerte">Mundo {mundo.mundo + 1}</span>
        <span className="jg-mundo-acciones">
          {onOtro && (
            <button type="button" className="jg-ayuda" onClick={onOtro}>
              Otro al azar
            </button>
          )}
          <button type="button" className="jg-ayuda" onClick={onCerrar}>
            Cerrar
          </button>
        </span>
      </div>
      <span className="jg-frase">
        {ganadora && segunda ? (
          <>
            Aquí gana <strong style={{ color: colores[ganadora.opcion] }}>«{ganadora.nombre}»</strong>: terminas con {plata(ganadora.sueldo_final)} al mes,{" "}
            {plata(ganadora.sueldo_final - segunda.sueldo_final)} más que con «{segunda.nombre}».
          </>
        ) : empatadas.length > 1 ? (
          `Aquí ${empatadas.map((o) => `«${o.nombre}»`).join(" y ")} terminan casi igual: a menos de 0,5% de diferencia.`
        ) : (
          "Aquí las opciones terminan casi igual: a menos de 0,5% de diferencia."
        )}
      </span>

      <DueloMundo vidas={lineas} hoy={hoy} recesiones={recesiones} ganador={mundo.ganador} />
      <span className="jg-leyenda jg-leyenda-fila">
        {lineas.map((l) => (
          <span key={l.opcion}>
            <i style={{ background: l.color }} />
            {l.nombre}
          </span>
        ))}
      </span>

      <div className="jg-mundo-comun">
        <span className="jg-chico">Lo que pasa en este mundo con cualquier opción</span>
        {/* la IA va aquí y no como chip suelto: así "sin sorpresas" no la contradice */}
        {mundo.ia && (
          <span className="jg-chico" title="Cada mundo sortea qué tan rápido llega la IA, dentro del rango medido por Brynjolfsson y otros (2025).">
            La IA llega {ESCENARIO_IA[mundo.ia.escenario]}: cada mundo sortea a qué ritmo cambia el trabajo.
          </span>
        )}
        {delMundo.length === 0 ? (
          <span className="jg-chico">{mundo.ia ? "Fuera de eso, ni recesión ni sorpresas." : "Ni recesión ni sorpresas."}</span>
        ) : (
          <ol className="jg-mundo-anios">
            {delMundo.map(({ i, l }) => (
              <li key={i}>
                <span className="jg-mundo-anio">Año {anioDe(i)}</span>
                <span className="jg-mundo-sucesos">
                  {l.map((x, j) => (
                    <span className="jg-mundo-suceso" data-tono={tonoSuceso(x.tono)} key={j}>
                      <i />
                      {x.texto}
                    </span>
                  ))}
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>

      <details className="jg-plegable">
      <summary>Leer la historia de cada vida, año a año</summary>
      <div className="jg-mundo-vidas">
        {vidas.map((o) => {
          const filas = o.anios.map((a, i) => ({
            a,
            i,
            propios: sinRepetir(a.sucesos.filter((x, j) => (i === 0 && j === 0) || !esComun(i, x))),
          }));
          return (
            <div className="jg-mundo-vida" key={o.opcion} style={{ borderTopColor: colores[o.opcion] }} data-gana={o.opcion === mundo.ganador}>
              <span className="jg-mundo-vida-cabeza">
                <span className="jg-fuerte">
                  {o.nombre}
                  {o.opcion === mundo.ganador && <span className="jg-mundo-gana">gana</span>}
                </span>
                <span className="jg-mundo-sueldo">{o.sueldo_final > 0 ? plata(o.sueldo_final) : "sin sueldo"}</span>
              </span>
              {o.empresa_final && (
                <span className="jg-chico">
                  Terminas {o.rol_final ? `como ${o.rol_final} ` : ""}en {o.empresa_final}
                </span>
              )}
              {historias[`mundo:${o.opcion}`] && <p className="jg-mundo-historia">{historias[`mundo:${o.opcion}`]}</p>}
              <ol className="jg-mundo-anios">
                {filas.map(({ a, i, propios }) => (
                  <li key={i}>
                    <span className="jg-mundo-anio">Año {anioDe(i)}</span>
                    <span className="jg-mundo-sucesos">
                      {propios.map((x, j) => (
                        <span className="jg-mundo-suceso" data-tono={tonoSuceso(x.tono)} key={j}>
                          <i />
                          {i === 0 && j === 0 && x.tipo === "decision" ? `Eliges «${x.opcion}»: ${x.texto}` : x.texto}
                        </span>
                      ))}
                      {a.fin && (
                        <span className="jg-mundo-fin">
                          {a.fin.estado === "buscando" ? "Sin trabajo" : `${a.fin.cargo} · ${plata(a.fin.sueldo)}`}
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          );
        })}
      </div>
      </details>
    </div>
  );
}

/**
 * La simulación, aparte de las opciones: cada punto es un mundo, del color de la opción con la que terminas
 * ganando más en él. Los puntos van agrupados por color, como en el tutorial. Al tocar uno se abre ese mundo.
 */
function Simulacion({
  comparadas, ganadores, gemelos, colores, anioInicial, hoy, onVerMundo, onNarrar,
}: {
  onNarrar?: Narrar;
  comparadas: OpcionComparada[];
  ganadores: (string | null)[];
  gemelos: number;
  colores: Record<string, string>;
  anioInicial: number;
  hoy: { edad: number; sueldo: number };
  onVerMundo: (n: number) => Promise<MundoDetalle>;
}) {
  const [abierto, setAbierto] = useState<number | null>(null);
  const edadAlFinal = comparadas[0]?.trayectoria[comparadas[0].trayectoria.length - 1]?.edad ?? hoy.edad;
  const [detalle, setDetalle] = useState<MundoDetalle | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** El mundo por el que pasa el cursor mientras se sortea uno al azar. */
  const [escaneo, setEscaneo] = useState<number | null>(null);
  const pedido = useRef(0);
  const sorteo = useRef<number[]>([]);
  const panel = useRef<HTMLDivElement>(null);
  const clave = ganadores.join(",");
  const pararSorteo = () => {
    sorteo.current.forEach((t) => clearTimeout(t));
    sorteo.current = [];
    setEscaneo(null);
  };
  useEffect(() => {
    pedido.current++;
    pararSorteo();
    setAbierto(null);
    setDetalle(null);
    setError(null);
  }, [clave]);
  useEffect(() => pararSorteo, []);
  useEffect(() => {
    if (abierto !== null) panel.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [abierto, detalle]);
  if (ganadores.length === 0) return null;

  const cuenta = new Map<string | null, number>();
  for (const g of ganadores) cuenta.set(g, (cuenta.get(g) ?? 0) + 1);
  const empates = cuenta.get(null) ?? 0;
  const nombreDe = (id: string | null) => comparadas.find((o) => o.opcion === id)?.nombre;
  // agrupados por opción, en el orden de las tarjetas; los empates al final
  const orden = new Map<string | null, number>(comparadas.map((o, i) => [o.opcion, i]));
  const puntos = ganadores.map((g, i) => ({ g, i })).sort((a, b) => (orden.get(a.g) ?? 99) - (orden.get(b.g) ?? 99) || a.i - b.i);

  const abrir = (n: number) => {
    pararSorteo();
    if (abierto === n) {
      setAbierto(null);
      return;
    }
    cargar(n);
  };

  /**
   * Un mundo al azar (de los que gana `solo`, si viene): el cursor salta entre los puntos, frena y cae en uno.
   * Es un sorteo de verdad entre esos mundos, no se elige uno favorable.
   */
  const alAzar = (solo?: string) => {
    const candidatos = ganadores.map((g, i) => ({ g, i })).filter((x) => (solo ? x.g === solo : x.g !== null && x.i !== abierto)).map((x) => x.i);
    if (candidatos.length === 0) return;
    pararSorteo();
    const azar = () => candidatos[Math.floor(Math.random() * candidatos.length)];
    const final = azar();
    if (sinMovimiento()) {
      cargar(final);
      return;
    }
    // cada salto un poco más lento, como una ruleta que frena
    const saltos = 11;
    let t = 0;
    for (let k = 0; k < saltos; k++) {
      t += 45 + k * k * 2.2;
      const n = k === saltos - 1 ? final : ganadores.length > 1 ? Math.floor(Math.random() * ganadores.length) : final;
      sorteo.current.push(window.setTimeout(() => setEscaneo(n), t));
    }
    sorteo.current.push(
      window.setTimeout(() => {
        sorteo.current = [];
        setEscaneo(null);
        cargar(final);
      }, t + 260),
    );
  };
  const sorteando = escaneo !== null;
  // atajos por opción solo si caben sin ensuciar: hasta tres opciones
  const atajos = comparadas.length <= 3 ? comparadas.filter((o) => (cuenta.get(o.opcion) ?? 0) > 0) : [];
  const cargar = (n: number) => {
    const mio = ++pedido.current;
    setAbierto(n);
    setDetalle(null);
    setError(null);
    setCargando(true);
    onVerMundo(n)
      .then((d) => mio === pedido.current && setDetalle(d))
      .catch((e: unknown) => mio === pedido.current && setError(textoError(e)))
      .finally(() => mio === pedido.current && setCargando(false));
  };

  if (empates === ganadores.length) {
    return (
      <section className="jg-seccion jg-simulacion">
        <Meta>La simulación</Meta>
        <Text size="sm">
          En los {gemelos} mundos tu sueldo termina igual con cualquier opción. Esta decisión no mueve tu sueldo: elige por lo que dice cada una.
        </Text>
      </section>
    );
  }

  return (
    <section className="jg-seccion jg-simulacion">
      <Stack gap={4}>
        <Meta>Tus {gemelos} mundos</Meta>
        <Heading level={3} as="h2">
          ¿Con qué opción terminas ganando más? Mundo por mundo
        </Heading>
        <Text size="sm">
          En cada uno de los {gemelos} mundos vives {comparadas.length === 2 ? "las dos" : comparadas.length === 3 ? "las tres" : `las ${comparadas.length}`} opciones, con los mismos años de recesión. Miramos tu
          sueldo a los {edadAlFinal} con cada una. Cada punto es un mundo.
        </Text>
      </Stack>
      <div className="jg-duelo">
        <div className="jg-mundos" role="group" aria-label="Los mundos, uno por punto" data-sorteando={sorteando}>
          {puntos.map(({ g, i }, k) => (
            <button
              type="button"
              key={i}
              className="jg-mundo-punto"
              aria-pressed={abierto === i}
              aria-label={`Mundo ${i + 1}: ${g ? `gana «${nombreDe(g)}»` : "empate"}`}
              title={`Mundo ${i + 1}`}
              style={{ ...cssVars({ "--jg-i": (k % 10) + Math.floor(k / 10) }), background: g ? colores[g] : undefined }}
              data-empate={g === null}
              data-escaneo={escaneo === i}
              onClick={() => abrir(i)}
            />
          ))}
        </div>
        <span className="jg-leyenda">
          {comparadas.map((o) => (
            <span key={o.opcion}>
              <i style={{ background: colores[o.opcion] }} />
              {/* el número primero, para que encolumne; el nombre entre comillas, para que «No» no se lea como negación */}
              <b>{cuenta.get(o.opcion) ?? 0}</b> mundos: gana «{o.nombre}»
            </span>
          ))}
          {empates > 0 && (
            <span>
              <i data-tipo="igual" />
              <b>{empates}</b> mundos: empate
            </span>
          )}
        </span>
      </div>
      {empates > 0 && <span className="jg-chico">Empate: {comparadas.length === 2 ? "las dos terminan" : "las dos mejores terminan"} casi igual, a menos de 0,5% de diferencia en el sueldo a los {edadAlFinal}.</span>}
      {abierto === null && (
        <div className="jg-atajos">
          <button type="button" className="jg-atajo" data-principal="true" onClick={() => alAzar()} disabled={sorteando}>
            {sorteando ? "Buscando un mundo…" : "Abrir un mundo al azar"}
          </button>
          {atajos.map((o) => (
            <button type="button" className="jg-atajo" key={o.opcion} onClick={() => alAzar(o.opcion)} disabled={sorteando}>
              <i style={{ background: colores[o.opcion] }} />
              Uno donde gana «{o.nombre}»
            </button>
          ))}
        </div>
      )}
      <div ref={panel} className="jg-mundo-ancla">
        {abierto !== null && cargando && <Cargando>Abriendo el mundo {abierto + 1}…</Cargando>}
        {abierto !== null && error && <ErrorCaja error={error} onReintentar={() => cargar(abierto)} />}
        {abierto !== null && detalle && (
          <MundoAbierto
            mundo={detalle}
            comparadas={comparadas}
            colores={colores}
            anioInicial={anioInicial}
            hoy={hoy}
            onCerrar={() => setAbierto(null)}
            onOtro={ganadores.length > 1 ? () => alAzar() : undefined}
            onNarrar={onNarrar}
          />
        )}
      </div>
    </section>
  );
}

/** El porqué: según lo que salió en el dado, cuántos gemelos son y cómo terminaron frente a su par de la opción base. */
function Porque({ o, base }: { o: OpcionComparada; base: OpcionComparada | undefined }) {
  const compara = !o.es_base && base !== undefined;
  return (
    <Stack gap={0}>
      {o.por_resultado.map((r) => {
        const hay = compara && r.gana_mas_que_base !== null && r.gana_menos_que_base !== null;
        const igual = r.igual_que_base ?? 0;
        return (
          <div className="jg-resultado" key={r.resultado}>
            <span className="jg-resultado-cabeza">
              <span>{r.texto || r.resultado}</span>
              <b>en {Math.round(r.prob * 100)} de 100 mundos</b>
            </span>
            <span className="jg-medidor" aria-hidden="true">
              <i style={{ width: `${Math.max(2, r.prob * 100)}%`, background: "var(--tinta)" }} />
            </span>
            {hay &&
              (igual >= 0.995 ? (
                <span className="jg-chico">Igual que con «{base!.nombre}».</span>
              ) : (
                <>
                  <span className="jg-chico">Frente a «{base!.nombre}», de cada 100:</span>
                  <BarraPartes
                    partes={[
                      { nombre: "ganan más", prob: r.gana_mas_que_base as number, tono: "mas" },
                      { nombre: "igual", prob: igual, tono: "igual" },
                      { nombre: "ganan menos", prob: r.gana_menos_que_base as number, tono: "menos" },
                    ]}
                  />
                  {r.diferencia_si_cambia != null && Math.abs(r.diferencia_si_cambia) >= 1000 && (
                    <span className="jg-chico">Cuando cambia, la mediana es {conSigno(r.diferencia_si_cambia)}/mes.</span>
                  )}
                </>
              ))}
          </div>
        );
      })}
    </Stack>
  );
}

/** La carta: la decisión pendiente con lo que vivieron los gemelos. Viene de "3 · Decisión del año" del kit. */
export function Carta({
  vista, partida, fuentes = null, cargando, onReintentar, recalculando, error, onElegir, onComparar, onVerMundo, onSalir, onNarrar, sinNovedad,
}: {
  /** El año anterior, si pasó sin novedades: va como franja arriba. */
  sinNovedad?: SinNovedad | null;
  /** Perfil y semilla de la partida: con ellos se mide cuánto pesa cada línea del CV en la duda. */
  partida?: Partida | null;
  /** De dónde salió cada dato del perfil: sin datos es un perfil de ejemplo. */
  fuentes?: Record<string, string> | null;
  /** Repite lo que falló (tirar el dado o volver a simular una opción). */
  onReintentar?: () => void;
  onNarrar?: Narrar;
  onVerMundo: (n: number) => Promise<MundoDetalle>;
  /** Volver a la portada sin perder la partida. */
  onSalir?: () => void;
  vista: Vista;
  riesgo: number;
  cargando: boolean;
  recalculando: boolean;
  error: string | null;
  onElegir: (e: Eleccion) => void;
  onComparar: (p: ParametrosComparar) => void;
}) {
  const pendiente = vista.pendiente!;
  const [sel, setSel] = useState<string | null>(null);
  const [internas, setInternas] = useState<Internas>({});
  const [filtro, setFiltro] = useState("");

  // otra carta: se parte sin nada marcado
  const llave = `${vista.historia.length}:${vista.anio_en_curso?.decisiones.length ?? 0}:${pendiente.decision}`;
  // la situación y las ofertas que escribe Claude se muestran cuando llegan, nunca antes la plantilla
  const { textos: narrados, listo } = useNarracion(onNarrar ? (signal) => onNarrar("pendiente", signal) : null, llave);

  useEffect(() => {
    setSel(null);
    setInternas({});
    setFiltro("");
    setHoja(null);
  }, [llave]);

  const e = vista.estado;
  const anio = Math.min(vista.anio + 1, vista.anios);
  const comparacion = pendiente.comparacion;
  const comparadas = comparacion?.opciones ?? [];
  const base = comparadas.find((o) => o.es_base);
  const tope = Math.max(...comparadas.map((o) => o.sueldo.p90), 1) * 1.05;
  const opcion: OpcionPendiente | undefined = pendiente.opciones.find((o) => o.opcion === sel);
  const faltan = opcion ? opcion.elecciones_internas.filter((i) => internas[i.variable] === undefined) : [];
  const foco = comparadas.find((o) => o.opcion === sel) ?? comparadas.find((o) => !o.es_base) ?? comparadas[0];

  /** La pregunta abierta en la hoja de abajo (a qué rubro, a qué región), o null si está cerrada. */
  const [hoja, setHoja] = useState<number | null>(null);
  const [defectos, setDefectos] = useState<Internas>({});
  const primeraFaltante = (o: OpcionPendiente, valores: Internas) =>
    Math.max(0, o.elecciones_internas.findIndex((i) => valores[i.variable] === undefined));

  const elegirOpcion = (id: string) => {
    const o = pendiente.opciones.find((x) => x.opcion === id);
    const pide = (o?.elecciones_internas.length ?? 0) > 0;
    // tocar de nuevo la elegida reabre lo que falta (o lo ya elegido, para cambiarlo)
    if (id === sel) {
      if (o && pide) setHoja(primeraFaltante(o, internas));
      return;
    }
    setSel(id);
    setInternas({});
    setHoja(pide ? 0 : null);
    // se anota antes de que tu elección vuelva a simular la opción y cambie sus parámetros
    if (o) setDefectos(Object.fromEntries(o.elecciones_internas.map((i) => [i.variable, defectoDe(o, i.variable)]).filter(([, v]) => v !== undefined)));
  };

  /** Lo que la simulación usa si no eliges: lo que trae la comparación, o lo más común. */
  const defectoDe = (o: OpcionPendiente, variable: string) => {
    const simulado = comparadas.find((c) => c.opcion === o.opcion)?.parametros?.[variable];
    if (simulado !== undefined) return simulado;
    const alts = o.elecciones_internas.find((i) => i.variable === variable)?.alternativas ?? [];
    return [...alts].sort((a, b) => (b.prob ?? 0) - (a.prob ?? 0))[0]?.valor;
  };
  const porDefecto = (variable: string) => defectos[variable] ?? (opcion ? defectoDe(opcion, variable) : undefined);

  const elegirInterna = (variable: string, valor: string | number) => {
    if (!opcion) return;
    const nuevas = { ...internas, [variable]: valor };
    setInternas(nuevas);
    const siguiente = opcion.elecciones_internas.findIndex((i) => nuevas[i.variable] === undefined);
    setHoja(siguiente >= 0 ? siguiente : null);
    // con todo elegido, los gemelos de esta opción se vuelven a simular por ese camino
    if (comparacion && siguiente < 0) onComparar({ [opcion.opcion]: nuevas });
  };

  const usarPorDefecto = () => {
    if (!opcion) return;
    const nuevas = { ...internas };
    for (const i of opcion.elecciones_internas) if (nuevas[i.variable] === undefined) nuevas[i.variable] = porDefecto(i.variable) as string | number;
    setInternas(nuevas);
    setHoja(null);
    // si ya había algo elegido distinto de lo simulado, se vuelve a simular con la mezcla
    if (comparacion && Object.keys(internas).length > 0) onComparar({ [opcion.opcion]: nuevas });
  };

  const confirmar = () => {
    if (!opcion || faltan.length > 0) return;
    onElegir({
      decision: pendiente.decision,
      opcion: opcion.opcion,
      ...(opcion.elecciones_internas.length > 0 ? { parametros: internas } : {}),
    });
  };

  const muchas = pendiente.opciones.length > 8;
  const visibles = muchas && filtro.trim() ? pendiente.opciones.filter((o) => o.nombre.toLowerCase().includes(filtro.trim().toLowerCase())) : pendiente.opciones;

  /** "Valparaíso" en vez del código 3: lo que se supuso dentro de la opción, con su nombre. */
  const supuestoDe = (o: OpcionComparada) => {
    const internas = pendiente.opciones.find((x) => x.opcion === o.opcion)?.elecciones_internas ?? [];
    return Object.entries(o.parametros ?? {})
      .map(([variable, valor]) => internas.find((i) => i.variable === variable)?.alternativas.find((a) => a.valor === valor)?.nombre ?? (typeof valor === "string" ? valor : null))
      .filter(Boolean)
      .join(" · ");
  };
  /** Hasta qué edad vivieron los gemelos de esta carta (no siempre es el fin de la partida). */
  const edadGemelos = comparadas[0]?.trayectoria[comparadas[0].trayectoria.length - 1]?.edad ?? vista.edad_final;
  const colores = coloresDe(comparadas);
  const ganadores = comparacion?.ganador_por_mundo ?? null;
  const ganadas = (id: string) => (ganadores ? ganadores.filter((g) => g === id).length : 0);
  const hoy = { edad: e.edad, sueldo: sinSueldo(e) ? 0 : e.sueldo };
  const sinEfecto = comparadas.length > 1 && comparadas.every((o) => o.es_base || (o.igual_que_base ?? 0) >= 0.9);
  /** "Lo que vale cada línea de tu CV" solo tiene sentido si hubo CV o tu Claude: sin ellos, no hay líneas tuyas. */
  const conFuentes = fuentes !== null && Object.values(fuentes).some((f) => f === "cv" || f === "claude");

  return (
    <Screen gap={16}>
      <ScreenHeader left={<Pill style={{ whiteSpace: "nowrap" }}>Año {anio} · {e.edad} años</Pill>} right={onSalir && <Salir onSalir={onSalir} />} />
      {cargando && <Pensando titulo={`Mundo ${GEMELOS + 1} · año ${anio}`} onSalir={onSalir} />}
      {/* mientras Claude escribe la carta no hay sorteo: una espera simple, no la apuesta */}
      {!cargando && !listo && (
        <div className="jg-preparando">
          <Cargando>Preparando tu carta…</Cargando>
        </div>
      )}
      <ProgresoAnios actual={anio} total={vista.anios} />
      <FranjaSinNovedad s={sinNovedad} />
      <Hoy e={e} />
      <AvisoPerfil fuentes={fuentes} />

      <Stack gap={8} style={{ marginTop: 4 }}>
        <Meta>
          {pendiente.nombre}
          {porQueCorto(pendiente.por_que) && ` · ${porQueCorto(pendiente.por_que)}`}
        </Meta>
        {porQueLargo(pendiente.por_que, vista.anio === 0) && (
          <Info pregunta="¿Por qué te tocó esto?">{porQueLargo(pendiente.por_que, vista.anio === 0)}</Info>
        )}
        {pendiente.narrativa && listo && (
          <div className="jg-mensaje" key={llave}>
            <span className="jg-mensaje-escribiendo" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            <p className="jg-mensaje-texto">{narrados.situacion ?? pendiente.narrativa.situacion}</p>
          </div>
        )}
        <Heading level={2} as="h1">
          {pendiente.pregunta}
        </Heading>
        {sinEfecto && <Text size="sm" className="jg-destacado">Tu sueldo termina casi igual con cualquier opción.</Text>}
      </Stack>

      {comparacion ? (
        <div className="vd-pila jg-columna jg-opciones-cortas" role="group" aria-label="Opciones" data-cargando={recalculando} style={{ gap: 14 }}>
          {comparadas.map((o) => (
            <OpcionConGemelos
              key={o.opcion}
              o={o}
              decision={pendiente.decision}
              categoria={pendiente.categoria}
              empresa={pendiente.opciones.find((x) => x.opcion === o.opcion)?.empresa}
              respaldo={pendiente.opciones.find((x) => x.opcion === o.opcion)?.respaldo}
              textoEmpresa={narrados[`oferta:${o.opcion}`]}
              lider={ganadores !== null && ganadas(o.opcion) > 0 && ganadas(o.opcion) === Math.max(...comparadas.map((c) => ganadas(c.opcion)))}
              base={base}
              tope={tope}
              selected={sel === o.opcion}
              onSelect={() => elegirOpcion(o.opcion)}
              supuesto={supuestoDe(o)}
              cambiable={(pendiente.opciones.find((x) => x.opcion === o.opcion)?.elecciones_internas.length ?? 0) > 0}
              edadFinal={edadGemelos}
              color={colores[o.opcion]}
              ganadas={ganadores ? ganadas(o.opcion) : null}
              total={ganadores?.length ?? 0}
            />
          ))}
        </div>
      ) : (
        <Stack gap={12} className="jg-columna">
          {muchas && (
            <input className="jg-campo" type="search" placeholder="Filtrar opciones" aria-label="Filtrar opciones" value={filtro} onChange={(ev) => setFiltro(ev.target.value)} />
          )}
          <DecisionList<string>
            label="Opciones"
            value={sel}
            onChange={elegirOpcion}
            options={visibles.slice(0, 40).map((o) => ({
              id: o.opcion,
              art: <DecisionArt kind={arteOpcion(pendiente.decision, o.opcion, pendiente.categoria)} />,
              title: o.nombre,
              subtitle: o.detalle ? primeraFrase(o.detalle) : undefined,
              detail:
                o.detalle && primeraFrase(o.detalle) !== o.detalle.trim() ? (
                  <span className="vd-opcion-sub">{o.detalle}</span>
                ) : o.empresa ? (
                  <EmpresaLinea empresa={o.empresa} texto={narrados[`oferta:${o.opcion}`]} />
                ) : undefined,
              tags: [{ label: CALIDAD[o.calidad]?.nombre ?? o.calidad, tone: o.calidad === "supuesto" ? ("minus" as const) : ("default" as const) }],
            }))}
          />
          {visibles.length > 40 && <Text size="sm">Hay {visibles.length - 40} más: usa el filtro.</Text>}
        </Stack>
      )}

      {comparacion && opcion && (() => {
        const c = comparadas.find((x) => x.opcion === opcion.opcion);
        return c ? <ComoLeer o={c} base={base} total={ganadores?.length ?? 0} edadFinal={edadGemelos} respaldo={opcion.respaldo} /> : null;
      })()}

      {comparacion && ganadores && ganadores.length > 0 && (
        <div className="jg-columna">
          <Simulacion
            comparadas={comparadas}
            ganadores={ganadores}
            gemelos={comparacion.gemelos}
            colores={colores}
            anioInicial={anio}
            hoy={hoy}
            onVerMundo={onVerMundo}
            onNarrar={onNarrar}
          />
        </div>
      )}

      {recalculando && <Cargando texto="Simulando los mundos por ese camino…" />}

      {opcion && hoja !== null && opcion.elecciones_internas.length > 0 && (
        <HojaEleccion
          titulo={opcion.nombre}
          preguntas={opcion.elecciones_internas}
          paso={hoja}
          valores={internas}
          porDefecto={porDefecto}
          onElegir={elegirInterna}
          onPorDefecto={usarPorDefecto}
          onCerrar={() => setHoja(null)}
        />
      )}

      {comparacion && foco && (
        <Stack gap={12} className="jg-columna">
          <section className="jg-seccion">
            <Heading level={3} as="h2">
              Todas tus opciones, año a año
            </Heading>
            <TodasAnioAnio comparadas={comparadas} colores={colores} hoy={hoy} foco={foco.opcion} />
          </section>

          {partida && pendiente.por_que?.tipo === "elegida" && conFuentes && (
            <PesoDelCv perfil={partida.perfil} duda={pendiente.decision} semilla={partida.semilla} />
          )}

          <details className="jg-plegable">
            <summary>¿Por qué sale así «{foco.nombre}»?</summary>
            <Stack gap={10}>
              <Text size="sm">Qué te pasa el primer año y cómo terminas.</Text>
              <Porque o={foco} base={base} />
            </Stack>
          </details>

          <details className="jg-plegable">
            <summary>De dónde salen los números</summary>
            <Stack gap={8}>
              <Row gap={6} style={{ alignItems: "center", flexWrap: "wrap" }}>
                <CalidadTag calidad={pendiente.calidad} />
                <span className="jg-chico">{CALIDAD[pendiente.calidad]?.explica}</span>
              </Row>
              {pendiente.creencia_vs_dato && (
                <Text size="sm">
                  <strong>Creencia y dato:</strong> {pendiente.creencia_vs_dato}
                </Text>
              )}
              {pendiente.evidencia.map((ev) => (
                <Text size="sm" key={ev.fuente + ev.cifra}>
                  {ev.cifra}
                </Text>
              ))}
            </Stack>
          </details>
        </Stack>
      )}

      <div className="jg-pie-fijo">
        {error && <ErrorCaja error={error} onReintentar={onReintentar} />}
        {/* elegir desde cualquier parte de la carta: no hay que volver arriba después de mirar los 100 mundos */}
        {comparacion && comparadas.length >= 2 && comparadas.length <= 3 && !cargando && (
          <div className="jg-pie-opciones" role="group" aria-label="Elegir una opción">
            {comparadas.map((o) => (
              <button key={o.opcion} type="button" className="vd-chip jg-pie-opcion" aria-pressed={sel === o.opcion} onClick={() => elegirOpcion(o.opcion)} disabled={recalculando}>
                <i className="jg-color" style={{ background: colores[o.opcion] }} aria-hidden="true" />
                {o.nombre}
              </button>
            ))}
          </div>
        )}
        {cargando && <Cargando>Sorteando y viviendo tu año…</Cargando>}
        {opcion && faltan.length > 0 && !cargando ? (
          <Button onClick={() => setHoja(primeraFaltante(opcion, internas))} disabled={recalculando}>
            Elegir el detalle
          </Button>
        ) : (
          <Button onClick={confirmar} disabled={!opcion || cargando || recalculando}>
            {cargando ? "Sorteando…" : opcion ? "Confirmar" : "Toca una opción"}
          </Button>
        )}
      </div>
    </Screen>
  );
}
