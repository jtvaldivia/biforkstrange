/** Respuesta de POST /api/juego/turno (ver backend/app/api/routes/game.py). */

export type Ficha = {
  edad: number;
  anio: number;
  situacion: "con empleo" | "sin trabajo" | "en pausa" | "emprendiendo";
  ocupacion: string;
  isco: string;
  nivel: string;
  empleador: string;
  sueldo: number;
  ingreso_mes: number;
  ahorros: number;
  gasto_mes: number;
  energia: number;
  animo: number;
  social: number;
  pareja: boolean;
  hijos: number;
  contactos: number;
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
  energia_min: number;
  p_burnout: number;
  ahorros: [number, number, number];
  p_deuda: number;
  p_mejor: number;
  p_peor: number;
  delta_ingreso: number;
  delta_animo: number;
  gemelos: number;
  extra: { afinidad?: number; logra?: number; ia_origen?: number; ia_destino?: number };
};

export type Turno = {
  decision: string;
  nombre: string;
  eventos: string[];
  yo: Ficha;
  sombra: Ficha;
  nube_eventos: Record<string, number>;
};

export type Partida = {
  perfil: { nombre: string; arquetipo: string; ocupacion: string; supuestos: string[] };
  yo: Ficha;
  sombra: Ficha;
  historial: Turno[];
  menu: Opcion[];
};

export type EscenarioIA = "lenta" | "base" | "rapida";
export type Perfil = Record<string, unknown>;
