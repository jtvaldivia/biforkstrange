import { useCallback, useEffect, useRef, useState } from "react";
import { sinMovimiento } from "../components/graficos";
import { loNuevo } from "../components/QuePaso";
import { sinSueldo } from "../textos";
import { comoErrorApi, getDudas, getNarracion, getVista, textoError } from "../api";
import type { Duda, DudaSugerida, Eleccion, ParametrosComparar, Partida, Perfil, SinNovedad, Vista } from "../types";
import { borradorInicial, useBorrador, type Borrador, type Fuente } from "./useBorrador";

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

/**
 * La clave lleva la versión de lo que se guarda: si cambia su forma, se sube y lo de antes no se lee
 * (v2: el borrador del onboarding, las fuentes y el retrato van con la partida).
 */
const CLAVE = "gemelo-laboral:juego:v2";
const CLAVES_VIEJAS = ["gemelo-laboral:juego:v1"];

/** `fuentes`: de dónde salió cada dato de `perfil` (lo que falta es supuesto); null en partidas de antes. */
type Guardado = {
  perfil: Perfil;
  partida: Partida | null;
  borrador?: Borrador;
  fuentes?: Record<string, Fuente> | null;
  /** "Lo que tu gemelo sabe de ti", de este perfil: va en la tarjeta que se comparte. */
  retrato?: string | null;
  /** Si la partida guardada ya terminó: la portada ofrece ver el resultado en vez de seguirla. */
  terminada?: boolean;
};

/** Antes el retrato se guardaba aparte y se asociaba por edad, sexo y estudios: podía salir el de otra persona. */
const RETRATO_VIEJO = "gemelo-laboral:retrato:v1";

