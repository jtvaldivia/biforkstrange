/** Respuesta de POST /api/juego/turno (ver backend/app/api/routes/game.py). */

export type Ficha = {
  edad: number;
  anio: number;
  situacion: "con empleo" | "sin trabajo" | "en pausa" | "emprendiendo";
  ocupacion: string;
  isco: string;
  nivel: string;
  empleador: string;
  empresa: string;
  rubro: string;
  antiguedad: number;
  colchon_meses: number;
  salud: number;
  depresion: boolean;
  horas: number;
  exp_ocupacion: number;
  sueldo: number;
  ingreso_mes: number;
  ahorros: number;
  gasto_mes: number;
  animo: number;
  social: number;
  pareja: boolean;
  hijos: number;
  postgrado: boolean;
  estudia: number;
  ia: number;
  meses_sin_trabajo: number;
};

export type Opcion = {
  decision: string;
  nombre: string;
  ingreso: [number, number, number];
  p_cesantia: number;
  animo: number;
  p_depresion: number;
  ahorros: [number, number, number];
  p_deuda: number;
  p_mejor: number;
  p_peor: number;
  delta_ingreso: number;
  delta_animo: number;
  /** Fracción de la gente de tu edad que toma esta decisión cada año (dato), o null si no hay dato. */
  gemelos: number | null;
  gemelos_texto: string;
  descripcion: string;
  tipo: "base" | "oportunidad" | "trabajo" | "crecer" | "vida" | "riesgo";
  efectos: { texto: string; tono: "mas" | "menos" | "neutro" }[];
  extra: { afinidad?: number; logra?: number; ia_origen?: number; ia_destino?: number };
};

export type Turno = {
  decision: string;
  nombre: string;
  eventos: string[];
  logros: string[];
  yo: Ficha;
  sombra: Ficha;
  nube_eventos: Record<string, number>;
};

export type Partida = {
  perfil: { nombre: string; arquetipo: string; ocupacion: string; supuestos: string[] };
  yo: Ficha;
  sombra: Ficha;
  historial: Turno[];
  logros: string[];
  menu: Opcion[];
};

export type EscenarioIA = "lenta" | "base" | "rapida";
export type Perfil = Record<string, unknown>;
