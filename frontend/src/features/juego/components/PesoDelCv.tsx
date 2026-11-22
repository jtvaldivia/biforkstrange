import { useEffect, useState } from "react";
import { Stack, Text, cssVars } from "@/shared/ui";
import { getPesoCv } from "../api";
import { mundos, plata } from "../textos";
import type { CampoCv, Perfil, PesoCv, PesoDato } from "../types";
import { Info } from "./graficos";
import { Cargando } from "./piezas";

const NIVEL = ["Junior", "Semi senior", "Senior", "Jefatura", "Gerencia"];
const TITULO: Record<string, string> = { postgrado: "Tu postgrado", universitaria: "Tu título universitario", tecnica: "Tu título técnico" };
const SIN_TITULO: Record<string, string> = { universitaria: "solo con tu título universitario", media: "solo con enseñanza media" };

/** Cómo se nombra cada línea del CV en la frase, y cómo se dice "sin ella". */
function etiqueta(d: PesoDato): { con: string; sin: string } {
  switch (d.campo) {
    case "ingles":
      return { con: "Tu inglés", sin: "sin él" };
    case "skill":
      return { con: "Tu habilidad según tu CV", sin: "con la que se estima solo por tus años" };
    case "red":
      return { con: "Tu red de contactos", sin: "con una red promedio" };
    case "usa_ia":
      return { con: "Que ya trabajes con IA", sin: "sin eso" };
    case "remoto":
      return { con: "Que ya trabajes remoto", sin: "sin eso" };
    case "anos_por_empleo":
      return { con: `Tu ritmo de cambiarte de trabajo (cada ${String(d.tuyo).replace(".", ",")} años)`, sin: "al ritmo típico" };
    case "nivel":
      return { con: `Tu cargo de ${NIVEL[Number(d.tuyo)] ?? d.tuyo}`, sin: `como ${NIVEL[Number(d.neutro)] ?? d.neutro}` };
    case "edu":
      return { con: TITULO[String(d.tuyo)] ?? "Tus estudios", sin: SIN_TITULO[String(d.neutro)] ?? "sin ellos" };
    case "parcial":
      return { con: "Tu media jornada", sin: "a jornada completa" };
    case "empresa_fondos":
      return { con: "La inversión que levantaste", sin: "sin ella" };
  }
}

const CORTO: Record<CampoCv, string> = {
  ingles: "tu inglés",
  skill: "tu habilidad",
  red: "tu red",
  usa_ia: "que uses IA",
  remoto: "que trabajes remoto",
  anos_por_empleo: "tu ritmo de cambio",
  nivel: "tu cargo",
  edu: "tus estudios",
  parcial: "tu media jornada",
  empresa_fondos: "tu inversión",
};

function lista(xs: string[]): string {
  return xs.length <= 1 ? (xs[0] ?? "") : `${xs.slice(0, -1).join(", ")} y ${xs[xs.length - 1]}`;
}

/** Una línea del CV: la frase y dos barras, con el dato y sin él. */
function Linea({ d, i }: { d: PesoDato; i: number }) {
  const o = d.opciones.find((x) => x.opcion === d.opcion) ?? d.opciones[0];
  if (!o) return null;
  const { con, sin } = etiqueta(d);
  const gana = d.mueve === "gana";
  const valorCon = gana ? o.gana_con : o.sueldo_con;
  const valorSin = gana ? o.gana_sin : o.sueldo_sin;
  const tope = gana ? 1 : Math.max(o.sueldo_con, o.sueldo_sin, 1);
  const frase = gana
    ? `«${o.nombre}» gana en ${mundos(o.gana_con)} mundos; ${sin}, en ${mundos(o.gana_sin)}.`
    : `con «${o.nombre}» tu sueldo típico llega a ${plata(o.sueldo_con)} al mes; ${sin}, a ${plata(o.sueldo_sin)}.`;
  const texto = (v: number) => (gana ? mundos(v) : plata(v));
  return (
    <div className="jg-peso-linea" style={cssVars({ "--jg-i": i })}>
      <Text size="sm">
        <strong>{con}:</strong> {frase}
      </Text>
      <div className="jg-peso-barras" aria-hidden="true">
        <span className="jg-chico">Con</span>
        <span className="jg-peso-barra" data-tuyo="true">
          <i style={{ width: `${Math.max(1, (valorCon / tope) * 100)}%` }} />
        </span>
        <span className="jg-chico jg-peso-valor">{texto(valorCon)}</span>
        <span className="jg-chico">Sin</span>
        <span className="jg-peso-barra">
          <i style={{ width: `${Math.max(1, (valorSin / tope) * 100)}%` }} />
        </span>
        <span className="jg-chico jg-peso-valor">{texto(valorSin)}</span>
      </div>
    </div>
  );
}

/**
 * "Lo que vale cada línea de tu CV": la misma duda, con los mismos dados, quitando un dato del CV a la vez.
 * Los números vienen del motor (`/peso-cv`); aquí solo se arman las frases.
 */
export function PesoDelCv({ perfil, duda, semilla }: { perfil: Perfil; duda: string; semilla: number }) {
  const [peso, setPeso] = useState<PesoCv | null>(null);
  const [error, setError] = useState(false);
  const clave = JSON.stringify([perfil, duda, semilla]);

  useEffect(() => {
    let vigente = true;
    setPeso(null);
    setError(false);
    getPesoCv(perfil, duda, semilla)
      .then((p) => vigente && setPeso(p))
      .catch(() => vigente && setError(true));
    return () => {
      vigente = false;
    };
    // la clave resume perfil, duda y semilla: el perfil puede llegar como objeto nuevo en cada render
  }, [clave]);

  if (error) return null; // es un extra de la carta: si falla, la carta sigue igual
  if (peso && peso.datos.length === 0) return null;
  const quietos = peso?.sin_efecto.map((c) => CORTO[c]).filter(Boolean) ?? [];
  // plegado: es un extra de la carta, no lo que se decide
  return (
    <details className="jg-plegable jg-peso">
      <summary>Lo que vale cada línea de tu CV</summary>
      {!peso ? (
        <Cargando>Midiendo cuánto pesa cada línea de tu CV…</Cargando>
      ) : (
        <Stack gap={10}>
          <Text size="sm">Volvimos a vivir tus {peso.gemelos} mundos con los mismos dados, quitando un dato de tu CV a la vez.</Text>
          {peso.datos.map((d, i) => (
            <Linea key={d.campo} d={d} i={i} />
          ))}
          {quietos.length > 0 && (
            <Text size="sm">
              En esta duda casi no {quietos.length === 1 ? "pesa" : "pesan"} {lista(quietos)}.
            </Text>
          )}
          <Info pregunta="¿Cómo se calcula?">
            Cada mundo tiene sus dados: si te despiden, si hay recesión, si te sale la oferta. Para cada dato de tu CV repetimos los mismos {peso.gemelos} mundos
            cambiando solo ese dato por lo que el simulador supone cuando no lo sabe (sin inglés, una red promedio, la habilidad que dan tus años). Lo que cambia
            es lo que vale esa línea en esta decisión.
          </Info>
        </Stack>
      )}
    </details>
  );
}
