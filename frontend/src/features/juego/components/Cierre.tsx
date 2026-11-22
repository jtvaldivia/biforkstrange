import { BigNumber, Button, Heading, Meta, Pill, RangeCompare, Screen, ScreenHeader, Stack, StationTimeline, SunCard, Tag, Text, type Range } from "@/shared/ui";
import { aniosDe, cargoYSueldo, deCada10, plata, sinSueldo, situacion } from "../textos";
import type { Anio, Perfil, Rango, Vista } from "../types";
import { GEMELOS } from "../api";
import { Abanico, Info } from "./graficos";
import { LeyendaCalidad } from "./piezas";
import { IntuicionResumen } from "./Apuesta";
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
        <Heading level={1}>Diez años en el mundo {GEMELOS + 1}: el que viviste tú.</Heading>
      </Stack>

      <SunCard>
        <Meta>{sinSueldo(e) ? "Tu último sueldo" : "Tu sueldo final"}</Meta>
        <BigNumber value={plata(cierre.sueldo_final)} unit="al mes" animate />
        <Text>
          Terminas a los {e.edad} años: {sinSueldo(e) ? situacion(e.estado).toLowerCase() : e.cargo}.{" "}
          {cierre.anios_sin_trabajo > 0
            ? `Pasaste ${cierre.anios_sin_trabajo} ${cierre.anios_sin_trabajo === 1 ? "año" : "años"} sin trabajo.`
            : "No pasaste ningún año sin trabajo."}
        </Text>
        {cierre.mejor_que_gemelos !== undefined && elegida && (
          <Text>
            <strong>
              {cierre.mejor_que_gemelos >= 0.95
                ? `Te fue mejor que en casi todos los mundos donde también elegiste «${elegida.nombre}».`
                : cierre.mejor_que_gemelos < 0.05
                  ? `En casi todos los mundos donde también elegiste «${elegida.nombre}» te fue mejor que aquí.`
                  : `Te fue mejor que en ${deCada10(cierre.mejor_que_gemelos)} mundos donde también elegiste «${elegida.nombre}».`}
            </strong>
          </Text>
        )}
      </SunCard>

      <IntuicionResumen />

      {primera && elegida && (
        <Stack as="section" gap={12}>
          <Stack gap={4}>
            <Heading level={3} as="h2">
              Tu mundo, el {GEMELOS + 1}, contra los otros {GEMELOS}
            </Heading>
            <Text size="sm">
              Tu primera decisión: {primera.pregunta} Aquí va tu sueldo año a año contra el de tus gemelos en los {primera.comparacion.gemelos} mundos donde
              elegiste lo mismo.
            </Text>
          </Stack>
          <Abanico puntos={elegida.trayectoria} hoy={{ edad: edadInicial, sueldo: sueldoInicial }} tu={recorrido} alto={190} />
          <Info pregunta="¿Cómo leo este gráfico?">
            La línea amarilla es tu sueldo en el mundo {GEMELOS + 1}, el que jugaste. La franja celeste contiene 8 de cada 10 mundos donde elegiste «{elegida.nombre}» y
            la línea azul es el mundo del medio. Si tu línea sale de la franja, tuviste más (o menos) suerte que casi todos, o tus decisiones de
            después te llevaron por otro lado.
          </Info>
          <Text size="sm">Y el sueldo final de cada opción, lado a lado. Cada barra va de la mala suerte a la buena suerte; la raya es el sueldo típico.</Text>
          <Stack gap={6}>
            <span className="vd-camino">
              <Tag tone="sol">Tú · {GEMELOS + 1}</Tag>
              {plata(cierre.sueldo_final)}
            </span>
            <span className="vd-camino">
              <Tag tone="accent">A</Tag>
              {elegida.nombre} (la que elegiste) · {plata(elegida.sueldo.p10)} a {plata(elegida.sueldo.p90)}
            </span>
            {otras.map((o, i) => (
              <span className="vd-camino" key={o.opcion}>
                <Tag>{letra(i)}</Tag>
                {o.nombre} (la que no tomaste) · {plata(o.sueldo.p10)} a {plata(o.sueldo.p90)}
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
          <Text>
            Ojo con la comparación: tú tomaste más decisiones en estos 10 años. En esos mundos tus gemelos solo tomaron la primera y después dejaron que la vida
            siguiera sin buscar más cambios.
          </Text>
        </Stack>
      )}
      {!primera && <Text size="sm">Tu primera decisión tenía demasiadas opciones para simular los mundos, así que aquí no hay con quién compararte.</Text>}


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
      <LeyendaCalidad />
    </Screen>
  );
}
