import { useState } from "react";
import { Button, Heading, LifePathHero, Panel, Row, Segmented, Slider, Stack, Tag, Text } from "@/shared/ui";
import type { StoryState } from "../hooks/useStory";

type Energia = "bien" | "normal" | "cansado";
const DESGASTE: Record<Energia, number> = { bien: 0.15, normal: 0.35, cansado: 0.6 };

/** Portada: cuéntanos dónde estás hoy y empieza. */
export function StartView({ st }: { st: StoryState }) {
  const [situacion, setSituacion] = useState("");
  const [edad, setEdad] = useState(27);
  const [energia, setEnergia] = useState<Energia>("normal");
  const [anios, setAnios] = useState<"5" | "8" | "10">("8");
  const ready = situacion.trim().length >= 20;

  return (
    <div className="st-start">
      <section className="st-hero">
        <div className="st-hero-art"><LifePathHero /></div>
        <Stack gap={12}>
          <div><span className="vd-pildora">Tu historia</span></div>
          <Heading level={1}>Vive tu vida antes de vivirla.</Heading>
          <Text>
            Cuéntanos dónde estás hoy. Cada año te ponemos frente a una decisión y te contamos qué pasó: con quién
            estuviste, qué ganaste y qué se quedó en el camino.
          </Text>
          <Row gap={6}>
            <Tag>Una decisión por año</Tag>
            <Tag>Tu historia, no un número</Tag>
            <Tag>Cada partida es distinta</Tag>
          </Row>
        </Stack>
      </section>

      <section className="st-form">
        <label className="st-field">
          <span className="st-label">¿Dónde estás hoy?</span>
          <span className="vd-p-sm">Qué haces, dónde vives, con quién, qué te tiene inquieto. Mientras más concreto, más tuya será la historia.</span>
          <textarea
            className="st-textarea"
            rows={5}
            value={situacion}
            onChange={(e) => setSituacion(e.target.value)}
            placeholder="Ej: Tengo 27, trabajo hace tres años en una consultora en Santiago. Me va bien, pero llego tarde todos los días y extraño hacer deporte. Pololeo hace dos años."
          />
        </label>

        <Panel>
          <Slider label="Tu edad" min={18} max={50} value={edad} onChange={setEdad} display={`${edad} años`} />
          <Stack gap={8}>
            <span className="vd-ind-n">¿Cómo llegas a este momento?</span>
            <Segmented label="Cómo llegas" value={energia} onChange={setEnergia}
              options={[{ value: "bien", label: "Con energía" }, { value: "normal", label: "Normal" }, { value: "cansado", label: "Sin energía" }]} />
          </Stack>
          <Stack gap={8}>
            <span className="vd-ind-n">¿Cuántos años quieres vivir?</span>
            <Segmented label="Cuántos años" value={anios} onChange={setAnios}
              options={[{ value: "5", label: "5 años" }, { value: "8", label: "8 años" }, { value: "10", label: "10 años" }]} />
          </Stack>
        </Panel>

        <Text size="sm">
          {st.twinId ? (
            <>Tu gemelo ya te conoce: la historia va a usar cómo eres para contar por qué cada decisión te afecta así. <a href="/gemelo">Enséñale más</a>.</>
          ) : (
            <>Si antes respondes unas preguntas en <a href="/gemelo">tu gemelo</a>, la historia va a reflejar cómo eres tú, no una persona promedio.</>
          )}
        </Text>

        {st.error && <p className="st-error" role="alert">{st.error}</p>}
        <Button disabled={!ready || st.pending !== null}
          onClick={() => st.start({ situacion, edad, desgaste: DESGASTE[energia], anios: Number(anios) })}>
          {ready ? "Empezar mi historia" : "Cuéntanos un poco más para empezar"}
        </Button>
      </section>
    </div>
  );
}
