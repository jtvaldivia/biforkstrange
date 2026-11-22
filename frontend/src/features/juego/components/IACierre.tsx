import { Meta, Stack, Text } from "@/shared/ui";
import { plata } from "../textos";
import type { CierreIA, Ritmo } from "../types";

export const NOMBRE_RITMO: Record<Ritmo, string> = { lento: "IA lenta", medio: "IA a ritmo medio", rapido: "IA rápida" };
const ORDEN: Ritmo[] = ["lento", "medio", "rapido"];

/** El cierre: el ritmo de la IA de tu mundo, cómo te habría ido con los otros y quién dice qué del futuro. */
export function IACierre({ ia, elegida, nombreElegida }: { ia: CierreIA; elegida?: string; nombreElegida?: string }) {
  const tuyo = ia.ritmos[ia.ritmo];
  const pr = ia.por_ritmo?.ritmos ?? {};
  const total = ORDEN.reduce((n, r) => n + (pr[r]?.mundos ?? 0), 0);
  // un ritmo con pocos mundos da una mediana que cambia mucho de una partida a otra: no se muestra
  const ritmos = ORDEN.filter((r) => (pr[r]?.mundos ?? 0) >= (ia.min_mundos ?? 1));
  const tipo = ia.tipo && ia.tipos ? ia.tipos[ia.tipo] : null;
  return (
    <Stack as="section" gap={10} className="jg-ia-cierre">
      <Meta>La IA en tu mundo</Meta>
      <Text>
        Viviste un mundo de <b>{NOMBRE_RITMO[ia.ritmo]}</b>. {tuyo.que_es}
      </Text>
      {ia.pesos && (
        <Text size="sm" className="jg-chico">
          El ritmo de cada mundo se sorteó con lo que pronostican economistas y superforecasters para 2030:{" "}
          {ORDEN.map((r) => `${NOMBRE_RITMO[r]} ${Math.round(ia.pesos![r] * 100)}%`).join(", ")}. Es un pronóstico, no una
          frecuencia.{" "}
          <a href={tuyo.url} target="_blank" rel="noreferrer">Fuente</a>
        </Text>
      )}
      {tipo && (
        <Text size="sm">
          Tu cargo al final: {tipo.nombre}, según la OIT.
        </Text>
      )}
      {elegida && ritmos.length > 1 && (
        <div className="jg-escenarios" role="list" aria-label="Sueldo típico al final según el ritmo de la IA">
          {ritmos.map((r) => (
            <span role="listitem" key={r} data-fuerte={r === ia.ritmo}>
              En los {pr[r]!.mundos} de {total} mundos con {NOMBRE_RITMO[r]}, «{nombreElegida}» terminaba en
              <b>{plata(pr[r]!.sueldo_p50[elegida] ?? 0)}</b>
            </span>
          ))}
        </div>
      )}
      <details>
        <summary className="jg-ayuda">Quién dice qué de la IA ({ia.voces.length} fuentes)</summary>
        <Stack gap={8} className="jg-vivido">
          {ia.voces.map((v) => (
            <div className="jg-ia-voz" key={v.quien}>
              <Text size="sm">
                <b>{v.quien}</b> <i className="jg-chico">({v.tipo})</i>: {v.dice}{" "}
                <a href={v.url} target="_blank" rel="noreferrer" className="jg-chico">Fuente</a>
              </Text>
            </div>
          ))}
          <Text size="sm" className="jg-chico">{ia.fuera_del_juego}</Text>
        </Stack>
      </details>
    </Stack>
  );
}
