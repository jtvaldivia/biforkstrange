import { http } from "@/shared/lib/http";
import { guardarRetrato } from "./retrato";
import type { Catalogo, Duda, EnJuego, MundoDetalle, ParametrosComparar, Partida, Perfil, PerfilLeido, PesoCv, Vista } from "./types";

export const GEMELOS = 100;

export const getCatalogo = () => http<Catalogo>("/api/juego/catalogo");

export const getDudas = (perfil: Perfil) =>
  http<Duda[]>("/api/juego/dudas", { method: "POST", body: JSON.stringify({ perfil }) });

export const getVista = (partida: Partida, parametros: ParametrosComparar = {}) =>
  http<Vista>("/api/juego/partida", {
    method: "POST",
    body: JSON.stringify({ ...partida, gemelos: GEMELOS, parametros }),
  });

/** Un mundo de la comparación de la decisión pendiente, con lo que te pasa en él con cada opción. */
export const getMundo = (partida: Partida, mundo: number, parametros: ParametrosComparar = {}) =>
  http<MundoDetalle>("/api/juego/mundo", {
    method: "POST",
    body: JSON.stringify({ ...partida, gemelos: GEMELOS, parametros, mundo }),
  });

/** Lo que vale cada línea del CV en la duda: la misma comparación de la carta, sin cada dato. */
export const getPesoCv = (perfil: Perfil, duda: string, semilla: number) =>
  http<PesoCv>("/api/juego/peso-cv", {
    method: "POST",
    body: JSON.stringify({ perfil, duda, semilla, gemelos: GEMELOS }),
  });

/** De las dudas que sugiere el CV, cuánto se juega en cada una y cuál es la que más. */
export const getEnJuego = (perfil: Perfil, dudas: string[]) =>
  http<EnJuego>("/api/juego/dudas-en-juego", {
    method: "POST",
    body: JSON.stringify({ perfil, dudas, gemelos: GEMELOS }),
  });

export const TEXTO_MAX = 60_000;

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

function comoErrorApi(e: unknown): ErrorApi {
  const m = /^(\d{3}): ([\s\S]*)$/.exec(e instanceof Error ? e.message : String(e));
  if (!m) return new ErrorApi(0, e instanceof Error ? e.message : String(e));
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

/** Lee el documento que armó el Claude de la persona (al tiro). Si es texto libre, Claude lo lee (cerca de medio minuto). */
/** Claude lee un texto, o un PDF en base64 (el CV o el "Guardar como PDF" de LinkedIn), y llena el perfil. */
export async function leerPerfil(entrada: string | { pdf: string }): Promise<PerfilLeido> {
  const cuerpo = typeof entrada === "string" ? { texto: entrada } : entrada;
  try {
    const leido = await http<PerfilLeido>("/api/juego/perfil", { method: "POST", body: JSON.stringify(cuerpo) });
    guardarRetrato(leido); // para la tarjeta que se comparte al final
    return leido;
  } catch (e) {
    throw comoErrorApi(e);
  }
}

