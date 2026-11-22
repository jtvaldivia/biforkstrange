import { useEffect, useMemo, useRef, useState } from "react";
import type { EleccionInterna } from "../types";

type Valor = string | number;

/**
 * Lo que se elige dentro de una opción (a qué rubro, a qué región), en una hoja que sube desde abajo:
 * una pregunta a la vez, la de por defecto primero y un buscador si la lista es larga.
 * Así la carta no se llena de chips ni salta de lugar.
 */
export function HojaEleccion({
  titulo,
  preguntas,
  paso,
  valores,
  porDefecto,
  onElegir,
  onPorDefecto,
  onCerrar,
}: {
  /** El nombre de la opción: "Cambiarte de rubro". */
  titulo: string;
  preguntas: EleccionInterna[];
  paso: number;
  valores: Record<string, Valor>;
  /** Lo que la simulación usa si no eliges nada. */
  porDefecto: (variable: string) => Valor | undefined;
  onElegir: (variable: string, valor: Valor) => void;
  onPorDefecto: () => void;
  onCerrar: () => void;
}) {
  const p = preguntas[paso];
  const [filtro, setFiltro] = useState("");
  const hoja = useRef<HTMLDivElement>(null);

  useEffect(() => setFiltro(""), [paso]);
  useEffect(() => {
    hoja.current?.focus();
    const antes = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = antes;
    };
  }, []);

  const def = p ? porDefecto(p.variable) : undefined;
  const orden = useMemo(
    () => (p ? [...p.alternativas].sort((a, b) => Number(b.valor === def) - Number(a.valor === def) || (b.prob ?? 0) - (a.prob ?? 0)) : []),
    [p, def],
  );
  if (!p) return null;
  const q = filtro.trim().toLowerCase();
  const lista = q ? orden.filter((a) => a.nombre.toLowerCase().includes(q)) : orden;

  return (
    <div className="jg-hoja-fondo" onClick={onCerrar}>
      <div
        ref={hoja}
        className="jg-hoja"
        role="dialog"
        aria-modal="true"
        aria-label={p.pregunta}
        tabIndex={-1}
        onClick={(ev) => ev.stopPropagation()}
        onKeyDown={(ev) => ev.key === "Escape" && onCerrar()}
      >
        <div className="jg-hoja-cabeza">
          <span className="vd-meta">
            {titulo}
            {preguntas.length > 1 ? ` · ${paso + 1} de ${preguntas.length}` : ""}
          </span>
          <button type="button" className="jg-ayuda" onClick={onCerrar}>
            Cerrar
          </button>
        </div>
        <h2 className="vd-h3">{p.pregunta}</h2>
        {p.alternativas.length > 8 && (
          <input className="jg-campo" type="search" placeholder="Buscar" aria-label="Buscar" value={filtro} onChange={(ev) => setFiltro(ev.target.value)} />
        )}
        <div className="jg-hoja-lista" role="group" aria-label={p.pregunta}>
          {lista.map((a) => (
            <button
              type="button"
              key={String(a.valor)}
              className="jg-hoja-item"
              aria-pressed={valores[p.variable] === a.valor}
              onClick={() => onElegir(p.variable, a.valor)}
            >
              <span>{a.nombre}</span>
              {a.valor === def && <small>Por defecto</small>}
            </button>
          ))}
          {lista.length === 0 && <span className="jg-chico">Nada con «{filtro}».</span>}
        </div>
        <button type="button" className="vd-btn vd-btn--quieto" onClick={onPorDefecto}>
          Usar lo de por defecto
        </button>
      </div>
    </div>
  );
}
