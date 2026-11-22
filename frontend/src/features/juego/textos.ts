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

/** Sobre 100, como se cuentan los mundos: "63 de 100". Lo que pasa muy rara vez no se redondea a cero. */
export const deCien = (p: number) => (p > 0 && p < 0.005 ? "menos de 1 de 100" : `${Math.round(p * 100)} de 100`);

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
/** "Analista de riesgo en BancoEstado · $1.400.000": el nombre del cargo y la empresa si se saben; si no, el nivel. */
export const cargoYSueldo = (e: Estado, corto = false) =>
  sinSueldo(e)
    ? situacion(e.estado)
    : `${e.rol || e.cargo}${!corto && e.empresa ? ` en ${e.empresa}` : ""} · ${corto ? plata(e.sueldo) : pesos(e.sueldo)}`;

export function riesgoEnPalabras(r: number): string {
  if (r <= 3) return "prefiero lo seguro";
  if (r >= 7) return "me la juego";
  return "depende";
}

const ARTE_CATEGORIA: Record<string, DecisionArtKind> = {
  estudios: "magister",
  trabajo: "consultora",
  emprender: "cohete",
  dinero: "chanchito",
  lugar: "viaje",
  salud: "corazon",
  familia: "casa",
};

const ARTE_DUDA: Record<string, DecisionArtKind> = {
  oferta_externa: "puerta",
  renunciar: "puerta",
  independizarse: "puerta",
  cambiar_de_rubro: "puerta",
  cambiar_de_ocupacion: "puerta",
  unirse_a_startup: "cohete",
  emprender: "invertir",
  seguir_con_tu_empresa: "invertir",
  pedir_aumento: "subir",
  jefatura: "subir",
  aprender_ia: "laptop",
  bootcamp: "laptop",
  remoto_para_afuera: "laptop",
  buscar_estando_empleado: "lupa",
  cesantia: "lupa",
  invertir_en_red: "negociar",
  pedir_hibrido: "casa",
  media_jornada: "pausa",
  trabajar_mas_horas: "consultora",
  sabatico: "viaje",
  emigrar: "viaje",
  mudarse_de_region: "viaje",
  volver_a_chile: "viaje",
  intercambio: "viaje",
  ahorro: "chanchito",
  financiar_estudios: "chanchito",
  comprar_vivienda: "casa",
  cuidar_familiar: "casa",
  tener_hijo: "casa",
  formalizar_pareja: "corazon",
  buscar_pareja: "corazon",
  separarse: "corazon",
  licencia_salud_mental: "corazon",
};

/** Ids que significan lo mismo en cualquier decisión. Los que cambian de sentido ("si", "ir") van en ARTE_PAR. */
const ARTE_OPCION: Record<string, DecisionArtKind> = {
  cambiar: "puerta",
  cambiarse: "puerta",
  renunciar: "puerta",
  dejar: "puerta",
  formal: "puerta",
  independiente: "puerta",
  contraoferta: "negociar",
  pedir: "negociar",
  levantar: "negociar",
  quedarse: "quedarte",
  aguantar: "quedarte",
  seguir: "quedarte",
  seguir_igual: "quedarte",
  rechazar: "quedarte",
  arrendar: "quedarte",
  no: "pausa",
  esperar: "pausa",
  ignorar: "pausa",
  pasar: "pausa",
  pausa: "pausa",
  emprender: "cohete",
  lado: "cohete",
  startup: "cohete",
  irse: "viaje",
  a_santiago: "viaje",
  a_region: "viaje",
  volver: "viaje",
  beca: "magister",
  vespertino: "magister",
  estudiar: "magister",
  universidad: "magister",
  instituto: "magister",
  cft: "magister",
  aprender: "laptop",
  postular: "laptop",
  bootcamp: "laptop",
  buscar: "lupa",
  rapido: "lupa",
  nivel: "lupa",
  aceptar: "subir",
  mucho: "chanchito",
  normal: "chanchito",
  gratuidad: "chanchito",
  cae: "chanchito",
  informal: "chanchito",
  gastar: "invertir",
  vender: "invertir",
  comprar: "casa",
  convivir: "casa",
  familia: "casa",
  casarse: "corazon",
  grande: "consultora",
  pyme: "consultora",
  estado: "consultora",
  trabajar: "consultora",
  tomar: "consultora",
};

