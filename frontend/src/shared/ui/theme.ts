import { useCallback, useSyncExternalStore } from "react";

/**
 * Tema claro / oscuro.
 *
 * Por defecto sigue al sistema (prefers-color-scheme) y no hay nada en <html>.
 * Si la persona elige uno, va como data-theme="dark" | "light" en <html> y se recuerda en
 * localStorage. El script inline de index.html lo aplica antes del primer pintado para que
 * no parpadee; la clave tiene que ser la misma de allá.
 * Los colores de cada tema viven en styles/vida.css.
 */
export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "vd-tema";
const SISTEMA_OSCURO = "(prefers-color-scheme: dark)";

const esTema = (v: unknown): v is Theme => v === "light" || v === "dark";

/** localStorage puede fallar (modo privado, almacenamiento bloqueado): entonces no se recuerda, y listo. */
function leerGuardado(): Theme | null {
  try {
    const v = window.localStorage.getItem(THEME_STORAGE_KEY);
    return esTema(v) ? v : null;
  } catch {
    return null;
  }
}

function guardar(t: Theme) {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, t);
  } catch {
    /* sin almacenamiento el tema se aplica igual, solo que no se recuerda */
  }
}

function aplicar(t: Theme | null) {
  const raiz = document.documentElement;
  if (t) raiz.setAttribute("data-theme", t);
  else raiz.removeAttribute("data-theme");
}

function sistemaOscuro() {
  return typeof window.matchMedia === "function" && window.matchMedia(SISTEMA_OSCURO).matches;
}

/** El tema que se está viendo: el elegido o, si no hay, el del sistema. */
function temaActual(): Theme {
  const elegido = document.documentElement.getAttribute("data-theme");
  if (esTema(elegido)) return elegido;
  return sistemaOscuro() ? "dark" : "light";
}

const oyentes = new Set<() => void>();
const avisar = () => oyentes.forEach((f) => f());

function suscribir(alCambiar: () => void) {
  oyentes.add(alCambiar);
  const mq = typeof window.matchMedia === "function" ? window.matchMedia(SISTEMA_OSCURO) : null;
  mq?.addEventListener?.("change", alCambiar);
  // Otra pestaña cambió el tema
  const alGuardar = (e: StorageEvent) => {
    if (e.key !== THEME_STORAGE_KEY) return;
    aplicar(leerGuardado());
    alCambiar();
  };
  window.addEventListener("storage", alGuardar);
  return () => {
    oyentes.delete(alCambiar);
    mq?.removeEventListener?.("change", alCambiar);
    window.removeEventListener("storage", alGuardar);
  };
}

/** Fija el tema y lo recuerda. */
export function setTheme(t: Theme) {
  aplicar(t);
  guardar(t);
  avisar();
}

/** Tema actual y cómo cambiarlo. Se actualiza si cambia el sistema u otra pestaña. */
export function useTheme() {
  const theme = useSyncExternalStore(suscribir, temaActual, () => "light" as Theme);
  const toggleTheme = useCallback(() => setTheme(temaActual() === "dark" ? "light" : "dark"), []);
  return { theme, setTheme, toggleTheme };
}
