import { BigNumber, Button, Heading, Meta, Pill, Screen, ScreenHeader, Stack, StationTimeline, SunCard, Text } from "@/shared/ui";
import { aniosDe, cargoYSueldo, plata, sinSueldo, situacion } from "../textos";
import type { Anio, Vista } from "../types";
import type { VidaAnterior } from "../hooks/usePartida";
import { GEMELOS } from "../api";
import { Abanico, EjeX, Info, LIENZO, RangosOpciones, escalaSueldo, rotuloSueldo } from "./graficos";
import { coloresDe, diferenciaDe } from "./Carta";
import { CompartirResultado } from "./Compartir";
import { Logo } from "./Logo";
import { Cargando, ErrorCaja, Salir } from "./piezas";
import { IACierre } from "./IACierre";

type Tramo = { titulo: string; empresa: string | null; empresaId: number | null; rubro: string; desde: number; hasta: number; sueldo: number };

/** Tu recorrido como en un perfil laboral: los años seguidos en el mismo cargo y la misma empresa son un tramo. Lo último arriba. */
function recorridoLaboral(historia: Anio[]): Tramo[] {
  const tramos: Tramo[] = [];
  for (const a of historia) {
    const f = a.fin;
    if (!f) continue;
    const trabaja = !sinSueldo(f);
    const titulo = trabaja ? f.rol || f.cargo : situacion(f.estado);
    const empresa = trabaja ? f.empresa ?? null : null;
    const ultimo = tramos.at(-1);
    if (ultimo && ultimo.titulo === titulo && ultimo.empresa === empresa) {
      ultimo.hasta = f.edad;
      ultimo.sueldo = f.sueldo;
    } else {
      const empresaId = empresa && (f.empresa_id ?? -1) >= 0 ? f.empresa_id! : null;
      tramos.push({ titulo, empresa, empresaId, rubro: f.rubro, desde: a.edad, hasta: f.edad, sueldo: f.sueldo });
    }
  }
  return tramos.reverse();
}

function Recorrido({ historia }: { historia: Anio[] }) {
  const tramos = recorridoLaboral(historia);
  if (tramos.length === 0) return null;
  return (
    <Stack as="section" gap={10}>
      <Heading level={3} as="h2">
        Tu recorrido
      </Heading>
      <ol className="jg-recorrido">
        {tramos.map((t, i) => {
          const anios = Math.max(1, t.hasta - t.desde);
          return (
            <li key={i} className="jg-tramo">
              {t.empresa ? (
                <Logo carpeta="empresas" id={t.empresaId ?? t.empresa} nombre={t.empresa} grupo={t.rubro} hay={t.empresaId !== null} tamano={40} />
              ) : (
                <span className="jg-tramo-vacio" aria-hidden="true" />
              )}
              <div className="jg-tramo-texto">
                <strong>{t.titulo}</strong>
                {t.empresa && <span>{t.empresa}</span>}
                <Meta>
                  {t.desde} a {t.hasta} años · {anios} {anios === 1 ? "año" : "años"}
                  {t.sueldo > 0 && ` · ${plata(t.sueldo)}/mes`}
                </Meta>
              </div>
            </li>
          );
        })}
      </ol>
    </Stack>
  );
}

/** Lo que se cuenta de un año: las decisiones que elegiste y lo que te pasó. */
function partesDelAnio(a: Anio): string[] {
  const partes: string[] = [];
  // las que elegiste tú; los sorteos automáticos (a qué empleador entras) no van en el resumen
  // un año tranquilo no va en el resumen: si buscaste algo, ya aparece la decisión que abriste
  for (const d of a.decisiones) if (d.opcion !== "sorteo" && d.decision !== "anio_tranquilo") partes.push(`${d.opcion_nombre}: ${d.texto}`);
  for (const e of a.eventos) if (!e.rutina) partes.push(e.texto);
  return partes;
}

/** Un año en que solo te reajustaron por inflación: ni decisiones ni otra noticia. */
const soloReajuste = (a: Anio) => a.eventos.some((e) => e.solo_ipc) && partesDelAnio(a).length === a.eventos.filter((e) => e.solo_ipc).length;

/**
 * La línea de tiempo año a año. Los años seguidos en que solo hubo reajuste por inflación van en una sola entrada
 * ("Años 3 a 6"), para no repetir la misma frase cuatro veces.
 */
