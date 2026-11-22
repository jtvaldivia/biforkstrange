import { useEffect, useState } from "react";
import { Button, Heading, Meta, Panel, Stack, SunCard, Text } from "@/shared/ui";
import { twinApi } from "../api";
import type { TwinState } from "../hooks/useTwin";
import type { Basics } from "../types";
import { LlmContext } from "./LlmContext";
import { DimBar, SectionIntro } from "./parts";

const FIELDS: { key: keyof Basics; label: string; placeholder: string; long?: boolean }[] = [
  { key: "nombre", label: "Nombre", placeholder: "Cómo te llama tu gemelo" },
  { key: "rasgos", label: "Cómo te describes", placeholder: "Ej: curioso, me cuesta decir que no…", long: true },
  { key: "valores", label: "Lo que te importa", placeholder: "Ej: prefiero estabilidad a un sueldo alto…", long: true },
  { key: "gustos", label: "Gustos", placeholder: "Ej: literatura, museos, gimnasio entre semana…", long: true },
];

export function ProfileTab({ twin }: { twin: TwinState }) {
  const { profile, catalog } = twin;
  const [basics, setBasics] = useState<Basics | null>(null);
  const [noteQ, setNoteQ] = useState("");
  const [noteA, setNoteA] = useState("");

  useEffect(() => {
    if (profile) setBasics(profile.basics);
  }, [profile?.id, profile?.version]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!profile || !catalog || !basics) return <Text size="sm">Cargando…</Text>;

  const dirty = JSON.stringify(basics) !== JSON.stringify(profile.basics);
  const report = profile.report;
  const notes = profile.notes.filter((n) => !n.q.startsWith("Calibración:"));

  async function addNote() {
    const ok = await twin.run((p) => twinApi.addNote(p.id, p.version, noteQ.trim(), noteA.trim()), (r) => r);
    if (ok) {
      setNoteQ("");
      setNoteA("");
    }
  }

  return (
    <Stack gap={28}>
      <SectionIntro eyebrow="Perfil" title="Lo que sabe de ti.">
        Lo que cuentas aquí es autodeclarado: pesa menos que lo que respondes en las preguntas y el examen.
      </SectionIntro>

      <LlmContext twin={twin} />

      <div className="tw-two">
        <Panel>
          <Heading level={3} as="h2">Sobre ti</Heading>
          {FIELDS.map((f) => (
            <label key={f.key} className="tw-field">
              <span className="vd-ind-n">{f.label}</span>
              {f.long ? (
                <textarea className="tw-textarea" value={basics[f.key]} placeholder={f.placeholder}
                  onChange={(e) => setBasics({ ...basics, [f.key]: e.target.value })} />
              ) : (
                <input className="tw-input" value={basics[f.key]} placeholder={f.placeholder}
                  onChange={(e) => setBasics({ ...basics, [f.key]: e.target.value })} />
              )}
            </label>
          ))}
          <Button onClick={() => twin.run((p) => twinApi.saveBasics(p.id, p.version, basics), (r) => r)}
            disabled={!dirty || twin.busy}>
            {dirty ? "Guardar" : "Guardado"}
          </Button>
        </Panel>

        <Panel>
          <Heading level={3} as="h2">Notas de contexto</Heading>
          <Text size="sm">Sin datos de salud, de otras personas ni cifras exactas de patrimonio.</Text>
          <label className="tw-field">
            <span className="vd-ind-n">Tema</span>
            <input className="tw-input" placeholder="Ej: Trabajo actual" value={noteQ} onChange={(e) => setNoteQ(e.target.value)} />
          </label>
          <label className="tw-field">
            <span className="vd-ind-n">Lo que quieres que sepa</span>
            <textarea className="tw-textarea" value={noteA} onChange={(e) => setNoteA(e.target.value)} />
          </label>
          <Button variant="white" onClick={addNote} disabled={!noteQ.trim() || !noteA.trim() || twin.busy}>
            Agregar nota
          </Button>
          {notes.slice(-6).reverse().map((n, i) => (
            <Text key={i} size="sm"><strong>{n.q}.</strong> {n.a}</Text>
          ))}
        </Panel>
      </div>

      <Stack gap={14}>
        <Heading level={2}>Tus 26 rasgos</Heading>
        <Text size="sm">
          La rayita es dónde cree que estás (50 = promedio); la banda, cuánto duda. Con IA puede hacer una primera
          estimación a partir de lo que contaste, sin pisar lo que ya respondiste.
        </Text>
        <div className="tw-actions">
          <Button variant="white" onClick={() => twin.run((p) => twinApi.prior(p.id, p.version), (r) => r)}
            disabled={twin.busy || dirty}>
            {twin.busy ? "Estimando…" : profile.prior_at ? "Volver a estimar con lo que conté" : "Estimar con lo que conté"}
          </Button>
        </div>
        <div className="tw-groups">
          {Object.entries(catalog.grupos).map(([g, label]) => (
            <Stack key={g} gap={12} className="tw-group">
              <Meta>{label}</Meta>
              {catalog.dims.filter((d) => d.grupo === g).map((d) => (
                <DimBar key={d.key} nombre={d.nombre} dim={profile.dims[d.key]}
                  hint={`${d.descripcion}${profile.dims[d.key].ev ? ` · Evidencia: ${profile.dims[d.key].ev}` : ""}`} />
              ))}
            </Stack>
          ))}
        </div>
      </Stack>

      <Stack gap={14}>
        <Heading level={2}>Informe</Heading>
        <div className="tw-actions">
          <Button variant="white" onClick={() => twin.run((p) => twinApi.report(p.id, p.version), (r) => r)} disabled={twin.busy}>
            {twin.busy ? "Escribiendo…" : report ? "Actualizar informe" : "Generar informe"}
          </Button>
        </div>
        {report && (
          <Stack gap={14}>
            <SunCard>
              <p className="vd-relato vd-relato--fuerte" style={{ color: "inherit" }}>{report.resumen}</p>
            </SunCard>
            <div className="tw-two">
              <List title="Fortalezas" items={report.fortalezas} />
              <List title="Riesgos" items={report.riesgos} />
              <List title="Donde rindes más" items={report.ambientes} />
              <List title="Lo que no está claro" items={report.dudas} />
            </div>
            {report.vida && <Text><strong>Fuera del trabajo.</strong> {report.vida}</Text>}
          </Stack>
        )}
      </Stack>
    </Stack>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <Panel>
      <Meta>{title}</Meta>
      <ul className="tw-list">
        {items.map((x, i) => <li key={i}>{x}</li>)}
      </ul>
    </Panel>
  );
}
