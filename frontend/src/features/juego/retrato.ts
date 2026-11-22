import type { Perfil, PerfilLeido } from "./types";

/**
 * El retrato que escribió Claude al leer el CV ("lo que tu gemelo sabe de ti"), guardado para la tarjeta
 * que se comparte al final. Se guarda con la edad, sexo y estudios que leyó: si la partida es de otro
 * perfil, no se usa.
 */
const CLAVE = "gemelo-laboral:retrato:v1";

type Guardado = { retrato: string; edad: number; sexo: string; edu: string };

export function guardarRetrato(leido: PerfilLeido) {
  try {
    if (!leido.retrato) window.localStorage.removeItem(CLAVE);
    else {
      const g: Guardado = { retrato: leido.retrato, edad: leido.perfil.edad, sexo: leido.perfil.sexo, edu: leido.perfil.edu };
      window.localStorage.setItem(CLAVE, JSON.stringify(g));
    }
  } catch {
    /* sin almacenamiento: la tarjeta sale sin retrato */
  }
}

export function leerRetrato(perfil: Perfil | undefined): string | null {
  if (!perfil) return null;
  try {
    const g = JSON.parse(window.localStorage.getItem(CLAVE) ?? "null") as Guardado | null;
    if (!g || typeof g.retrato !== "string") return null;
    return g.edad === perfil.edad && g.sexo === perfil.sexo && g.edu === perfil.edu ? g.retrato : null;
  } catch {
    return null;
  }
}
