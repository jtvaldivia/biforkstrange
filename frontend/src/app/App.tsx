import { JuegoPage } from "@/features/juego";
import { ThemeToggle } from "@/shared/ui";

export default function App() {
  return (
    <>
      {/* Modo claro / oscuro, el mismo botón en todas las rutas */}
      <ThemeToggle />
      <JuegoPage />
    </>
  );
}
