import { useCallback, useEffect, useState } from "react";
import { getCatalogo, textoError } from "../api";
import type { Catalogo } from "../types";

export function useCatalogo() {
  const [catalogo, setCatalogo] = useState<Catalogo | null>(null);
  const [error, setError] = useState<string | null>(null);
  /** Cada reintento vuelve a pedirlo: si el backend estaba caído al cargar la página, no hay que recargarla. */
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    let vivo = true;
    setError(null);
    getCatalogo()
      .then((c) => vivo && setCatalogo(c))
      .catch((e: unknown) => vivo && setError(textoError(e)));
    return () => {
      vivo = false;
    };
  }, [intento]);

  const reintentar = useCallback(() => setIntento((n) => n + 1), []);
  return { catalogo, error, reintentar };
}
