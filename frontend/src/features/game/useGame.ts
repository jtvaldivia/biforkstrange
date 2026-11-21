import { useCallback, useState } from "react";
import { pedirTurno } from "./api";
import type { EscenarioIA, Ficha, Partida, Perfil } from "./types";

export type Fase = "inicio" | "decision" | "resultado" | "resumen";
const EDAD_FINAL = 50;

export function useGame() {
  const [fase, setFase] = useState<Fase>("inicio");
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [escenario, setEscenario] = useState<EscenarioIA>("base");
  const [seed, setSeed] = useState(7);
  const [decisiones, setDecisiones] = useState<string[]>([]);
  const [partida, setPartida] = useState<Partida | null>(null);
  const [inicial, setInicial] = useState<Ficha | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  const llamar = useCallback(async (p: Perfil, ds: string[], s: number, esc: EscenarioIA) => {
    setCargando(true);
    setError("");
    try {
      const r = await pedirTurno(p, ds, s, esc);
      setPartida(r);
      setDecisiones(ds);
      return r;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      return null;
    } finally {
      setCargando(false);
    }
  }, []);

  /** Parte una vida. Con `mismaSuerte` reutiliza la semilla: sirve para probar otras decisiones con el mismo azar. */
  const empezar = async (p: Perfil, esc: EscenarioIA, mismaSuerte = false) => {
    const s = mismaSuerte ? seed : Math.floor(Math.random() * 1e6);
    const r = await llamar(p, [], s, esc);
    if (!r) return;
    setPerfil(p);
    setEscenario(esc);
    setSeed(s);
    setInicial(r.yo);
    setFase("decision");
  };

  const decidir = async (decision: string) => {
    if (!perfil) return;
    if (await llamar(perfil, [...decisiones, decision], seed, escenario)) setFase("resultado");
  };

  const seguir = () => setFase(partida && partida.yo.edad >= EDAD_FINAL ? "resumen" : "decision");

  return {
    fase, partida, inicial, perfil, escenario, cargando, error,
    empezar, decidir, seguir,
    terminar: () => setFase("resumen"),
    reiniciar: () => setFase("inicio"),
    repetir: () => perfil && empezar(perfil, escenario, true),
  };
}
