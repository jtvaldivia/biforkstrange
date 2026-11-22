import { env } from "@/shared/config/env";

// Una partida tarda hasta un minuto en el plan gratis de Render (0,1 CPU), más el arranque si el
// servidor dormía. Pasado este tope se corta, para que la pantalla muestre un error en vez de girar para siempre.
const TOPE_MS = 120_000;

export async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const control = new AbortController();
  const tope = setTimeout(() => control.abort(new DOMException("tope", "TimeoutError")), TOPE_MS);
  const externa = init?.signal;
  const seguir = () => control.abort(externa?.reason);
  if (externa) {
    if (externa.aborted) seguir();
    else externa.addEventListener("abort", seguir, { once: true });
  }
  try {
    const res = await fetch(`${env.apiUrl}${path}`, {
      ...init,
      signal: control.signal,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    return (await res.json()) as T;
  } catch (error) {
    if (control.signal.reason instanceof DOMException && control.signal.reason.name === "TimeoutError") {
      throw new Error("El servidor tardó más de dos minutos en responder. Prueba de nuevo en un rato.");
    }
    throw error;
  } finally {
    clearTimeout(tope);
    externa?.removeEventListener("abort", seguir);
  }
}

/** Despierta el servidor apenas carga la página: en Render gratis duerme tras 15 minutos y tarda en arrancar.
 * Mientras la persona llena su perfil, el servidor ya está listo. Si falla no importa. */
export function despertarServidor(): void {
  fetch(`${env.apiUrl}/health`).catch(() => {});
}
