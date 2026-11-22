import { useEffect, useRef, useState } from "react";
import { Button, Heading, Panel, Text } from "@/shared/ui";
import { twinApi } from "../api";
import type { TwinState } from "../hooks/useTwin";

const MAX = 60000;

/** El prompt que la persona pega en su propio asistente (Claude, ChatGPT...) para exportar lo que sabe de ella. */
export const PROMPT_EXPORTAR = `Quiero exportar lo que sabes de mí para que otra herramienta me conozca. Con lo que recuerdas de nuestras conversaciones (memorias, proyectos, instrucciones), escribe un resumen en español, en viñetas, con estas secciones:

1. Trabajo y carrera: qué hago, dónde, cuánto tiempo, qué me gusta y qué no de mi pega, planes.
2. Cómo decido: frente al riesgo, la plata, el tiempo, la estabilidad, los cambios.
3. Personalidad: cómo me describirías, cómo trabajo con otras personas, qué me energiza o me desgasta.
4. Lo que me importa: valores, prioridades, dilemas que he tenido.
5. Vida personal relevante para mis decisiones de trabajo (sin datos de salud ni de terceros).

Solo lo que sabes de verdad: si no sabes algo, dilo. Sin datos sensibles (salud, RUT, cuentas, contraseñas).`;

export function LlmContext({ twin }: { twin: TwinState }) {
  const profile = twin.profile!;
  const [texto, setTexto] = useState(profile.contexto_llm);
  const [copiado, setCopiado] = useState(false);
  const file = useRef<HTMLInputElement>(null);

  useEffect(() => setTexto(profile.contexto_llm), [profile.id, profile.contexto_llm_at]); // eslint-disable-line react-hooks/exhaustive-deps

  const dirty = texto.trim() !== profile.contexto_llm;

  async function copiar() {
    try {
      await navigator.clipboard.writeText(PROMPT_EXPORTAR);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      /* sin permiso de portapapeles: el prompt igual está visible */
    }
  }

  async function leer(f: File | undefined) {
    if (!f) return;
    const t = await f.text();
    setTexto(t.slice(0, MAX));
    if (file.current) file.current.value = "";
  }

  const importar = () =>
    twin.run((p) => twinApi.importContext(p.id, p.version, texto.slice(0, MAX), true), (r) => r);

  return (
    <Panel>
      <Heading level={3} as="h2">Lo que sabe tu IA de ti</Heading>
      <Text size="sm">
        Si usas Claude, ChatGPT u otro asistente, ya te conoce. Pégale este prompt, copia lo que te responda y súbelo
        aquí: tu gemelo parte de eso y después lo afina con tus respuestas.
      </Text>
      <details className="tw-prompt">
        <summary>Ver el prompt</summary>
        <pre>{PROMPT_EXPORTAR}</pre>
      </details>
      <div className="tw-actions">
        <Button variant="white" onClick={copiar}>{copiado ? "Copiado" : "Copiar prompt"}</Button>
        <Button variant="white" onClick={() => file.current?.click()}>Subir archivo</Button>
        <input ref={file} type="file" accept=".txt,.md,.markdown,.json,text/plain" hidden
          onChange={(e) => leer(e.target.files?.[0])} />
      </div>
      <label className="tw-field">
        <span className="vd-ind-n">Lo que te respondió (o pégalo aquí)</span>
        <textarea className="tw-textarea tw-textarea-tall" value={texto} maxLength={MAX}
          placeholder="Pega aquí el resumen de tu asistente…" onChange={(e) => setTexto(e.target.value)} />
      </label>
      <Text size="sm">
        {texto.length.toLocaleString("es-CL")} caracteres · No subas datos de salud, de otras personas ni claves.
      </Text>
      <Button onClick={importar} disabled={!dirty || twin.busy}>
        {twin.busy ? "Leyendo…" : profile.contexto_llm ? "Actualizar y volver a estimar" : "Importar y estimar mis rasgos"}
      </Button>
    </Panel>
  );
}
