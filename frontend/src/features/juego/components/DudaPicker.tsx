import "./onboarding.css";
import { useEffect, useState } from "react";
import { Espera } from "./Apuesta";
import {
  Button, ChevronLeftIcon, Chip, DecisionArt, DecisionList, Heading, IconButton, Screen, ScreenHeader, Stack, Tag, Text,
} from "@/shared/ui";
import { GEMELOS, getEnJuego } from "../api";
import { arteDuda, mayuscula, plata, preguntaCorta } from "../textos";
import type { Duda, DudaEnJuego, DudaSugerida, Perfil } from "../types";
import { AvisoPerfil, Cargando, ErrorCaja } from "./piezas";

const VISIBLES = 4;
/** Las dudas más comunes van primero; el resto sigue en el orden del paquete. */
const DESTACADAS = ["oferta_externa", "unirse_a_startup", "magister", "emprender", "pedir_aumento", "emigrar", "cambiar_de_rubro", "aprender_ia"];
const prioridad = (id: string) => {
  const i = DESTACADAS.indexOf(id);
  return i < 0 ? DESTACADAS.length : i;
};

/** Tu duda: la decisión que te trajo. Viene de la lista de caminos de "3 · Decisión del año" del kit. */
/** "La más en juego para ti": de las dudas que sugiere el CV, la que abre más distancia entre la mala y la buena suerte. */
function useMasEnJuego(perfil: Perfil | undefined, dudas: Duda[] | null, sugeridas: DudaSugerida[], semilla: number): DudaEnJuego | null {
  const posibles = new Set(dudas?.map((d) => d.decision) ?? []);
  const candidatas = sugeridas.map((s) => s.decision).filter((d) => posibles.has(d));
  const clave = perfil && candidatas.length >= 2 ? JSON.stringify([perfil, candidatas, semilla]) : null;
  const [mas, setMas] = useState<DudaEnJuego | null>(null);
  useEffect(() => {
    setMas(null);
    if (!clave || !perfil) return;
    let vigente = true;
    getEnJuego(perfil, candidatas, semilla)
      .then((r) => vigente && setMas(r.dudas.find((d) => d.decision === r.mas_en_juego) ?? null))
      .catch(() => undefined); // es un extra: si falla, la lista sigue igual
    return () => {
      vigente = false;
    };
    // la clave resume perfil, candidatas y semilla
  }, [clave]);
  return mas;
}