function estaciones(historia: Anio[], edadInicial: number): { when: string; what: string }[] {
  const salida: { when: string; what: string }[] = [];
  const cierre = (a: Anio) => (a.fin ? ` Cierras con: ${cargoYSueldo(a.fin, true)}.` : "");
  for (let i = 0; i < historia.length; i++) {
    const a = historia[i];
    let j = i;
    if (soloReajuste(a)) while (j + 1 < historia.length && soloReajuste(historia[j + 1])) j++;
    if (j > i) {
      const b = historia[j];
      salida.push({
        when: `${aniosDe(a.edad, b.fin?.edad ?? b.edad + 1, edadInicial)} · ${a.edad} a ${b.edad} años`,
        what: `Sin cambios: solo reajuste por inflación, así que en pesos de hoy tu sueldo quedó igual.${cierre(b)}`,
      });
      i = j;
      continue;
    }
    const partes = partesDelAnio(a);
    salida.push({
      when: `${aniosDe(a.edad, a.fin?.edad, edadInicial)} · ${a.edad} años`,
      what: `${partes.length ? partes.join(" ") : "Un año sin noticias."}${cierre(a)}`,
    });
  }
  return salida;
}

/** "+$90 mil" o "−$1,1 M". */
const conSignoPlata = (n: number) => `${n >= 0 ? "+" : "−"}${plata(Math.abs(n))}`;

/**
 * ¿Fue la decisión o la suerte? Separa tu resultado en dos partes que ya están en la simulación:
 * lo que movía tu primera decisión (lo típico de lo que elegiste frente a lo típico de la otra opción) y lo que
 * pusieron tu suerte y tus decisiones de después (tu sueldo frente a lo típico de tus copias).
 */
function DecisionOSuerte({
  elegida, otra, sueldoFinal, gemelos,
}: {
  elegida: { nombre: string; p50: number };
  /**
   * La otra opción y la diferencia típica mundo a mundo (con la misma suerte), con el mismo criterio de la carta:
   * con muchos empates, solo entre los mundos donde cambia algo (`cuandoCambia`).
   */
  otra: { nombre: string; diferencia: number | null; cuandoCambia: boolean } | null;
  sueldoFinal: number;
  gemelos: number;
}) {
  const porDecision = otra?.diferencia ?? null;
  const porLoDemas = sueldoFinal - elegida.p50;
  const chica = (n: number) => Math.abs(n) < 0.03 * Math.max(1, elegida.p50);
  // para el veredicto: bajo 5% del sueldo típico no se puede decir que algo "pesó"
  const poco = (n: number) => Math.abs(n) < 0.05 * Math.max(1, elegida.p50);
  const pesoMas =
    porDecision === null ? null : poco(porDecision) && poco(porLoDemas) ? "nada" : Math.abs(porLoDemas) > Math.abs(porDecision) ? "suerte" : "decision";
  return (
    <Stack as="section" gap={12}>
      <Stack gap={4}>
        <Heading level={3} as="h2">
          ¿Fue la decisión o la suerte?
        </Heading>
        <Text size="sm">
          En tus {gemelos} mundos, tu copia eligió «{elegida.nombre}», igual que tú, y después decidió como la mayoría. Tú, a tu manera.
        </Text>
      </Stack>
      <div className="jg-datos jg-cierre-partes">
        {otra && porDecision !== null && (
          <div className="jg-dato">
            <span>
              Tu decisión
              <small>
                Elegir «{elegida.nombre}» en vez de «{otra.nombre}» {chica(porDecision) ? "casi no cambiaba" : porDecision > 0 ? "subía" : "bajaba"} el sueldo
                del mismo mundo, típico (comparando cada mundo consigo mismo{otra.cuandoCambia ? ", en los mundos donde no da lo mismo" : ""}).
              </small>
            </span>
            <span data-tono={chica(porDecision) ? "igual" : porDecision > 0 ? "mas" : "menos"}>{conSignoPlata(porDecision)}</span>
          </div>
        )}
        <div className="jg-dato">
          <span>
            Tu suerte y lo que decidiste después
            <small>
              Lo que te separó de lo típico de tu copia en tus {gemelos} mundos ({plata(elegida.p50)}).
            </small>
          </span>
          <span data-tono={chica(porLoDemas) ? "igual" : porLoDemas > 0 ? "mas" : "menos"}>{conSignoPlata(porLoDemas)}</span>
        </div>
      </div>
      {pesoMas && (
        <Text className="jg-destacado">
          {pesoMas === "nada"
            ? "Ni tu primera decisión ni la suerte movieron mucho tu sueldo: terminaste cerca de lo típico."
            : pesoMas === "suerte"
              ? "En tu vida pesó más la suerte y lo que decidiste después que tu primera decisión."
              : "En tu vida pesó más tu primera decisión que la suerte."}
        </Text>
      )}
    </Stack>
  );
}

