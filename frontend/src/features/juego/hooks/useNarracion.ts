import { useEffect, useState } from "react";
import type { Narrado } from "../types";

export type Narracion = {
  /** Los textos que contó Claude, por id. Lo que no está aquí se muestra con su plantilla. */
  textos: Record<string, string>;
  /** Ya respondió el narrador (o falló, o no hay narrador): lo que se muestre ahora no cambia más. */
  listo: boolean;
};

/**
 * Textos contados por Claude para lo que hay en pantalla. La pantalla espera a `listo` antes de mostrar
 * esos textos, para que nunca aparezca la plantilla y después cambie. El servidor corta a los 10 segundos;
 * si falla, `listo` llega igual y queda la plantilla. Si cambia `llave` antes de que respondan, el pedido
 * anterior se cancela.
 */
export function useNarracion(
  pedir: ((signal: AbortSignal) => Promise<{ items: Narrado[] }>) | null,
  llave: string,
): Narracion {
  const [estado, setEstado] = useState<{ llave: string; textos: Record<string, string> } | null>(null);
  useEffect(() => {
    if (!pedir) return;
    const control = new AbortController();
    const terminar = (textos: Record<string, string>) => {
      if (!control.signal.aborted) setEstado({ llave, textos });
    };
    pedir(control.signal)
      .then(({ items }) => terminar(Object.fromEntries(items.filter((x) => x.via !== "plantilla").map((x) => [x.id, x.texto]))))
      .catch(() => terminar({})); // sin narración: queda la plantilla
    return () => control.abort();
    // `pedir` cambia con cada render del padre; la llave dice cuándo hay algo nuevo que narrar
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [llave]);
  if (!pedir) return { textos: {}, listo: true };
  // lo que quedó de la llave anterior no sirve: hasta que llegue lo nuevo, no está listo
  return estado?.llave === llave ? { textos: estado.textos, listo: true } : { textos: {}, listo: false };
}
