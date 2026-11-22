import { useCallback, useEffect, useRef, useState } from "react";
import { getDudas, getMundo, getNarracion, getVista } from "../api";
import type { Duda, DudaSugerida, Eleccion, ParametrosComparar, Partida, Perfil, Vista } from "../types";

export type Fase = "inicio" | "perfil" | "duda" | "carta" | "paso" | "cierre";

export const PERFIL_INICIAL: Perfil = {
  edad: 30,
  sexo: "m",
  edu: "universitaria",
  carrera_id: -1,
  rubro: "Servicios profesionales",
  tipo_empleador: "pyme",
  nivel: 1,
  sueldo: 1_400_000,
  riesgo: 5,
};

const CLAVE = "gemelo-laboral:juego:v1";

type Guardado = { perfil: Perfil; partida: Partida | null };

function leer(): Guardado | null {
  try {
    const crudo = window.localStorage.getItem(CLAVE);
    if (!crudo) return null;
    const g = JSON.parse(crudo) as Guardado;
    if (!g || typeof g.perfil !== "object" || g.perfil === null) return null;
    return { perfil: { ...PERFIL_INICIAL, ...g.perfil }, partida: g.partida ?? null };
  } catch {
    return null;
  }
}

function guardar(g: Guardado) {
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify(g));
  } catch {
    /* sin almacenamiento (modo privado, cuota): la partida sigue en memoria */
  }
}

const mensaje = (e: unknown) => (e instanceof Error ? e.message : String(e));

/**
 * La partida de la persona. El servidor no guarda nada: aquí vive (perfil, semilla, duda, elecciones)
 * y se manda completa en cada llamada. Se guarda en localStorage para no perderla al recargar.
 */
