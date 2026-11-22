import { useEffect, useRef, useState } from "react";
import {
  Button, DecisionArt, DecisionCard, DecisionList, Heading, Meta, Pill, Row, Screen, ScreenHeader, Stack, Text, cssVars, type DecisionTag,
} from "@/shared/ui";
import { CALIDAD, TIPO_EMPLEADOR, arteOpcion, cargoYSueldo, conSigno, plata, primeraFrase, sinSueldo } from "../textos";
import type { ContraBase, Eleccion, EmpresaOferta, EscenarioIA, PorQue, MundoDetalle, Narrado, OpcionComparada, OpcionPendiente, ParametrosComparar, Partida, Suceso, Vista } from "../types";
import { useNarracion } from "../hooks/useNarracion";
import { Logo } from "./Logo";
import { Abanico, BarraPartes, Info, ProgresoAnios, type Reparto } from "./graficos";
import { PesoDelCv } from "./PesoDelCv";
import { HojaEleccion } from "./HojaEleccion";
import { CalidadTag, Cargando, ErrorCaja, Pensando, RangoSueldo } from "./piezas";
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
  if (p.tipo === "sorteo") return "salió al azar";
  if (p.tipo === "obligada") return "por tu situación";
  if (p.tipo === "elegida") return "la elegiste tú";
  return "por algo que te pasó";
}

type Narrar = (que: "pendiente" | "historia" | "mundo", signal: AbortSignal, mundo?: number) => Promise<{ items: Narrado[] }>;

/** "+8%" o "−20%" respecto del promedio de su tipo y rubro; "promedio" si casi no se mueve. */
function relativo(x: number): string {
  const d = Math.round((x - 1) * 100);
  return Math.abs(d) < 3 ? "promedio" : `${d > 0 ? "+" : "−"}${Math.abs(d)}%`;
}

function nivelIA(x: number): string {
  return x >= 0.35 ? "alta" : x >= 0.2 ? "media" : "baja";
}

export function ofertaTexto(e: EmpresaOferta): string {
  return e.cargo ? `Te ofrecen ser ${e.cargo} en ${e.nombre}.` : `Te ofrecen entrar a ${e.nombre}.`;
}

