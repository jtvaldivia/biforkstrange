import { useState } from "react";
import { Button, DecisionArt, Heading, Meta, Pill, Screen, ScreenFooter, ScreenHeader, Stack, Text } from "@/shared/ui";
import { GEMELOS } from "../api";
import { arteDuda, porciento } from "../textos";
import type { Eleccion, SinNovedad, Vista } from "../types";
import { Cargando, ErrorCaja, FranjaSinNovedad, Noticia, Salir } from "./piezas";

/**
 * Un año en que no te llegó nada. No te obliga a decidir ni te pone una lista: te hace una propuesta,
 * la que más se le plantea a gente como tú, con un dato real. Dices sí o sigues igual.
 * Quien quiere hacer otra cosa puede abrir la lista completa.
 */
export function AnioTranquilo({ vista, cargando, error, onElegir, onSalir, sinNovedad }: {
  vista: Vista;
  sinNovedad?: SinNovedad | null;
  cargando: boolean;
  error: string | null;
  onElegir: (e: Eleccion) => void;
  onSalir?: () => void;
}) {
  const [verTodo, setVerTodo] = useState(false);
  const p = vista.pendiente!;
  const s = p.sugerencia;
  const anio = Math.min(vista.anio + 1, vista.anios);
  const otras = p.opciones.filter((o) => o.opcion !== "seguir" && o.opcion !== s?.decision);
  // lo último que se apretó, para decir qué se está calculando: en prod la siguiente carta tarda varios segundos
  const [elegida, setElegida] = useState<string | null>(null);
  const elegir = (opcion: string) => {
    setElegida(opcion);
    onElegir({ decision: p.decision, opcion });
  };
  const esperando = cargando && elegida !== null;
  const ultimo = anio >= vista.anios;
  // con "seguir", el botón ya dice a qué año pasas: aquí va lo que se está calculando
  const frases = elegida === "seguir"
    ? ["Viviendo tu año…", `Simulando tus ${GEMELOS} mundos…`, "Ya casi…"]
    : [`Simulando «${p.opciones.find((o) => o.opcion === elegida)?.nombre ?? s?.nombre ?? "eso"}»…`, `Simulando tus ${GEMELOS} mundos…`, "Ya casi…"];
  // lo que ya pasó este año sin que lo eligieras (una recesión, un ascenso): no es un año "sin sobresaltos"
  const eventos = (vista.anio_en_curso?.eventos ?? []).filter((e) => !e.rutina);

  return (
    <Screen gap={16}>
      <ScreenHeader left={<Pill style={{ whiteSpace: "nowrap" }}>Año {anio} · {vista.estado.edad} años</Pill>} right={onSalir && <Salir onSalir={onSalir} />} />
      <FranjaSinNovedad s={sinNovedad} />
      <Stack gap={8} className="vd-subir">
        <Meta>{eventos.length > 0 ? "Sin propuestas" : "Un año tranquilo"}</Meta>
        <Heading level={2} as="h1">
          {eventos.length > 0 ? "No te llegó ninguna propuesta." : "Un año sin sobresaltos."}
        </Heading>
        <Text>
          {eventos.length > 0
            ? "Pero el año trae esto. Puedes seguir igual, o mirar algo por tu cuenta."
            : "No te llegó ninguna propuesta. Puedes seguir igual, o mirar algo por tu cuenta."}
        </Text>
      </Stack>

      {eventos.length > 0 && (
        <Stack gap={8} className="vd-subir">
          {eventos.map((e, i) => (
            <Noticia key={i} titulo={e.nombre} texto={e.texto} lado={e.directo ? undefined : `${porciento(e.prob)} al año`} />
          ))}
        </Stack>
      )}

      {/* La sugerencia es opcional: va como una idea suave, no como la acción principal */}
      {s && (
        <div className="jg-propuesta vd-subir">
          <span className="jg-propuesta-eti">Si quieres, una idea</span>
          <b>{s.nombre}</b>
          <span className="jg-propuesta-dato">{s.pregunta}</span>
          {/* solo la estadística de qué tan seguido la gente lo hace; las cifras de papers van dentro de la decisión */}
          {s.dato && s.es_frecuencia && (
            <span className="jg-propuesta-dato">
              <small>
                {s.dato} · {s.fuente}
              </small>
            </span>
          )}
          <button type="button" className="ob-link jg-propuesta-ver" onClick={() => elegir(s.decision)} disabled={cargando}>
            Ver cómo te iría
          </button>
        </div>
      )}

      {verTodo && (
        <div className="jg-tranquilo vd-subir" role="list" aria-label="Otras cosas que puedes hacer este año">
          {otras.map((o) => (
            <button key={o.opcion} type="button" role="listitem" className="jg-tranquilo-op" disabled={cargando} onClick={() => elegir(o.opcion)}>
              {/* el mismo dibujo que esa duda tiene en la lista de dudas */}
              <span className="jg-tranquilo-arte" aria-hidden="true">
                <DecisionArt kind={arteDuda(o.opcion, "")} llenar />
              </span>
              <span className="jg-tranquilo-texto">
                <b>{o.nombre}</b>
                <span>{o.detalle}</span>
              </span>
            </button>
          ))}
        </div>
      )}

      {/* si el simulador no respondió, se repite lo mismo que apretaste: la partida no se movió */}
      {error && <ErrorCaja error={error} onReintentar={elegida ? () => elegir(elegida) : undefined} />}
      <ScreenFooter>
        {esperando && <Cargando frases={frases} cada={3000} />}
        <Button onClick={() => elegir("seguir")} disabled={cargando}>
          {esperando && elegida === "seguir" ? (ultimo ? "Cerrando tu último año…" : `Pasando al año ${anio + 1}…`) : "Seguir igual este año"}
        </Button>
        {!verTodo && otras.length > 0 && !esperando && (
          <button type="button" className="ob-link" onClick={() => setVerTodo(true)}>
            Ver más cosas que podrías hacer
          </button>
        )}
      </ScreenFooter>
    </Screen>
  );
}
