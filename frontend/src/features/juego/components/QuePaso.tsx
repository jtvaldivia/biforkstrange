import { Button, Meta, Narrative, NightBand, Panel, Pill, Screen, ScreenFooter, ScreenHeader, SlowReveal, Stack, Text, YearTicker, cssVars } from "@/shared/ui";
import { TIPO_EMPLEADOR, aniosDe, cargoYSueldo, conSigno, pesos, porciento, sinSueldo, situacion } from "../textos";
import type { Anio, DecisionTomada, Estado, Narrado, Vista } from "../types";
import { useNarracion } from "../hooks/useNarracion";
import { GEMELOS } from "../api";
import { Info, LineaSueldo, ProgresoAnios, Ruleta, sinMovimiento, type Casilla } from "./graficos";
import { Noticia, Pensando, Salir } from "./piezas";
import { ComoCambioTuSueldo, TuIngreso } from "./Plata";
import { TiraMeses, mesesDelAnio } from "./BuscandoTrabajo";

/** Todo lo que pasó entre la elección y la siguiente decisión pendiente: años cerrados y lo que va del año en curso. */
export function loNuevo(previa: Vista | null, vista: Vista): Anio[] {
  const todos = [...vista.historia, ...(vista.anio_en_curso ? [vista.anio_en_curso] : [])];
  if (!previa) return todos;
  const yaDecisiones = previa.anio_en_curso?.decisiones.length ?? 0;
  const yaEventos = previa.anio_en_curso?.eventos.length ?? 0;
  return todos
    .slice(previa.historia.length)
    .map((a, i) => (i === 0 ? { ...a, decisiones: a.decisiones.slice(yaDecisiones), eventos: a.eventos.slice(yaEventos) } : a));
}

// lo que puede pasarte en el año va en porcentaje; "X de 50" queda solo para contar mundos
const queTanProbable = (prob: number) => (prob >= 0.995 ? "Seguro" : porciento(prob));

/** Por qué bajó el sueldo, según lo que de verdad pasó: un despido, otro empleador o el mismo trabajo. */
function porQueBajo(antes: Estado, ahora: Estado, despido: boolean): string {
  const otroEmpleador = (antes.empresa_id ?? -1) !== (ahora.empresa_id ?? -1) || antes.tipo_empleador !== ahora.tipo_empleador;
  if (despido && otroEmpleador)
    return "No es el mismo trabajo: perdiste el anterior y encontraste otro el mismo año. Quien vuelve a trabajar después de un despido suele entrar ganando menos que antes (Couch y Placzek 2010).";
  if (otroEmpleador)
    return "Cambiaste de empleador, y no todos los cambios mejoran el sueldo: en Chile, casi la mitad no lo mejora (Banco Central). En el mismo trabajo, en cambio, el sueldo no baja.";
  return "En el mismo trabajo el alza anual nunca es negativa. Si bajó, es por algo que elegiste o te pasó este año, como menos horas o un cambio de cargo.";
}

/** Bajo este cambio (±2%), el sueldo se cuenta como "casi igual": así la frase y el número no se contradicen. */
const CASI_IGUAL = 0.02;

/** Un año con algo que se mostró con su %: desde el segundo, la ayuda del % ya se vio. */
const conPorcentaje = (a: Anio, primero: boolean) => a.eventos.some((e) => !e.rutina && !e.directo) || a.decisiones.length > (primero ? 1 : 0);

/**
 * El texto del resultado del dado, coherente con lo que de verdad pasó con el sueldo. "Ganas lo mismo o menos"
 * describe el resultado antes de sortear el empleador nuevo; si con él terminas ganando más, se dice eso.
 */
function textoDado(dado: DecisionTomada, tramo: Anio | undefined, finAnio?: number): string {
  if (!/mismo o menos/i.test(dado.texto) || dado.sueldo_antes === undefined || !(dado.sueldo_antes > 0)) return dado.texto;
  // el sorteo del empleador que sigue a la decisión es parte del mismo cambio de sueldo
  const siguen = tramo ? tramo.decisiones.slice(tramo.decisiones.indexOf(dado) + 1) : [];
  let despues = dado.sueldo_despues;
  for (const d of siguen) {
    if (d.decision !== "tipo_de_empleador") break;
    despues = d.sueldo_despues ?? despues;
  }
  if (despues === undefined || !(despues > 0)) return dado.texto;
  const cambio = despues / dado.sueldo_antes - 1;
  if (cambio >= CASI_IGUAL) return `Al final ganas ${Math.round(cambio * 100)}% más que antes.`;
  // el cambio en sí no sube el sueldo, pero el alza del año puede dejarte arriba: se dicen las dos cosas
  const delAnio = finAnio !== undefined && finAnio > 0 ? finAnio / dado.sueldo_antes - 1 : 0;
  if (delAnio >= CASI_IGUAL) return `El cambio no te sube el sueldo, pero con el alza del año terminas ganando ${Math.round(delAnio * 100)}% más.`;
  if (Math.abs(cambio) < CASI_IGUAL) return "Ganas casi lo mismo que antes.";
  return dado.texto;
}

