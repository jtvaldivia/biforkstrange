import { useEffect, useRef, useState } from "react";
import {
  Button, DecisionArt, DecisionCard, DecisionList, Heading, Pill, Row, Screen, ScreenHeader, Stack, Text,
} from "@/shared/ui";
import { CALIDAD, EMPRESA_EJEMPLO, TIPO_EMPLEADOR, arteOpcion, conSigno, deMundos, mayuscula, mundos, plata, primeraFrase, sinSueldo } from "../textos";
import type { ContraBase, Eleccion, EmpresaOferta, PorQue, MundoDetalle, Narrado, OpcionComparada, OpcionPendiente, ParametrosComparar, Partida, Respaldo, SinNovedad, Vista } from "../types";
import { useNarracion } from "../hooks/useNarracion";
import { Logo } from "./Logo";
import { BarraPartes, Info, ProgresoAnios, type Reparto } from "./graficos";
import { PesoDelCv } from "./PesoDelCv";
import { HojaEleccion } from "./HojaEleccion";
import { AvisoPerfil, CalidadTag, Cargando, ErrorCaja, FranjaSinNovedad, Hoy, Pensando, Salir } from "./piezas";
import { Espera } from "./Apuesta";
import { GEMELOS } from "../api";

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
    const cuanto = chance === null ? "" : chance < 1 ? " Entre todo lo que podía pasarte este año, esto tenía menos de 1% de probabilidad." : ` Entre todo lo que podía pasarte este año, esto tenía cerca de ${chance}% de probabilidad.`;
    return base + cuanto + (primerAnio ? " El primer año siempre te llega algo para decidir." : "");
  }
  if (p.tipo === "obligada") return "Te pasó algo que no se puede dejar pasar, como quedar sin trabajo. Cuando eso ocurre, hay que decidir qué hacer.";
  if (p.tipo === "elegida") return "La elegiste tú al empezar, como la duda que querías probar.";
  if (p.tipo === "buscada") return "No te llegó nada este año y decidiste mirar esto por tu cuenta.";
  if (p.tipo === "consecuencia") return "Viene de algo que pasó o elegiste antes: por ejemplo, después de aceptar una oferta toca ver dónde entras.";
  return null;
}

/**
 * La única ayuda sobre los números de la carta: qué es cada cifra, de dónde salen las probabilidades de la opción
 * que miras y qué tan firme es el dato de la decisión.
 */
function DeDondeSalen({ o, ganadas, total, edadFinal, respaldo, pendiente }: {
  o: OpcionComparada;
  ganadas: number | null;
  total: number;
  edadFinal: number;
  respaldo?: Respaldo[];
  pendiente: NonNullable<Vista["pendiente"]>;
}) {
  const de = total || GEMELOS;
  const sorteo = respaldo && respaldo.length > 1 ? respaldo : null;
  return (
    <details className="jg-plegable">
      <summary>De dónde salen los números</summary>
      <Stack gap={8}>
        <Text size="sm">
          En cada uno de los {de} mundos tu copia vivió todas las opciones con la misma suerte.
          {ganadas !== null && (
            <>
              {" "}
              «{o.nombre}» <strong>{ganadas === 0 ? "no es la mejor en ningún mundo" : `es la mejor en ${ganadas} de ${de} mundos`}</strong>: en esos mundos es con la que más
              ganas a los {edadFinal}.
            </>
          )}
        </Text>
        <Text size="sm">
          <strong>Si te va bien</strong> es lo que superan solo 1 de cada 10 mundos; <strong>si te va mal</strong>, lo que no alcanzan 1 de cada 10; <strong>lo típico</strong>, el
          mundo del medio.
        </Text>
        {sorteo &&
          sorteo.map((r) => (
            <Text size="sm" key={r.resultado}>
              <strong>{r.texto}:</strong> {r.valor !== null ? `${Math.round(r.valor * 100)}%.` : "depende de tu situación."}{" "}
              {r.fuentes.length > 0 ? `Fuente: ${r.fuentes.join("; ")}.` : ""}
            </Text>
          ))}
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
  );
}

