import { useEffect, useRef, useState } from "react";
import { Button, CheckIcon, Chip, DecisionArt, DecisionList, Heading, Meta, Panel, Pill, Row, Screen, ScreenHeader, Stack, Text, cssVars } from "@/shared/ui";
import { CALIDAD, TIPO_EMPLEADOR, arte, cargoYSueldo, conSigno, minuscula, plata, sinSueldo } from "../textos";
import type { ContraBase, Eleccion, EmpresaOferta, EscenarioIA, PorQue, MundoDetalle, Narrado, OpcionComparada, OpcionPendiente, ParametrosComparar, Partida, Suceso, Vista } from "../types";
import { useNarracion } from "../hooks/useNarracion";
import { Logo } from "./Logo";
import { Abanico, BarraPartes, Info, ProgresoAnios, type Reparto } from "./graficos";
import { PesoDelCv } from "./PesoDelCv";
import { CalidadTag, Cargando, ErrorCaja, LeyendaCalidad, Pensando, RangoSueldo } from "./piezas";
import { GEMELOS } from "../api";
import { ApuestaAntesDeMirar } from "./Apuesta";

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

/** A quien tolera poco riesgo se le destaca el piso; a quien lo busca, el techo. */
function destacado(o: OpcionComparada, base: OpcionComparada | undefined, riesgo: number): string | null {
  if (riesgo > 3 && riesgo < 7) return null;
  const piso = riesgo <= 3;
  const nombre = piso ? "Tu peor caso" : "Tu mejor caso";
  const valor = piso ? o.sueldo.p10 : o.sueldo.p90;
  if (o.es_base || !base) return `${nombre}: ${plata(valor)}`;
  const antes = piso ? base.sueldo.p10 : base.sueldo.p90;
  if (Math.abs(valor - antes) < 0.03 * antes) return null; // una diferencia que no se nota no se destaca
  return `${nombre} ${valor < antes ? "baja" : "sube"} de ${plata(antes)} a ${plata(valor)}`;
}

/** Por qué te tocó esta decisión, en una frase. */
function porQueTexto(p: PorQue | undefined): string | null {
  if (!p) return null;
  if (p.tipo === "sorteo")
    return `Esta carta salió al azar: este año podían tocarte ${p.posibles} decisiones según tu situación, y esta tenía ${Math.max(1, Math.round(p.prob * 100))} de 100 de salir.`;
  if (p.tipo === "obligada") return "Esta decisión no es al azar: te toca por tu situación de este año.";
  if (p.tipo === "elegida") return "Es la duda que elegiste para empezar.";
  return "Esta decisión viene de algo que te acaba de pasar este año.";
}