const ARTE_PAR: Record<string, DecisionArtKind> = {
  "unirse_a_startup:ir": "cohete",
  "doctorado:ir": "magister",
  "intercambio:ir": "viaje",
  "seguir_con_tu_empresa:seguir": "cohete",
  "seguir_con_tu_empresa:cerrar": "puerta",
  "licencia_salud_mental:pedir": "corazon",
  "licencia_salud_mental:seguir": "consultora",
  "pedir_aumento:pedir": "subir",
  "pedir_hibrido:pedir": "casa",
  "media_jornada:pedir": "pausa",
  "cuidar_familiar:pagar": "chanchito",
  "cuidar_familiar:reducir": "pausa",
  "cuidar_familiar:dejar_pega": "casa",
  "separarse:intentar": "corazon",
  "separarse:terminar": "puerta",
  // para que dos opciones de la misma carta no compartan dibujo
  "salir_del_colegio:instituto": "laptop",
  "salir_del_colegio:cft": "chanchito",
  "financiar_estudios:cae": "invertir",
  "seguir_o_desertar:dejar": "consultora",
  "magister:vespertino": "laptop",
  "primera_pega:pyme": "quedarte",
  "primera_pega:estado": "lupa",
  "primera_pega:emprender": "invertir",
  "cesantia:nivel": "pausa",
  "media_jornada:no": "consultora",
  "emprender:lado": "laptop",
  "mudarse_de_region:a_santiago": "consultora",
  "ahorro:normal": "quedarte",
  "ahorro:gastar": "viaje",
};

/** El dibujo de una duda: el suyo propio o, si no tiene, el de su categoría. */
export const arteDuda = (decision: string, categoria: string): DecisionArtKind =>
  ARTE_DUDA[decision] ?? ARTE_CATEGORIA[categoria] ?? "consultora";

/** El dibujo de una opción, para que cada camino de la carta se vea distinto. "Sí" y "Hacerlo" usan el de la duda. */
export const arteOpcion = (decision: string, opcion: string, categoria: string): DecisionArtKind =>
  ARTE_PAR[`${decision}:${opcion}`] ?? ARTE_OPCION[opcion] ?? arteDuda(decision, categoria);

/** "Otra empresa te ofrece trabajo. ¿Te cambias?" → "¿Te cambias?". Sin pregunta, queda entera. */
export function preguntaCorta(pregunta: string): string {
  const i = pregunta.lastIndexOf("¿");
  return i > 0 ? pregunta.slice(i) : pregunta;
}

/** La primera oración: "Cuatro a cinco años con beca. Retorno mediano…" → "Cuatro a cinco años con beca." */
export function primeraFrase(texto: string): string {
  const m = texto.match(/^(.+?[.!?])(\s|$)/);
  return (m ? m[1] : texto).trim();
}

export const sinPunto = (s: string) => s.replace(/[.\s]+$/, "");

export const mayuscula = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** Diferencia con signo: +$88 mil, −$329 mil. */
export const conSigno = (n: number) => `${n < 0 ? "−" : "+"}${plata(Math.abs(n))}`;

/** "Año 3" o, si la ronda ocupó varios, "Años 1 a 5". Los años se cuentan por edad desde la edad inicial. */
export function aniosDe(edad: number, edadFin: number | undefined, edadInicial: number): string {
  const desde = edad - edadInicial + 1;
  const hasta = edadFin === undefined ? desde : Math.max(desde, edadFin - edadInicial);
  return hasta > desde ? `Años ${desde} a ${hasta}` : `Año ${desde}`;
}
