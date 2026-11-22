/** Cómo se dicen las cosas en pantalla. Aquí no se calcula ningún número: solo se les da formato. */
import type { DecisionArtKind } from "@/shared/ui";
import type { Calidad, Estado } from "./types";

const numero = (n: number, decimales = 0) =>
  n.toLocaleString("es-CL", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });

/** Plata completa: $1.688.202 */
export const pesos = (n: number) => `$${numero(Math.round(n))}`;

/** Plata corta para espacios chicos: $1,69 M · $850 mil */
export function plata(n: number): string {
  if (n >= 1_000_000) return `$${numero(n / 1_000_000, n >= 10_000_000 ? 1 : 2)} M`;
  if (n >= 1_000) return `$${numero(Math.round(n / 1_000))} mil`;
  return pesos(n);
}

/** Proporción dicha en simple: "1 de cada 3", "casi todos". */
export function deCada(p: number): string {
  if (p <= 0) return "ninguno";
  if (p >= 1) return "todos";
  if (p < 0.05) return "menos de 1 de cada 10";
  if (p > 0.95) return "casi todos";
  let mejor = { n: 1, d: 2, error: Infinity };
  for (const d of [2, 3, 4, 5, 10]) {
    for (let n = 1; n < d; n++) {
      const error = Math.abs(n / d - p);
      if (error < mejor.error - 1e-9) mejor = { n, d, error };
    }
  }
  return `${mejor.n} de cada ${mejor.d}`;
}

/** Siempre sobre 10, para comparar opciones entre sí: "7 de cada 10". */
export const deCada10 = (p: number) => `${Math.round(p * 10)} de cada 10`;

export const minuscula = (s: string) => s.charAt(0).toLowerCase() + s.slice(1);

export const CALIDAD: Record<Calidad, { nombre: string; explica: string }> = {
  dato: { nombre: "Dato", explica: "Viene de una medición." },
  mixto: { nombre: "Mixto", explica: "Parte medición, parte supuesto." },
  sintetico: { nombre: "Sintético", explica: "Sorteado a partir de datos reales del rubro y tamaño, no medido para esta empresa." },
  supuesto: { nombre: "Supuesto", explica: "Es una regla nuestra, sin medición detrás." },
};

export const EDUCACION: Record<string, string> = {
  media: "Media",
  tecnica: "Técnica",
  universitaria: "Universitaria",
  postgrado: "Postgrado",
};

export const TIPO_EMPLEADOR: Record<string, string> = {
  grande: "Empresa grande",
  pyme: "Pyme",
  startup: "Startup",
  publico: "Estado",
  extranjero: "Empresa de afuera",
};

const SITUACION: Record<string, string> = {
  estudiando: "Estudiando",
  buscando: "Sin trabajo, buscando",
  empleado: "Con trabajo",
  independiente: "Por tu cuenta",
  fundador: "Con tu empresa",
  inactivo: "Sin trabajar",
};

export const situacion = (estado: string) => SITUACION[estado] ?? estado;

export const sinSueldo = (e: Estado) => e.sueldo <= 0;

/** "Semi senior · $1.688.202" o, sin sueldo, "Sin trabajo, buscando". */
export const cargoYSueldo = (e: Estado, corto = false) =>
  sinSueldo(e) ? situacion(e.estado) : `${e.cargo} · ${corto ? plata(e.sueldo) : pesos(e.sueldo)}`;

export function riesgoEnPalabras(r: number): string {
  if (r <= 3) return "prefiero lo seguro";
  if (r >= 7) return "me la juego";
  return "depende";
}

const ARTE: Record<string, DecisionArtKind> = {
  estudios: "magister",
  trabajo: "consultora",
  emprender: "invertir",
  dinero: "invertir",
  lugar: "viaje",
  salud: "viaje",
};

/** El kit trae cuatro dibujos: se elige por la categoría de la decisión. */
export const arte = (categoria: string): DecisionArtKind => ARTE[categoria] ?? "consultora";

/** Diferencia con signo: +$88 mil, −$329 mil. */
export const conSigno = (n: number) => `${n < 0 ? "−" : "+"}${plata(Math.abs(n))}`;

/** "Año 3" o, si la ronda ocupó varios, "Años 1 a 5". Los años se cuentan por edad desde la edad inicial. */
export function aniosDe(edad: number, edadFin: number | undefined, edadInicial: number): string {
  const desde = edad - edadInicial + 1;
  const hasta = edadFin === undefined ? desde : Math.max(desde, edadFin - edadInicial);
  return hasta > desde ? `Años ${desde} a ${hasta}` : `Año ${desde}`;
}