/** Lo que puede pasar apenas eliges la opción, con su probabilidad: es el dado que vas a tirar. */
function Probabilidades({ o }: { o: OpcionComparada }) {
  const resultados = o.por_resultado;
  if (resultados.length === 0) return null;
  if (resultados.length === 1 && resultados[0].prob >= 0.995) {
    return (
      <span className="jg-probs">
        <span className="jg-chico">Al elegirla</span>
        <span className="jg-prob" data-tono={resultados[0].tono}>
          <i />
          <span>{resultados[0].texto || resultados[0].resultado}</span>
          <b>seguro</b>
        </span>
      </span>
    );
  }
  return (
    <span className="jg-probs">
      <span className="jg-chico">Al elegirla, el primer año</span>
      {resultados.map((r) => (
        <span className="jg-prob" data-tono={r.tono} key={r.resultado}>
          <i />
          <span>{r.texto || r.resultado}</span>
          <b>{Math.round(r.prob * 100)} de 100</b>
        </span>
      ))}
    </span>
  );
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
function OpcionConGemelos({
  o, base, tope, riesgo, selected, onSelect, supuesto, edadFinal, color, ganadas, total, empresa, textoEmpresa,
}: {
  o: OpcionComparada;
  empresa?: EmpresaOferta | null;
  textoEmpresa?: string;
  base: OpcionComparada | undefined;
  tope: number;
  riesgo: number;
  selected: boolean;
  onSelect: () => void;
  /** Lo que se supuso dentro de la opción, ya con nombre ("Valparaíso"), no con código. */
  supuesto: string;
  edadFinal: number;
  color: string;
  /** En cuántos mundos esta opción es la que más gana (el mismo número que la nube). */
  ganadas: number | null;
  total: number;
}) {
  const nota = destacado(o, base, riesgo);
  return (
    <button type="button" className="vd-opcion jg-opcion" aria-pressed={selected} onClick={onSelect}>
      <span className="jg-opcion-cabeza">
        <span className="vd-opcion-titulo">
          <i className="jg-color" style={{ background: color }} aria-hidden="true" />
          {o.nombre}
        </span>
        {o.detalle && <span className="vd-opcion-sub">{o.detalle}</span>}
        {supuesto && <span className="vd-opcion-sub">En la simulación vas a: {supuesto}</span>}
        {empresa && <EmpresaLinea empresa={empresa} texto={textoEmpresa} />}
        {ganadas !== null && (
          <span className="jg-veredicto">
            Gana en {ganadas} de {total} mundos
          </span>
        )}
      </span>

      <span className="jg-opcion-bloque">
        <Probabilidades o={o} />
      </span>

      <span className="jg-opcion-bloque">
        <span className="jg-chico">Sueldo típico a los {edadFinal} años</span>
        <span className="jg-opcion-num">{plata(o.sueldo.p50)}</span>
        <span className="jg-rango-solo">
          <RangoSueldo rango={o.sueldo} tope={tope} color={color} />
        </span>
        <span className="jg-chico">
          Con mala suerte <strong className="jg-plata">{plata(o.sueldo.p10)}</strong> · con buena suerte{" "}
          <strong className="jg-plata">{plata(o.sueldo.p90)}</strong>
        </span>
        {nota && <span className="jg-destacado">{nota}</span>}
      </span>

      <span className="vd-opcion-check">
        <CheckIcon />
      </span>
    </button>
  );
}

/** Un color por opción: la base siempre naranja; las demás en este orden. El gris es el empate. */
const COLORES = ["var(--jg-mas)", "var(--acento)", "var(--vida)", "#7C5CD6", "#0E9AA7"];
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
  const historias = useNarracion(onNarrar ? (signal) => onNarrar("mundo", signal, mundo.mundo) : null, `mundo:${mundo.mundo}`);

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
                <span className="jg-chico">En esos mundos te va igual que con «{base!.nombre}».</span>
              ) : (
                <>
                  <span className="jg-chico">En esos mundos, frente a «{base!.nombre}» (de cada 100):</span>
                  <BarraPartes
                    partes={[
                      { nombre: "ganan más", prob: r.gana_mas_que_base as number, tono: "mas" },
                      { nombre: "igual", prob: igual, tono: "igual" },
                      { nombre: "ganan menos", prob: r.gana_menos_que_base as number, tono: "menos" },
                    ]}
                  />
                  {r.diferencia_si_cambia != null && Math.abs(r.diferencia_si_cambia) >= 1000 && (
                    <span className="jg-chico">Cuando cambia, la diferencia típica es de {conSigno(r.diferencia_si_cambia)} al mes.</span>
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
  vista, partida, riesgo, cargando, recalculando, error, onElegir, onComparar, onAyuda, onVerMundo, onNarrar,
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
  const narrados = useNarracion(onNarrar ? (signal) => onNarrar("pendiente", signal) : null, llave);

  useEffect(() => {
    setSel(null);
    setInternas({});
    setFiltro("");
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

  const panelInternas = useRef<HTMLDivElement>(null);
  const elegirOpcion = (id: string) => {
    if (id === sel) return;
    setSel(id);
    setInternas({});
    // si la opción pide algo más (a qué rubro, a qué región), se lleva la vista hasta esa pregunta
    if ((pendiente.opciones.find((o) => o.opcion === id)?.elecciones_internas.length ?? 0) > 0) {
      setTimeout(() => panelInternas.current?.scrollIntoView({ behavior: "smooth", block: "center" }), 80);
    }
  };

  const elegirInterna = (variable: string, valor: string | number) => {
    if (!opcion) return;
    const nuevas = { ...internas, [variable]: valor };
    setInternas(nuevas);
    // con todo elegido, los gemelos de esta opción se vuelven a simular por ese camino
    if (comparacion && opcion.elecciones_internas.every((i) => nuevas[i.variable] !== undefined)) onComparar({ [opcion.opcion]: nuevas });
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
  const hoy = { edad: e.edad, sueldo: sinSueldo(e) ? 0 : e.sueldo };
  const sinEfecto = comparadas.length > 1 && comparadas.every((o) => o.es_base || (o.igual_que_base ?? 0) >= 0.9);
  // los mundos se muestran después de apostar (o saltarse la apuesta) en esta carta
  const [vistoEn, setVistoEn] = useState<string | null>(null);
  const revelado = !ganadores || vistoEn === llave;

  return (
    <Screen gap={16} className={comparadas.length > 4 ? "jg-ancha jg-muy-ancha" : "jg-ancha"}>
      <ScreenHeader left={<Pill style={{ whiteSpace: "nowrap" }}>Año {anio} · {e.edad} años</Pill>} right={<Meta>{anio} de {vista.anios}</Meta>} />
      {cargando && <Pensando titulo={`Mundo ${GEMELOS + 1} · año ${anio}`} />}
      <ProgresoAnios actual={anio} total={vista.anios} />
      <Text size="sm">
        <strong>Tú, en el mundo {GEMELOS + 1}:</strong> {cargoYSueldo(e)}
        {sinSueldo(e) ? ` · último sueldo ${plata(e.sueldo_ref)}` : " al mes"}
        {!sinSueldo(e) && e.tipo_empleador ? ` · ${TIPO_EMPLEADOR[e.tipo_empleador] ?? e.tipo_empleador}` : ""}
        {e.rubro ? ` · ${e.rubro}` : ""}
      </Text>

      <Stack gap={8} style={{ marginTop: 4 }}>
        <Meta>{pendiente.nombre}</Meta>
        {porQueTexto(pendiente.por_que) && (
          <span className="jg-por-que">
            <span aria-hidden="true">⚄</span>
            {porQueTexto(pendiente.por_que)}
          </span>
        )}
        {pendiente.narrativa && (
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
        {comparacion ? (
          <Text size="sm">
            Simulamos {comparacion.gemelos} mundos posibles. En cada uno, tu gemelo ya vivió cada opción hasta los {edadGemelos} años. Mira cómo le fue y toca la que eliges para tu mundo, el {GEMELOS + 1}.
          </Text>
        ) : (
          <Meta>{pendiente.opciones.length} opciones · toca una para elegirla</Meta>
        )}
        <button type="button" className="jg-ayuda" onClick={onAyuda}>
          ¿Cómo funciona la simulación?
        </button>
        {sinEfecto && <Text size="sm" className="jg-destacado">En esta decisión tu sueldo termina casi igual con cualquier opción: elige por lo que dice cada una.</Text>}
      </Stack>

      {comparacion ? (
        <div
          className="jg-opciones"
          role="group"
          aria-label="Opciones"
          data-muchas={comparadas.length > 2}
          data-cargando={recalculando}
          style={cssVars({ "--jg-n": comparadas.length })}
        >
          {comparadas.map((o) => (
            <OpcionConGemelos
              key={o.opcion}
              o={o}
              base={base}
              tope={tope}
              riesgo={riesgo}
              selected={sel === o.opcion}
              onSelect={() => elegirOpcion(o.opcion)}
              supuesto={supuestoDe(o)}
              edadFinal={edadGemelos}
              color={colores[o.opcion]}
              ganadas={ganadores && revelado ? ganadores.filter((g) => g === o.opcion).length : null}
              total={ganadores?.length ?? 0}
              empresa={pendiente.opciones.find((x) => x.opcion === o.opcion)?.empresa}
              textoEmpresa={narrados[`oferta:${o.opcion}`]}
            />
          ))}
        </div>
      ) : (
        <Stack gap={12} className="jg-columna">
          <Text size="sm">Esta carta tiene demasiadas opciones para simular los mundos con cada una. Aquí eliges con lo que dice cada opción.</Text>
          {muchas && (
            <input className="jg-campo" type="search" placeholder="Filtrar opciones" aria-label="Filtrar opciones" value={filtro} onChange={(ev) => setFiltro(ev.target.value)} />
          )}
          <DecisionList<string>
            label="Opciones"
            value={sel}
            onChange={elegirOpcion}
            options={visibles.slice(0, 40).map((o) => ({
              id: o.opcion,
              art: <DecisionArt kind={arte(pendiente.categoria)} />,
              title: o.nombre,
              subtitle: [o.detalle, o.empresa && (narrados[`oferta:${o.opcion}`] ?? ofertaTexto(o.empresa))].filter(Boolean).join(" · ") || undefined,
              tags: [{ label: CALIDAD[o.calidad]?.nombre ?? o.calidad, tone: o.calidad === "supuesto" ? ("minus" as const) : ("default" as const) }],
            }))}
          />
          {visibles.length > 40 && <Text size="sm">Hay {visibles.length - 40} más: usa el filtro.</Text>}
        </Stack>
      )}

      {comparacion && (
        <Info pregunta="¿Qué es el sueldo típico y la barra?">
          <strong>Sueldo típico:</strong> si ordenas los {comparacion.gemelos} mundos de esa opción desde donde ganas menos hasta donde ganas más, es el que
          queda justo al medio. <strong>Mala y buena suerte:</strong> la barra va desde el sueldo que no alcanzas solo en 1 de cada 10 mundos hasta el que
          superas solo en 1 de cada 10.
        </Info>
      )}

      {recalculando && <Cargando>Simulando los mundos por ese camino…</Cargando>}

      {opcion && opcion.elecciones_internas.length > 0 && (
        <div ref={panelInternas} className="jg-columna">
        <Panel className="jg-falta">
          <Meta>Falta un detalle de «{opcion.nombre}»</Meta>
          {opcion.elecciones_internas.map((i) => (
            <Stack key={i.variable} gap={8}>
              <Heading level={3} as="h2">
                {i.pregunta}
              </Heading>
              <Row>
                {i.alternativas.map((a) => (
                  <Chip key={String(a.valor)} pressed={internas[i.variable] === a.valor} onToggle={() => elegirInterna(i.variable, a.valor)}>
                    {a.nombre}
                    {comparadas.find((c) => c.opcion === opcion.opcion)?.parametros?.[i.variable] === a.valor && internas[i.variable] === undefined
                      ? " · lo más común"
                      : ""}
                  </Chip>
                ))}
              </Row>
            </Stack>
          ))}
          {comparacion && (
            <Text size="sm">
              {faltan.length > 0
                ? "Mientras no elijas, en la simulación de esta opción vas a donde va más gente."
                : "La simulación de esta opción ya va por el camino que elegiste."}
            </Text>
          )}
        </Panel>
        </div>
      )}

      {comparacion && foco && (
        <Stack gap={12} className="jg-columna">
          {ganadores && (
            <ApuestaAntesDeMirar
              key={llave}
              opcion={foco}
              ganadores={ganadores}
              gemelos={comparacion.gemelos}
              color={colores[foco.opcion]}
              revelado={revelado}
              onVer={() => setVistoEn(llave)}
              creencia={pendiente.creencia_vs_dato}
            >
              <Simulacion
                comparadas={comparadas}
                ganadores={ganadores}
                gemelos={comparacion.gemelos}
                colores={colores}
                anioInicial={anio}
                onVerMundo={onVerMundo}
                onNarrar={onNarrar}
              />
            </ApuestaAntesDeMirar>
          )}
          {partida && pendiente.por_que?.tipo === "elegida" && (
            <PesoDelCv perfil={partida.perfil} duda={pendiente.decision} semilla={partida.semilla} />
          )}
          <section className="jg-seccion" key={`abanico:${foco.opcion}`}>
            <Heading level={3} as="h2">
              «{foco.nombre}», año a año
            </Heading>
            <Abanico
              color={colores[foco.opcion]}
              colorReferencia={base ? colores[base.opcion] : undefined}
              puntos={foco.trayectoria}
              hoy={hoy}
              referencia={foco.es_base ? undefined : base?.trayectoria}
              nombreReferencia={foco.es_base ? undefined : base?.nombre}
            />
            <Info pregunta="¿Qué muestra este gráfico?">
              Tu sueldo en los mundos donde eliges «{foco.nombre}», desde hoy hasta los {edadGemelos} años. La línea de color es el mundo del medio. La
              franja celeste contiene 8 de cada 10 mundos: mientras más se abre, más depende de la suerte. Toca otra opción para ver la suya.
            </Info>
          </section>

          <section className="jg-seccion">
            <Heading level={3} as="h2">
              Además del sueldo
            </Heading>
            {(() => {
              const firma = (o: OpcionComparada) =>
                `${Math.round(o.paso_por_cesantia * 100)}|${Math.round(o.meses_sin_trabajo)}|${o.cargos.map((c) => `${c.cargo}:${Math.round(c.prob * 100)}`).join(",")}`;
              const iguales = comparadas.every((o) => firma(o) === firma(comparadas[0]));
              return (iguales ? comparadas.slice(0, 1) : comparadas).map((o) => {
                const meses = Math.round(o.meses_sin_trabajo);
                return (
                  <div className="jg-fila-opcion" key={o.opcion} data-foco={!iguales && comparadas.length > 1 && o.opcion === sel}>
                    <span className="jg-fuerte">
                      {iguales ? (
                        "Igual con todas las opciones"
                      ) : (
                        <>
                          <i className="jg-color" style={{ background: colores[o.opcion] }} aria-hidden="true" />
                          {o.nombre}
                        </>
                      )}
                    </span>
                    <span className="jg-chico">
                      Quedas sin trabajo alguna vez en <strong>{Math.round(o.paso_por_cesantia * 100)} de 100</strong> mundos
                      {meses > 0 ? ` · en promedio ${meses} ${meses === 1 ? "mes" : "meses"} sin pega en todo el período` : ""}
                    </span>
                    <span className="jg-medidor" aria-hidden="true">
                      <i style={{ width: `${Math.max(1, o.paso_por_cesantia * 100)}%` }} />
                    </span>
                    <span className="jg-chico">Cargo a los {edadGemelos} años (de cada 100 mundos):</span>
                    <BarraPartes partes={o.cargos.map((c) => ({ nombre: c.cargo, prob: c.prob }))} />
                  </div>
                );
              });
            })()}
            <Info pregunta="¿Por qué en tantos mundos paso por cesantía?">
              Cuenta cualquier mundo donde estás al menos un mes sin trabajo en todo el período, aunque después encuentres otro: un despido, el
              cierre de la empresa, una renuncia o un tiempo estudiando.
            </Info>
          </section>

          <details className="jg-plegable">
            <summary>¿Por qué sale así «{foco.nombre}»?</summary>
            <Stack gap={10}>
              <Text size="sm">Lo primero que te puede pasar si la eliges, en cuántos mundos pasa, y cómo terminas después de cada cosa.</Text>
              <Porque o={foco} base={base} />
            </Stack>
          </details>

          <details className="jg-plegable">
            <summary>De dónde salen los números</summary>
            <Stack gap={8}>
              {pendiente.creencia_vs_dato && (
                <Text size="sm">
                  <strong>Lo que se cree y lo que dice el dato:</strong> {pendiente.creencia_vs_dato}
                </Text>
              )}
              {pendiente.evidencia.map((ev) => (
                <Text size="sm" key={ev.fuente + ev.cifra}>
                  {ev.cifra}
                </Text>
              ))}
              <Row gap={6} style={{ alignItems: "center" }}>
                <span className="jg-chico">Esta decisión:</span>
                <CalidadTag calidad={pendiente.calidad} />
              </Row>
              <LeyendaCalidad />
            </Stack>
          </details>
        </Stack>
      )}

      <div className="jg-pie-fijo">
        {error && <ErrorCaja error={error} />}
        {cargando && <Cargando>Tirando tu dado y viviendo el año…</Cargando>}
        {opcion && faltan.length > 0 && !cargando && <Text size="sm">Falta elegir: {faltan.map((f) => minuscula(f.pregunta)).join(" ")}</Text>}
        <Button onClick={confirmar} disabled={!opcion || faltan.length > 0 || cargando || recalculando}>
          {cargando ? "Tirando el dado…" : opcion ? `Elegir «${opcion.nombre}» y tirar mi dado` : "Toca una opción"}
        </Button>
      </div>
    </Screen>
  );
}
