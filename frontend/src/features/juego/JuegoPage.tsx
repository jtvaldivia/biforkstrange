import "./juego.css";
import { useEffect, useRef, useState } from "react";
import { Button, Heading, Screen, ScreenFooter, Stack, Text } from "@/shared/ui";
import { AnioTranquilo } from "./components/AnioTranquilo";
import { OfertaLiviana } from "./components/OfertaLiviana";
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

  // cada pantalla nueva (otra fase, otra carta, otra tarjeta del onboarding) parte desde arriba
  const { paso, completo } = j.onboarding.borrador;
  const enOnboarding = j.fase === "perfil" ? `${paso}:${completo}` : "";
  const punto = `${tutorial}:${j.fase}:${enOnboarding}:${j.vista?.historia.length ?? 0}:${j.vista?.anio_en_curso?.decisiones.length ?? 0}:${j.vista?.pendiente?.decision ?? ""}`;
  const pantalla = useRef<HTMLDivElement>(null);
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
    <div ref={pantalla} className="jg-pantalla">
      <Fase j={j} tutorial={tutorial} setTutorial={setTutorial} catalogo={catalogo} errorCatalogo={errorCatalogo} reintentarCatalogo={reintentarCatalogo} />
    </div>
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
        onListo={() => {
          setTutorial(null);
          j.empezarDeCero();
        }}
      />
    );
  }
  if (j.fase === "perfil") {
    return <Onboarding o={j.onboarding} catalogo={catalogo} errorCatalogo={errorCatalogo} onReintentarCatalogo={reintentarCatalogo} onReintentar={j.reintentar} onVolver={j.irAInicio} onListo={j.empezarAlAzar} onElegirDuda={j.verDudas} cargando={j.cargando} error={j.error} />;
  }
  if (j.fase === "duda") {
    return (
      <DudaPicker fuentes={j.fuentes} origenSugeridas={j.origenSugeridas} perfil={j.perfil} dudas={j.dudas} sugeridas={j.dudasSugeridas} cargando={j.cargando} error={j.error} onVolver={j.irAPerfil} onElegir={j.empezar} onReintentarDudas={j.reintentarDudas} onReintentar={j.reintentar} onSinDuda={() => j.empezarAlAzar(j.perfil)} />
    );
  }
  if (j.fase === "carta" && j.vista?.pendiente?.decision === "anio_tranquilo") {
    return <AnioTranquilo vista={j.vista} cargando={j.cargando} error={j.error} onElegir={j.elegir} onSalir={j.irAInicio} sinNovedad={j.sinNovedad} />;
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
        onVerMundo={j.verMundo}
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
        onCambiarPerfil={j.irAPerfil}
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
      cargando={j.cargando}
      error={j.error}
      aviso={j.aviso}
      onContinuar={() => void j.continuar()}
      onEmpezar={j.empezarDeCero}
      onComoFunciona={() => setTutorial("antes")}
    />
  );
}