function Quedaste({ antes, ahora, recorrido, espera, despido }: { antes: Estado | undefined; ahora: Estado; recorrido: { edad: number; sueldo: number }[]; espera: number; despido: boolean }) {
  const cargo = antes && antes.cargo !== ahora.cargo ? `${antes.cargo} → ${ahora.cargo}` : ahora.cargo;
  const donde = [TIPO_EMPLEADOR[ahora.tipo_empleador] ?? ahora.tipo_empleador, ahora.rubro].filter(Boolean).join(" · ");
  const comparable = antes && !sinSueldo(antes) && !sinSueldo(ahora);
  const delta = comparable ? ahora.sueldo - antes!.sueldo : 0;
  const casiIgual = comparable && Math.abs(delta) < CASI_IGUAL * antes!.sueldo;
  return (
    <Panel className="jg-despues" style={cssVars({ "--jg-espera": `${espera}s` })}>
      <Meta>Cómo quedaste · {ahora.edad} años</Meta>
      <div className="jg-cambio">
        <span className="jg-cambio-num">
          {sinSueldo(ahora) ? "Sin sueldo" : pesos(ahora.sueldo)}
        </span>
        {comparable && delta !== 0 && casiIgual && <span className="jg-delta">casi igual</span>}
        {comparable && !casiIgual && (
          <span className="jg-delta" data-signo={delta > 0 ? "mas" : "menos"}>
            {conSigno(delta)} al mes
          </span>
        )}
        <span className="jg-cambio-antes">
          {/* en pesos completos, como el número grande de al lado */}
          {sinSueldo(ahora) ? (ahora.sueldo_ref > 0 ? `El último fue ${pesos(ahora.sueldo_ref)}` : "") : comparable && delta !== 0 ? `Antes: ${pesos(antes!.sueldo)}` : "al mes"}
        </span>
      </div>
      {comparable && delta < -1000 && <Info pregunta="¿Por qué bajó?">{porQueBajo(antes!, ahora, despido)}</Info>}
      <LineaSueldo puntos={recorrido} />
      <div className="jg-datos">
        <div className="jg-dato">
          <span>Cargo</span>
          <span>{cargo}</span>
        </div>
        <div className="jg-dato">
          <span>Situación</span>
          <span>{situacion(ahora.estado)}</span>
        </div>
        {donde && !sinSueldo(ahora) && (
          <div className="jg-dato">
            <span>Dónde</span>
            <span>{donde}</span>
          </div>
        )}
      </div>
    </Panel>
  );
}

/**
 * Qué te pasó: el dado, las noticias del año y cómo quedaste.
 * Viene de "4 · Work and travel" / "5 · Las noches largas" (resultado del año) y "6 · Años sin decidir" (años que pasan) del kit.
 */
