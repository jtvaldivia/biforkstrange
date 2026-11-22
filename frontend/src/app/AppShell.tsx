import type { ReactNode } from "react";
import "./shell.css";

type Section = "historia" | "gemelo";

const LINKS: { id: Section; href: string; label: string }[] = [
  { id: "historia", href: "/", label: "Tu historia" },
  { id: "gemelo", href: "/gemelo", label: "Tu gemelo" },
];

/**
 * Carcasa de la app: barra superior con la marca y las secciones.
 * En teléfono la barra queda compacta y el contenido usa la columna del kit;
 * en escritorio el contenido se abre en columnas (cada página decide cómo).
 */
export function AppShell({ active, children }: { active: Section; children: ReactNode }) {
  return (
    <div className="vd sh">
      <header className="sh-top">
        <div className="sh-top-in">
          <a href="/" className="sh-brand" aria-label="BiforkStrange, inicio">
            <span className="sh-brand-dot" aria-hidden="true" />
            BiforkStrange
          </a>
          <nav className="sh-nav" aria-label="Secciones">
            {LINKS.map((l) => (
              <a key={l.id} href={l.href} className="sh-link" aria-current={l.id === active ? "page" : undefined}>
                {l.label}
              </a>
            ))}
          </nav>
        </div>
      </header>
      <main className="sh-main">{children}</main>
    </div>
  );
}
