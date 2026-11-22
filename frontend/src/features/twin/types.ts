export type Dim = { m: number; sd: number; n: number; ev: string | null; updated_at: number | null };

export type Basics = { nombre: string; rasgos: string; valores: string; gustos: string };

export type ExamItem = {
  id: string;
  q: string;
  opts: string[];
  tema: string;
  probs: number[]; // vacío mientras está pendiente
  top: number;
  pq: string;
  ans: number | null;
  ans_text: string;
  why: string | null;
  hit: boolean | null;
  p_ans: number | null;
  at: number;
};

export type Note = { q: string; a: string };

export type Report = {
  resumen: string;
  fortalezas: string[];
  riesgos: string[];
  ambientes: string[];
  vida: string;
  dudas: string[];
};

export type TwinProfile = {
  id: string;
  version: number;
  basics: Basics;
  dims: Record<string, Dim>;
  exam: ExamItem[];
  notes: Note[];
  contexto_llm: string;
  contexto_llm_at: number | null;
  corrections: { s: string; r: string; v: string; fix: string | null }[];
  qs: { id: string; q: string; ans: number | null }[];
  prior_at: number | null;
  report: Report | null;
};

export type Catalog = {
  grupos: Record<string, string>;
  dims: { key: string; nombre: string; grupo: string; descripcion: string }[];
  temas: Record<string, string>;
};

export type AdaptiveQuestion = { id: string; q: string; dims: string[]; opts: string[] };
export type ExamQuestion = { id: string; q: string; opts: string[]; tema: string };
export type Delta = { key: string; nombre: string; antes: number; despues: number; sd_antes: number; sd_despues: number };
export type Patron = { tema: string; patron: string; evidencia: string };

export type Summary = {
  claridad: { claridad: number; medidas: number; total: number };
  ajuste: { trabajo: string; score: number; margen: number; suman: string[]; restan: string[] }[];
  examen: {
    n: number;
    acierto: number | null;
    azar: number | null;
    p_media: number | null;
    log_score: number | null;
    brier: number | null;
    calibracion: { rango: string; n: number; confianza: number; acierto: number }[];
    por_tema: { tema: string; label: string; n: number; acierto: number }[];
    tendencia: number[];
  };
};
