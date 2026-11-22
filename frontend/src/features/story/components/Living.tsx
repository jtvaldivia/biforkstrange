import { Meta, Narrative, Stack } from "@/shared/ui";
import type { Pending } from "../hooks/useStory";

/** Mientras el narrador escribe: el año pasando. */
export function Living({ p }: { p: Pending }) {
  const lines: Record<Pending["kind"], { meta: string; big: string; text: string }> = {
    start: { meta: "Empezando", big: "Hoy", text: "Leyendo dónde estás y pensando en lo que viene…" },
    year: {
      meta: p.kind === "year" ? p.eleccion : "",
      big: p.kind === "year" ? String(p.anio) : "",
      text: "Viviendo el año: lo que pasa, quién aparece, qué cambia…",
    },
    close: { meta: "Mirando hacia atrás", big: "Fin", text: "Juntando los años para contar tu historia completa…" },
  };
  const l = lines[p.kind];
  return (
    <div className="st-living vd-noche" role="status" aria-live="polite">
      <Stack gap={10} style={{ alignItems: "center", textAlign: "center" }}>
        <Meta>{l.meta}</Meta>
        <span className="st-living-big">{l.big}</span>
        <Narrative>{l.text}</Narrative>
        <span className="st-dots" aria-hidden="true"><i /><i /><i /></span>
      </Stack>
    </div>
  );
}
