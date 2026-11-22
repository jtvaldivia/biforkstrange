import { useCallback, useEffect, useState } from "react";
import { StaleStoryError, storyApi } from "../api";
import type { StartInput, Story } from "../types";

const STORY_KEY = "biforkstrange.storyId";
const TWIN_KEY = "biforkstrange.twinProfileId"; // lo guarda el módulo del gemelo

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* sin storage: la historia dura lo que dure la pestaña */
  }
}

export type Pending = { kind: "start" } | { kind: "year"; anio: number; eleccion: string } | { kind: "close" };

/** Estado de la historia en curso. Se retoma al volver (el id queda en el navegador). */
export function useStory() {
  const [story, setStory] = useState<Story | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const [error, setError] = useState("");
  const twinId = read(TWIN_KEY);

  useEffect(() => {
    const id = read(STORY_KEY);
    if (!id) return setLoaded(true);
    storyApi
      .get(id)
      .then(setStory)
      .catch(() => write(STORY_KEY, null))
      .finally(() => setLoaded(true));
  }, []);

  const wrap = useCallback(async (p: Pending, fn: () => Promise<Story>) => {
    setPending(p);
    setError("");
    try {
      const s = await fn();
      setStory(s);
      write(STORY_KEY, s.id);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return true;
    } catch (e) {
      if (e instanceof StaleStoryError) setStory(e.current);
      else setError(e instanceof Error ? e.message : String(e));
      return false;
    } finally {
      setPending(null);
    }
  }, []);

  return {
    story, loaded, pending, error, twinId,
    start: (input: Omit<StartInput, "profile_id">) =>
      wrap({ kind: "start" }, () => storyApi.start({ ...input, profile_id: twinId })),
    choose: (choice: { option_id?: string; texto?: string }, eleccion: string) => {
      if (!story) return Promise.resolve(false);
      const anio = story.inicio.anio + story.capitulos.length;
      return wrap({ kind: "year", anio, eleccion }, () => storyApi.choose(story.id, story.capitulos.length, choice));
    },
    close: () => (story ? wrap({ kind: "close" }, () => storyApi.close(story.id)) : Promise.resolve(false)),
    restart: () => {
      write(STORY_KEY, null);
      setStory(null);
      window.scrollTo({ top: 0 });
    },
  };
}

export type StoryState = ReturnType<typeof useStory>;
