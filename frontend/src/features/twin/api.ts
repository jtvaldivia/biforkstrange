import { env } from "@/shared/config/env";
import type {
  AdaptiveQuestion,
  Basics,
  Catalog,
  Delta,
  ExamItem,
  ExamQuestion,
  Patron,
  Summary,
  TwinProfile,
} from "./types";

/** El servidor tiene una versión más nueva (otra pestaña escribió antes). Trae el perfil actual. */
export class StaleProfileError extends Error {
  constructor(public current: TwinProfile) {
    super("Había una versión más nueva del perfil; se cargó en vez de pisarla.");
  }
}

async function call<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const res = await fetch(`${env.apiUrl}/api/twin${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 409) {
    const { detail } = await res.json();
    throw new StaleProfileError(detail.profile);
  }
  if (!res.ok) {
    const text = await res.text();
    let msg = text;
    try {
      const d = JSON.parse(text).detail;
      msg = typeof d === "string" ? d : JSON.stringify(d);
    } catch { /* texto plano */ }
    throw new Error(`${res.status}: ${msg}`);
  }
  return res.json() as Promise<T>;
}

const p = (id: string) => `/profiles/${id}`;

export const twinApi = {
  catalog: () => call<Catalog>("/catalog"),
  create: () => call<TwinProfile>("/profiles", "POST", { basics: {} }),
  get: (id: string) => call<TwinProfile>(p(id)),
  summary: (id: string) => call<Summary>(`${p(id)}/summary`),

  saveBasics: (id: string, version: number, basics: Basics) =>
    call<TwinProfile>(`${p(id)}/basics`, "PUT", { version, basics }),
  addNote: (id: string, version: number, q: string, a: string) =>
    call<TwinProfile>(`${p(id)}/notes`, "POST", { version, q, a }),
  importContext: (id: string, version: number, texto: string, estimar: boolean) =>
    call<TwinProfile>(`${p(id)}/contexto`, "PUT", { version, texto, estimar }),
  prior: (id: string, version: number) => call<TwinProfile>(`${p(id)}/prior`, "POST", { version }),
  report: (id: string, version: number) => call<TwinProfile>(`${p(id)}/report`, "POST", { version }),

  adaptiveNext: (id: string, version: number) =>
    call<{ profile: TwinProfile; question: AdaptiveQuestion | null }>(`${p(id)}/adaptive/next`, "POST", { version }),
  adaptiveAnswer: (id: string, version: number, qid: string, ans: number, note?: string) =>
    call<{ profile: TwinProfile; deltas: Delta[] }>(`${p(id)}/adaptive/answer`, "POST", { version, qid, ans, note }),

  examNext: (id: string, version: number, tema: string) =>
    call<{ profile: TwinProfile; question: ExamQuestion }>(`${p(id)}/exam/next`, "POST", { version, tema }),
  examAnswer: (id: string, version: number, eid: string, ans: number, ans_text?: string, why?: string) =>
    call<{ profile: TwinProfile; reveal: ExamItem }>(`${p(id)}/exam/answer`, "POST", { version, eid, ans, ans_text, why }),

  proposeCalibration: (id: string) => call<{ patrones: Patron[] }>(`${p(id)}/calibration/propose`, "POST"),
  saveCalibration: (id: string, version: number, patrones: Patron[]) =>
    call<TwinProfile>(`${p(id)}/calibration`, "PUT", { version, patrones }),
};
