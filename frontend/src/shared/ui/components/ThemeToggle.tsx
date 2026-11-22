import { useTheme } from "../theme";
import { cx } from "../tokens";
import { MoonIcon, SunIcon } from "./Icon";

/**
 * Botón para pasar de modo claro a oscuro y de vuelta. Muestra el modo al que te lleva:
 * la luna en claro, el sol en oscuro. 44px de área tocable.
 * Va una sola vez, en App: queda arriba a la derecha de la página, en todas las pantallas.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();
  const oscuro = theme === "dark";
  return (
    <button
      type="button"
      className={cx("vd-tema", className)}
      aria-label={oscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      title={oscuro ? "Modo claro" : "Modo oscuro"}
      onClick={toggleTheme}
    >
      <span>{oscuro ? <SunIcon size={18} /> : <MoonIcon size={18} />}</span>
    </button>
  );
}
