export type Option = { id: string; titulo: string; detalle: string; decision: string };
export type Dilemma = { situacion: string; pregunta: string; opciones: Option[] };
export type Moment = { de: string; texto: string; hora: string };

export type Chapter = {
  n: number;
  edad: number;
  anio: number;
  eleccion: string;
  decision: string;
  titulo: string;
  relato: string;
  momentos: Moment[];
  ganaste: string;
  dejaste: string;
  estado: { trabajo?: string; plata?: string; energia?: string; vida?: string };
  tono: "dia" | "noche";
  hilo: Hilo;
};

/** Dónde quedó la persona al cerrar el año (lo usa el narrador para el año siguiente). */
export type Hilo = { donde?: string; trabajo?: string; vinculos?: string; en_curso?: string };

export type Epilogue = { titulo: string; relato: string; lo_que_ganaste: string[]; lo_que_no_vuelve: string[] };

export type Story = {
  id: string;
  profile_id: string | null;
  inicio: { edad: number; anio: number; situacion: string };
  anios: number;
  titulo: string;
  prologo: string;
  hilo: Hilo;
  capitulos: Chapter[];
  dilema: Dilemma | null;
  epilogo: Epilogue | null;
  terminada: boolean;
};

export type StartInput = { situacion: string; edad: number; desgaste: number; anios: number; profile_id: string | null };