/** Tus dos vidas en el mismo mundo, en un solo gráfico: la de ahora en amarillo y la anterior punteada. */
function DosVidas({ ahora, antes }: { ahora: { edad: number; sueldo: number }[]; antes: { edad: number; sueldo: number }[] }) {
  if (ahora.length < 2 || antes.length < 2) return null;
  const { W, X0, X1 } = LIENZO;
  const H = 160;
  const Y0 = 14;
  const Y1 = H - 22;
  const todos = [...ahora, ...antes];
  const e0 = Math.min(...todos.map((p) => p.edad));
  const e1 = Math.max(...todos.map((p) => p.edad));
  const x = (edad: number) => X0 + ((edad - e0) / Math.max(1, e1 - e0)) * (X1 - X0);
  const y = escalaSueldo(todos.map((p) => p.sueldo), Y0, Y1);
  const linea = (ps: { edad: number; sueldo: number }[]) => ps.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.edad).toFixed(1)},${y(p.sueldo).toFixed(1)}`).join(" ");
  const finA = ahora[ahora.length - 1];
  const finB = antes[antes.length - 1];
  let yA = y(finA.sueldo);
  let yB = y(finB.sueldo);
  if (Math.abs(yA - yB) < 14) {
    if (yA <= yB) yB = yA + 14;
    else yA = yB + 14;
  }
  return (
    <svg className="jg-abanico" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Tu vida de ahora termina en ${plata(finA.sueldo)} y la anterior en ${plata(finB.sueldo)}.`}>
      <EjeX alto={H} y1={Y1} e0={e0} e1={e1} sueldo0={ahora[0].sueldo} hoy={false} />
      <path className="jg-abanico-ref" style={{ stroke: "var(--suave)" }} pathLength={1} d={linea(antes)} />
      <path className="jg-abanico-tu-borde" pathLength={1} d={linea(ahora)} />
      <path className="jg-abanico-tu" pathLength={1} d={linea(ahora)} />
      <circle className="jg-abanico-tu-punto" cx={x(finA.edad)} cy={y(finA.sueldo)} r={5.5} />
      <text x={X1 + 8} y={yA + 4} className="jg-abanico-num">{rotuloSueldo(finA.sueldo)}</text>
      <text x={X1 + 8} y={yA + 15} className="jg-abanico-sub">esta vida</text>
      <text x={X1 + 8} y={yB + 4} className="jg-abanico-num" style={{ fill: "var(--suave)" }}>{rotuloSueldo(finB.sueldo)}</text>
      <text x={X1 + 8} y={yB + 15} className="jg-abanico-sub">la anterior</text>
    </svg>
  );
}

/** La comparación con tu vida anterior en este mismo mundo: el gráfico y una frase con la diferencia. */
function MismoMundo({ antes, ahora, sueldoFinal, primeraAhora }: { antes: VidaAnterior; ahora: { edad: number; sueldo: number }[]; sueldoFinal: number; primeraAhora: string | null }) {
  const dif = sueldoFinal - antes.sueldoFinal;
  const igual = Math.abs(dif) < 0.03 * Math.max(1, antes.sueldoFinal);
  const nombreAntes = antes.primera?.nombre ?? null;
  const misma = nombreAntes !== null && nombreAntes === primeraAhora;
  let frase: string;
  if (igual) frase = "Terminaste casi con el mismo sueldo que en tu vida anterior.";
  else if (primeraAhora && nombreAntes && !misma)
    frase = `Con «${primeraAhora}» terminaste ${plata(Math.abs(dif))} ${dif > 0 ? "arriba" : "abajo"} de lo que te dio «${nombreAntes}», en el mismo mundo.`;
  else frase = `Terminaste ${plata(Math.abs(dif))} ${dif > 0 ? "arriba" : "abajo"} de tu vida anterior, en el mismo mundo.`;
  return (
    <Stack as="section" gap={10}>
      <Stack gap={4}>
        <Heading level={3} as="h2">
          Tus dos vidas en el mismo mundo
        </Heading>
        <Text size="sm">Las dos partieron igual y vivieron la misma suerte del país. La de tu pega cambia cuando te cambias de trabajo.</Text>
      </Stack>
      <DosVidas ahora={ahora} antes={antes.recorrido} />
      <Text className="jg-destacado">{frase}</Text>
      {misma && !igual && (
        <Text size="sm">Elegiste lo mismo al principio, así que la diferencia viene de lo que decidiste después.</Text>
      )}
    </Stack>
  );
}

