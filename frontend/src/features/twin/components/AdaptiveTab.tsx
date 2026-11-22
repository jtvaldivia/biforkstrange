import { useState } from "react";
import { BigNumber, Button, Heading, Meta, Panel, Row, ScreenFooter, Stack, SunCard, Tag, Text } from "@/shared/ui";
import { twinApi } from "../api";
import type { TwinState } from "../hooks/useTwin";
import type { AdaptiveQuestion } from "../types";
import { ChoiceList, clarityOf, DimBar, SectionIntro } from "./parts";

const NONE = -1;

export function AdaptiveTab({ twin }: { twin: TwinState }) {
  const { profile, catalog, lastDeltas, setLastDeltas } = twin;
  const [question, setQuestion] = useState<AdaptiveQuestion | null>(null);
  const [choice, setChoice] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [clear, setClear] = useState(false);
  const [justAnswered, setJustAnswered] = useState(false);
  if (!profile) return null;

  const answered = profile.qs.filter((q) => q.ans !== null).length;
  const c = clarityOf(profile.dims);
  const name = (k: string) => catalog?.dims.find((d) => d.key === k)?.nombre ?? k;

  async function next() {
    setChoice(null);
    setNote("");
    setJustAnswered(false);
    const r = await twin.run((p) => twinApi.adaptiveNext(p.id, p.version), (r) => r.profile);
    if (!r) return;
    setQuestion(r.question);
    setClear(r.question === null);
    window.scrollTo({ top: 0 });
  }

  async function answer() {
    if (!question || choice === null) return;
    const r = await twin.run(
      (p) => twinApi.adaptiveAnswer(p.id, p.version, question.id, choice, note.trim() || undefined),
      (r) => r.profile,
    );
    if (!r) return;
    setLastDeltas(r.deltas);
    setQuestion(null);
    setJustAnswered(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  /* Pregunta abierta */
  if (question) {
    return (
      <Stack gap={20}>
        <Row gap={8} style={{ alignItems: "center", justifyContent: "space-between" }}>
          <Meta>Pregunta {answered + 1}</Meta>
          <Row gap={6}>
            {question.dims.map((k) => <Tag key={k} tone="accent">{name(k)}</Tag>)}
          </Row>
        </Row>
        <Heading level={2} as="h1" className="tw-question">{question.q}</Heading>
        <ChoiceList
          label="Opciones"
          options={question.opts}
          value={choice}
          onChange={setChoice}
          extra={{ value: NONE, label: "Ninguna me representa" }}
          disabled={twin.busy}
        />
        <label className="tw-field">
          <span className="vd-ind-n">¿Algún matiz? <span className="tw-soft">Opcional</span></span>
          <textarea
            className="tw-textarea"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Ej: depende de si el equipo es nuevo"
          />
        </label>
        <ScreenFooter>
          <Button onClick={answer} disabled={choice === null || twin.busy}>
            {twin.busy ? "Guardando…" : "Responder"}
          </Button>
        </ScreenFooter>
      </Stack>
    );
  }

  /* Entre preguntas */
  return (
    <Stack gap={20}>
      <SectionIntro eyebrow="Preguntas" title="Enséñale cómo decides.">
        Solo pregunta donde todavía tiene dudas. No hay respuestas correctas: elige lo que harías tú, no lo que
        suena mejor.
      </SectionIntro>

      {justAnswered && (
        <Panel className="tw-learned">
          <Stack gap={12}>
            <Heading level={3} as="h2">{lastDeltas.length ? "Esto aprendió" : "Lo preguntará de otra forma"}</Heading>
            {lastDeltas.length === 0 && <Text size="sm">Ninguna opción te representaba, así que no movió nada.</Text>}
            {lastDeltas.map((d) => (
              <Stack key={d.key} gap={4}>
                <DimBar
                  nombre={d.nombre}
                  dim={profile.dims[d.key]}
                  previous={d.antes}
                />
                <span className="tw-soft tw-mono">
                  {d.antes} → {d.despues} · duda ±{Math.round(d.sd_antes)} → ±{Math.round(d.sd_despues)}
                </span>
              </Stack>
            ))}
          </Stack>
        </Panel>
      )}

      {!justAnswered && (
        <SunCard className="tw-narrow-only">
          <Meta>Cuánto te conoce hoy</Meta>
          <BigNumber value={c.pct} unit="% de claridad" />
          <Text size="sm">
            {c.measured} de {c.total} rasgos ya medidos · {answered} {answered === 1 ? "respuesta" : "respuestas"}
          </Text>
        </SunCard>
      )}

      {clear ? (
        <Panel>
          <Heading level={3} as="h2">Tu perfil ya está claro.</Heading>
          <Text size="sm">
            Todos los rasgos tienen poco margen. Ponlo a prueba en el examen o genera tu informe en Perfil.
          </Text>
        </Panel>
      ) : (
        !justAnswered && (
          <Row gap={6}>
            <Tag>Una situación concreta</Tag>
            <Tag>3 o 4 opciones</Tag>
            <Tag>Menos de un minuto</Tag>
          </Row>
        )
      )}

      {!clear && (
        <ScreenFooter>
          <Button onClick={next} disabled={twin.busy}>
            {twin.busy ? "Pensando la pregunta…" : answered ? "Siguiente pregunta" : "Empezar"}
          </Button>
        </ScreenFooter>
      )}
    </Stack>
  );
}
