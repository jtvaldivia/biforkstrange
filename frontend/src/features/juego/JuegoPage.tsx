import "./juego.css";
import { useEffect, useState } from "react";
import { Button, Heading, Screen, ScreenFooter, Stack, Text } from "@/shared/ui";
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
  const { catalogo, error: errorCatalogo } = useCatalogo();
  /** El tutorial: "antes" de armar el perfil, o "ayuda" cuando se reabre a mitad de la partida. */
  const [tutorial, setTutorial] = useState<"antes" | "ayuda" | null>(null);
  const sueldoInicial = j.partida?.perfil.sueldo ?? j.perfil.sueldo;

  // cada pantalla nueva (otra fase, otra carta) parte desde arriba
  const punto = `${tutorial}:${j.fase}:${j.vista?.historia.length ?? 0}:${j.vista?.anio_en_curso?.decisiones.length ?? 0}:${j.vista?.pendiente?.decision ?? ""}`;
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [punto]);

  if (tutorial === "ayuda") {
    return <ComoFunciona textoListo="Volver a mi partida" onVolver={() => setTutorial(null)} onListo={() => setTutorial(null)} />;
  }
  if (tutorial === "antes") {
    return (
      <ComoFunciona
        onVolver={() => setTutorial(null)}
        onListo={() => {
          setTutorial(null);
          j.descartar();
          j.irAPerfil();
        }}
      />
    );
  }
  if (j.fase === "perfil") {
    return <Onboarding inicial={j.perfil} catalogo={catalogo} errorCatalogo={errorCatalogo} onVolver={j.irAInicio} onListo={j.empezarAlAzar} onElegirDuda={j.verDudas} cargando={j.cargando} error={j.error} />;
  }
  if (j.fase === "duda") {
    return (
      <DudaPicker perfil={j.perfil} dudas={j.dudas} sugeridas={j.dudasSugeridas} cargando={j.cargando} error={j.error} onVolver={j.irAPerfil} onElegir={j.empezar} />
    );
  }
  if (j.fase === "carta" && j.vista?.pendiente) {
    return (
      <Carta
        vista={j.vista}
        partida={j.partida}
        riesgo={j.perfil.riesgo}
        cargando={j.cargando}
        recalculando={j.recalculando}
        error={j.error}
        onElegir={j.elegir}
        onComparar={j.compararCon}
        onAyuda={() => setTutorial("ayuda")}
        onVerMundo={j.verMundo}
      />
    );
  }
  if (j.fase === "paso" && j.vista) return <QuePaso previa={j.previa} vista={j.vista} sueldoInicial={sueldoInicial} onSeguir={j.seguir} />;
  if (j.fase === "cierre" && j.vista?.cierre)
    return (
      <CierrePantalla
        vista={j.vista}
        sueldoInicial={sueldoInicial}
        perfil={j.partida?.perfil ?? j.perfil}
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
      onContinuar={j.continuar}
      onEmpezar={() => {
        j.descartar();
        j.irAPerfil();
      }}
      onComoFunciona={() => setTutorial("antes")}
    />
  );
}