/** El cierre: tu vida frente a los gemelos de tu primera decisión. Viene de "8 · Fin de la partida" del kit. */
export function CierrePantalla({
  vista, sueldoInicial, onOtraVida, onRevivir, anterior = null, onCambiarPerfil, onSalir, retrato = null, cargando = false, error = null, onReintentar,
}: {
  /** Mientras arranca la otra vida, el cierre sigue a la vista: si falla, se puede reintentar o quedarse aquí. */
  cargando?: boolean;
  error?: string | null;
  onReintentar?: () => void;
  vista: Vista;
  sueldoInicial: number;
  onOtraVida: () => void;
  /** Vuelve a vivir este mismo mundo desde el año 1. */
  onRevivir: () => void;
  /** Tu vida anterior en este mismo mundo, si vienes de revivirlo. */
  anterior?: VidaAnterior | null;
  onCambiarPerfil: () => void;
  onSalir?: () => void;
  /** "Lo que tu gemelo sabe de ti", si Claude leyó tu CV o tu Claude: va en la tarjeta que se comparte. */
  retrato?: string | null;
}) {
  const cierre = vista.cierre!;
  const e = cierre.estado;
  const primera = cierre.primera_decision;
  const opciones = primera?.comparacion.opciones ?? [];
  const elegida = opciones.find((o) => o.opcion === primera?.elegida);
  const otras = opciones.filter((o) => o.opcion !== primera?.elegida);
  // contra qué se mide tu decisión: la otra opción con mejor sueldo típico (el backend la elige igual y trae la
  // diferencia mundo a mundo en `contra`)
  const otraTipica = otras.find((o) => o.opcion === primera?.contra?.opcion) ?? [...otras].sort((a, b) => b.sueldo.p50 - a.sueldo.p50)[0] ?? null;
  // la diferencia que movió tu decisión, con el mismo criterio que la carta
  const dif = primera?.contra ? diferenciaDe(primera.contra) : { d: null, cuandoCambia: false };
  // los mismos colores de opción que en la carta: «Irte» es verde allá y aquí
  const colores = coloresDe(opciones);
  const conCeros = opciones.some((o) => o.sin_trabajo_al_final > 0);
  const mesesSinTrabajo = cierre.meses_sin_trabajo ?? cierre.anios_sin_trabajo * 12;
  const edadInicial = vista.edad_final - vista.anios;
  const recorrido = [
    { edad: edadInicial, sueldo: sueldoInicial },
    ...vista.historia.filter((a) => a.fin).map((a) => ({ edad: a.fin!.edad, sueldo: a.fin!.sueldo })),
  ];

  return (
    <Screen gap={28}>
      <Stack gap={12}>
        <ScreenHeader left={<Pill tone="sol">Fin de la partida</Pill>} right={onSalir && <Salir onSalir={onSalir} />} />
        <Heading level={1}>Así terminó tu mundo {GEMELOS + 1}.</Heading>
      </Stack>

      <SunCard>
        <Meta>Tu sueldo final · en pesos de hoy</Meta>
        <BigNumber value={plata(cierre.sueldo_final)} unit="al mes" animate />
        <Text>{sinSueldo(e) ? situacion(e.estado) : [e.rol || e.cargo, e.empresa].filter(Boolean).join(" · ")}</Text>
        {/* sin trabajo cuenta $0, como en tus copias; el último sueldo va aparte, solo como dato */}
        {sinSueldo(e) && (cierre.ultimo_sueldo ?? 0) > 0 && <Text size="sm">Terminas sin trabajo, así que cuenta $0. Tu último sueldo fue {plata(cierre.ultimo_sueldo!)} al mes.</Text>}
        <Text size="sm">
          {mesesSinTrabajo > 0 ? `${mesesSinTrabajo} ${mesesSinTrabajo === 1 ? "mes" : "meses"} sin trabajo.` : "Siempre con trabajo."}
        </Text>
      </SunCard>

      {anterior && <MismoMundo antes={anterior} ahora={recorrido} sueldoFinal={cierre.sueldo_final} primeraAhora={elegida?.nombre ?? null} />}

      {primera && elegida && (
        <Stack as="section" gap={12}>
          <Stack gap={4}>
            <Heading level={3} as="h2">
              Tú contra tus {GEMELOS} mundos
            </Heading>
            <Text size="sm">{primera.pregunta}</Text>
          </Stack>
          <Abanico
            puntos={elegida.trayectoria}
            hoy={{ edad: edadInicial, sueldo: sueldoInicial }}
            tu={recorrido}
            alto={190}
            color={colores[elegida.opcion]}
            referencia={otraTipica?.trayectoria}
            nombreReferencia={otraTipica?.nombre}
            colorReferencia={otraTipica ? colores[otraTipica.opcion] : undefined}
          />
          {cierre.mejor_que_gemelos !== undefined && (
            <Text className="jg-destacado">
              Terminaste ganando más que tu copia en {Math.round(cierre.mejor_que_gemelos * primera.comparacion.gemelos)}{" "}de{" "}{primera.comparacion.gemelos} mundos.
            </Text>
          )}
          <Info pregunta="¿Cómo leo este gráfico?">
            La línea amarilla es tu sueldo. La franja va de «si te va mal» a «si te va bien» (8 de cada 10 de tus {primera.comparacion.gemelos} mundos) con
            «{elegida.nombre}», y la línea gruesa es lo típico.{otraTipica && ` La punteada es lo típico si hubieras elegido «${otraTipica.nombre}».`} Si
            tu línea sale de la franja, te fue mejor (o peor) que a tu copia en casi todos los mundos, por tu dado o por tus decisiones de después.
          </Info>
          <details>
            <summary className="jg-ayuda">Ver el sueldo final de cada opción</summary>
            <Stack gap={10} className="jg-vivido">
              <Meta>De «si te va mal» a «si te va bien»</Meta>
              <RangosOpciones
                tu={cierre.sueldo_final}
                opciones={[elegida, ...otras].map((o) => ({
                  id: o.opcion,
                  nombre: o.nombre,
                  nota: o.opcion === elegida.opcion ? "la elegiste" : undefined,
                  rango: o.sueldo,
                  color: colores[o.opcion],
                }))}
              />
              {conCeros && <Text size="sm">Los mundos que terminan sin trabajo cuentan con $0, por eso «si te va mal» puede quedar bajo.</Text>}
            </Stack>
          </details>
        </Stack>
      )}

      {primera && elegida && (
        <DecisionOSuerte
          elegida={{ nombre: elegida.nombre, p50: elegida.sueldo.p50 }}
          otra={otraTipica ? { nombre: otraTipica.nombre, diferencia: dif.d, cuandoCambia: dif.cuandoCambia } : null}
          sueldoFinal={cierre.sueldo_final}
          gemelos={primera.comparacion.gemelos}
        />
      )}

      {!primera && <Text size="sm">Tu primera decisión no se pudo simular: no hay con quién compararte.</Text>}

      <Recorrido historia={vista.historia} />

      <details>
        <summary className="jg-ayuda">Ver tus {vista.anios} años, año a año</summary>
        <div className="jg-vivido">
          <StationTimeline stations={estaciones(vista.historia, edadInicial)} />
        </div>
      </details>

      {cierre.ia && <IACierre ia={cierre.ia} elegida={elegida?.opcion} nombreElegida={elegida?.nombre} />}

      <Stack gap={10}>
        {error && <ErrorCaja error={error} onReintentar={onReintentar} />}
        {cargando && <Cargando>Preparando tu otra vida…</Cargando>}
        <Button onClick={onRevivir} disabled={cargando}>Vivir este mismo mundo eligiendo distinto</Button>
        <Text size="sm">Vuelves al año 1 con la misma primera decisión y la misma suerte del país. Al final ves tus dos vidas juntas.</Text>
      </Stack>
      {primera && (
        <CompartirResultado comparacion={primera.comparacion} elegida={primera.elegida} sueldoFinal={cierre.sueldo_final} retrato={retrato} />
      )}
      <Stack gap={10}>
        <Button variant="white" onClick={onOtraVida} disabled={cargando}>
          Jugar otra vida, en otro mundo
        </Button>
        <Button variant="white" onClick={onCambiarPerfil}>
          Cambiar mi perfil
        </Button>
      </Stack>
      <Info pregunta="¿De dónde salen los números?">
        Qué tan seguido pasa cada cosa sale de encuestas a trabajadores chilenos (ESI y ENE del INE, entre otras). Donde no hay medición, usamos
        un supuesto nuestro. No es una predicción: es el abanico de lo que le pasa a gente como tú.
      </Info>
    </Screen>
  );
}
