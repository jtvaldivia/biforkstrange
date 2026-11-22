import { useEffect, useState, type ReactNode } from "react";
import { Button, Tag, cx } from "@/shared/ui";
import { CALIDAD, CAMPOS_PERFIL, enLista, plata } from "../textos";
import type { Calidad, Rango } from "../types";
import { Espera } from "./Apuesta";

/** Calidad del dato, discreta: dato / mixto / supuesto. */
export function CalidadTag({ calidad }: { calidad: Calidad }) {
  const c = CALIDAD[calidad];
  if (!c) return null;
  return (
    <span title={c.explica}>
      <Tag tone={calidad === "supuesto" ? "minus" : "default"}>{c.nombre}</Tag>
    </span>
  );
}

export function LeyendaCalidad() {
  return (
    <p className="jg-chico" style={{ margin: 0 }}>
      Cada número dice de dónde sale. Dato: {CALIDAD.dato.explica.toLowerCase()} Mixto: {CALIDAD.mixto.explica.toLowerCase()}{" "}
      Supuesto: {CALIDAD.supuesto.explica.toLowerCase()}
    </p>
  );
}

/**
 * Rango de sueldos de los gemelos de una opción, del 10% peor al 10% mejor, con la raya en el gemelo del medio.
 * Usa la pista de <RangeCompare> del kit, pero en pesos y con una escala común (`tope`) para todas las opciones.
 */
export function RangoSueldo({ rango, tope, color = "var(--dinero)", enPalabras = false }: { rango: Rango; tope: number; color?: string; enPalabras?: boolean }) {
  const pos = (n: number) => (tope > 0 ? Math.min(100, Math.max(0, (n / tope) * 100)) : 0);
  return (
    <span
      className="vd-pila"
      style={{ gap: 4 }}
      role="img"
      aria-label={`10%: ${plata(rango.p10)}. Mediana: ${plata(rango.p50)}. 90%: ${plata(rango.p90)}.`}
    >
      <span className="vd-rango-pista">
        <i style={{ left: `${pos(rango.p10)}%`, width: `${Math.max(pos(rango.p90) - pos(rango.p10), 2)}%`, background: color }} />
        <b style={{ left: `${pos(rango.p50)}%` }} />
      </span>
      {enPalabras ? (
        <span className="jg-chico">
          8 de cada 10 mundos terminan entre {plata(rango.p10)} y {plata(rango.p90)}
        </span>
      ) : (
        <span className="jg-extremos">
          <span>10% · {plata(rango.p10)}</span>
          <span>90% · {plata(rango.p90)}</span>
        </span>
      )}
    </span>
  );
}

/**
 * Espera sin juego: un punto que late y una frase. Para todo lo que no es un sorteo (simular opciones,
 * leer el CV); la apuesta queda solo para cuando confirmas y se tira tu año. Con `frases`, van rotando.
 */
export function Cargando({ children, texto, frases, cada = 2400 }: { children?: ReactNode; texto?: string; frases?: string[]; cada?: number }) {
  const [n, setN] = useState(0);
  const total = frases?.length ?? 0;
  useEffect(() => {
    if (total < 2) return;
    const id = window.setInterval(() => setN((x) => x + 1), cada);
    return () => window.clearInterval(id);
  }, [total, cada]);
  const linea = total ? frases![n % total] : (texto ?? children);
  return (
    <div className="jg-cargando" role="status" aria-live="polite">
      <i aria-hidden="true" />
      <span key={total ? n % total : undefined}>{linea}</span>
    </div>
  );
}

export function ErrorCaja({ error, onReintentar }: { error: string; onReintentar?: () => void }) {
  return (
    <div className="vd-pila" style={{ gap: 10 }} role="alert">
      <div className="jg-error">No pudimos hablar con el simulador. {error}</div>
      {onReintentar && (
        <Button variant="white" onClick={onReintentar}>
          Reintentar
        </Button>
      )}
    </div>
  );
}

/**
 * Si el perfil no es del todo tuyo, se dice: sin datos es un perfil de ejemplo; si saltaste preguntas, esas quedan
 * como supuesto. `fuentes` son los campos que sí se saben; null si no se sabe (una partida guardada de antes).
 */
export function AvisoPerfil({ fuentes }: { fuentes: Record<string, string> | null }) {
  if (!fuentes) return null;
  const supuestos = Object.keys(CAMPOS_PERFIL).filter((k) => !(k in fuentes));
  if (supuestos.length === 0) return null;
  const ejemplo = supuestos.length === Object.keys(CAMPOS_PERFIL).length;
  return (
    <div className="jg-aviso-perfil" role="note">
      <Tag tone="sol">{ejemplo ? "Perfil de ejemplo" : "Con supuestos"}</Tag>
      <span className="jg-chico">
        {ejemplo
          ? "Jugaste sin datos: estos mundos son de una persona de ejemplo, no los tuyos."
          : `No nos dijiste tu ${enLista(supuestos.map((k) => CAMPOS_PERFIL[k]))}: ahí usamos un supuesto.`}
      </span>
    </div>
  );
}

/** Salir de la partida: vuelve a la portada, donde se puede continuar o empezar otra. La partida no se borra. */
export function Salir({ onSalir }: { onSalir: () => void }) {
  return (
    <button type="button" className="jg-ayuda jg-salir" onClick={onSalir}>
      Salir
    </button>
  );
}

/** Algo que pasó en el año. Es la <Notification> del kit, con el texto completo en vez de cortado. */
export function Noticia({ titulo, texto, lado, className }: { titulo: string; texto: string; lado?: string; className?: string }) {
  return (
    <div className={cx("vd-noti", "jg-noti", className)}>
      <span className="vd-noti-texto">
        <span className="vd-noti-quien">{titulo}</span>
        <span className="vd-noti-msg">{texto}</span>
      </span>
      {lado && <span className="vd-noti-hora">{lado}</span>}
    </div>
  );
}

/** Lo que el motor sortea de verdad en un año, y un par de cosas que no (dichas como lo que son: bromas). */
const FRASES = [
  "Tirando tu dado…",
  "¿Habrá recesión este año?",
  "Revisando si te ascienden…",
  "¿Te llegará una oferta?",
  "Los robots aún no llegan…",
  "Preguntando por los despidos…",
  "Nadie sabe quién gana el Mundial…",
  "Calculando tu sueldo nuevo…",
];

/** Pantalla de espera mientras se vive tu año: una apuesta que va girando y lo que se está viendo en tu mundo. */
export function Pensando({ titulo }: { titulo: string }) {
  return <Espera pantalla titulo={titulo} frases={FRASES} cada={900} />;
}
