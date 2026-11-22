import "./juego.css";
import { useEffect, useRef, useState } from "react";
import { Button, Heading, Screen, ScreenFooter, Stack, Text } from "@/shared/ui";
import { AnioTranquilo } from "./components/AnioTranquilo";
import { OfertaLiviana } from "./components/OfertaLiviana";
import { BuscandoTrabajo } from "./components/BuscandoTrabajo";
import { Carta } from "./components/Carta";
import { CierrePantalla } from "./components/Cierre";
import { ComoFunciona } from "./components/ComoFunciona";
import { DudaPicker } from "./components/DudaPicker";
import { Inicio } from "./components/Inicio";
import { Onboarding } from "./components/Onboarding";
import { QuePaso } from "./components/QuePaso";
import { useCatalogo } from "./hooks/useCatalogo";
import { usePartida } from "./hooks/usePartida";

/** El juego completo: perfil → duda → carta → qué te pasó → … → cierre. */
export function JuegoPage() {
  return (
    <div className="jg-fondo">
      <Juego />
    </div>
  );
}

function Juego() {
  const j = usePartida();
  const { catalogo, error: errorCatalogo, reintentar: reintentarCatalogo } = useCatalogo();
  /** El tutorial, que se abre desde el inicio antes de armar el perfil. */
  const [tutorial, setTutorial] = useState<"antes" | null>(null);
  useNavegacion(j, tutorial, setTutorial);

  // cada pantalla nueva (otra fase, otra carta, otra tarjeta del onboarding) parte desde arriba
  const { paso, completo } = j.onboarding.borrador;
  const enOnboarding = j.fase === "perfil" ? `${paso}:${completo}` : "";
  const punto = `${tutorial}:${j.fase}:${enOnboarding}:${j.vista?.historia.length ?? 0}:${j.vista?.anio_en_curso?.decisiones.length ?? 0}:${j.vista?.pendiente?.decision ?? ""}`;
  const pantalla = useRef<HTMLElement>(null);
  const primera = useRef(true);
  useEffect(() => {
    window.scrollTo(0, 0);
    // y el foco va a su título, para que un lector de pantalla (o el teclado) siga desde ahí y no desde un botón que ya no existe
    if (primera.current) {
      primera.current = false;
      return;
    }
    const titulo = pantalla.current?.querySelector<HTMLElement>("h1") ?? pantalla.current?.querySelector<HTMLElement>("h2");
    if (!titulo) return;
    if (!titulo.hasAttribute("tabindex")) titulo.setAttribute("tabindex", "-1");
    titulo.focus({ preventScroll: true });
  }, [punto]);

  return (
    <main ref={pantalla} className="jg-pantalla">
      <Fase j={j} tutorial={tutorial} setTutorial={setTutorial} catalogo={catalogo} errorCatalogo={errorCatalogo} reintentarCatalogo={reintentarCatalogo} />
    </main>
  );
}

