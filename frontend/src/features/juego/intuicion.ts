/**
 * El puntaje de intuición: cuántas veces tu apuesta antes de mirar quedó cerca de lo que dieron los mundos.
 * Se acumula en este navegador (todas las partidas). Sin almacenamiento, el juego sigue igual y no se cuenta.
 */

const CLAVE = "gemelo-laboral:intuicion:v1";

/** Le achuntas si tu apuesta queda a esta distancia (en mundos) o menos de lo que salió. */
export const MARGEN = 10;

export type Intuicion = { aciertos: number; total: number };

export function leerIntuicion(): Intuicion {
  try {
    const g = JSON.parse(window.localStorage.getItem(CLAVE) ?? "null") as Partial<Intuicion> | null;
    const aciertos = Number(g?.aciertos);
    const total = Number(g?.total);
    if (!Number.isFinite(aciertos) || !Number.isFinite(total) || total < aciertos || aciertos < 0) return { aciertos: 0, total: 0 };
    return { aciertos, total };
  } catch {
    return { aciertos: 0, total: 0 };
  }
}

/** Suma una apuesta y devuelve el puntaje nuevo. */
export function anotarApuesta(acierto: boolean): Intuicion {
  const antes = leerIntuicion();
  const nuevo = { aciertos: antes.aciertos + (acierto ? 1 : 0), total: antes.total + 1 };
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify(nuevo));
  } catch {
    /* modo privado o sin cuota: el puntaje no se guarda */
  }
  return nuevo;
}

export const acerto = (apuesta: number, real: number) => Math.abs(apuesta - real) <= MARGEN;
