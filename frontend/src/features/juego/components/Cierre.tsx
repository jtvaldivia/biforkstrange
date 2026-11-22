import { BigNumber, Button, Heading, Meta, Pill, RangeCompare, Screen, ScreenHeader, Stack, StationTimeline, SunCard, Tag, Text, type Range } from "@/shared/ui";
import { aniosDe, cargoYSueldo, deCien, plata, sinSueldo, situacion } from "../textos";
import type { Anio, Perfil, Rango, Vista } from "../types";
import { GEMELOS } from "../api";
import { Abanico, Info } from "./graficos";
import { CompartirResultado } from "./Compartir";

/** Lo más importante del año, en una línea, para la línea de tiempo. */
function resumenDelAnio(a: Anio): string {
  const partes: string[] = [];
  // las que elegiste tú; los sorteos automáticos (a qué empleador entras) no van en el resumen
  for (const d of a.decisiones) if (d.opcion !== "sorteo") partes.push(`${d.opcion_nombre}: ${d.texto}`);
  for (const e of a.eventos) if (!e.rutina) partes.push(e.texto);
  if (partes.length === 0) partes.push("Un año sin noticias.");
  return `${partes.join(" ")}${a.fin ? ` Cierras con: ${cargoYSueldo(a.fin, true)}.` : ""}`;
}

/** El cierre: tu vida frente a los gemelos de tu primera decisión. Viene de "8 · Fin de la partida" del kit. */
export function CierrePantalla({
  vista, sueldoInicial, onOtraVida, onCambiarPerfil, perfil,
}: {
  vista: Vista;
  sueldoInicial: number;
  onOtraVida: () => void;
  onCambiarPerfil: () => void;
  /** El perfil con que se jugó: para el retrato de la tarjeta que se comparte. */
  perfil?: Perfil;
}) {
  const cierre = vista.cierre!;
  const e = cierre.estado;
  const primera = cierre.primera_decision;
  const opciones = primera?.comparacion.opciones ?? [];
  const elegida = opciones.find((o) => o.opcion === primera?.elegida);
  const otras = opciones.filter((o) => o.opcion !== primera?.elegida);
  const tope = Math.max(cierre.sueldo_final, ...opciones.map((o) => o.sueldo.p90), 1) * 1.05;
  const pos = (n: number) => Math.min(100, Math.max(0, (n / tope) * 100));
  const aRango = (r: Rango): Range => ({ low: pos(r.p10), high: pos(r.p90), median: pos(r.p50) });
  const letra = (i: number) => String.fromCharCode(66 + i);
  const edadInicial = vista.edad_final - vista.anios;
  const recorrido = [
    { edad: edadInicial, sueldo: sueldoInicial },
    ...vista.historia.filter((a) => a.fin).map((a) => ({ edad: a.fin!.edad, sueldo: a.fin!.sueldo })),
  ];

  return (
    <Screen gap={28}>
      <Stack gap={12}>
        <ScreenHeader left={<Pill tone="sol">Fin de la partida</Pill>} right={<Meta>{vista.anios} años · {e.edad} años</Meta>} />
        <Heading level={1}>Así terminó tu mundo {GEMELOS + 1}.</Heading>
      </Stack>

      <SunCard>
        <Meta>{sinSueldo(e) ? "Tu último sueldo" : "Tu sueldo final"}</Meta>
        <BigNumber value={plata(cierre.sueldo_final)} unit="al mes" animate />
        <Text>{sinSueldo(e) ? situacion(e.estado) : e.cargo}</Text>
        <Text size="sm">
          {cierre.anios_sin_trabajo > 0
            ? `${cierre.anios_sin_trabajo} ${cierre.anios_sin_trabajo === 1 ? "año" : "años"} sin trabajo.`
            : "Ningún año sin trabajo."}
        </Text>
        {cierre.mejor_que_gemelos !== undefined && elegida && (
          <Text>
            <strong>
              Te fue mejor que en {deCien(cierre.mejor_que_gemelos)} mundos con «{elegida.nombre}».
            </strong>
          </Text>
        )}
      </SunCard>


      {primera && elegida && (
        <Stack as="section" gap={12}>
          <Stack gap={4}>
            <Heading level={3} as="h2">
              Tú contra tus {GEMELOS} gemelos
            </Heading>
            <Text size="sm">{primera.pregunta}</Text>
          </Stack>
          <Abanico puntos={elegida.trayectoria} hoy={{ edad: edadInicial, sueldo: sueldoInicial }} tu={recorrido} alto={190} />
          <Info pregunta="¿Cómo leo este gráfico?">
            La línea amarilla es tu sueldo. La franja celeste va del 10% al 90% de los {primera.comparacion.gemelos} mundos donde elegiste «{elegida.nombre}», y
            la línea azul es la mediana. Si tu línea sale de la franja, te fue mejor (o peor) que a casi todos tus gemelos, por tu dado o por tus
            decisiones de después.
          </Info>
          <Meta>Sueldo final por opción · 10% a 90%</Meta>
          <Stack gap={6}>
            <span className="vd-camino">
              <Tag tone="sol">Tú · {GEMELOS + 1}</Tag>
              {plata(cierre.sueldo_final)}
            </span>
            <span className="vd-camino">
              <Tag tone="accent">A</Tag>
              {elegida.nombre} (elegiste) · {plata(elegida.sueldo.p10)} a {plata(elegida.sueldo.p90)}
            </span>
            {otras.map((o, i) => (
              <span className="vd-camino" key={o.opcion}>
                <Tag>{letra(i)}</Tag>
                {o.nombre} · {plata(o.sueldo.p10)} a {plata(o.sueldo.p90)}
              </span>
            ))}
          </Stack>
          <Stack gap={12}>
            {otras.map((o, i) => (
              <Stack gap={5} key={o.opcion}>
                <RangeCompare indicator="dinero" label={`A · ${elegida.nombre} contra ${letra(i)} · ${o.nombre}`} a={aRango(elegida.sueldo)} b={aRango(o.sueldo)} />
                <div className="vd-rangos" aria-hidden="true">
                  <em>Tú</em>
                  <span className="vd-rango-pista jg-pista-tu">
                    <span style={{ left: `${pos(cierre.sueldo_final)}%` }} />
                  </span>
                </div>
              </Stack>
            ))}
          </Stack>
          <Info pregunta="¿Es justa la comparación?">
            No del todo: tú tomaste más decisiones en estos 10 años. Tus gemelos solo tomaron la primera y después dejaron que la vida siguiera sin
            buscar más cambios.
          </Info>
        </Stack>
      )}
      {!primera && <Text size="sm">Tu primera decisión no se pudo simular: no hay con quién compararte.</Text>}


      <Stack as="section" gap={10}>
        <Heading level={3} as="h2">
          Tus {vista.anios} años
        </Heading>
        <div className="jg-vivido">
          <StationTimeline stations={vista.historia.map((a) => ({ when: `${aniosDe(a.edad, a.fin?.edad, edadInicial)} · ${a.edad} años`, what: resumenDelAnio(a) }))} />
        </div>
      </Stack>

      {primera && <CompartirResultado comparacion={primera.comparacion} elegida={primera.elegida} sueldoFinal={cierre.sueldo_final} perfil={perfil} />}

      <Stack gap={14}>
        <Button onClick={onOtraVida}>Jugar otra vida</Button>
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
