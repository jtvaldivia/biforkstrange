import { http } from "@/shared/lib/http";
import type { EscenarioIA, Partida, Perfil } from "./types";

/** El servidor no guarda la partida: se reconstruye con el perfil, la semilla y las decisiones. */
export const pedirTurno = (perfil: Perfil, decisiones: string[], seed: number, escenario_ia: EscenarioIA) =>
  http<Partida>("/api/juego/turno", { method: "POST", body: JSON.stringify({ perfil, decisiones, seed, escenario_ia }) });
