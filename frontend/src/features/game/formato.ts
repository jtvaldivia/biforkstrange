import type { IndicatorValues } from "@/shared/ui";
import type { Ficha } from "./types";

export const plata = (x: number) => {
  const s = x < 0 ? "−" : "";
  const a = Math.abs(x);
  return a >= 1e6 ? `${s}$${(a / 1e6).toFixed(1).replace(".", ",")} M` : `${s}$${Math.round(a / 1e3)} mil`;
};

const tope = (n: number) => Math.round(Math.min(100, Math.max(0, n)));
const NIVELES = ["junior", "semi senior", "senior", "jefatura", "gerencia"];

/**
 * Traduce la ficha del motor a los cuatro indicadores del kit (0 a 100).
 * Es una escala de presentación: el motor trabaja en pesos, energía y ánimo.
 */
export function indicadores(f: Ficha, sueldo0: number): IndicatorValues {
  const colchon = f.ahorros > 0 ? 100 * (1 - Math.exp(-f.ahorros / (24 * f.gasto_mes))) : 0; // 2 años de gastos ≈ 63
  const ingreso = f.ingreso_mes > 0 ? 50 + 40 * Math.log2(f.ingreso_mes / sueldo0) : 0;
  const conEmpleo = f.situacion === "con empleo";
  return {
    dinero: tope(0.5 * colchon + 0.5 * ingreso - (f.ahorros < 0 ? 15 : 0)),
    carrera: tope(
      conEmpleo ? 25 + 14 * Math.max(0, NIVELES.indexOf(f.nivel)) + 30 * Math.log2(Math.max(f.sueldo, 1) / sueldo0) : f.situacion === "emprendiendo" ? 45 : 12,
    ),
    bienestar: tope((f.energia + f.animo) / 2),
    vida: tope(0.55 * f.social + (f.pareja ? 20 : 0) + 8 * Math.min(f.hijos, 2)),
  };
}

export type Atributo = { clave: string; nombre: string; color: "dinero" | "carrera" | "bienestar" | "vida"; valor: number };

/** Los ocho atributos del gemelo, de 0 a 100, en el orden en que se muestran. */
export function atributos(f: Ficha): Atributo[] {
  return [
    { clave: "energia", nombre: "Energía", color: "bienestar", valor: tope(f.energia) },
    { clave: "animo", nombre: "Ánimo", color: "bienestar", valor: tope(f.animo) },
    { clave: "salud", nombre: "Salud", color: "bienestar", valor: tope(f.salud) },
    { clave: "social", nombre: "Tu gente", color: "vida", valor: tope(f.social) },
    { clave: "habilidad", nombre: "Habilidades", color: "carrera", valor: tope(f.habilidad) },
    { clave: "reputacion", nombre: "Reputación", color: "carrera", valor: tope(f.reputacion) },
    { clave: "contactos", nombre: "Contactos", color: "carrera", valor: tope(f.contactos / 1.5) },   // 150 contactos = 100
    { clave: "colchon", nombre: "Colchón", color: "dinero", valor: tope((100 * f.colchon_meses) / 24) }, // 2 años de gastos = 100
  ];
}

export const cargo = (f: Ficha) => f.ocupacion.split(" (")[0];

export function resumenFicha(f: Ficha): string {
  const trabajo = f.situacion === "con empleo" ? `${cargo(f)} · ${f.nivel} en ${f.empresa} · ${plata(f.sueldo)} al mes` : `Estás ${f.situacion}`;
  return `${trabajo}. Ahorros ${plata(f.ahorros)}. ${f.pareja ? "Con pareja" : "Sin pareja"}, ${f.hijos} ${f.hijos === 1 ? "hijo" : "hijos"}.`;
}

export const nivelIA = (p: number) => (p >= 0.85 ? "muy alta" : p >= 0.65 ? "alta" : p >= 0.35 ? "media" : "baja");

/** Ilustración del kit que mejor calza con cada decisión. */
export function arte(decision: string): "viaje" | "consultora" | "invertir" | "magister" {
  const clave = decision.split(":")[0];
  if (["sabatico", "bajar_ritmo", "tener_hijo", "cuidarte", "tu_gente"].includes(clave)) return "viaje";
  if (["magister", "reconvertir", "capacitarte"].includes(clave)) return "magister";
  if (["emprender", "pedir_aumento", "buscar_pega", "pituto", "networking", "bajar_pretensiones"].includes(clave)) return "invertir";
  return "consultora";
}