export function QuePaso({
  previa, vista, sueldoInicial, onSeguir, onNarrar, onSalir,
}: {
  previa: Vista | null;
  vista: Vista;
  sueldoInicial: number;
  onSeguir: () => void;
  /** Volver a la portada sin perder la partida. */
  onSalir?: () => void;
  /** Los eventos de cada año contados por Claude; sin él (o si falla) queda el texto del paquete. */
  onNarrar?: (que: "historia", signal: AbortSignal) => Promise<{ items: Narrado[] }>;
}) {
  // el resultado ya está decidido: se muestra de inmediato; lo que cuenta Claude reemplaza la plantilla cuando llega
  const { textos: narrados, listo } = useNarracion(onNarrar ? (signal) => onNarrar("historia", signal) : null, `${vista.historia.length}:${vista.anio_en_curso?.decisiones.length ?? 0}`);
  const tramos = loNuevo(previa, vista).filter((a) => a.fin || a.decisiones.length > 0 || a.eventos.some((e) => !e.rutina));
  const dado = tramos[0]?.decisiones[0];
  const cerrados = tramos.filter((a) => a.fin);
  const primero = tramos[0];
  const quedoSinTrabajo = vista.estado.estado === "buscando" && previa?.estado.estado !== "buscando";
  const noche = dado?.tono === "malo" || quedoSinTrabajo;

  const edadInicial = vista.edad_final - vista.anios;
  // el dado a la vista: todo lo que les pasó a los gemelos que eligieron lo mismo, y cuál te tocó a ti
  const elegida = dado ? previa?.pendiente?.comparacion?.opciones.find((o) => o.opcion === dado.opcion) : undefined;
  const casillas: Casilla[] = (elegida?.por_resultado ?? []).map((r) => ({ id: r.resultado, texto: r.texto || r.resultado, prob: r.prob, tono: r.tono }));
  const tocada = dado ? casillas.find((c) => c.id === dado.resultado) : undefined;
  const hayRuleta = casillas.length > 1 && tocada !== undefined;
  // el sorteo ya se vio en la espera: acá el resultado aparece de una
  const espera = sinMovimiento() ? 0 : 0.15;
  const recorrido = [
    { edad: edadInicial, sueldo: sueldoInicial },
    ...vista.historia.filter((a) => a.fin).map((a) => ({ edad: a.fin!.edad, sueldo: a.fin!.sueldo })),
  ];
  // con el año todavía en curso, el número grande ya es el de hoy: la línea tiene que terminar ahí también
  const ultimo = recorrido[recorrido.length - 1];
  if (vista.anio_en_curso && !sinSueldo(vista.estado) && ultimo && ultimo.sueldo !== vista.estado.sueldo)
    recorrido.push({ edad: vista.estado.edad, sueldo: vista.estado.sueldo });
  const despido = tramos.some((a) => a.eventos.some((e) => e.evento === "separacion_empleo"));
  const conProbabilidad = tramos.some((a) => conPorcentaje(a, a === tramos[0]));
  // la ayuda del % va solo el primer año en que aparece un %
  const yaVioPorcentaje = (previa?.historia ?? []).some((a) => conPorcentaje(a, true));
  const proximo = Math.min(vista.anio + 1, vista.anios);
  // una ronda puede ocupar varios años (un doctorado, cinco): se cuentan por edad
  const edades: number[] = [];
  for (const a of cerrados) for (let ed = a.edad; ed < a.fin!.edad; ed++) edades.push(ed);
  const mismoAnio = !vista.terminada && cerrados.length === 0;
  // en el mismo año viene otra decisión: el botón dice cuál, no "Otra decisión este año"
  const siguiente = vista.pendiente;
  const queSigue = siguiente?.decision === "oferta_externa" && siguiente.por_que?.tipo === "llega"
    ? "Ver la oferta que te llegó"
    : siguiente ? `Siguiente: ${siguiente.nombre}` : "Seguir";
  const boton = vista.terminada ? "Ver cómo terminaste" : mismoAnio ? queSigue : `Seguir al año ${proximo}`;

  // el dado sigue girando hasta que Claude cuenta el año: las noticias se muestran una vez y no cambian
  // mientras Claude cuenta el año sigue la misma escena de la carta: la ficha buscando, o la espera corta si era segura
  if (!listo)
    return (
      // el mismo título que la espera de la carta: el año de la partida
      <Pensando titulo={`Mundo ${GEMELOS + 1} · año ${primero ? primero.edad - edadInicial + 1 : proximo}`} onSalir={onSalir} />
    );


  return (
    <Screen tone={noche ? "noche" : "dia"} gap={16} className="jg-quepaso" key={`${vista.historia.length}:${vista.anio_en_curso?.decisiones.length ?? 0}`}>
      <ScreenHeader
        left={<Pill style={{ whiteSpace: "nowrap" }}>{primero ? `${aniosDe(primero.edad, primero.fin?.edad, edadInicial)} · ${primero.edad} años` : `Año ${proximo}`}</Pill>}
        right={onSalir && <Salir onSalir={onSalir} />}
      />
      <ProgresoAnios actual={primero ? Math.min(primero.edad - edadInicial + 1, vista.anios) : proximo} total={vista.anios} />
      <h1 className="vd-sr">{dado ? `Qué te pasó al elegir «${dado.opcion_nombre}»` : "Qué te pasó"}</h1>

      {edades.length > 1 && (
        <Stack gap={6}>
          <YearTicker years={edades.map((ed) => `Año ${ed - edadInicial + 1}`)} stepMs={900} />
          <Text>Pasaron {edades.length} años.</Text>
        </Stack>
      )}

      {dado && (
        <Stack gap={10}>
          <Meta>Elegiste «{dado.opcion_nombre}»{hayRuleta ? " · tiramos tu dado" : ""}</Meta>
          {hayRuleta && (
            <>
              <Text size="sm">Así salió en tus {GEMELOS} mundos:</Text>
              <Ruleta casillas={casillas} salio={dado.resultado} />
              {/* el conteo de los mundos y tu sorteo son dos cosas: que no parezca que tu dado es el conteo */}
              <Text size="sm">
                Lo tuyo se sorteó aparte, con la probabilidad de cada resultado: lo que te tocó tenía {porciento(dado.prob)}.
              </Text>
            </>
          )}
          <SlowReveal delay={espera}>
            <Narrative strong>{textoDado(dado, primero, sinSueldo(vista.estado) ? undefined : vista.estado.sueldo)}</Narrative>
          </SlowReveal>
        </Stack>
      )}

      {tramos.map((a, i) => {
        // la oferta del mes y su sorteo de empleador se ven en la tira de meses, no como noticias
        const decisiones = (i === 0 ? a.decisiones.slice(1) : a.decisiones).filter((d) => d.decision !== "tipo_de_oferta");
        const eventos = a.eventos.filter((e) => !e.rutina && e.evento !== "oferta_cesante");
        const celdas = mesesDelAnio(a);
        const titular = a.ia?.titular;
        const nada = decisiones.length === 0 && eventos.length === 0 && !titular;
        return (
          <Stack as="section" gap={8} key={`${a.anio}:${a.edad}`} className="jg-despues" style={cssVars({ "--jg-espera": `${espera + 0.2 + i * 0.1}s` })}>
            <Meta>
              {aniosDe(a.edad, a.fin?.edad, edadInicial)} · {a.edad} años{a.fin ? "" : " · en curso"}
            </Meta>
            {titular && <Noticia titulo="En las noticias" texto={titular} className="jg-titular-ia" />}
            {celdas && <TiraMeses celdas={celdas} />}
            {eventos.map((e, j) => (
              <Noticia
                key={`e${j}`}
                titulo={e.nombre}
                texto={narrados[`anio:${a.anio}:evento:${a.eventos.indexOf(e)}`] ?? e.texto}
                lado={e.directo ? undefined : `${queTanProbable(e.prob)}${e.prob >= 0.995 ? "" : " al año"}`}
              />
            ))}
            {decisiones.map((d, j) => (
              <Noticia
                key={`d${j}`}
                titulo={d.nombre}
                texto={narrados[`anio:${a.anio}:decision:${a.decisiones.indexOf(d)}`] ??
                  // la historia nombra a la empresa real: un resultado malo (la startup cierra) va sin ella
                  (d.narrativa && d.tono !== "malo" ? `${d.narrativa.situacion} ${d.texto}` : d.texto)}
                lado={queTanProbable(d.prob)}
              />
            ))}
            {nada && <Text size="sm">{a.fin && a.fin.edad - a.edad > 1
                  ? "Nada más en estos años."
                  : i === 0 && dado
                    ? "Nada más este año."
                    : "Un año sin noticias."}</Text>}
            {a.fin && a.fin.edad - a.edad > 1 && <Text size="sm">Te tomó {a.fin.edad - a.edad} años.</Text>}
            {a.fin && tramos.length > 1 && <Text size="sm">Cierras con: {cargoYSueldo(a.fin, true)}.</Text>}
          </Stack>
        );
      })}

      {conProbabilidad && !yaVioPorcentaje && (
        <Info pregunta="¿Qué es el % junto a cada noticia?">
          Qué tan probable era que te pasara eso, a alguien en tu situación. Por ejemplo, «4% al año» junto a un despido: de cada 100 personas como tú, a
          unas 4 las despiden en un año. Junto a una decisión, es qué tan probable era el resultado que te tocó. Los «de {GEMELOS} mundos», en cambio, cuentan en
          cuántos de tus {GEMELOS} mundos simulados pasó algo.
        </Info>
      )}

      {quedoSinTrabajo && (
        <NightBand>
          <Meta>Quedaste sin trabajo</Meta>
          <Text>La próxima decisión: cómo sigues buscando.</Text>
        </NightBand>
      )}

      <Quedaste antes={previa?.estado} ahora={vista.estado} recorrido={recorrido} espera={espera + 0.3} despido={despido} />
      <details className="jg-plegable">
        <summary>Ver detalle de tu plata</summary>
        <Stack gap={12}>
          <ComoCambioTuSueldo tramos={tramos} antes={previa?.estado} ahora={vista.estado} />
          <TuIngreso tramos={tramos} ahora={vista.estado} />
        </Stack>
      </details>

      <ScreenFooter>
        <Button variant={vista.terminada ? "sol" : "primary"} onClick={onSeguir}>
          {boton}
        </Button>
      </ScreenFooter>
    </Screen>
  );
}
