import { useState } from "react";
import { BigNumber, Button, Heading, Meta, Panel, Row, Stack, SunCard, Tag, Text } from "@/shared/ui";
import { twinApi } from "../api";
import type { TwinState } from "../hooks/useTwin";
import type { Patron } from "../types";
import { Meter, SectionIntro } from "./parts";

const MIN_FOR_RECALIBRATION = 4;

export function PanelTab({ twin }: { twin: TwinState }) {
  const { summary } = twin;
  if (!summary) return <Text size="sm">Cargando…</Text>;
  const ex = summary.examen;

  return (
    <Stack gap={28}>
      <SectionIntro eyebrow="Panel" title="Cuánto te conoce.">
        Todo sale de tus respuestas reales en el examen a ciegas, no de lo que la IA dice saber.
      </SectionIntro>

      {ex.n === 0 ? (
        <Panel>
          <Heading level={3} as="h2">Todavía no hay examen.</Heading>
          <Text size="sm">Responde un par de preguntas en Examen y aquí verás si te lee mejor que el azar.</Text>
        </Panel>
      ) : (
        <>
          <SunCard>
            <Meta>Acierto a ciegas</Meta>
            <BigNumber value={ex.acierto} unit="%" />
            <Text size="sm">Al azar acertaría {ex.azar}% · {ex.n} {ex.n === 1 ? "pregunta" : "preguntas"}</Text>
          </SunCard>

          <div className="tw-stats">
            <Stat value={`${ex.p_media}%`} label="Probabilidad media que le dio a tu respuesta" />
            <Stat value={String(ex.log_score)} label="Log-score · menor es mejor" />
            <Stat value={String(ex.brier)} label="Brier · menor es mejor" />
          </div>

          {ex.tendencia.length > 1 && (
            <Stack gap={8}>
              <Heading level={3} as="h2">¿Mejora con el tiempo?</Heading>
              <Trend values={ex.tendencia} chance={ex.azar ?? 0} />
            </Stack>
          )}

          <div className="tw-two">
            <Stack gap={12}>
              <Heading level={3} as="h2">Calibración</Heading>
              <Text size="sm">Cuando dice estar X% seguro, ¿acierta X%? La rayita es lo que dice; la barra, lo que acierta.</Text>
              {ex.calibracion.map((c) => (
                <Meter key={c.rango} label={`Dice ${c.rango} · ${c.n}`} value={c.acierto} marker={c.confianza} />
              ))}
            </Stack>
            <Stack gap={12}>
              <Heading level={3} as="h2">Acierto por tema</Heading>
              <Text size="sm">La rayita es el azar. El examen automático pregunta donde más falla.</Text>
              {ex.por_tema.map((t) => (
                <Meter key={t.tema} label={`${t.label} · ${t.n}`} value={t.acierto} tone="sol" marker={ex.azar ?? undefined} />
              ))}
            </Stack>
          </div>
        </>
      )}

      <Recalibrate twin={twin} />

      <Stack gap={12}>
        <Heading level={2}>Dónde calzarías</Heading>
        <Text size="sm">
          50 es neutro. La banda es el margen: se angosta a medida que respondes. Claridad del perfil:{" "}
          <strong>{summary.claridad.claridad}%</strong> ({summary.claridad.medidas} de {summary.claridad.total} rasgos medidos).
        </Text>
        <div className="tw-fits">
          {summary.ajuste.map((f) => (
            <Panel key={f.trabajo} className="tw-fit">
              <div className="tw-dim-top">
                <span className="vd-ind-n">{f.trabajo}</span>
                <span className="tw-dim-val">{Math.round(f.score)} ±{Math.round(f.margen)}</span>
              </div>
              <span className="tw-track" aria-hidden="true">
                <span className="tw-mid" />
                <span className="tw-band" style={{ left: `${Math.max(0, f.score - f.margen)}%`, width: `${Math.min(100, f.score + f.margen) - Math.max(0, f.score - f.margen)}%` }} />
                <span className="tw-mark" style={{ left: `${f.score}%` }} />
              </span>
              {(f.suman.length > 0 || f.restan.length > 0) && (
                <Row gap={4}>
                  {f.suman.map((s) => <Tag key={s} tone="accent">+ {s}</Tag>)}
                  {f.restan.map((s) => <Tag key={s} tone="minus">− {s}</Tag>)}
                </Row>
              )}
            </Panel>
          ))}
        </div>
      </Stack>
    </Stack>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="tw-stat">
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}

/** Media móvil del acierto, con la línea del azar. */
function Trend({ values, chance }: { values: number[]; chance: number }) {
  const w = 320, h = 110, pad = 6;
  const x = (i: number) => pad + (i / (values.length - 1)) * (w - 2 * pad);
  const y = (v: number) => h - pad - (v / 100) * (h - 2 * pad);
  const d = values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <figure className="tw-trend">
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="Tendencia del acierto contra el azar">
        <line x1={pad} x2={w - pad} y1={y(chance)} y2={y(chance)} stroke="var(--control)" strokeWidth={1.5} strokeDasharray="3 5" />
        <path d={d} fill="none" stroke="var(--tinta)" strokeWidth={3.5} strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={x(values.length - 1)} cy={y(values[values.length - 1])} r={5} fill="var(--sol)" stroke="var(--tinta)" strokeWidth={2} />
      </svg>
      <figcaption className="vd-meta">Acierto, media de las últimas 10 · punteado: azar</figcaption>
    </figure>
  );
}

