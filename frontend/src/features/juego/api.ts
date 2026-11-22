import { http } from "@/shared/lib/http";
import type { Catalogo, Duda, EnJuego, MundoDetalle, Narrado, ParametrosComparar, Partida, Perfil, PerfilLeido, PesoCv, Vista } from "./types";

export const GEMELOS = 100;

export const getCatalogo = () => http<Catalogo>("/api/juego/catalogo");

export const getDudas = (perfil: Perfil) =>
  http<Duda[]>("/api/juego/dudas", { method: "POST", body: JSON.stringify({ perfil }) });

export const getVista = (partida: Partida, parametros: ParametrosComparar = {}) =>
  http<Vista>("/api/juego/partida", {
    method: "POST",
    body: JSON.stringify({ ...partida, gemelos: GEMELOS, parametros, edad_final: partida.perfil.edad_final ?? null }),
  });

/** Un mundo de la comparación de la decisión pendiente, con lo que te pasa en él con cada opción. */
export const getMundo = (partida: Partida, mundo: number, parametros: ParametrosComparar = {}) =>
  http<MundoDetalle>("/api/juego/mundo", {
    method: "POST",
    body: JSON.stringify({ ...partida, gemelos: GEMELOS, parametros, mundo, edad_final: partida.perfil.edad_final ?? null }),
  });

/** Lo que vale cada línea del CV en la duda: la misma comparación de la carta, sin cada dato. */
export const getPesoCv = (perfil: Perfil, duda: string, semilla: number) =>
  http<PesoCv>("/api/juego/peso-cv", {
    method: "POST",
    body: JSON.stringify({ perfil, duda, semilla, gemelos: GEMELOS, edad_final: perfil.edad_final ?? null }),
  });

/**
 * De las dudas que sugiere el CV, cuánto se juega en cada una y cuál es la que más. Con la semilla y la edad
 * final de la partida que viene, el servidor deja calculada la primera carta de la duda que se elija.
 */
export const getEnJuego = (perfil: Perfil, dudas: string[], semilla: number) =>
  http<EnJuego>("/api/juego/dudas-en-juego", {
    method: "POST",
    body: JSON.stringify({ perfil, dudas, semilla, gemelos: GEMELOS, edad_final: perfil.edad_final ?? null }),
  });

/** Textos de la partida contados por Claude. Sin gemelos: el servidor solo rejuega tu vida. */
export const getNarracion = (
  partida: Partida,
  que: "pendiente" | "historia" | "mundo",
  opciones: { mundo?: number; parametros?: ParametrosComparar; signal?: AbortSignal } = {},
) =>
  http<{ items: Narrado[] }>("/api/juego/narrar", {
    method: "POST",
    body: JSON.stringify({ ...partida, gemelos: 0, que, mundo: opciones.mundo, parametros: opciones.parametros ?? {} }),
    signal: opciones.signal,
  });

/** El prompt que la persona pega en su propio Claude para que le arme su perfil. */
export const getPrompt = () => http<{ prompt: string }>("/api/juego/prompt");

/** Error de la API con su código, para distinguir "Claude no está disponible" (503) de "texto inválido" (422). */
export class ErrorApi extends Error {
  constructor(
    public status: number,
    public detalle: string,
  ) {
    super(detalle);
  }
}

/** Sin respuesta del servidor (caído, sin red, CORS): el navegador dice "Failed to fetch" o "Load failed". */
const SIN_RESPUESTA = "Puede que esté caído o que se haya cortado tu conexión. Prueba de nuevo en un rato.";

export function comoErrorApi(e: unknown): ErrorApi {
  if (e instanceof ErrorApi) return e;
  const m = /^(\d{3}): ([\s\S]*)$/.exec(e instanceof Error ? e.message : String(e));
  if (!m) return new ErrorApi(0, e instanceof TypeError ? SIN_RESPUESTA : e instanceof Error ? e.message : String(e));
  let detalle = m[2];
  try {
    const d = (JSON.parse(m[2]) as { detail?: unknown }).detail;
    if (typeof d === "string") detalle = d;
    else if (Array.isArray(d)) detalle = d.map((x: { msg?: string }) => x.msg ?? "").filter(Boolean).join(" ");
  } catch {
    /* el cuerpo no era JSON: se muestra tal cual */
  }
  return new ErrorApi(Number(m[1]), detalle);
}

/** El error en palabras de persona, para poner después de "No pudimos hablar con el simulador.". */
export function textoError(e: unknown): string {
  const err = comoErrorApi(e);
  if (err.status === 0) return err.detalle || SIN_RESPUESTA;
  if (err.status >= 500) return `Algo le falló al calcular (error ${err.status}). Prueba de nuevo.`;
  return err.detalle;
}

/** Lee el documento que armó el Claude de la persona (al tiro). Si es texto libre, Claude lo lee (cerca de medio minuto). */
/** Claude lee un texto, o un PDF en base64 (el CV o el "Guardar como PDF" de LinkedIn), y llena el perfil. */
export async function leerPerfil(entrada: string | { pdf: string }): Promise<PerfilLeido> {
  const cuerpo = typeof entrada === "string" ? { texto: entrada } : entrada;
  try {
    return await http<PerfilLeido>("/api/juego/perfil", { method: "POST", body: JSON.stringify(cuerpo) });
  } catch (e) {
    throw comoErrorApi(e);
  }
}