export function DudaPicker({
  fuentes = null,
  perfil,
  dudas,
  sugeridas = [],
  cargando,
  error,
  onVolver,
  onElegir,
  onReintentarDudas,
  onReintentar,
  onSinDuda,
  semilla,
}: {
  /** La semilla de la partida que viene: con ella se mide "más en juego" y la carta elegida queda lista. */
  semilla: number;
  /** Empezar sin una duda: la vida decide qué te llega el primer año, como en cualquier otro. */
  onSinDuda?: () => void;
  /** De dónde salió cada dato del perfil: lo que falta es supuesto. */
  fuentes?: Record<string, string> | null;
  /** De dónde vienen las sugeridas: del CV, o de lo que contaste a tu Claude. */
  origenSugeridas?: "cv" | "claude" | null;
  /** Con el perfil se mide cuál de las dudas sugeridas tiene más en juego para esta persona. */
  perfil?: Perfil;
  dudas: Duda[] | null;
  /** Las dudas que le calzan según su CV o su Claude, con el porqué: van primero y la primera queda elegida. */
  sugeridas?: DudaSugerida[];
  cargando: boolean;
  error: string | null;
  onVolver: () => void;
  onElegir: (decision: string) => void;
  /** Si la lista de dudas no llegó, se vuelve a pedir. */
  onReintentarDudas?: () => void;
  /** Si lo que falló fue simular la primera carta, se repite eso. */
  onReintentar?: () => void;
}) {
  const porQue = new Map(sugeridas.map((s) => [s.decision, s.por_que]));
  const rango = (id: string) => {
    const i = sugeridas.findIndex((s) => s.decision === id);
    return i < 0 ? sugeridas.length : i;
  };
  const sugerida = sugeridas[0]?.decision ?? null;
  const [sel, setSel] = useState<string | null>(sugerida);
  const [todas, setTodas] = useState(false);
  /** Con la lista completa abierta, se puede ver solo una categoría (Trabajo, Estudios…). */
  const [categoria, setCategoria] = useState<string | null>(null);
  const orden = dudas
    ? [...dudas].sort((a, b) => rango(a.decision) - rango(b.decision) || prioridad(a.decision) - prioridad(b.decision))
    : dudas;
  // las categorías en orden de cuántas dudas tienen
  const conteo = new Map<string, number>();
  for (const d of dudas ?? []) conteo.set(d.categoria, (conteo.get(d.categoria) ?? 0) + 1);
  const categorias = [...conteo.keys()].sort((a, b) => conteo.get(b)! - conteo.get(a)!);
  const mostradas = (orden ?? dudas ?? []).filter((d) => categoria === null || d.categoria === categoria || d.decision === sel);
  const elegirCategoria = (c: string | null) => {
    setCategoria(c);
    if (c !== null) setTodas(true); // una categoría muestra todas las suyas, no solo las primeras
  };
  const simulando = cargando && dudas !== null;
  const enJuego = useMasEnJuego(perfil, dudas, sugeridas, semilla);
  return (
    <Screen gap={16}>
      <ScreenHeader
        left={
          <IconButton label="Volver a tu perfil" onClick={onVolver}>
            <ChevronLeftIcon />
          </IconButton>
        }
      />
      <Stack gap={6}>
        <Heading level={1}>¿Qué duda te trajo?</Heading>
        <AvisoPerfil fuentes={fuentes} />
      </Stack>
      {enJuego && (
        <div className="jg-en-juego" role="note">
          <Tag tone="accent">La más en juego para ti</Tag>
          <Text size="sm">
            «{enJuego.nombre}»: de {plata(enJuego.mala)} (10%) a {plata(enJuego.buena)} (90%) al mes.
          </Text>
        </div>
      )}
      {cargando && !dudas && <Cargando>Buscando tus dudas…</Cargando>}
      {dudas && dudas.length === 0 && <Text>No hay dudas para este perfil. Vuelve y cámbialo.</Text>}
      {dudas && dudas.length > VISIBLES && categorias.length > 1 && (
        <div className="jg-filtro-dudas" role="group" aria-label="Filtrar dudas por tema">
          <Chip pressed={categoria === null} onToggle={() => elegirCategoria(null)}>
            Todas
          </Chip>
          {categorias.map((c) => (
            <Chip key={c} pressed={categoria === c} onToggle={() => elegirCategoria(categoria === c ? null : c)}>
              {mayuscula(c)}
            </Chip>
          ))}
        </div>
      )}
      {dudas && dudas.length > 0 && (
        <DecisionList<string>
          tile
          label="Dudas posibles"
          value={sel}
          onChange={setSel}
          options={mostradas.slice(0, todas ? undefined : VISIBLES).map((d) => ({
            id: d.decision,
            art: <DecisionArt kind={arteDuda(d.decision, d.categoria)} llenar />,
            title: d.nombre,
            subtitle: preguntaCorta(d.pregunta),
            tags: [
              enJuego?.decision === d.decision
                ? { label: "La más en juego", tone: "accent" as const }
                : porQue.has(d.decision)
                  ? { label: "Para ti", tone: "sol" as const }
                  : { label: mayuscula(d.categoria) },
            ],
          }))}
        />
      )}
      {sel && porQue.get(sel) && (
        <div className="vd-caja" style={{ gap: 4 }}>
          <span className="vd-meta">Por qué te calza</span>
          <Text size="sm">{porQue.get(sel)}</Text>
        </div>
      )}
      {dudas && !todas && categoria === null && dudas.length > VISIBLES && (
        <Button variant="quiet" onClick={() => setTodas(true)}>
          Ver las otras {dudas.length - VISIBLES}
        </Button>
      )}
      {onSinDuda && (
        <button type="button" className="ob-link" onClick={onSinDuda} disabled={cargando}>
          Empezar sin una duda
        </button>
      )}
      <div className="jg-pie-fijo">
        {error && <ErrorCaja error={error} onReintentar={dudas ? onReintentar : onReintentarDudas} />}
        {simulando && <Espera frases={[`Corriendo tus ${GEMELOS} simulaciones…`, "Diez años con cada opción…"]} />}
        <Button onClick={() => sel && onElegir(sel)} disabled={!sel || cargando}>
          {simulando ? "Simulando…" : sel ? `Ver mis ${GEMELOS} simulaciones` : "Elige una duda"}
        </Button>
      </div>
    </Screen>
  );
}
