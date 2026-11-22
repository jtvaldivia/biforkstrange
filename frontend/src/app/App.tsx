import { JuegoPage } from "@/features/juego";
import { SimulationPage } from "@/features/simulation";
import { UiKitPage } from "@/features/ui-kit";
import { ThemeToggle } from "@/shared/ui";

export default function App() {
  return (
    <>
      {/* Modo claro / oscuro, el mismo botón en todas las rutas */}
      <ThemeToggle />
      <Ruta />
    </>
  );
}

function Ruta() {
  const ruta = window.location.pathname;

  // Catálogo del kit de UI en /ui (sin router por ahora)
  if (ruta.startsWith("/ui")) return <UiKitPage />;

  // La simulación del esqueleto, que antes era la pantalla principal
  if (ruta.startsWith("/simulacion")) {
    return (
      <main style={{ fontFamily: "system-ui", maxWidth: 720, margin: "2rem auto", padding: "0 1rem" }}>
        <h1>Bifurca</h1>
        <p>
          <a href="/">Ir al juego</a> · <a href="/ui">Ver el kit de UI</a>
        </p>
        <SimulationPage />
      </main>
    );
  }

  // Pantalla principal: el juego
  return <JuegoPage />;
}
