import { GamePage } from "@/features/game";
import { SimulationPage } from "@/features/simulation";
import { UiKitPage } from "@/features/ui-kit";

export default function App() {
  // Sin router por ahora: /ui es el catálogo del kit y /simple, la prueba mínima de la API
  const ruta = window.location.pathname;
  if (ruta.startsWith("/ui")) return <UiKitPage />;
  if (ruta.startsWith("/simple"))
    return (
      <main style={{ fontFamily: "system-ui", maxWidth: 720, margin: "2rem auto", padding: "0 1rem" }}>
        <h1>BiforkStrange</h1>
        <SimulationPage />
      </main>
    );
  return <GamePage />;
}
