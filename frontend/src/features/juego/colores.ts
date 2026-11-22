/**
 * Los colores de opción: SOLO dicen cuál opción es («Quedarte» naranja, «Irte» verde…), igual en la carta, el
 * cierre y la imagen que se comparte. No dicen si algo es mejor o peor: eso va en sol (ganan más) y tinta (ganan
 * menos), con --jg-mas y --jg-menos de juego.css.
 *
 * Cada color es una variable del kit (vida.css) con su valor del tema claro al lado: la imagen exportada usa el
 * claro fijo, para verse igual con tema claro u oscuro. Si cambias un color en vida.css, cámbialo aquí también.
 */
const BASE = { variable: "var(--bienestar)", claro: "#F08A1C" };
const OTRAS = [
  { variable: "var(--dinero)", claro: "#17794B" },
  { variable: "var(--vida)", claro: "#D6336C" },
  { variable: "var(--violeta)", claro: "#7C5CD6" },
  { variable: "var(--turquesa)", claro: "#0E9AA7" },
];
/** Los mundos empatados (da lo mismo qué elijas). */
export const COLOR_EMPATE = { variable: "var(--apagado)", claro: "#B9BAC0" };

/** Un color por opción: la base siempre naranja; las demás en este orden. Sin azul: es el de la interfaz y "tú, ahora". */
export function coloresDeOpciones(
  opciones: { opcion: string; es_base?: boolean }[],
  tema: "variable" | "claro" = "variable",
): Record<string, string> {
  const salida: Record<string, string> = {};
  let i = 0;
  for (const o of opciones) salida[o.opcion] = (o.es_base ? BASE : OTRAS[i++ % OTRAS.length])[tema];
  return salida;
}
