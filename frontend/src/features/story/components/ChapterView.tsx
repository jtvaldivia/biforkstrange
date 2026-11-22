import { Heading, Meta, MissedList, NightBand, Notification, Pill, SlowReveal, Stack, SunCard } from "@/shared/ui";
import type { Chapter } from "../types";

const ESTADO: { key: keyof Chapter["estado"]; label: string }[] = [
  { key: "trabajo", label: "Trabajo" },
  { key: "plata", label: "Plata" },
  { key: "energia", label: "Energía" },
  { key: "vida", label: "Tu vida" },
];

export function paragraphs(text: string) {
  return text.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
}

/** Un año contado: relato, mensajes de tu gente, cómo quedaste, qué ganaste y qué dejaste. */
export function ChapterView({ c, total }: { c: Chapter; total: number }) {
  const night = c.tono === "noche";
  const momentos = [...c.momentos].sort((a, b) => a.hora.localeCompare(b.hora));
  return (
    <article className={`st-chapter${night ? " vd-noche st-chapter--noche" : ""}`}>
      <header className="st-chapter-head">
        <Pill>{c.anio} · {c.edad} años</Pill>
        <Meta>Capítulo {c.n} de {total}</Meta>
      </header>
      <Stack gap={6}>
        <Meta>Elegiste: {c.eleccion}</Meta>
        <Heading level={1} as="h2">{c.titulo}.</Heading>
      </Stack>

      <div className="st-relato">
        {paragraphs(c.relato).map((p, i) => (
          <SlowReveal key={i} delay={0.15 + i * 0.5}><p className="vd-relato">{p}</p></SlowReveal>
        ))}
      </div>

      {momentos.length > 0 && (
        <Stack gap={8} aria-label="Mensajes de tu gente este año">
          {momentos.map((m, i) => (
            <Notification key={i} from={m.de} message={m.texto} time={m.hora} />
          ))}
        </Stack>
      )}

      <div className="st-estado" aria-label="Cómo quedaste este año">
        {ESTADO.filter((e) => c.estado[e.key]).map((e) => (
          <div key={e.key} className="st-estado-item">
            <span className="vd-meta">{e.label}</span>
            <span className="st-estado-word">{c.estado[e.key]}</span>
          </div>
        ))}
      </div>

      <div className="st-balance">
        {c.ganaste && (
          <SunCard>
            <Meta>Lo que ganaste</Meta>
            <p className="st-balance-text">{c.ganaste}</p>
          </SunCard>
        )}
        {c.dejaste && (
          <NightBand>
            <Meta>Lo que dejaste ir</Meta>
            <MissedList items={[c.dejaste]} />
          </NightBand>
        )}
      </div>
    </article>
  );
}
