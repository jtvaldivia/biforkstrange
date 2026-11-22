import { useState, type ReactNode } from "react";
import { Button, Heading, Meta, Slider, Stack, Text } from "@/shared/ui";
import { MARGEN, acerto, anotarApuesta, leerIntuicion, type Intuicion } from "../intuicion";
import type { OpcionComparada } from "../types";
import "../demo.css";

type Resultado = { nombre: string; apuesta: number; real: number; puntaje: Intuicion };

/** Qué tan cerca quedó la apuesta, en una frase. */
function fraseDe(r: Resultado): string {
  const d = Math.abs(r.apuesta - r.real);
  if (d === 0) return "¡Exacto! Le achuntaste al mundo justo.";
  if (d <= MARGEN) return `Le achuntaste: quedaste a ${d} ${d === 1 ? "mundo" : "mundos"}.`;
  return r.apuesta > r.real
    ? `Le tenías más fe a «${r.nombre}» que los mundos: te pasaste por ${d}.`
    : `Los mundos le tienen más fe a «${r.nombre}» que tú: te quedaste corto por ${d}.`;
}

/**
 * "Apuesta antes de mirar": antes de mostrar los puntos de los mundos, la persona apuesta en cuántos gana
 * una opción. Al ver, su apuesta queda al lado de lo que salió y se suma a su puntaje de intuición.
 * Los mundos (`children`) solo aparecen después de ver o de saltarse la apuesta.
 */
export function ApuestaAntesDeMirar({
  opcion, ganadores, gemelos, color, revelado, onVer, creencia, children,
}: {
  /** La opción sobre la que se apuesta: la que está tocada o, si no hay, la que no es la base. */
  opcion: OpcionComparada;
  ganadores: (string | null)[];
  gemelos: number;
  color: string;
  revelado: boolean;
  onVer: () => void;
  /** Lo que se cree y lo que dice el dato, si la decisión lo trae: se muestra cuando la intuición falla. */
  creencia?: string | null;
  children: ReactNode;
}) {
  const [valor, setValor] = useState(Math.round(gemelos / 2));
  const [resultado, setResultado] = useState<Resultado | null>(null);

  if (!revelado) {
    const ver = () => {
      const real = ganadores.filter((g) => g === opcion.opcion).length;
      setResultado({ nombre: opcion.nombre, apuesta: valor, real, puntaje: anotarApuesta(acerto(valor, real)) });
      onVer();
    };
    return (
      <section className="jg-seccion jg-apuesta" aria-label="Apuesta antes de mirar">
        <Stack gap={4}>
          <Meta>Antes de mirar</Meta>
          <Heading level={3} as="h2">
            ¿En cuántos de {gemelos} mundos gana «{opcion.nombre}»?
          </Heading>
          <Text size="sm">
            Los {gemelos} mundos ya están simulados. Antes de verlos, apuesta con tu intuición: «gana» es terminar ganando más que con cualquier otra opción.
          </Text>
        </Stack>
        <Slider label="Tu apuesta" value={valor} onChange={setValor} min={0} max={gemelos} color={color} display={`${valor} de ${gemelos} mundos`} />
        <div className="jg-apuesta-acciones">
          <Button onClick={ver}>Ver</Button>
          <button type="button" className="jg-ayuda" onClick={onVer}>
            Saltar y ver los mundos
          </button>
        </div>
      </section>
    );
  }

  return (
    <>
      {resultado && (
        <section className="jg-seccion jg-apuesta-revela" aria-live="polite">
          <Meta>Tu intuición contra los mundos</Meta>
          <div className="jg-apuesta-barras">
            <span className="jg-chico">Tu apuesta</span>
            <span className="jg-apuesta-pista">
              <i data-tipo="apuesta" style={{ width: `${(resultado.apuesta / gemelos) * 100}%` }} />
            </span>
            <b>{resultado.apuesta}</b>
            <span className="jg-chico">Lo que salió</span>
            <span className="jg-apuesta-pista">
              <i data-tipo="real" style={{ width: `${(resultado.real / gemelos) * 100}%`, background: color }} />
            </span>
            <b>{resultado.real}</b>
          </div>
          <Text size="sm">
            <strong>{fraseDe(resultado)}</strong> «{resultado.nombre}» gana en {resultado.real} de {gemelos} mundos.
          </Text>
          {!acerto(resultado.apuesta, resultado.real) && creencia && (
            <Text size="sm">
              <strong>Lo que se cree y lo que dice el dato:</strong> {creencia}
            </Text>
          )}
          <span className="jg-chico">
            Tu intuición: le achuntaste {resultado.puntaje.aciertos} de {resultado.puntaje.total} {resultado.puntaje.total === 1 ? "vez" : "veces"} (a {MARGEN} mundos o menos).
          </span>
        </section>
      )}
      {children}
    </>
  );
}

/** En el cierre: el puntaje de intuición acumulado. No aparece si nunca apostó. */
export function IntuicionResumen() {
  const [puntaje] = useState(leerIntuicion);
  if (puntaje.total === 0) return null;
  return (
    <section className="jg-seccion jg-apuesta-revela">
      <Meta>Tu intuición</Meta>
      <Text>
        <strong>
          Le achuntaste a tu intuición {puntaje.aciertos} de {puntaje.total} {puntaje.total === 1 ? "vez" : "veces"}.
        </strong>
      </Text>
      <span className="jg-chico">
        Cuenta las apuestas antes de mirar los mundos que quedaron a {MARGEN} mundos o menos de lo que salió, en todas tus partidas en este navegador.
      </span>
    </section>
  );
}
