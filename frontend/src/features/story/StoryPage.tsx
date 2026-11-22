import { useEffect, useState } from "react";
import { Button, Heading, Meta, Pill, SlowReveal, Stack, Text } from "@/shared/ui";
import { ChapterView, paragraphs } from "./components/ChapterView";
import { DilemmaView } from "./components/DilemmaView";
import { EpilogueView } from "./components/EpilogueView";
import { Living } from "./components/Living";
import { StartView } from "./components/StartView";
import { useStory } from "./hooks/useStory";
import type { Story } from "./types";
import "./story.css";

/**
 * Tu historia, capítulo a capítulo.
 * Teléfono: una columna. Escritorio: el capítulo al centro y "tu historia hasta ahora" a la izquierda,
 * para releer cualquier año sin perder dónde vas.
 */
export function StoryPage() {
  const st = useStory();
  const s = st.story;
  const [reading, setReading] = useState<number | null>(null); // capítulo pasado que se está releyendo

  useEffect(() => setReading(null), [s?.capitulos.length, s?.epilogo]);

  if (!st.loaded) return null;
  // el "viviendo el año" va encima: así nada de lo que escribiste se pierde si algo falla
  const overlay = st.pending ? <Living p={st.pending} /> : null;
  if (!s) return <>{overlay}<StartView st={st} /></>;

  const last = s.capitulos.at(-1);
  const shown = reading !== null ? s.capitulos[reading] : last;
  const nextAnio = s.inicio.anio + s.capitulos.length;
  const nextEdad = s.inicio.edad + s.capitulos.length + 1;

  return (
    <div className="st-layout">
      {overlay}
      <aside className="st-side" aria-label="Tu historia hasta ahora">
        <SoFar s={s} reading={reading} onRead={setReading} />
      </aside>

      <main className="st-main">
        {s.epilogo ? (
          <EpilogueView s={s} st={st} />
        ) : (
          <Stack gap={28}>
            {reading !== null && (
              <button type="button" className="st-back" onClick={() => setReading(null)}>← Volver a {nextAnio}</button>
            )}

            {!shown ? (
              <article className="st-chapter">
                <header className="st-chapter-head">
                  <Pill>{s.inicio.anio - 1} · {s.inicio.edad} años</Pill>
                  <Meta>Prólogo</Meta>
                </header>
                <Heading level={1} as="h2">{s.titulo}.</Heading>
                <div className="st-relato">
                  {paragraphs(s.prologo).map((p, i) => (
                    <SlowReveal key={i} delay={0.15 + i * 0.5}><p className="vd-relato">{p}</p></SlowReveal>
                  ))}
                </div>
              </article>
            ) : (
              <ChapterView c={shown} total={s.anios} />
            )}

            {reading === null && s.dilema && (
              <DilemmaView key={s.capitulos.length} d={s.dilema} anio={nextAnio} edad={nextEdad} st={st} />
            )}

            {reading === null && s.terminada && !s.epilogo && (
              <section className="st-dilemma">
                <Heading level={2}>Llegaste a los {s.inicio.edad + s.capitulos.length}.</Heading>
                <Text>Ya viviste los {s.anios} años. Mira hacia atrás y lee tu historia completa.</Text>
                {st.error && <p className="st-error" role="alert">{st.error}</p>}
                <div className="st-cta"><Button variant="sol" onClick={() => void st.close()}>Cerrar mi historia</Button></div>
              </section>
            )}

            {reading === null && !s.terminada && s.capitulos.length > 0 && (
              <div className="st-early">
                <button type="button" className="st-link" onClick={() => void st.close()}>Cerrar la historia aquí</button>
                <button type="button" className="st-link" onClick={st.restart}>Empezar de nuevo</button>
              </div>
            )}
          </Stack>
        )}
      </main>
    </div>
  );
}

function SoFar({ s, reading, onRead }: { s: Story; reading: number | null; onRead: (i: number | null) => void }) {
  const last = s.capitulos.at(-1);
  const hilo = (last ? last.hilo : s.hilo) ?? {};
  return (
    <Stack gap={16}>
      <Stack gap={4}>
        <Meta>Tu historia</Meta>
        <span className="st-side-title">{s.titulo || "Sin título"}</span>
        <span className="vd-p-sm">{s.capitulos.length} de {s.anios} años vividos</span>
      </Stack>
      <ol className="st-path">
        <li className="st-path-item st-path-item--start">
          <span className="st-path-dot" aria-hidden="true" />
          <span className="vd-meta">{s.inicio.edad} años · hoy</span>
          <span className="st-path-what">Donde partiste</span>
        </li>
        {s.capitulos.map((c, i) => {
          const current = reading === i || (reading === null && i === s.capitulos.length - 1);
          return (
            <li key={c.n} className={`st-path-item${c.tono === "noche" ? " is-night" : ""}`}>
              <span className="st-path-dot" aria-hidden="true" />
              <button type="button" className="st-path-btn" aria-current={current ? "step" : undefined}
                onClick={() => onRead(i === s.capitulos.length - 1 ? null : i)}>
                <span className="vd-meta">{c.anio} · {c.edad} años</span>
                <span className="st-path-what">{c.titulo}</span>
                <span className="vd-p-sm">{c.eleccion}</span>
              </button>
            </li>
          );
        })}
        {!s.terminada && (
          <li className="st-path-item st-path-item--next">
            <span className="st-path-dot" aria-hidden="true" />
            <span className="vd-meta">{s.inicio.anio + s.capitulos.length}</span>
            <span className="st-path-what">Por decidir</span>
          </li>
        )}
      </ol>
      {(last || s.hilo?.donde) && (
        <div className="st-side-now">
          <Meta>Dónde estás</Meta>
          {hilo.donde && <span className="vd-p-sm"><strong>Vives:</strong> {hilo.donde}</span>}
          {hilo.vinculos && <span className="vd-p-sm"><strong>Tu gente:</strong> {hilo.vinculos}</span>}
          {hilo.en_curso && <span className="vd-p-sm"><strong>Quedó abierto:</strong> {hilo.en_curso}</span>}
          {last && Object.entries(last.estado).map(([k, v]) => (
            <span key={k} className="vd-p-sm"><strong>{LABEL[k] ?? k}:</strong> {v}</span>
          ))}
        </div>
      )}
    </Stack>
  );
}

const LABEL: Record<string, string> = { trabajo: "Trabajo", plata: "Plata", energia: "Energía", vida: "Tu vida" };
