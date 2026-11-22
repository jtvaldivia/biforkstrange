import { env } from "@/shared/config/env";
import type { StartInput, Story } from "./types";

/** La historia avanzó en otra pestaña o por doble clic: trae la versión actual. */
export class StaleStoryError extends Error {
  constructor(public current: Story) {
    super("La historia ya había avanzado; te mostramos dónde va.");
  }
}

async function call<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const res = await fetch(`${env.apiUrl}/api/stories${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 409) throw new StaleStoryError((await res.json()).detail.story);
  if (!res.ok) {
    const text = await res.text();
    let msg = text;
    try {
      const d = JSON.parse(text).detail;
      msg = typeof d === "string" ? d : JSON.stringify(d);
    } catch { /* texto plano */ }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export const storyApi = {
  start: (input: StartInput) => call<Story>("", "POST", input),
  get: (id: string) => call<Story>(`/${id}`),
  choose: (id: string, capitulo: number, choice: { option_id?: string; texto?: string }) =>
    call<Story>(`/${id}/choose`, "POST", { capitulo, ...choice }),
  close: (id: string) => call<Story>(`/${id}/close`, "POST"),
};
