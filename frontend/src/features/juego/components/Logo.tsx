import { useState } from "react";

/** Color estable por rubro o país: el mismo nombre da siempre el mismo tono. */
function tono(clave: string): number {
  let h = 0;
  for (const c of clave) h = (h * 31 + c.charCodeAt(0)) % 360;
  return h;
}

function iniciales(nombre: string): string {
  const palabras = nombre.replace(/[^\p{L}\p{N} ]/gu, " ").split(/\s+/).filter((p) => p.length > 1 || /\p{Lu}/u.test(p));
  return (palabras.length > 1 ? palabras[0][0] + palabras[1][0] : (palabras[0] ?? "?").slice(0, 2)).toUpperCase();
}

/**
 * Logo de una empresa o institución: el ícono descargado (frontend/public/logos/...) o, si no hay o no
 * carga, un monograma con el color de su rubro.
 */
export function Logo({
  carpeta, id, nombre, grupo, hay, tamano = 32,
}: {
  carpeta: "empresas" | "universidades";
  id: string | number;
  nombre: string;
  /** Rubro (empresas) o país (universidades): define el color del monograma. */
  grupo: string;
  hay: boolean;
  tamano?: number;
}) {
  const [fallo, setFallo] = useState(false);
  if (hay && !fallo) {
    return (
      <img
        className="jg-logo"
        src={`/logos/${carpeta}/${id}.png`}
        alt=""
        width={tamano}
        height={tamano}
        // margen y radio proporcionales: el logo no toca el borde y la baldosa se ve igual en cualquier tamaño
        style={{ padding: Math.round(tamano * 0.1), borderRadius: Math.round(tamano * 0.25) }}
        loading="lazy"
        onError={() => setFallo(true)}
      />
    );
  }
  const h = tono(grupo || nombre);
  return (
    <svg className="jg-logo jg-logo--iniciales" width={tamano} height={tamano} viewBox="0 0 32 32" aria-hidden="true">
      {/* tono de la empresa mezclado con el papel y la tinta del tema: pastel en claro, oscuro en oscuro */}
      <rect width="32" height="32" rx="8" style={{ fill: `color-mix(in srgb, hsl(${h} 60% 50%) 22%, var(--papel))` }} />
      <text x="16" y="21" textAnchor="middle" fontSize="13" fontWeight="700" fontFamily="inherit"
        style={{ fill: `color-mix(in srgb, hsl(${h} 55% 40%) 55%, var(--tinta))` }}>
        {iniciales(nombre)}
      </text>
    </svg>
  );
}
