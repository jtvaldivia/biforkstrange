import { useState } from "react";
import { Button, DecisionArt, DecisionCard, Heading, Meta, Stack, Text, type DecisionArtKind } from "@/shared/ui";
import type { StoryState } from "../hooks/useStory";
import type { Dilemma } from "../types";

const ART: Record<string, DecisionArtKind> = {
  sabatico: "viaje",
  cambiar_pega: "consultora",
  trabajar_mas: "consultora",
  trabajar_menos: "viaje",
  estudiar: "magister",
  seguir: "invertir",
};

const OWN = "__propia__";

/** La decisión del año: opciones pensadas para ti, o lo que tú harías con tus palabras. */
export function DilemmaView({ d, anio, edad, st }: { d: Dilemma; anio: number; edad: number; st: StoryState }) {
  const [sel, setSel] = useState<string | null>(null);
  const [own, setOwn] = useState("");
  const opt = d.opciones.find((o) => o.id === sel);
  const canGo = sel === OWN ? own.trim().length >= 4 : !!opt;

  const go = () => {
    if (sel === OWN) void st.choose({ texto: own.trim() }, own.trim());
    else if (opt) void st.choose({ option_id: opt.id }, opt.titulo);
  };

  return (
    <section className="st-dilemma" aria-labelledby="st-dilemma-q">
      <Stack gap={8}>
        <Meta>{anio} · cumples {edad}</Meta>
        <Text>{d.situacion}</Text>
        <Heading level={2} id="st-dilemma-q">{d.pregunta}</Heading>
      </Stack>
      <div className="st-options" role="group" aria-label="Caminos posibles">
        {d.opciones.map((o) => (
          <DecisionCard
            key={o.id}
            art={<DecisionArt kind={ART[o.decision] ?? "invertir"} />}
            title={o.titulo}
            subtitle={o.detalle}
            selected={sel === o.id}
            onSelect={() => setSel(o.id)}
          />
        ))}
        <button type="button" className="vd-opcion st-own" aria-pressed={sel === OWN} onClick={() => setSel(OWN)}>
          <span className="st-own-mark" aria-hidden="true">✎</span>
          <span className="vd-opcion-texto">
            <span className="vd-opcion-titulo">Otra cosa</span>
            <span className="vd-opcion-sub">Escribe lo que harías tú</span>
          </span>
        </button>
      </div>
      {sel === OWN && (
        <textarea className="st-textarea" rows={3} autoFocus value={own} onChange={(e) => setOwn(e.target.value)}
          placeholder="Ej: Le pido a mi jefa trabajar cuatro días y vuelvo al fútbol de los martes" />
      )}
      {st.error && <p className="st-error" role="alert">{st.error}</p>}
      <div className="st-cta">
        <Button onClick={go} disabled={!canGo || st.pending !== null}>Vivir {anio}</Button>
      </div>
    </section>
  );
}