function Fase({
  j, tutorial, setTutorial, catalogo, errorCatalogo, reintentarCatalogo,
}: {
  j: ReturnType<typeof usePartida>;
  tutorial: "antes" | null;
  setTutorial: (t: "antes" | null) => void;
  catalogo: ReturnType<typeof useCatalogo>["catalogo"];
  errorCatalogo: string | null;
  reintentarCatalogo: () => void;
}) {
  const sueldoInicial = j.partida?.perfil.sueldo ?? j.perfil.sueldo;
  // una oferta que te llegó se muestra en corto; "Mirarla" abre la carta completa solo para esa oferta
  const llaveCarta = `${j.vista?.historia.length ?? 0}:${j.vista?.anio_en_curso?.decisiones.length ?? 0}:${j.vista?.pendiente?.decision ?? ""}`;
  const [mirada, setMirada] = useState<string | null>(null);

  if (tutorial === "antes") {
    return (
      <ComoFunciona
        onVolver={() => setTutorial(null)}
        // con una partida guardada, el tutorial vuelve a la portada: armar otro perfil borraría la partida
        textoListo={j.partida ? "Volver al inicio" : undefined}
        onListo={() => {
          setTutorial(null);
          if (!j.partida) j.empezarDeCero();
        }}
      />
    );
  }
  if (j.fase === "perfil") {
    return <Onboarding o={j.onboarding} catalogo={catalogo} errorCatalogo={errorCatalogo} onReintentarCatalogo={reintentarCatalogo} onReintentar={j.reintentar} onVolver={j.irAInicio} onListo={j.empezarAlAzar} onElegirDuda={j.verDudas} cargando={j.cargando} error={j.error} />;
  }
  if (j.fase === "duda") {
    return (
      <DudaPicker semilla={j.semillaNueva} fuentes={j.fuentes} origenSugeridas={j.origenSugeridas} perfil={j.perfil} dudas={j.dudas} sugeridas={j.dudasSugeridas} cargando={j.cargando} error={j.error} onVolver={j.irAPerfil} onElegir={j.empezar} onReintentarDudas={j.reintentarDudas} onReintentar={j.reintentar} onSinDuda={() => j.empezarAlAzar(j.perfil)}
        onVolverPartida={j.partida ? () => (j.vista ? j.seguir() : void j.continuar()) : undefined} terminada={j.terminada} />
    );
  }
  if (j.fase === "carta" && j.vista?.pendiente?.decision === "anio_tranquilo") {
    return <AnioTranquilo vista={j.vista} cargando={j.cargando} error={j.error} onElegir={j.elegir} onSalir={j.irAInicio} sinNovedad={j.sinNovedad} />;
  }
  if (j.fase === "carta" && j.vista?.pendiente?.decision === "oferta_en_cesantia" && j.vista.pendiente.busqueda && mirada !== llaveCarta) {
    return <BuscandoTrabajo vista={j.vista} cargando={j.cargando} error={j.error} onMirar={() => setMirada(llaveCarta)} onElegir={j.elegir} onSalir={j.irAInicio} />;
  }
  if (j.fase === "carta" && j.vista?.pendiente?.decision === "oferta_externa" && j.vista.pendiente.por_que?.tipo === "llega" && mirada !== llaveCarta) {
    return <OfertaLiviana vista={j.vista} cargando={j.cargando} error={j.error} onMirar={() => setMirada(llaveCarta)} onElegir={j.elegir} onSalir={j.irAInicio} sinNovedad={j.sinNovedad} />;
  }
  if (j.fase === "carta" && j.vista?.pendiente) {
    return (
      <Carta
        vista={j.vista}
        partida={j.partida}
        fuentes={j.fuentes}
        riesgo={j.perfil.riesgo}
        cargando={j.cargando}
        recalculando={j.recalculando}
        error={j.error}
        onElegir={j.elegir}
        onReintentar={j.reintentar}
        onComparar={j.compararCon}
        onSalir={j.irAInicio}
        onNarrar={j.narrar}
        sinNovedad={j.sinNovedad}
      />
    );
  }
  if (j.fase === "paso" && j.vista) return <QuePaso previa={j.previa} vista={j.vista} sueldoInicial={sueldoInicial} onSeguir={j.seguir} onNarrar={j.narrar} onSalir={j.irAInicio} />;
  if (j.fase === "cierre" && j.vista?.cierre)
    return (
      <CierrePantalla
        vista={j.vista}
        sueldoInicial={sueldoInicial}
        onSalir={j.irAInicio}
        retrato={j.retrato}
        onOtraVida={j.jugarDeNuevo}
        onRevivir={j.revivir}
        anterior={j.anterior}
        onCambiarPerfil={j.irAPerfil}
        cargando={j.cargando}
        error={j.error}
        onReintentar={j.reintentar}
      />
    );
  if (j.fase !== "inicio") {
    // no debería pasar: una fase sin los datos que necesita
    return (
      <Screen>
        <Stack>
          <Heading level={2}>Se nos perdió el hilo.</Heading>
          <Text>No pudimos mostrar este punto de la partida.</Text>
        </Stack>
        <ScreenFooter>
          <Button onClick={j.irAInicio}>Volver al inicio</Button>
        </ScreenFooter>
      </Screen>
    );
  }
  return (
    <Inicio
      hayPartida={j.partida !== null}
      terminada={j.terminada}
      cargando={j.cargando}
      error={j.error}
      aviso={j.aviso}
      onContinuar={() => void j.continuar()}
      onEmpezar={j.empezarDeCero}
      onComoFunciona={() => setTutorial("antes")}
      onOtraDuda={() => void j.verDudas(j.partida?.perfil ?? j.perfil, j.onboarding.sugeridas)}
    />
  );
}

/** Cada pantalla principal tiene su hash: así el botón atrás del navegador (y el gesto en el celular) no saca del sitio. */
type Ruta = "" | "como-funciona" | "perfil" | "duda" | "partida" | "fin";
const RUTAS: readonly Ruta[] = ["", "como-funciona", "perfil", "duda", "partida", "fin"];

