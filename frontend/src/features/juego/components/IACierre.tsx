import { Meta, Stack, Text } from "@/shared/ui";
import { plata } from "../textos";
import type { CierreIA, Ritmo } from "../types";

export const NOMBRE_RITMO: Record<Ritmo, string> = { lento: "IA lenta", medio: "IA a ritmo medio", rapido: "IA rápida" };
const ORDEN: Ritmo[] = ["lento", "medio", "rapido"];

/** El cierre: el ritmo de la IA de tu mundo, cómo te habría ido con los otros y quién dice qué del futuro. */
export function IACierre({ ia, elegida, nombreElegida }: { ia: CierreIA; elegida?: string; nombreElegida?: string }) {
  const tuyo = ia.ritmos[ia.ritmo];
  const ritmos = ia.por_ritmo ? ORDEN.filter((r) => ia.por_ritmo!.ritmos[r]) : [];
  return (
    <Stack as="section" gap={10} className="jg-ia-cierre">
      <Meta>La IA en tu mundo</Meta>
      <Text>
        Viviste un mundo de <b>{NOMBRE_RITMO[ia.ritmo]}</b>. {tuyo.que_es}
      </Text>
      {elegida && ritmos.length > 1 && (
        <div className="jg-escenarios" role="list" aria-label="Sueldo típico al final según el ritmo de la IA">
          {ritmos.map((r) => (
            <span role="listitem" key={r} data-fuerte={r === ia.ritmo}>
              Con {NOMBRE_RITMO[r]}, «{nombreElegida}» terminaba en
              <b>{plata(ia.por_ritmo!.ritmos[r]!.sueldo_p50[elegida] ?? 0)}</b>
            </span>
          ))}
        </div>
      )}
      <Meta>Quién dice qué</Meta>
      <Stack gap={8}>
        {ia.voces.map((v) => (
          <div className="jg-ia-voz" key={v.quien}>
            <Text size="sm">
              <b>{v.quien}</b> <i className="jg-chico">({v.tipo})</i>: {v.dice}{" "}
              <a href={v.url} target="_blank" rel="noreferrer" className="jg-chico">Fuente</a>
            </Text>
          </div>
        ))}
      </Stack>
      <Text size="sm" className="jg-chico">{ia.fuera_del_juego}</Text>
    </Stack>
  );
}
