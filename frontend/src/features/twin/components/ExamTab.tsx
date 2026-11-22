import { useState } from "react";
import {
  BigNumber, Button, Chip, Heading, Meta, NightBand, Row, ScreenFooter, Stack, SunCard, Tag, Text,
} from "@/shared/ui";
import { twinApi } from "../api";
import type { TwinState } from "../hooks/useTwin";
import type { ExamItem, ExamQuestion } from "../types";
import { ChoiceList, SectionIntro } from "./parts";

const OTHER = -1;

export function ExamTab({ twin }: { twin: TwinState }) {
  const temas = twin.catalog?.temas ?? {};
  const [tema, setTema] = useState("auto");
  const [question, setQuestion] = useState<ExamQuestion | null>(null);
  const [choice, setChoice] = useState<number | null>(null);
  const [other, setOther] = useState("");
  const [why, setWhy] = useState("");
  const [reveal, setReveal] = useState<ExamItem | null>(null);
  const done = twin.profile?.exam.filter((e) => e.ans !== null).length ?? 0;

  async function next() {
    setReveal(null);
    setChoice(null);
    setOther("");
    setWhy("");
    const r = await twin.run((p) => twinApi.examNext(p.id, p.version, tema), (r) => r.profile);
    if (r) {
      setQuestion(r.question);
      window.scrollTo({ top: 0 });
    }
  }

  async function answer() {
    if (!question || choice === null) return;
    const r = await twin.run(
      (p) =>
        twinApi.examAnswer(
          p.id, p.version, question.id, choice,
          choice === OTHER ? other.trim() : undefined, why.trim() || undefined,
        ),
      (r) => r.profile,
    );
    if (!r) return;
    setReveal(r.reveal);
    setQuestion(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const canSubmit = choice !== null && (choice !== OTHER || other.trim().length > 0);

  /* Pregunta abierta: la predicción ya está guardada */
  if (question) {
    return (
      <Stack gap={20}>
        <Row gap={8} style={{ alignItems: "center", justifyContent: "space-between" }}>
          <Meta>Examen · pregunta {done + 1}</Meta>
          <Tag tone="sol">{temas[question.tema] ?? question.tema}</Tag>
        </Row>
        <NightBand>
          <Row gap={10} style={{ alignItems: "center" }}>
            <span className="tw-seal" aria-hidden="true" />
            <Text size="sm" style={{ color: "inherit" }}>
              Tu gemelo ya apostó cómo vas a responder. Su predicción está guardada y la verás después.
            </Text>
          </Row>
        </NightBand>
        <Heading level={2} as="h1" className="tw-question">{question.q}</Heading>
        <ChoiceList
          label="Opciones"
          options={question.opts}
          value={choice}
          onChange={setChoice}
          extra={{ value: OTHER, label: "Otra cosa…" }}
          disabled={twin.busy}
        />
        {choice === OTHER && (
          <label className="tw-field">
            <span className="vd-ind-n">¿Qué harías tú?</span>
            <input className="tw-input" value={other} onChange={(e) => setOther(e.target.value)} autoFocus />
          </label>
        )}
        <label className="tw-field">
          <span className="vd-ind-n">¿Por qué? <span className="tw-soft">Opcional, pero es lo que más le enseña</span></span>
          <textarea className="tw-textarea" value={why} onChange={(e) => setWhy(e.target.value)} />
        </label>
        <ScreenFooter>
          <Button onClick={answer} disabled={!canSubmit || twin.busy}>
            {twin.busy ? "Guardando…" : "Responder y ver su apuesta"}
          </Button>
        </ScreenFooter>
      </Stack>
    );
  }

  return (
    <Stack gap={20}>
      {reveal ? (
        <Reveal item={reveal} />
      ) : (
        <SectionIntro eyebrow="Examen a ciegas" title="¿Cuánto te conoce?">
          Te hace una pregunta, apuesta en secreto qué vas a responder y después te muestra si te leyó. Así se mide
          de verdad, no con lo que la IA dice saber.
        </SectionIntro>
      )}

      <Stack gap={10}>
        <span className="vd-ind-n">Tema de la próxima</span>
        <Row gap={8}>
          <Chip pressed={tema === "auto"} onToggle={() => setTema("auto")}>Donde más falla</Chip>
          {Object.entries(temas).map(([k, label]) => (
            <Chip key={k} pressed={tema === k} onToggle={() => setTema(k)}>{label}</Chip>
          ))}
        </Row>
      </Stack>

      <ScreenFooter>
        <Button onClick={next} disabled={twin.busy}>
          {twin.busy ? "Tu gemelo está apostando…" : reveal ? "Otra pregunta" : "Hacer una pregunta"}
        </Button>
      </ScreenFooter>
    </Stack>
  );
}

function Reveal({ item }: { item: ExamItem }) {
  const Card = item.hit ? SunCard : NightBand;
  return (
    <Stack gap={16}>
      <Card className="tw-verdict">
        <Meta>{item.hit ? "Acertó" : "Falló"}</Meta>
        <Heading level={2} as="h1">{item.hit ? "Te leyó." : "Esta vez no te leyó."}</Heading>
        <BigNumber value={Math.round(item.p_ans ?? 0)} unit="% le dio a tu respuesta" />
      </Card>
      <Text style={{ fontWeight: 600 }}>{item.q}</Text>
      <div className="tw-bets">
        {item.opts.map((o, i) => (
          <Bet key={i} label={o} pct={item.probs[i]} top={i === item.top} you={i === item.ans} />
        ))}
        {item.ans === -1 && <Bet label={`Otra: ${item.ans_text}`} pct={0} top={false} you />}
      </div>
      <Stack gap={4}>
        <Meta>Lo que pensó</Meta>
        <p className="vd-relato tw-thought">“{item.pq}”</p>
      </Stack>
    </Stack>
  );
}

function Bet({ label, pct, top, you }: { label: string; pct: number; top: boolean; you: boolean }) {
  return (
    <div className={`tw-bet${you ? " is-you" : ""}`}>
      <div className="tw-dim-top">
        <span className="tw-bet-label">
          {label}
          {you && <Tag tone="sol">Tú</Tag>}
          {top && <Tag tone="accent">Su apuesta</Tag>}
        </span>
        <span className="tw-dim-val">{Math.round(pct)}%</span>
      </div>
      <span className="tw-meter-track">
        <i className={`tw-meter-fill tw-meter-fill--${top ? "acento" : "control"}`} style={{ width: `${pct}%` }} />
      </span>
    </div>
  );
}
