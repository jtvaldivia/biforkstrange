import { Button, Heading, Meta, MissedList, NightBand, Pill, SlowReveal, Stack, SunCard } from "@/shared/ui";
import type { StoryState } from "../hooks/useStory";
import type { Story } from "../types";
import { ChapterView, paragraphs } from "./ChapterView";

/** El cierre: quién eres ahora, lo que ganaste, lo que no vuelve, y la historia completa para releer. */
export function EpilogueView({ s, st }: { s: Story; st: StoryState }) {
  const e = s.epilogo!;
  const last = s.capitulos.at(-1)!;
  return (
    <Stack gap={28}>
      <article className="st-chapter vd-noche st-chapter--noche">
        <header className="st-chapter-head">
          <Pill>{s.inicio.anio} → {last.anio}</Pill>
          <Meta>Fin de tu historia</Meta>
        </header>
        <Heading level={1} as="h2">{e.titulo}.</Heading>
        <div className="st-relato">
          {paragraphs(e.relato).map((p, i) => (
            <SlowReveal key={i} delay={0.2 + i * 0.6}><p className="vd-relato">{p}</p></SlowReveal>
          ))}
        </div>
      </article>

      <div className="st-balance">
        <SunCard>
          <Meta>Lo que estos años te dieron</Meta>
          <ul className="st-list">{e.lo_que_ganaste.map((x, i) => <li key={i}>{x}</li>)}</ul>
        </SunCard>
        <NightBand>
          <Meta>Lo que no vuelve</Meta>
          <MissedList items={e.lo_que_no_vuelve} />
        </NightBand>
      </div>

      <div className="st-cta">
        <Button variant="sol" onClick={st.restart}>Vivir otra historia</Button>
      </div>

      <Stack gap={16}>
        <Heading level={2}>Tu historia completa</Heading>
        <p className="vd-relato">{s.prologo}</p>
        {s.capitulos.map((c) => (
          <details key={c.n} className="st-reread">
            <summary>
              <span className="vd-meta">{c.anio} · {c.edad} años</span>
              <span className="st-reread-title">{c.titulo}</span>
              <span className="vd-p-sm">{c.eleccion}</span>
            </summary>
            <ChapterView c={c} total={s.anios} />
          </details>
        ))}
      </Stack>
    </Stack>
  );
}