function leer(): Guardado | null {
  try {
    window.localStorage.removeItem(RETRATO_VIEJO);
    for (const vieja of CLAVES_VIEJAS) window.localStorage.removeItem(vieja);
    const crudo = window.localStorage.getItem(CLAVE);
    if (!crudo) return null;
    const g = JSON.parse(crudo) as Guardado;
    if (!g || typeof g.perfil !== "object" || g.perfil === null) return null;
    const borrador = g.borrador && typeof g.borrador === "object" ? { ...borradorInicial(PERFIL_INICIAL), ...g.borrador } : undefined;
    if (borrador) borrador.perfil = { ...PERFIL_INICIAL, ...borrador.perfil };
    return { perfil: { ...PERFIL_INICIAL, ...g.perfil }, partida: g.partida ?? null, borrador, fuentes: g.fuentes ?? null, retrato: g.retrato ?? null, terminada: g.terminada ?? false };
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

const mensaje = textoError;

const semillaAlAzar = () => Math.floor(Math.random() * 1_000_000);

/** La vida que terminaste, para compararla con la siguiente cuando vuelves a vivir el mismo mundo. */
export type VidaAnterior = {
  recorrido: { edad: number; sueldo: number }[];
  sueldoFinal: number;
  /** Lo que elegiste en la primera decisión, con su nombre. */
  primera: { decision: string; nombre: string } | null;
};

function vidaDe(v: Vista, sueldoInicial: number): VidaAnterior | null {
  if (!v.cierre) return null;
  const edadInicial = v.edad_final - v.anios;
  const pd = v.cierre.primera_decision;
  const nombre = pd?.comparacion.opciones.find((o) => o.opcion === pd.elegida)?.nombre;
  return {
    recorrido: [{ edad: edadInicial, sueldo: sueldoInicial }, ...v.historia.filter((a) => a.fin).map((a) => ({ edad: a.fin!.edad, sueldo: a.fin!.sueldo }))],
    sueldoFinal: v.cierre.sueldo_final,
    primera: pd && nombre ? { decision: pd.decision, nombre } : null,
  };
}

/**
 * Si al seguir igual el año pasó sin nada que contar (solo el ajuste normal del sueldo), lo que cambió;
 * si no, null. Una oferta que llega no cuenta: la muestra la pantalla siguiente.
 */
function anioSinNovedad(antes: Vista, v: Vista): SinNovedad | null {
  const tramos = loNuevo(antes, v);
  const cerrados = tramos.filter((a) => a.fin);
  if (cerrados.length !== 1 || sinSueldo(v.estado) !== sinSueldo(antes.estado)) return null;
  // lo que trae el año que empieza ya lo muestra la pantalla siguiente si es un año tranquilo (o la oferta)
  const loMuestraLaSiguiente = v.pendiente?.decision === "anio_tranquilo";
  const noticia = tramos.some(
    (a, i) =>
      (!(loMuestraLaSiguiente && !a.fin) && a.eventos.some((e) => !e.rutina && e.evento !== "oferta_llega")) ||
      a.decisiones.slice(i === 0 ? 1 : 0).some((d) => d.opcion !== "sorteo"),
  );
  if (noticia) return null;
  return { anio: cerrados[0].edad - (v.edad_final - v.anios) + 1, sueldo: v.estado.sueldo, delta: v.estado.sueldo - antes.estado.sueldo };
}

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
  /** El año que acaba de pasar sin novedades, para la franja del año siguiente. */
  const [sinNovedad, setSinNovedad] = useState<SinNovedad | null>(null);
  const [dudas, setDudas] = useState<Duda[] | null>(null);
  const [cargando, setCargando] = useState(false);
  const [recalculando, setRecalculando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** Un aviso para la portada (no un error): por ejemplo, que la partida guardada ya no se puede seguir. */
  const [aviso, setAviso] = useState<string | null>(null);
  /** Tu vida anterior en este mismo mundo: el cierre la dibuja junto a la de ahora. Solo en memoria. */
  const [anterior, setAnterior] = useState<VidaAnterior | null>(null);
  const turno = useRef(0);
  /**
   * La semilla de la próxima partida nueva, elegida antes de empezar: "más en juego" calcula las dudas con
   * ella, así que la primera carta de la duda que se elija ya está calculada en el servidor.
   */
  const [semillaNueva, setSemillaNueva] = useState(semillaAlAzar);
  /** Lo elegido dentro de las opciones de la carta actual: los mundos se ven con eso mismo. */
  const parametrosCarta = useRef<ParametrosComparar>({});
  /** El onboarding a medio armar: sobrevive a ir y volver de las dudas. */
  const onboarding = useBorrador(guardado?.borrador ?? borradorInicial(guardado?.perfil ?? PERFIL_INICIAL));
  const borrador = onboarding.borrador;
  const borradorActual = onboarding.actual;
  /** De dónde salió cada dato del perfil con que se juega: lo que no está quedó como supuesto. */
  const [fuentes, setFuentes] = useState<Record<string, Fuente> | null>(guardado?.fuentes ?? null);
  const [retrato, setRetrato] = useState<string | null>(guardado?.retrato ?? null);
  /** El perfil con que se va a jugar: con él van sus fuentes y su retrato, sacados del borrador de ahora. */
  const fijarPerfil = useCallback((p: Perfil) => {
    const b = borradorActual.current;
    setPerfil(p);
    setFuentes(b.fuentes);
    setRetrato(b.claude?.retrato ?? b.leido?.retrato ?? null);
  }, []);

  const [terminada, setTerminada] = useState(guardado?.terminada ?? false);
  useEffect(() => {
    if (vista) setTerminada(vista.terminada);
    else if (!partida) setTerminada(false);
  }, [vista, partida]);

  useEffect(() => guardar({ perfil, partida, borrador, fuentes, retrato, terminada }), [perfil, partida, borrador, fuentes, retrato, terminada]);

  /** Lo último que falló, para el botón "Reintentar": se repite eso mismo, no otra cosa. */
  const reintento = useRef<(() => void) | null>(null);

  /** Pide la vista de `p`; si llega (y nadie pidió otra cosa entremedio) corre `listo`. */
  const pedir = useCallback(async (p: Partida, listo: (v: Vista) => void, parametros?: ParametrosComparar, minimo = 0): Promise<void> => {
    const mio = ++turno.current;
    reintento.current = null;
    setError(null);
    const inicio = Date.now();
    try {
      const v = await getVista(p, parametros);
      // el dado se alcanza a ver aunque el motor responda al tiro
      const falta = minimo - (Date.now() - inicio);
      if (falta > 0) await new Promise((r) => setTimeout(r, falta));
      if (mio === turno.current) listo(v);
    } catch (e) {
      if (mio === turno.current) {
        setError(mensaje(e));
        reintento.current = () => {
          if (parametros) setRecalculando(true);
          else setCargando(true);
          void pedir(p, listo, parametros, minimo);
        };
      }
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
    setSinNovedad(null);
    setFase("inicio");
  }, []);

  /** Perfil listo: se piden las dudas que esa persona puede elegir. */
  const [dudasSugeridas, setDudasSugeridas] = useState<DudaSugerida[]>([]);
  /** Si las sugeridas las trajo tu Claude (van primero) o solo el CV: la pantalla lo dice. */
  const [origenSugeridas, setOrigenSugeridas] = useState<"cv" | "claude" | null>(null);

  const verDudas = useCallback(async (p: Perfil, sugeridas: DudaSugerida[] = []) => {
    const mio = ++turno.current;
    setDudasSugeridas(sugeridas);
    const b = borradorActual.current;
    const deClaude = new Set(b.claude?.sugeridas.map((d) => d.decision) ?? []);
    setOrigenSugeridas(sugeridas.length === 0 ? null : sugeridas.some((d) => deClaude.has(d.decision)) ? "claude" : "cv");
    fijarPerfil(p);
    // la partida que tenías sigue ahí hasta que la nueva duda arranque: si te arrepientes, puedes volver a ella
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
  }, [fijarPerfil]);

  /** Vuelve a la lista de dudas (el botón atrás del navegador): si ya estaba cargada no se pide de nuevo. */
  const irADudas = useCallback(() => {
    if (!dudas) return void verDudas(perfil, dudasSugeridas);
    turno.current++;
    setCargando(false);
    setError(null);
    setFase("duda");
  }, [dudas, verDudas, perfil, dudasSugeridas]);

  /** Si las dudas no llegaron (el backend no respondía), se vuelven a pedir con el mismo perfil. */
  const reintentar = useCallback(() => reintento.current?.(), []);
  const reintentarDudas = useCallback(() => verDudas(perfil, dudasSugeridas), [verDudas, perfil, dudasSugeridas]);

  /**
   * Una partida nueva de `p` con la duda dada (o sin duda). Con `semilla` es el mismo mundo de antes: la misma
   * primera carta y la misma suerte del país (la de la pega cambia si te cambias de trabajo). La partida de antes
   * se reemplaza solo cuando la nueva llega; `anterior` es la vida que el cierre dibuja junto a la nueva.
   */
  const nuevaPartida = useCallback(
    (p: Perfil, duda: string | null, semilla?: number, anterior: VidaAnterior | null = null) => {
      parametrosCarta.current = {};
      setCargando(true);
      const nueva: Partida = { perfil: p, semilla: semilla ?? semillaNueva, duda, elecciones: [] };
      setSemillaNueva(semillaAlAzar()); // la próxima partida nueva es otro mundo
      void pedir(nueva, (v) => {
        setAnterior(anterior);
        setPartida(nueva);
        setPrevia(null);
        setVista(v);
        setFase(v.terminada ? "cierre" : "carta");
      });
    },
    [pedir, semillaNueva],
  );

  /** Perfil listo y sin duda elegida: la primera carta se sortea como todas las demás. */
  const empezarAlAzar = useCallback(
    (p: Perfil) => {
      turno.current++;
      fijarPerfil(p);
      setDudasSugeridas([]);
      nuevaPartida(p, null);
    },
    [nuevaPartida, fijarPerfil],
  );

  const empezar = useCallback((duda: string) => nuevaPartida(perfil, duda), [perfil, nuevaPartida]);

  /**
   * Retoma la partida guardada (al recargar la página). Si el motor cambió desde que se guardó y ya no la
   * acepta (422: una decisión u opción que ya no existe), se descarta y se avisa en la portada: reintentar
   * no la arreglaría.
   */
  const continuar = useCallback(async () => {
    if (!partida) return;
    const mio = ++turno.current;
    reintento.current = null;
    setAviso(null);
    setError(null);
    setCargando(true);
    try {
      const v = await getVista(partida);
      if (mio !== turno.current) return;
      setPrevia(null);
      setVista(v);
      setFase(v.terminada ? "cierre" : "carta");
    } catch (e) {
      if (mio !== turno.current) return;
      if (comoErrorApi(e).status === 422) {
        setPartida(null);
        setVista(null);
        setPrevia(null);
        setFase("inicio");
        setAviso("Tu partida guardada es de una versión anterior del simulador y ya no se puede seguir. Empieza una nueva.");
      } else {
        setError(mensaje(e));
        reintento.current = () => void continuar();
      }
    } finally {
      if (mio === turno.current) setCargando(false);
    }
  }, [partida]);

  const elegir = useCallback(
    (eleccion: Eleccion) => {
      if (!partida || !vista) return;
      const siguiente: Partida = { ...partida, elecciones: [...partida.elecciones, eleccion] };
      parametrosCarta.current = {};
      const antes = vista;
      // en un año tranquilo, buscar algo abre esa decisión de inmediato: no hay dado que tirar todavía
      const busca = eleccion.decision === "anio_tranquilo" && eleccion.opcion !== "seguir";
      // seguir igual no tiene dado: si el año no trajo nada, se pasa directo al siguiente (sin "qué te pasó")
      const seguirIgual = eleccion.decision === "anio_tranquilo" && eleccion.opcion === "seguir";
      // el dado solo se toma su tiempo si la opción tiene algo que sortear; si era segura, la espera es corta
      const resultados = vista.pendiente?.comparacion?.opciones.find((o) => o.opcion === eleccion.opcion)?.por_resultado.length ?? 0;
      setCargando(true);
      void pedir(siguiente, (v) => {
        const quieto = seguirIgual ? anioSinNovedad(antes, v) : null;
        setPartida(siguiente);
        setPrevia(antes);
        setVista(v);
        setSinNovedad(quieto);
        setFase(quieto ? (v.terminada ? "cierre" : "carta") : busca && v.pendiente ? "carta" : "paso");
      }, undefined, busca || seguirIgual || sinMovimiento() ? 0 : resultados > 1 ? 2400 : 600); // sin dado o sin animaciones, no se espera
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

  /** Textos de la partida contados por Claude (la carta, la historia o un mundo de la carta). */
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

  /** Otra vida, en otro mundo, con la misma duda que elegiste (o sin duda, si empezaste sin una). */
  const jugarDeNuevo = useCallback(() => {
    turno.current++;
    nuevaPartida(partida?.perfil ?? perfil, partida?.duda ?? null);
  }, [nuevaPartida, partida, perfil]);

  /** El mismo mundo otra vez, desde el año 1, para elegir distinto. La vida que terminaste queda para comparar. */
  const revivir = useCallback(() => {
    if (!partida || !vista) return;
    turno.current++;
    nuevaPartida(partida.perfil, partida.duda, partida.semilla, vidaDe(vista, partida.perfil.sueldo));
  }, [nuevaPartida, partida, vista]);

  const descartar = useCallback(() => {
    turno.current++;
    setPartida(null);
    setVista(null);
    setPrevia(null);
    setCargando(false);
    setError(null);
  }, []);

  /**
   * "Empezar": una persona nueva parte de cero. Ni el perfil, ni lo que leyó Claude, ni las dudas sugeridas
   * de quien jugó antes en este navegador.
   */
  const empezarDeCero = useCallback(() => {
    turno.current++;
    setAnterior(null);
    setPartida(null);
    setVista(null);
    setPrevia(null);
    setDudas(null);
    setDudasSugeridas([]);
    setPerfil(PERFIL_INICIAL);
    setFuentes({});
    setRetrato(null);
    setAviso(null);
    onboarding.reiniciar(PERFIL_INICIAL);
    setCargando(false);
    setError(null);
    setFase("perfil");
  }, [onboarding.reiniciar]);

  return {
    aviso, fuentes, retrato, origenSugeridas, terminada, irADudas, empezarDeCero, reintentarDudas, reintentar, semillaNueva,
    fase, perfil, partida, vista, previa, sinNovedad, dudas, dudasSugeridas, cargando, recalculando, error, onboarding,
    irAInicio, irAPerfil, verDudas, empezar, empezarAlAzar, continuar, elegir, compararCon, narrar, seguir, jugarDeNuevo, revivir, anterior, descartar,
  };
}