function Recalibrate({ twin }: { twin: TwinState }) {
  const { profile } = twin;
  const [draft, setDraft] = useState<Patron[] | null>(null);
  const [loading, setLoading] = useState(false);
  if (!profile) return null;
  const count = profile.corrections.length;
  const current = profile.notes.filter((n) => n.q.startsWith("Calibración:"));

  async function propose() {
    if (!profile) return;
    setLoading(true);
    twin.setError("");
    try {
      setDraft((await twinApi.proposeCalibration(profile.id)).patrones);
    } catch (e) {
      twin.setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function save() {
    if (!draft) return;
    const ok = await twin.run((p) => twinApi.saveCalibration(p.id, p.version, draft), (r) => r);
    if (ok) setDraft(null);
  }

  const edit = (i: number, patch: Partial<Patron>) =>
    setDraft((d) => d && d.map((x, j) => (j === i ? { ...x, ...patch } : x)));

  return (
    <Stack gap={12}>
      <Heading level={2}>Recalibrar</Heading>
      <Text size="sm">
        Busca patrones en lo que acertó y falló. Tú los revisas y editas antes de guardar; reemplazan la calibración
        anterior y pesan más que lo que contaste de ti.
      </Text>
      {current.length > 0 && !draft && (
        <Panel>
          <Meta>Calibración actual</Meta>
          {current.map((n, i) => (
            <Text key={i} size="sm">
              <strong>{n.q.replace("Calibración:", "").trim()}.</strong> {n.a}
            </Text>
          ))}
        </Panel>
      )}
      {draft ? (
        <Stack gap={12}>
          {draft.length === 0 && <Text size="sm">No encontró patrones claros todavía.</Text>}
          {draft.map((x, i) => (
            <Panel key={i}>
              <input className="tw-input" aria-label="Tema" value={x.tema} onChange={(e) => edit(i, { tema: e.target.value })} />
              <textarea className="tw-textarea" aria-label="Patrón" value={x.patron} onChange={(e) => edit(i, { patron: e.target.value })} />
              <Text size="sm">Evidencia: {x.evidencia}</Text>
              <div>
                <button type="button" className="tw-link" onClick={() => setDraft((d) => d && d.filter((_, j) => j !== i))}>
                  Quitar este patrón
                </button>
              </div>
            </Panel>
          ))}
          <div className="tw-actions">
            <Button onClick={save} disabled={twin.busy}>Guardar calibración</Button>
            <Button variant="white" onClick={() => setDraft(null)}>Cancelar</Button>
          </div>
        </Stack>
      ) : (
        <div className="tw-actions">
          <Button variant="white" onClick={propose} disabled={loading || count < MIN_FOR_RECALIBRATION}>
            {loading
              ? "Analizando tus respuestas…"
              : count < MIN_FOR_RECALIBRATION
                ? `Faltan ${MIN_FOR_RECALIBRATION - count} respuestas del examen`
                : "Recalibrar con mis respuestas"}
          </Button>
        </div>
      )}
    </Stack>
  );
}
