import { useState } from "react";
import { Button, Heading, Meta, Stack, Tag, Text } from "@/shared/ui";
import { twinApi } from "@/features/twin/api";
import type { ExamItem, ExamQuestion, TwinProfile } from "@/features/twin/types";
import type { Perfil } from "../types";

const CLAVE_GEMELO = "biforkstrange.twinProfileId"; // la misma que usa /gemelo
const RONDAS = 3;

function guardarGemelo(id: string) {
  try {
    localStorage.setItem(CLAVE_GEMELO, id);
  } catch {
    /* sin storage: el gemelo dura lo que dure la partida */
  }
}

/** Lo que el gemelo sabe de la persona al partir: su relato y lo que ya llenó del perfil. */
function contexto(p: Perfil): string {
  const datos = [
    `${p.edad} años`, p.rubro && `trabaja en ${p.rubro.toLowerCase()}`, `empleador: ${p.tipo_empleador}`,
    `tolerancia al riesgo ${p.riesgo}/10`,
  ].filter(Boolean).join(", ");
  return [p.relato?.trim(), `Datos del juego: ${datos}.`].filter(Boolean).join("\n\n");
}

/**
 * Paso del onboarding: tu gemelo apuesta en secreto cómo vas a responder, respondes y ves si te leyó.
 * Usa el examen a ciegas de /gemelo; si no tienes gemelo, lo arma con lo que contaste. Las respuestas del
 * examen no mueven rasgos por sí solas: al cerrar la última ronda se vuelve a estimar el perfil con ellas.
 */
export function Prueba({ perfil, onGemelo }: { perfil: Perfil; onGemelo: (id: string) => void }) {
  const [gemelo, setGemelo] = useState<TwinProfile | null>(null);
  const [pregunta, setPregunta] = useState<ExamQuestion | null>(null);
  const [revelado, setRevelado] = useState<ExamItem | null>(null);
  const [rondas, setRondas] = useState<ExamItem[]>([]);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aprendio, setAprendio] = useState(false);

  async function asegurarGemelo(): Promise<TwinProfile> {
    if (gemelo) return gemelo;
    if (perfil.gemelo_id) {
      try {
        const g = await twinApi.get(perfil.gemelo_id);
        setGemelo(g);
        return g;
      } catch {
        /* se borró (el servidor se reinició): se arma uno nuevo */
      }
    }
    setOcupado("Tu gemelo está leyendo lo que contaste…");
    let g = await twinApi.create();
    g = await twinApi.importContext(g.id, g.version, contexto(perfil), true);
    guardarGemelo(g.id);
    onGemelo(g.id);
    setGemelo(g);
    return g;
  }

  async function otra() {
    setError(null);
    setRevelado(null);
    try {
      const g = await asegurarGemelo();
      setOcupado("Tu gemelo está apostando cómo vas a responder…");
      const r = await twinApi.examNext(g.id, g.version, "auto");
      setGemelo(r.profile);
      setPregunta(r.question);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No pudimos preguntarle a tu gemelo.");
    } finally {
      setOcupado(null);
    }
  }

  async function responder(i: number) {
    if (!gemelo || !pregunta) return;
    setError(null);
    setOcupado("Revisando su apuesta…");
    try {
      const r = await twinApi.examAnswer(gemelo.id, gemelo.version, pregunta.id, i);
      setGemelo(r.profile);
      setRevelado(r.reveal);
      setRondas((x) => [...x, r.reveal]);
      setPregunta(null);
      if (rondas.length + 1 >= RONDAS) {
        // lo que respondiste entra al contexto del gemelo; se vuelven a estimar los rasgos que no has medido
        setOcupado("Tu gemelo está aprendiendo de tus respuestas…");
        setGemelo(await twinApi.prior(r.profile.id, r.profile.version));
        setAprendio(true);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "No pudimos guardar tu respuesta.");
    } finally {
      setOcupado(null);
    }
  }

  const aciertos = rondas.filter((r) => r.hit).length;

  return (
    <div className="ob-tarjeta ob-prueba">
      <Stack gap={6}>
        <Meta>{rondas.length ? `${aciertos} de ${rondas.length} acertadas` : "Opcional"}</Meta>
        <Heading level={2}>¿Tu gemelo te conoce?</Heading>
        {!pregunta && !revelado && (
          <Text size="sm">
            Te hace una pregunta, apuesta en secreto qué vas a responder y después comparamos. Después de {RONDAS}{" "}
            preguntas recalcula tus rasgos con lo que respondiste. Si lo pruebas, queda conectado a tu partida: sus rasgos
            deciden qué cartas te salen, no lo que pasa con cada una.
          </Text>
        )}
      </Stack>

      {ocupado && <div className="ob-prueba-espera">{ocupado}</div>}
      {error && <div className="jg-error" role="alert">{error}</div>}

      {pregunta && !ocupado && (
        <Stack gap={10}>
          <Text size="sm" className="ob-prueba-sello">Ya apostó. Su predicción está guardada.</Text>
          <Text style={{ fontWeight: 600 }}>{pregunta.q}</Text>
          {pregunta.opts.map((o, i) => (
            <button key={i} type="button" className="ob-prueba-op" onClick={() => void responder(i)}>
              {o}
            </button>
          ))}
        </Stack>
      )}

      {revelado && !ocupado && <Comparacion item={revelado} />}

      {!pregunta && !ocupado && rondas.length < RONDAS && (
        <Button variant="white" onClick={() => void otra()}>
          {rondas.length ? "Otra pregunta" : "Ponlo a prueba"}
        </Button>
      )}
      {rondas.length >= RONDAS && !pregunta && (
        <Text size="sm">
          {aprendio ? "Listo: tu gemelo ya recalculó tus rasgos con lo que respondiste. " : "Listo. "}
          Puedes seguir afinándolo cuando quieras en <a href="/gemelo#examen" target="_blank" rel="noreferrer">tu gemelo</a>.
        </Text>
      )}
    </div>
  );
}

function Comparacion({ item }: { item: ExamItem }) {
  const suya = item.opts[item.top] ?? "—";
  const tuya = item.ans === -1 ? item.ans_text : item.opts[item.ans ?? -1] ?? "—";
  return (
    <Stack gap={10}>
      <Tag tone={item.hit ? "sol" : "accent"}>{item.hit ? "Te leyó" : "Esta vez no te leyó"}</Tag>
      <Text size="sm" style={{ fontWeight: 600 }}>{item.q}</Text>
      <div className="ob-prueba-comp">
        <div>
          <Meta>Tu gemelo apostó</Meta>
          <span>{suya}</span>
          <small>{Math.round(item.probs[item.top] ?? 0)}% seguro</small>
        </div>
        <div data-tu>
          <Meta>Tú respondiste</Meta>
          <span>{tuya}</span>
          <small>{Math.round(item.p_ans ?? 0)}% le daba</small>
        </div>
      </div>
      {item.pq && <Text size="sm" className="ob-prueba-pq">“{item.pq}”</Text>}
    </Stack>
  );
}