export function usePartida() {
  const [guardado] = useState(leer);
  const [perfil, setPerfil] = useState<Perfil>(guardado?.perfil ?? PERFIL_INICIAL);
  const [partida, setPartida] = useState<Partida | null>(guardado?.partida ?? null);
  const [fase, setFase] = useState<Fase>("inicio");
  const [vista, setVista] = useState<Vista | null>(null);
  /** La vista de antes de la última elección: con ella se arma "qué te pasó". */
  const [previa, setPrevia] = useState<Vista | null>(null);
  const [dudas, setDudas] = useState<Duda[] | null>(null);
  const [cargando, setCargando] = useState(false);
  const [recalculando, setRecalculando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const turno = useRef(0);
  /** Lo elegido dentro de las opciones de la carta actual: los mundos se ven con eso mismo. */
  const parametrosCarta = useRef<ParametrosComparar>({});

  useEffect(() => guardar({ perfil, partida }), [perfil, partida]);

  /** Pide la vista de `p`; si llega (y nadie pidió otra cosa entremedio) corre `listo`. */
  const pedir = useCallback(async (p: Partida, listo: (v: Vista) => void, parametros?: ParametrosComparar, minimo = 0) => {
    const mio = ++turno.current;
    setError(null);
    const inicio = Date.now();
    try {
      const v = await getVista(p, parametros);
      // el dado se alcanza a ver aunque el motor responda al tiro
      const falta = minimo - (Date.now() - inicio);
      if (falta > 0) await new Promise((r) => setTimeout(r, falta));
      if (mio === turno.current) listo(v);
    } catch (e) {
      if (mio === turno.current) setError(mensaje(e));
    } finally {
      if (mio === turno.current) {
        setCargando(false);
        setRecalculando(false);
      }
    }
  }, []);

  const irAPerfil = useCallback(() => {
    turno.current++;
    setCargando(false);
    setError(null);
    setFase("perfil");
  }, []);

  const irAInicio = useCallback(() => {
    turno.current++;
    setCargando(false);
    setError(null);
    setFase("inicio");
  }, []);

  /** Perfil listo: se piden las dudas que esa persona puede elegir. */
  const [dudasSugeridas, setDudasSugeridas] = useState<DudaSugerida[]>([]);

  const verDudas = useCallback(async (p: Perfil, sugeridas: DudaSugerida[] = []) => {
    const mio = ++turno.current;
    setDudasSugeridas(sugeridas);
    setPerfil(p);
    setPartida(null);
    setVista(null);
    setPrevia(null);
    setDudas(null);
    setError(null);
    setFase("duda");
    setCargando(true);
    try {
      const d = await getDudas(p);
      if (mio === turno.current) setDudas(d);
    } catch (e) {
      if (mio === turno.current) setError(mensaje(e));
    } finally {
      if (mio === turno.current) setCargando(false);
    }
  }, []);

  /** Perfil listo y sin duda elegida: la primera carta se sortea como todas las demás. */
  const empezarAlAzar = useCallback(
    (p: Perfil) => {
      turno.current++;
      setPerfil(p);
      setDudasSugeridas([]);
      setVista(null);
      setPrevia(null);
      const nueva: Partida = { perfil: p, semilla: Math.floor(Math.random() * 1_000_000), duda: null, elecciones: [] };
      parametrosCarta.current = {};
      setCargando(true);
      void pedir(nueva, (v) => {
        setPartida(nueva);
        setPrevia(null);
        setVista(v);
        setFase(v.terminada ? "cierre" : "carta");
      });
    },
    [pedir],
  );

  const empezar = useCallback(
    (duda: string) => {
      const nueva: Partida = { perfil, semilla: Math.floor(Math.random() * 1_000_000), duda, elecciones: [] };
      parametrosCarta.current = {};
      setCargando(true);
      void pedir(nueva, (v) => {
        setPartida(nueva);
        setPrevia(null);
        setVista(v);
        setFase(v.terminada ? "cierre" : "carta");
      });
    },
    [perfil, pedir],
  );

  /** Retoma la partida guardada (al recargar la página). */
  const continuar = useCallback(() => {
    if (!partida) return;
    setCargando(true);
    void pedir(partida, (v) => {
      setPrevia(null);
      setVista(v);
      setFase(v.terminada ? "cierre" : "carta");
    });
  }, [partida, pedir]);

  const elegir = useCallback(
    (eleccion: Eleccion) => {
      if (!partida || !vista) return;
      const siguiente: Partida = { ...partida, elecciones: [...partida.elecciones, eleccion] };
      parametrosCarta.current = {};
      const antes = vista;
      setCargando(true);
      void pedir(siguiente, (v) => {
        setPartida(siguiente);
        setPrevia(antes);
        setVista(v);
        setFase("paso");
      }, undefined, 2400);
    },
    [partida, vista, pedir],
  );

  /** Vuelve a simular a los gemelos de la carta con lo elegido dentro de una opción (a qué rubro, etc.). */
  const compararCon = useCallback(
    (parametros: ParametrosComparar) => {
      if (!partida) return;
      setRecalculando(true);
      parametrosCarta.current = parametros;
      void pedir(partida, setVista, parametros);
    },
    [partida, pedir],
  );

  /** La historia de un mundo de la carta actual. */
  const verMundo = useCallback((mundo: number) => {
    if (!partida) return Promise.reject(new Error("No hay partida"));
    return getMundo(partida, mundo, parametrosCarta.current);
  }, [partida]);

  /** Textos de la partida contados por Sonnet (la carta, la historia o un mundo de la carta). */
  const narrar = useCallback(
    (que: "pendiente" | "historia" | "mundo", signal: AbortSignal, mundo?: number) => {
      if (!partida) return Promise.reject(new Error("No hay partida"));
      return getNarracion(partida, que, { mundo, parametros: que === "mundo" ? parametrosCarta.current : {}, signal });
    },
    [partida],
  );

  const seguir = useCallback(() => {
    if (vista) setFase(vista.terminada ? "cierre" : "carta");
  }, [vista]);

  /** Otra vida con el mismo perfil: se vuelve a elegir la duda. */
  const jugarDeNuevo = useCallback(() => empezarAlAzar(perfil), [empezarAlAzar, perfil]);

  const descartar = useCallback(() => {
    turno.current++;
    setPartida(null);
    setVista(null);
    setPrevia(null);
    setCargando(false);
    setError(null);
  }, []);

  return {
    fase, perfil, partida, vista, previa, dudas, dudasSugeridas, cargando, recalculando, error,
    irAInicio, irAPerfil, verDudas, empezar, empezarAlAzar, continuar, elegir, compararCon, verMundo, narrar, seguir, jugarDeNuevo, descartar,
  };
}
