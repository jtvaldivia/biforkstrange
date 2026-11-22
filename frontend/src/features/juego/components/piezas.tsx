import { useEffect, useState, type ReactNode } from "react";
import { Button, Tag, Text, cx } from "@/shared/ui";
import { CALIDAD, CAMPOS_PERFIL, conSigno, enLista, plata, sinSueldo, situacion } from "../textos";
import type { Calidad, Estado, Rango, SinNovedad } from "../types";
import { Logo } from "./Logo";
import { Espera } from "./Apuesta";

/**
 * "Año 2 sin novedades · $657 mil": lo único que cambió en un año que pasó sin nada. Si el alza anual movió el
 * sueldo más de 2%, se dice eso: "sin novedades" junto a +$124 mil se contradecía.
 */
export function FranjaSinNovedad({ s }: { s?: SinNovedad | null }) {
  if (!s) return null;
  const antes = s.sueldo - s.delta;
  const casiIgual = antes > 0 ? Math.abs(s.delta) < 0.02 * antes : Math.abs(s.delta) < 1000;
  return (
    <div className="jg-sin-novedad" role="status">
      <span>
        {casiIgual ? `Año ${s.anio} sin novedades` : `Año ${s.anio}: solo el alza anual`} · <b>{plata(s.sueldo)}</b>
      </span>
      {!casiIgual && (
        <span className="jg-delta" data-signo={s.delta > 0 ? "mas" : "menos"}>
          {conSigno(s.delta)} al mes
        </span>
      )}
    </div>
  );
}

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

/**
 * Rango de sueldos de los gemelos de una opción, del 10% peor al 10% mejor, con la raya en el gemelo del medio.
 * En pesos y con una escala común (`tope`) para todas las opciones.
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
      <div className="jg-error">No pudimos conectar con el simulador. {error}</div>
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
export function AvisoPerfil({ fuentes, corto = false }: { fuentes: Record<string, string> | null; corto?: boolean }) {
  if (!fuentes) return null;
  const supuestos = Object.keys(CAMPOS_PERFIL).filter((k) => !(k in fuentes));
  if (supuestos.length === 0) return null;
  // ya se explicó en la primera carta: después basta un chip que lo recuerde
  if (corto) {
    const todo = supuestos.length === Object.keys(CAMPOS_PERFIL).length;
    return (
      <span title={todo ? "Jugaste sin datos: estos mundos son de una persona de ejemplo." : `Supuestos en: ${enLista(supuestos.map((k) => CAMPOS_PERFIL[k]))}.`}>
        <Tag tone="sol">{todo ? "Ejemplo" : "Con supuestos"}</Tag>
      </span>
    );
  }
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

/** Algo que pasó en el año. Va con el texto completo, sin cortar. */
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

/** "Hoy: Desarrollador backend en Betterfly [logo]" y, abajo, el sueldo: en su línea para que no se corte. */
export function Hoy({ e }: { e: Estado }) {
  return (
    <div className="jg-hoy">
      <Text size="sm">
        <strong>Hoy:</strong>{" "}
        {sinSueldo(e) ? (
          situacion(e.estado)
        ) : (
          <>
            {e.rol || e.cargo}
            {e.empresa && (
              <>
                {" en "}
                {e.empresa}{" "}
                <span className="jg-hoy-logo">
                  <Logo carpeta="empresas" id={e.empresa_id ?? e.empresa} nombre={e.empresa} grupo={e.rubro} hay={(e.empresa_id ?? -1) >= 0} tamano={22} />
                </span>
              </>
            )}
          </>
        )}
      </Text>
      <Text size="sm" className="jg-hoy-sueldo">
        {sinSueldo(e) ? `Antes ganabas ${plata(e.sueldo_ref)}/mes` : `${plata(e.sueldo)}/mes`}
      </Text>
    </div>
  );
}

const FRASES = [
  "Sorteando tu año…",
  "¿Habrá recesión este año?",
  "Revisando si te ascienden…",
  "¿Te llegará una oferta?",
  "Los robots aún no llegan…",
  "Preguntando por los despidos…",
  "Nadie sabe quién gana el Mundial…",
  "Calculando tu sueldo nuevo…",
];

/** Pantalla de espera mientras se vive tu año: una apuesta que va girando (ruleta, tragamonedas, caballos…) y lo que se está viendo en tu mundo. */
export function Pensando({ titulo, onSalir }: { titulo: string; onSalir?: () => void }) {
  return <Espera pantalla titulo={titulo} frases={FRASES} cada={900} onSalir={onSalir} />;
}
