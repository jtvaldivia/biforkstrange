import { Button, Meta, Narrative, NightBand, Panel, Pill, Screen, ScreenFooter, ScreenHeader, SlowReveal, Stack, Text, YearTicker, cssVars } from "@/shared/ui";
import { TIPO_EMPLEADOR, aniosDe, cargoYSueldo, conSigno, deCada, deCada10, deCien, pesos, plata, sinSueldo, situacion } from "../textos";
import type { Anio, Estado, Narrado, Vista } from "../types";
import { useNarracion } from "../hooks/useNarracion";
import { GEMELOS } from "../api";
import { Info, LineaSueldo, Ruleta, type Casilla } from "./graficos";
import { Noticia, Pensando } from "./piezas";

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

const queTanProbable = (prob: number) => (prob >= 0.995 ? "Seguro" : deCien(prob));

function Quedaste({ antes, ahora, recorrido, espera }: { antes: Estado | undefined; ahora: Estado; recorrido: { edad: number; sueldo: number }[]; espera: number }) {
  const cargo = antes && antes.cargo !== ahora.cargo ? `${antes.cargo} → ${ahora.cargo}` : ahora.cargo;
  const donde = [TIPO_EMPLEADOR[ahora.tipo_empleador] ?? ahora.tipo_empleador, ahora.rubro].filter(Boolean).join(" · ");
  const comparable = antes && !sinSueldo(antes) && !sinSueldo(ahora);
  const delta = comparable ? ahora.sueldo - antes!.sueldo : 0;
  return (
    <Panel className="jg-despues" style={cssVars({ "--jg-espera": `${espera}s` })}>
      <Meta>Cómo quedaste · {ahora.edad} años</Meta>
      <div className="jg-cambio">
        <span className="jg-cambio-num">
          {sinSueldo(ahora) ? "Sin sueldo" : pesos(ahora.sueldo)}
        </span>
        {comparable && Math.abs(delta) >= 1000 && (
          <span className="jg-delta" data-signo={delta > 0 ? "mas" : "menos"}>
            {conSigno(delta)} al mes
          </span>
        )}
        <span className="jg-cambio-antes">
          {sinSueldo(ahora) ? `El último fue ${pesos(ahora.sueldo_ref)}` : comparable && delta !== 0 ? `Antes: ${pesos(antes!.sueldo)}` : "al mes"}
        </span>
      </div>
      {comparable && delta < -1000 && antes!.cargo === ahora.cargo && (
        <Info pregunta="¿Por qué bajó?">Además de tus decisiones, cada año tu sueldo se mueve solo, según tu edad y tu dado.</Info>
      )}
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
  previa, vista, sueldoInicial, onSeguir, onNarrar,
}: {
  previa: Vista | null;
  vista: Vista;
  sueldoInicial: number;
  onSeguir: () => void;
  /** Los eventos de cada año contados por Sonnet; sin él (o si falla) queda el texto del paquete. */
  onNarrar?: (que: "historia", signal: AbortSignal) => Promise<{ items: Narrado[] }>;
}) {
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
  const espera = 0.15;
  const recorrido = [
    { edad: edadInicial, sueldo: sueldoInicial },
    ...vista.historia.filter((a) => a.fin).map((a) => ({ edad: a.fin!.edad, sueldo: a.fin!.sueldo })),
  ];
  const proximo = Math.min(vista.anio + 1, vista.anios);
  // una ronda puede ocupar varios años (un doctorado, cinco): se cuentan por edad
  const edades: number[] = [];
  for (const a of cerrados) for (let ed = a.edad; ed < a.fin!.edad; ed++) edades.push(ed);
  const mismoAnio = !vista.terminada && cerrados.length === 0;
  const boton = vista.terminada ? "Ver cómo terminaste" : mismoAnio ? "Otra decisión este año" : `Seguir al año ${proximo}`;

  // el dado sigue girando hasta que Sonnet cuenta el año: las noticias se muestran una vez y no cambian
  if (!listo) return <Pensando titulo={`Mundo ${GEMELOS + 1} · ${primero ? `${primero.edad} años` : `año ${proximo}`}`} />;

  return (
    <Screen tone={noche ? "noche" : "dia"} gap={16} className="jg-quepaso" key={`${vista.historia.length}:${vista.anio_en_curso?.decisiones.length ?? 0}`}>
      <ScreenHeader
        left={<Pill style={{ whiteSpace: "nowrap" }}>{primero ? `${aniosDe(primero.edad, primero.fin?.edad, edadInicial)} · ${primero.edad} años` : `Año ${proximo}`}</Pill>}
        right={<Meta>Mundo {GEMELOS + 1}</Meta>}
      />

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
              <Text size="sm">Así salió en los {GEMELOS} mundos. Este es tu dado:</Text>
              <Ruleta casillas={casillas} salio={dado.resultado} />
            </>
          )}
          <SlowReveal delay={espera}>
            <Narrative strong>{dado.texto}</Narrative>
          </SlowReveal>
          <SlowReveal delay={espera + 0.1}>
            <Text size="sm">
              {hayRuleta
                ? `Pasó en ${deCien(tocada!.prob)} mundos.`
                : dado.prob >= 0.995
                  ? "Con esta opción, era seguro."
                  : `Pasa en ${deCien(dado.prob)} mundos.`}
            </Text>
          </SlowReveal>
        </Stack>
      )}

      {tramos.map((a, i) => {
        const decisiones = i === 0 ? a.decisiones.slice(1) : a.decisiones;
        const eventos = a.eventos.filter((e) => !e.rutina);
        const nada = decisiones.length === 0 && eventos.length === 0;
        return (
          <Stack as="section" gap={8} key={`${a.anio}:${a.edad}`} className="jg-despues" style={cssVars({ "--jg-espera": `${espera + 0.2 + i * 0.1}s` })}>
            <Meta>
              {aniosDe(a.edad, a.fin?.edad, edadInicial)} · {a.edad} años{a.fin ? "" : " · en curso"}
            </Meta>
            {eventos.map((e, j) => (
              <Noticia
                key={`e${j}`}
                titulo={e.nombre}
                texto={narrados[`anio:${a.anio}:evento:${a.eventos.indexOf(e)}`] ?? e.texto}
                lado={e.directo ? undefined : queTanProbable(e.prob)}
              />
            ))}
            {decisiones.map((d, j) => (
              <Noticia
                key={`d${j}`}
                titulo={d.nombre}
                texto={narrados[`anio:${a.anio}:decision:${a.decisiones.indexOf(d)}`] ?? (d.narrativa ? `${d.narrativa.situacion} ${d.texto}` : d.texto)}
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

      {quedoSinTrabajo && (
        <NightBand>
          <Meta>Quedaste sin trabajo</Meta>
          <Text>La próxima carta: cómo sigues buscando.</Text>
        </NightBand>
      )}

      <Quedaste antes={previa?.estado} ahora={vista.estado} recorrido={recorrido} espera={espera + 0.3} />

      <ScreenFooter>
        <Button variant={vista.terminada ? "sol" : "primary"} onClick={onSeguir}>
          {boton}
        </Button>
      </ScreenFooter>
    </Screen>
  );
}