const rutaDelHash = (hash: string): Ruta => {
  const r = hash.replace(/^#\/?/, "") as Ruta;
  return RUTAS.includes(r) ? r : "";
};
const urlDe = (r: Ruta) => (r ? `#/${r}` : window.location.pathname + window.location.search);
const enPartida = (r: Ruta) => r === "partida" || r === "fin";

function rutaDe(j: ReturnType<typeof usePartida>, tutorial: "antes" | null): Ruta {
  if (tutorial === "antes") return "como-funciona";
  if (j.fase === "perfil") return "perfil";
  if (j.fase === "duda") return "duda";
  if (j.fase === "carta" || j.fase === "paso") return "partida";
  if (j.fase === "cierre") return "fin";
  return "";
}

/**
 * Navegación con el History API, sin router: cada cambio de pantalla deja una entrada (`#/perfil`, `#/duda`, …)
 * y atrás vuelve a la anterior sin perder estado. Dentro de la partida (los años y el cierre son una sola
 * entrada), atrás va a la portada, que ofrece seguirla. Al recargar se retoma la pantalla si hay con qué;
 * si no, la portada.
 */
function useNavegacion(j: ReturnType<typeof usePartida>, tutorial: "antes" | null, setTutorial: (t: "antes" | null) => void) {
  const ruta = rutaDe(j, tutorial);
  /** La entrada del historial en que estamos y la ruta de cada una que conocemos (para saltar a la portada). */
  const nav = useRef({ i: 0, rutas: [] as Ruta[] });
  const ahora = useRef({ j, ruta });
  ahora.current = { j, ruta };

  /** Lleva el estado a la pantalla `r`; si para esa pantalla no hay datos, a la portada. */
  const irA = useRef((r: Ruta) => {
    const { j } = ahora.current;
    if (r === "como-funciona") return setTutorial("antes");
    setTutorial(null);
    if (r === "perfil") return j.irAPerfil();
    if (r === "duda") return j.irADudas();
    if (enPartida(r) && j.vista) return j.seguir();
    if (enPartida(r) && j.partida) return void j.continuar();
    if (r !== "") {
      const n = nav.current;
      n.rutas[n.i] = "";
      window.history.replaceState({ bifurca: n.i }, "", urlDe(""));
    }
    if (j.fase !== "inicio") j.irAInicio();
  });

  // al cargar: la entrada actual queda como portada y, si la URL pedía otra pantalla, se intenta abrirla
  useEffect(() => {
    const n = nav.current;
    const pedida = rutaDelHash(window.location.hash);
    const previo: unknown = window.history.state;
    n.i = previo && typeof (previo as { bifurca?: unknown }).bifurca === "number" ? (previo as { bifurca: number }).bifurca : 0;
    n.rutas[n.i] = "";
    window.history.replaceState({ bifurca: n.i }, "", urlDe(""));
    // la lista de dudas no se guarda: recargar ahí vuelve a la portada
    if (pedida === "perfil" || pedida === "como-funciona" || enPartida(pedida)) irA.current(pedida);
  }, []);

  // cada pantalla nueva deja su entrada; volver a la anterior con un botón de la app es lo mismo que atrás
  useEffect(() => {
    const n = nav.current;
    if (n.rutas[n.i] === ruta) return;
    if (n.i > 0 && n.rutas[n.i - 1] === ruta) {
      n.i--;
      window.history.back();
      return;
    }
    n.i++;
    n.rutas.length = n.i;
    n.rutas[n.i] = ruta;
    window.history.pushState({ bifurca: n.i }, "", urlDe(ruta));
  }, [ruta]);

  useEffect(() => {
    const alVolver = (e: PopStateEvent) => {
      const n = nav.current;
      const estado: unknown = e.state;
      const t = estado && typeof (estado as { bifurca?: unknown }).bifurca === "number" ? (estado as { bifurca: number }).bifurca : 0;
      const destino = rutaDelHash(window.location.hash);
      n.i = t;
      n.rutas[t] = destino;
      const actual = ahora.current.ruta;
      if (destino === actual) return;
      if (enPartida(actual) && destino !== "") {
        // atrás desde la partida no deshace años ni vuelve a la duda: va a la portada
        const portada = n.rutas.lastIndexOf("", t);
        if (portada >= 0 && portada < t) {
          window.history.go(portada - t);
          return;
        }
        n.rutas[t] = "";
        window.history.replaceState({ bifurca: t }, "", urlDe(""));
        irA.current("");
        return;
      }
      irA.current(destino);
    };
    window.addEventListener("popstate", alVolver);
    return () => window.removeEventListener("popstate", alVolver);
  }, []);
}
