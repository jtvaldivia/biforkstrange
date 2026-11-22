import { useCallback, useEffect, useRef, useState } from "react";
import { StaleProfileError, twinApi } from "../api";
import type { Catalog, Delta, Summary, TwinProfile } from "../types";

const STORAGE_KEY = "biforkstrange.twinProfileId";

function readId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeId(id: string) {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    /* sin storage: el perfil dura lo que dure la pestaña */
  }
}

/**
 * Perfil del gemelo + control de versión. Toda escritura pasa por `run`:
 * si otra pestaña guardó antes (409), carga la versión remota en vez de pisarla.
 */
export function useTwin() {
  const [profile, setProfile] = useState<TwinProfile | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [lastDeltas, setLastDeltas] = useState<Delta[]>([]);
  const profileRef = useRef<TwinProfile | null>(null);
  profileRef.current = profile;

  useEffect(() => {
    twinApi.catalog().then(setCatalog).catch((e) => setError(String(e)));
    const id = readId();
    const load = id ? twinApi.get(id).catch(() => twinApi.create()) : twinApi.create();
    load
      .then((p) => {
        writeId(p.id);
        setProfile(p);
      })
      .catch((e) => setError(String(e)));
  }, []);

  // métricas del panel: se recalculan cada vez que cambia la versión del perfil
  useEffect(() => {
    if (!profile) return;
    twinApi.summary(profile.id).then(setSummary).catch(() => {});
  }, [profile?.id, profile?.version]); // eslint-disable-line react-hooks/exhaustive-deps

  // al volver a la pestaña, trae la versión remota si es más nueva
  useEffect(() => {
    const onFocus = () => {
      const cur = profileRef.current;
      if (!cur) return;
      twinApi.get(cur.id).then((remote) => {
        if (remote.version > cur.version) {
          setProfile(remote);
          setNotice("Se cargaron cambios hechos en otra pestaña.");
        }
      }).catch(() => {});
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  /** Ejecuta una escritura con la versión actual. Devuelve el resultado o null si falló. */
  const run = useCallback(async <T,>(fn: (p: TwinProfile) => Promise<T>, pick: (r: T) => TwinProfile): Promise<T | null> => {
    const cur = profileRef.current;
    if (!cur) return null;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const r = await fn(cur);
      setProfile(pick(r));
      return r;
    } catch (e) {
      if (e instanceof StaleProfileError) {
        setProfile(e.current);
        setNotice(e.message);
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
      return null;
    } finally {
      setBusy(false);
    }
  }, []);

  const reset = useCallback(async () => {
    const p = await twinApi.create();
    writeId(p.id);
    setLastDeltas([]);
    setProfile(p);
  }, []);

  return { profile, catalog, summary, busy, error, notice, run, reset, setError, lastDeltas, setLastDeltas };
}

export type TwinState = ReturnType<typeof useTwin>;