/** La empresa real y el cargo que trae la opción, con sus cifras. Las cifras son sintéticas: salen de su rubro y tamaño. */
function EmpresaLinea({ empresa, texto }: { empresa: EmpresaOferta; texto?: string }) {
  const c = empresa.cifras;
  return (
    <span className="jg-empresa">
      <span className="jg-empresa-cabeza">
        <Logo carpeta="empresas" id={empresa.empresa_id} nombre={empresa.nombre} grupo={empresa.rubro} hay={empresa.logo} />
        <span className="jg-empresa-texto">
          <span className="jg-fuerte">{texto ?? ofertaTexto(empresa)}</span>
          <span className="jg-chico">
            {empresa.rubro} · {TIPO_EMPLEADOR[empresa.tipo] ?? empresa.tipo}
            {empresa.pais && empresa.pais !== "Chile" ? ` · ${empresa.pais}` : ""}
          </span>
        </span>
      </span>
      <span className="jg-empresa-cifras">
        <span>Sueldo {relativo(c.sueldo)}</span>
        <span>Despidos {relativo(c.despido)}</span>
        <span>Ascensos {relativo(c.ascenso)}</span>
        {empresa.tipo === "startup" && <span>Cierre {relativo(c.cierre)}</span>}
        <span>Exposición a IA {nivelIA(c.exposicion_ia)}</span>
        <span>{c.horas} h</span>
      </span>
      <span className="jg-chico jg-empresa-nota">Cifras simuladas a partir de su rubro y tamaño: no son datos de la empresa.</span>
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
  o, decision, categoria, base, tope, selected, onSelect, supuesto, cambiable, edadFinal, color, ganadas, total, lider, empresa, textoEmpresa,
}: {
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
  // la resta de las medianas que se ven al abrir la tarjeta, redondeadas como se muestran ($3,40 M − $3,12 M)
  const aDiez = (n: number) => Math.round(n / 10_000) * 10_000;
  const d = base ? aDiez(o.sueldo.p50) - aDiez(base.sueldo.p50) : null;
  const tags: DecisionTag[] = [];
  if (ganadas !== null) tags.push({ label: `Mejor opción en ${ganadas} de ${total}`, tone: lider ? "accent" : "default" });
  if (o.es_base) tags.push({ label: "Punto de partida", tone: "minus" });
  else if (d !== null && Math.abs(d) >= 1000) tags.push({ label: `${conSigno(d)}/mes` });
  return (
    <DecisionCard
      art={<DecisionArt kind={arteOpcion(decision, o.opcion, categoria)} />}
      title={
        <>
          <i className="jg-color" style={{ background: color }} aria-hidden="true" />
          {o.nombre}
        </>
      }
      subtitle={fraseCorta(o, o.detalle)}
      tags={tags}
      selected={selected}
      onSelect={onSelect}
      detail={
        <>
          <span className="vd-meta">
            Sueldo a los {edadFinal} · mediana {plata(o.sueldo.p50)}
          </span>
          <RangoSueldo rango={o.sueldo} tope={tope} color={color} />
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

/** Un color por opción: la base siempre naranja; las demás en este orden. El gris es el empate. */
const COLORES = ["var(--jg-mas)", "var(--acento)", "var(--vida)", "var(--violeta)", "var(--turquesa)"];
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
 * Un mundo abierto. Lo que le pasa en él con todas las opciones (la recesión, una oferta que llega) va una sola vez
 * arriba; en cada vida, solo lo que cambia por la decisión, con el sueldo al cerrar cada año.
 */
function MundoAbierto({
  mundo, comparadas, colores, anioInicial, onCerrar, onNarrar,
}: {
  mundo: MundoDetalle;
  onNarrar?: Narrar;
  comparadas: OpcionComparada[];
  colores: Record<string, string>;
  /** El año de la partida en que se toma la decisión: los años del mundo se cuentan desde ahí. */
  anioInicial: number;
  onCerrar: () => void;
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
  const esComun = (i: number, x: Suceso) => comunes[i].some((y) => claveSuceso(y) === claveSuceso(x));
  const anioDe = (i: number) => anioInicial + i;
  const delMundo = comunes.map((l, i) => ({ i, l })).filter((x) => x.l.length > 0);
  const { textos: historias } = useNarracion(onNarrar ? (signal) => onNarrar("mundo", signal, mundo.mundo) : null, `mundo:${mundo.mundo}`);

  return (
    <div className="jg-mundo" role="region" aria-label={`Mundo ${mundo.mundo + 1}`}>
      <div className="jg-mundo-cabeza">
        <span className="jg-fuerte">Mundo {mundo.mundo + 1}</span>
        {mundo.ia && (
          <span className="jg-chip-ia" title="Cada mundo sortea qué tan rápido llega la IA, dentro del rango medido por Brynjolfsson y otros (2025).">
            La IA llega {ESCENARIO_IA[mundo.ia.escenario]}
          </span>
        )}
        <button type="button" className="jg-ayuda" onClick={onCerrar}>
          Cerrar
        </button>
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

      <div className="jg-mundo-comun">
        <span className="jg-chico">Lo que pasa en este mundo con cualquier opción</span>
        {delMundo.length === 0 ? (
          <span className="jg-chico">Nada fuera de lo normal: sin recesión ni sorpresas.</span>
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
    </div>
  );
}

/**
 * La simulación, aparte de las opciones: cada punto es un mundo, del color de la opción con la que terminas
 * ganando más en él. Los puntos van agrupados por color, como en el tutorial. Al tocar uno se abre ese mundo.
 */
function Simulacion({
  comparadas, ganadores, gemelos, colores, anioInicial, onVerMundo, onNarrar,
}: {
  onNarrar?: Narrar;
  comparadas: OpcionComparada[];
  ganadores: (string | null)[];
  gemelos: number;
  colores: Record<string, string>;
  anioInicial: number;
  onVerMundo: (n: number) => Promise<MundoDetalle>;
}) {
  const [abierto, setAbierto] = useState<number | null>(null);
  const [detalle, setDetalle] = useState<MundoDetalle | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pedido = useRef(0);
  const panel = useRef<HTMLDivElement>(null);
  const clave = ganadores.join(",");
  useEffect(() => {
    pedido.current++;
    setAbierto(null);
    setDetalle(null);
    setError(null);
  }, [clave]);
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
    if (abierto === n) {
      setAbierto(null);
      return;
    }
    const mio = ++pedido.current;
    setAbierto(n);
    setDetalle(null);
    setError(null);
    setCargando(true);
    onVerMundo(n)
      .then((d) => mio === pedido.current && setDetalle(d))
      .catch((e: unknown) => mio === pedido.current && setError(e instanceof Error ? e.message : String(e)))
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
        <Meta>La simulación</Meta>
        <Heading level={3} as="h2">
          ¿Con qué opción ganas más en cada mundo?
        </Heading>
        <Text size="sm">Cada punto es uno de los {gemelos} mundos, del color de la opción con la que ahí terminas ganando más. Toca uno para ver qué pasa en él.</Text>
      </Stack>
      <div className="jg-duelo">
        <div className="jg-mundos" role="group" aria-label="Los mundos, uno por punto">
          {puntos.map(({ g, i }, k) => (
            <button
              type="button"
              key={i}
              className="jg-mundo-punto"
              aria-pressed={abierto === i}
              aria-label={`Mundo ${i + 1}: ${g ? `gana «${nombreDe(g)}»` : "da lo mismo"}`}
              title={`Mundo ${i + 1}`}
              style={{ ...cssVars({ "--jg-i": (k % 10) + Math.floor(k / 10) }), background: g ? colores[g] : undefined }}
              data-empate={g === null}
              onClick={() => abrir(i)}
            />
          ))}
        </div>
        <span className="jg-leyenda">
          {comparadas.map((o) => (
            <span key={o.opcion}>
              <i style={{ background: colores[o.opcion] }} />
              en <b>{cuenta.get(o.opcion) ?? 0}</b> gana «{o.nombre}»
            </span>
          ))}
          {empates > 0 && (
            <span>
              <i data-tipo="igual" />
              en <b>{empates}</b> da lo mismo
            </span>
          )}
        </span>
      </div>
      {empates > 0 && <span className="jg-chico">«Da lo mismo» es cuando las mejores opciones de ese mundo terminan a menos de 0,5% de diferencia.</span>}
      <div ref={panel} className="jg-mundo-ancla">
        {abierto !== null && cargando && <Cargando>Abriendo el mundo {abierto + 1}…</Cargando>}
        {abierto !== null && error && <ErrorCaja error={error} />}
        {abierto !== null && detalle && (
          <MundoAbierto mundo={detalle} comparadas={comparadas} colores={colores} anioInicial={anioInicial} onCerrar={() => setAbierto(null)} onNarrar={onNarrar} />
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
  vista, partida, cargando, recalculando, error, onElegir, onComparar, onAyuda, onVerMundo, onNarrar,
}: {
  /** Perfil y semilla de la partida: con ellos se mide cuánto pesa cada línea del CV en la duda. */
  partida?: Partida | null;
  onNarrar?: Narrar;
  onAyuda: () => void;
  onVerMundo: (n: number) => Promise<MundoDetalle>;
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
  // la situación y las ofertas que escribe Sonnet se muestran cuando llegan, nunca antes la plantilla
  const { textos: narrados, listo } = useNarracion(onNarrar ? (signal) => onNarrar("pendiente", signal) : null, llave);
  // la empresa de la que habla el mensaje de arriba: la que te ofrece trabajo o, si no hay oferta, donde trabajas
  const oferta = pendiente.opciones.find((x) => x.empresa)?.empresa;
  const quienEscribe = oferta
    ? { id: oferta.empresa_id, nombre: oferta.nombre, rubro: oferta.rubro, logo: oferta.logo }
    : vista.estado.empresa && (vista.estado.empresa_id ?? -1) >= 0
      ? { id: vista.estado.empresa_id!, nombre: vista.estado.empresa, rubro: vista.estado.rubro, logo: true }
      : null;

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

  return (
    <Screen gap={16}>
      <ScreenHeader left={<Pill style={{ whiteSpace: "nowrap" }}>Año {anio} · {e.edad} años</Pill>} right={<Meta>{anio} de {vista.anios}</Meta>} />
      {cargando && <Pensando titulo={`Mundo ${GEMELOS + 1} · año ${anio}`} />}
      {/* mientras Sonnet escribe la carta no hay sorteo: una espera simple, no la apuesta */}
      {!cargando && !listo && (
        <div className="jg-preparando">
          <Cargando>Preparando tu carta…</Cargando>
        </div>
      )}
      <ProgresoAnios actual={anio} total={vista.anios} />
      <Text size="sm">
        <strong>Hoy:</strong> {cargoYSueldo(e, true)}
        {sinSueldo(e) ? ` · antes ${plata(e.sueldo_ref)}` : "/mes"}
      </Text>

      <Stack gap={8} style={{ marginTop: 4 }}>
        <Meta>
          {pendiente.nombre}
          {porQueCorto(pendiente.por_que) && ` · ${porQueCorto(pendiente.por_que)}`}
        </Meta>
        {pendiente.narrativa && listo && (
          <div className="jg-mensaje" key={llave} data-logo={quienEscribe ? "si" : undefined}>
            {quienEscribe && (
              <Logo carpeta="empresas" id={quienEscribe.id} nombre={quienEscribe.nombre} grupo={quienEscribe.rubro} hay={quienEscribe.logo} tamano={36} />
            )}
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
        <Row gap={8} style={{ alignItems: "center", flexWrap: "wrap" }}>
          <Meta>{comparacion ? `${comparacion.gemelos} mundos simulados` : `${pendiente.opciones.length} opciones · sin simular`}</Meta>
          <button type="button" className="jg-ayuda" onClick={onAyuda}>
            ¿Cómo funciona?
          </button>
        </Row>
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
          {partida && pendiente.por_que?.tipo === "elegida" && (
            <PesoDelCv perfil={partida.perfil} duda={pendiente.decision} semilla={partida.semilla} />
          )}
          <section className="jg-seccion" key={`abanico:${foco.opcion}`}>
            <Heading level={3} as="h2">
              {foco.nombre}, año a año
            </Heading>
            <Abanico
              color={colores[foco.opcion]}
              colorReferencia={base ? colores[base.opcion] : undefined}
              puntos={foco.trayectoria}
              hoy={hoy}
              referencia={foco.es_base ? undefined : base?.trayectoria}
              nombreReferencia={foco.es_base ? undefined : base?.nombre}
            />
            <Info pregunta="¿Qué son mediana, 10% y 90%?">
              <strong>Mediana:</strong> el mundo del medio, si los ordenas por sueldo. <strong>10% y 90%:</strong> 1 de cada 10 mundos queda bajo el 10%, y
              1 de cada 10 sobre el 90%.
            </Info>
          </section>

          <details className="jg-plegable">
            <summary>¿Por qué sale así?</summary>
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
              {pendiente.por_que?.tipo === "sorteo" && (
                <span className="jg-chico">
                  Salió al azar: {Math.max(1, Math.round(pendiente.por_que.prob * 100))} de 100, entre {pendiente.por_que.posibles} cartas posibles.
                </span>
              )}
            </Stack>
          </details>
        </Stack>
      )}

      <div className="jg-pie-fijo">
        {error && <ErrorCaja error={error} />}
        {cargando && <Cargando>Tirando tu dado y viviendo el año…</Cargando>}
        {opcion && faltan.length > 0 && !cargando ? (
          <Button onClick={() => setHoja(primeraFaltante(opcion, internas))} disabled={recalculando}>
            Elegir el detalle
          </Button>
        ) : (
          <Button onClick={confirmar} disabled={!opcion || cargando || recalculando}>
            {cargando ? "Tirando el dado…" : opcion ? "Confirmar" : "Toca una opción"}
          </Button>
        )}
      </div>
    </Screen>
  );
}
