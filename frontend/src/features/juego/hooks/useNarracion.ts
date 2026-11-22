import { useEffect, useState } from "react";
import type { Narrado } from "../types";

/**
 * Textos contados por Sonnet para lo que hay en pantalla. Mientras no llegan (o si Sonnet no está), la
 * pantalla muestra su plantilla: este hook solo reemplaza. Si cambia `llave` antes de que respondan,
 * el pedido anterior se cancela.
 */
export function useNarracion(
  pedir: ((signal: AbortSignal) => Promise<{ items: Narrado[] }>) | null,
  llave: string,
): Record<string, string> {
  const [textos, setTextos] = useState<Record<string, string>>({});
  useEffect(() => {
    setTextos({});
    if (!pedir) return;
    const control = new AbortController();
    pedir(control.signal)
      .then(({ items }) => {
        if (control.signal.aborted) return;
        // solo lo que contó Sonnet: la plantilla ya está en pantalla
        setTextos(Object.fromEntries(items.filter((x) => x.via === "sonnet").map((x) => [x.id, x.texto])));
      })
      .catch(() => {
        /* sin narración: queda la plantilla */
      });
    return () => control.abort();
    // `pedir` cambia con cada render del padre; la llave dice cuándo hay algo nuevo que narrar
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [llave]);
  return textos;
}
