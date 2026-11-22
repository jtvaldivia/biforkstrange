import { BigNumber, Button, Heading, Meta, Pill, RangeCompare, Screen, ScreenHeader, Stack, StationTimeline, SunCard, Tag, Text, type Range } from "@/shared/ui";
import { aniosDe, cargoYSueldo, deCien, plata, sinSueldo, situacion } from "../textos";
import type { Anio, Rango, Vista } from "../types";
import { GEMELOS } from "../api";
import { Abanico, Info } from "./graficos";
import { coloresDe } from "./Carta";
import { CompartirResultado } from "./Compartir";
import { Logo } from "./Logo";
import { Salir } from "./piezas";

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

/** Lo más importante del año, en una línea, para la línea de tiempo. */
function resumenDelAnio(a: Anio): string {
  const partes: string[] = [];
  // las que elegiste tú; los sorteos automáticos (a qué empleador entras) no van en el resumen
  // un año tranquilo no va en el resumen: si buscaste algo, ya aparece la decisión que abriste
  for (const d of a.decisiones) if (d.opcion !== "sorteo" && d.decision !== "anio_tranquilo") partes.push(`${d.opcion_nombre}: ${d.texto}`);
  for (const e of a.eventos) if (!e.rutina) partes.push(e.texto);
  if (partes.length === 0) partes.push("Un año sin noticias.");
  return `${partes.join(" ")}${a.fin ? ` Cierras con: ${cargoYSueldo(a.fin, true)}.` : ""}`;
}

/** El cierre: tu vida frente a los gemelos de tu primera decisión. Viene de "8 · Fin de la partida" del kit. */
export function CierrePantalla({
  vista, sueldoInicial, onOtraVida, onCambiarPerfil, onSalir, retrato = null,
}: {
  vista: Vista;
  sueldoInicial: number;
  onOtraVida: () => void;
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
  const tope = Math.max(cierre.sueldo_final, ...opciones.map((o) => o.sueldo.p90), 1) * 1.05;
  const pos = (n: number) => Math.min(100, Math.max(0, (n / tope) * 100));
  const aRango = (r: Rango): Range => ({ low: pos(r.p10), high: pos(r.p90), median: pos(r.p50) });
  const letra = (i: number) => String.fromCharCode(66 + i);
  // los mismos colores de opción que en la carta: «Irte» es verde allá y aquí
  const colores = coloresDe(opciones);
  const punto = (opcion: string) => <i className="jg-color" style={{ background: colores[opcion] }} aria-hidden="true" />;
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
        <Meta>{sinSueldo(e) ? "Tu último sueldo" : "Tu sueldo final"}</Meta>
        <BigNumber value={plata(cierre.sueldo_final)} unit="al mes, en pesos de hoy" animate />
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
            la línea azul es la mediana. Si tu línea sale de la franja, te fue mejor (o peor) que a casi todas tus copias, por tu dado o por tus
            decisiones de después.
          </Info>
          <Meta>Sueldo final por opción · 10% a 90%</Meta>
          <Stack gap={6}>
            <span className="vd-camino">
              <Tag tone="sol">Tú · {GEMELOS + 1}</Tag>
              {plata(cierre.sueldo_final)}
            </span>
            <span className="vd-camino">
              <Tag>A</Tag>
              {punto(elegida.opcion)}
              {elegida.nombre} (elegiste) · {plata(elegida.sueldo.p10)} a {plata(elegida.sueldo.p90)}
            </span>
            {otras.map((o, i) => (
              <span className="vd-camino" key={o.opcion}>
                <Tag>{letra(i)}</Tag>
                {punto(o.opcion)}
                {o.nombre} · {plata(o.sueldo.p10)} a {plata(o.sueldo.p90)}
              </span>
            ))}
          </Stack>
          <Stack gap={12}>
            {otras.map((o, i) => (
              <Stack gap={5} key={o.opcion}>
                <RangeCompare indicator="dinero" label={`A · ${elegida.nombre} contra ${letra(i)} · ${o.nombre}`} a={aRango(elegida.sueldo)} b={aRango(o.sueldo)} colorA={colores[elegida.opcion]} colorB={colores[o.opcion]} />
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
            No del todo. En esos mundos tus copias tomaron la primera decisión como tú, y después decidieron lo que les fue llegando como decide
            la gente real. Tú decidiste el resto a tu manera.
          </Info>
        </Stack>
      )}
      {!primera && <Text size="sm">Tu primera decisión no se pudo simular: no hay con quién compararte.</Text>}


      <Recorrido historia={vista.historia} />

      <Stack as="section" gap={10}>
        <Heading level={3} as="h2">
          Tus {vista.anios} años
        </Heading>
        <div className="jg-vivido">
          <StationTimeline stations={vista.historia.map((a) => ({ when: `${aniosDe(a.edad, a.fin?.edad, edadInicial)} · ${a.edad} años`, what: resumenDelAnio(a) }))} />
        </div>
      </Stack>

      {primera && <CompartirResultado comparacion={primera.comparacion} elegida={primera.elegida} sueldoFinal={cierre.sueldo_final} retrato={retrato} />}

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