/** El sueldo que trae una oferta, si la vista lo sabe y es la opción de aceptarla: "Te ofrecen $X al mes (+Y%)". */
function textoOferta(p: NonNullable<Vista["pendiente"]>, opcion: string): string | null {
  const o = p.oferta_sueldo;
  const acepta = (p.decision === "oferta_externa" && opcion === "cambiar") || (p.decision === "oferta_en_cesantia" && opcion === "aceptar");
  if (!o || !acepta || o.si_aceptas === null || o.si_aceptas === undefined) return null;
  if (!(o.hoy > 0)) return `Te ofrecen ${plata(o.si_aceptas)} al mes`;
  const cambio = Math.round((o.si_aceptas / o.hoy - 1) * 100);
  const cuanto = Math.abs(cambio) < 2 ? "casi lo mismo que ganas" : `${cambio > 0 ? "+" : "−"}${Math.abs(cambio)}%`;
  return `Te ofrecen ${plata(o.si_aceptas)} al mes (${cuanto}${o.cesante && Math.abs(cambio) >= 2 ? " frente a lo que ganabas" : ""})`;
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


/** La opción para elegir: qué es, en cuántos mundos gana y el sueldo típico. La simulación va aparte, más abajo. */
/**
 * La frase de una línea bajo el nombre: qué es la opción, sin números. El único número de la tarjeta es
 * "Mejor opción en X de 50"; el dado del primer año va en "¿Por qué sale así?", para no poner dos cifras
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
  o, decision, categoria, base, selected, onSelect, supuesto, cambiable, edadFinal, color, ganadas, empates = 0, total, lider, empresa, textoEmpresa, oferta,
}: {
  /** "Te ofrecen $X al mes (+Y%)": el sueldo que trae la oferta, en la opción de aceptarla. */
  oferta?: string | null;
  /** Tiene algo que elegir dentro (rubro, región): tocarla de nuevo abre la hoja. */
  cambiable: boolean;
  o: OpcionComparada;
  decision: string;
  categoria: string;
  base: OpcionComparada | undefined;
  selected: boolean;
  onSelect: () => void;
  /** Lo que se supuso dentro de la opción, ya con nombre ("Valparaíso"), no con código. */
  supuesto: string;
  edadFinal: number;
  color: string;
  /** En cuántos mundos esta opción es la que más gana (el mismo número que la nube). */
  ganadas: number | null;
  /** En cuántos mundos da lo mismo qué elijas. */
  empates?: number;
  total: number;
  /** Es la que gana en más mundos. */
  lider: boolean;
  empresa?: EmpresaOferta | null;
  textoEmpresa?: string;
}) {
  // Un solo número en todas partes: en cuántos mundos esta es la mejor opción, el mismo que la grilla de
  // "Tus 50 mundos". Así la tarjeta y la grilla nunca dicen cosas distintas, y con los empates suman 50.
  const de = total || GEMELOS;
  const veredicto = !o.es_base ? contraBase(o, base)?.frase : null;
  // el tiempo sin trabajo dice más que "cuántas copias pasaron por la cesantía": en 10 años a casi todos
  // les toca una vez, pero suele durar meses. Es el promedio de tus copias, contando a las que nunca la vivieron.
  const mesesSinTrabajo = Math.round(o.meses_sin_trabajo);
  // El rango de sueldo cuenta con $0 a quien termina sin trabajo; aquí se muestra solo entre quienes trabajan y los demás aparte.
  const conTrabajo = o.sueldo_con_trabajo ?? o.sueldo;
  const sinTrabajoFinal = mundos(o.sin_trabajo_al_final, de);
  const sube = mundos(o.sube_de_cargo ?? 0, de);
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
                {ganadas === 0 ? "En ningún mundo es la mejor" : <>Es la mejor en <b>{ganadas}</b> de {de} mundos</>}
                {empates >= de / 2 && ganadas < POCAS_GANADAS * de && `; en ${empates} da lo mismo`}
              </span>
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
      subtitle={oferta ?? fraseCorta(o, o.detalle)}
      tags={o.es_base ? [{ label: "Seguir como vas", tone: "minus" }] : []}
      selected={selected}
      onSelect={onSelect}
      detail={
        <>
          <span className="jg-escenarios" role="list" aria-label={`Sueldo a los ${edadFinal}`}>
            <span role="listitem">
              <span>Si te va bien</span>
              <b>{plata(conTrabajo.p90)}</b>
            </span>
            <span role="listitem" data-fuerte="true">
              <span>Lo típico a los {edadFinal}, en pesos de hoy</span>
              <b>{plata(conTrabajo.p50)}</b>
            </span>
            <span role="listitem">
              <span>Si te va mal</span>
              <b>{plata(conTrabajo.p10)}</b>
            </span>
            {sinTrabajoFinal > 0 && (
              <span role="listitem">
                <span>Terminan sin trabajo a los {edadFinal} (no cuentan arriba)</span>
                <b>{sinTrabajoFinal} de {de}</b>
              </span>
            )}
            <span role="listitem">
              <span>Tiempo sin trabajo hasta los {edadFinal}</span>
              <b>{mesesSinTrabajo === 0 ? "casi nada" : `unos ${mesesSinTrabajo} ${mesesSinTrabajo === 1 ? "mes" : "meses"}`}</b>
            </span>
            <span role="listitem">
              <span>Terminas en un cargo más alto</span>
              <b>{sube === 0 ? "en ningún mundo" : `en ${sube} de ${de}`}</b>
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

// Desde qué parte de los mundos empatados se avisa arriba de las opciones, y bajo qué parte ganada una opción dice que "da lo mismo"
const MUCHOS_EMPATES = 0.3;
const POCAS_GANADAS = 0.15;

/** Un color por opción: la base siempre naranja; las demás en este orden. El gris es el empate. Sin azul: es el de la interfaz y la mediana. */
const COLORES = ["var(--jg-mas)", "var(--vida)", "var(--violeta)", "var(--turquesa)"];
export function coloresDe(comparadas: OpcionComparada[]): Record<string, string> {
  const salida: Record<string, string> = {};
  let i = 0;
  for (const o of comparadas) salida[o.opcion] = o.es_base ? "var(--jg-menos)" : COLORES[i++ % COLORES.length];
  return salida;
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
              <b>en {deMundos(r.prob)} mundos</b>
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
  const opcion: OpcionPendiente | undefined = pendiente.opciones.find((o) => o.opcion === sel);
  const faltan = opcion ? opcion.elecciones_internas.filter((i) => internas[i.variable] === undefined) : [];
  const foco = comparadas.find((o) => o.opcion === sel) ?? comparadas.find((o) => !o.es_base) ?? comparadas[0];

  /** La pregunta abierta en la hoja de abajo (a qué rubro, a qué región), o null si está cerrada. */
  const [hoja, setHoja] = useState<number | null>(null);
  // Sin opción elegida, el botón del pie sube a las tarjetas: después de mirar los mundos no hay que buscarlas
  const opcionesRef = useRef<HTMLDivElement>(null);
  const irAOpciones = () => opcionesRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
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
  // mundos donde da lo mismo qué elijas (las dos mejores a menos de 0,5%): el "X de 50 es la mejor" solo no los muestra
  const empates = ganadores ? ganadores.filter((g) => g === null).length : 0;
  const hoy = { edad: e.edad, sueldo: sinSueldo(e) ? 0 : e.sueldo };
  const sinEfecto = comparadas.length > 1 && comparadas.every((o) => o.es_base || (o.igual_que_base ?? 0) >= 0.9);
  /** "Lo que vale cada línea de tu CV" solo tiene sentido si hubo CV o tu Claude: sin ellos, no hay líneas tuyas. */
  const conFuentes = fuentes !== null && Object.values(fuentes).some((f) => f === "cv" || f === "claude");

  return (
    <Screen gap={16}>
      <ScreenHeader
        left={<Pill style={{ whiteSpace: "nowrap" }}>Año {anio} · {e.edad} años</Pill>}
        right={
          <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            {vista.anio > 0 && <AvisoPerfil fuentes={fuentes} corto />}
            {onSalir && <Salir onSalir={onSalir} />}
          </span>
        }
      />
      {/* el único dado de la decisión: gira mientras responde el motor; "qué te pasó" cierra el sorteo */}
      {cargando && <Pensando titulo={`Mundo ${GEMELOS + 1} · año ${anio}`} onSalir={onSalir} />}
      {/* mientras Claude escribe la carta no hay sorteo: una espera simple, no la apuesta */}
      {!cargando && !listo && (
        <div className="jg-preparando">
          <Espera pantalla frases={["Preparando tu carta…", "Claude está escribiendo tu situación…"]} onSalir={onSalir} />
        </div>
      )}
      <ProgresoAnios actual={anio} total={vista.anios} />
      <FranjaSinNovedad s={sinNovedad} />
      <Hoy e={e} />
      {vista.anio === 0 && <AvisoPerfil fuentes={fuentes} />}

      <Stack gap={8} style={{ marginTop: 4 }}>
        {/* el nombre de la decisión ya lo dice la pregunta: aquí solo de dónde viene, en una línea */}
        {/* si la duda la elegiste tú, no hace falta explicar por qué te tocó */}
        {pendiente.por_que?.tipo === "elegida" ? null : porQueLargo(pendiente.por_que, vista.anio === 0) ? (
          <Info pregunta={`${mayuscula(porQueCorto(pendiente.por_que) ?? "por qué te tocó")} · ¿por qué?`}>{porQueLargo(pendiente.por_que, vista.anio === 0)}</Info>
        ) : (
          porQueCorto(pendiente.por_que) && <span className="jg-chico">{mayuscula(porQueCorto(pendiente.por_que)!)}</span>
        )}
        {/* la carta se ve apenas llega del motor; la situación que escribe Claude entra cuando llega */}
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
        <Heading level={2} as="h1" className="jg-carta-pregunta">
          {pendiente.pregunta}
        </Heading>
        {sinEfecto && <Text size="sm" className="jg-destacado">Tu sueldo termina casi igual con cualquier opción.</Text>}
        {!sinEfecto && empates >= MUCHOS_EMPATES * ganadores!.length && (
          <Text size="sm" className="jg-destacado">
            En {empates} de tus {ganadores!.length} mundos da lo mismo qué elijas: tu sueldo termina igual.
          </Text>
        )}
      </Stack>

      {comparacion ? (
        <div ref={opcionesRef} className="vd-pila jg-columna jg-opciones-cortas" role="group" aria-label="Opciones" data-cargando={recalculando} style={{ gap: 14, scrollMarginTop: 16 }}>
          {comparadas.map((o) => (
            <OpcionConGemelos
              key={o.opcion}
              o={o}
              decision={pendiente.decision}
              categoria={pendiente.categoria}
              empresa={pendiente.opciones.find((x) => x.opcion === o.opcion)?.empresa}
              textoEmpresa={narrados[`oferta:${o.opcion}`]}
              oferta={textoOferta(pendiente, o.opcion)}
              lider={ganadores !== null && ganadas(o.opcion) > 0 && ganadas(o.opcion) === Math.max(...comparadas.map((c) => ganadas(c.opcion)))}
              base={base}
              selected={sel === o.opcion}
              onSelect={() => elegirOpcion(o.opcion)}
              supuesto={supuestoDe(o)}
              cambiable={(pendiente.opciones.find((x) => x.opcion === o.opcion)?.elecciones_internas.length ?? 0) > 0}
              edadFinal={edadGemelos}
              color={colores[o.opcion]}
              ganadas={ganadores ? ganadas(o.opcion) : null}
              empates={empates}
              total={ganadores?.length ?? 0}
            />
          ))}
        </div>
      ) : (
        <div ref={opcionesRef} className="vd-pila jg-columna" style={{ gap: 12, scrollMarginTop: 16 }}>
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
        </div>
      )}



      {recalculando && <Espera texto="Simulando los mundos por ese camino…" />}

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

          <DeDondeSalen
            o={foco}
            ganadas={ganadores ? ganadas(foco.opcion) : null}
            total={ganadores?.length ?? 0}
            edadFinal={edadGemelos}
            respaldo={pendiente.opciones.find((x) => x.opcion === foco.opcion)?.respaldo}
            pendiente={pendiente}
          />
        </Stack>
      )}

      <div className="jg-pie-fijo">
        {error && <ErrorCaja error={error} onReintentar={onReintentar} />}
        {cargando && <Cargando>Sorteando y viviendo tu año…</Cargando>}
        {opcion && faltan.length > 0 && !cargando ? (
          <Button onClick={() => setHoja(primeraFaltante(opcion, internas))} disabled={recalculando}>
            Elegir el detalle
          </Button>
        ) : opcion || cargando ? (
          <Button onClick={confirmar} disabled={cargando || recalculando}>
            {cargando ? "Sorteando…" : `Confirmar «${opcion?.nombre}»`}
          </Button>
        ) : (
          <Button variant="white" onClick={irAOpciones}>
            Toca una opción ↑
          </Button>
        )}
      </div>
    </Screen>
  );
}
