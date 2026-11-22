import { useEffect, useState } from "react";
import { Button, ChevronLeftIcon, Heading, IconButton, Meta, Pill, Screen, ScreenFooter, ScreenHeader, Stack, Text, cssVars } from "@/shared/ui";
import { GEMELOS } from "../api";

const COLUMNAS = 10;

/** A cada mundo le toca un final, siempre el mismo (no es azar de verdad: es el dibujo de la explicación). */
const FINALES = Array.from({ length: GEMELOS }, (_, i) => {
  const r = ((i * 7919 + 104729) % 1000) / 1000;
  return r < 0.46 ? "mas" : r < 0.8 ? "igual" : "menos";
});
const CUENTA = { mas: FINALES.filter((f) => f === "mas").length, igual: FINALES.filter((f) => f === "igual").length, menos: FINALES.filter((f) => f === "menos").length };
const ORDENADOS = [...FINALES].sort((a, b) => "mas igual menos".indexOf(a) - "mas igual menos".indexOf(b));

const PASOS = [
  {
    titulo: "Este eres tú, hoy.",
    texto: "Cada año te toca una decisión de trabajo: ¿me cambio?, ¿pido aumento?, ¿emprendo? Nadie puede decirte cómo va a salir, porque depende de la decisión y también de la suerte.",
  },
  {
    titulo: `Imaginamos ${GEMELOS} mundos posibles.`,
    texto: `En cada mundo vive una copia tuya, tu gemelo: misma edad, mismo sueldo, misma pega. Lo que cambia de un mundo a otro es la suerte: en uno hay recesión el año 3, en otro te despiden, en otro no pasa nada. También cambia qué tan rápido llega la IA, dentro del rango que han medido los estudios.`,
  },
  {
    titulo: "En cada mundo, tu gemelo vive todas las opciones.",
    texto: "Una vida cambiándose y otra quedándose, en el mismo mundo: la misma recesión, el mismo despido. Así, si en un mundo termina ganando más con una opción, es por la decisión y no por la suerte.",
  },
  {
    titulo: `Contamos los ${GEMELOS} mundos.`,
    texto: "¿En cuántos te va mejor con una opción, en cuántos con la otra y en cuántos da lo mismo? Qué tan seguido pasa cada cosa sale de encuestas a trabajadores chilenos (ESI y ENE del INE, entre otras). No es una predicción: es el abanico de lo que le pasa a gente como tú. Las empresas son reales, pero sus cifras se simulan a partir de su rubro y tamaño.",
  },
  {
    titulo: `Y tú eres el mundo ${GEMELOS + 1}.`,
    texto: `Los ${GEMELOS} mundos son para mirar antes de decidir. El tuyo es uno más, con su propio dado, y es el único que se vive de verdad. Cada año te sale una carta al azar, entre las decisiones que calzan con tu situación. Cada opción tiene sus probabilidades: eliges una, tiramos tu dado y avanzas, durante 10 años. Al final comparas tu mundo con los otros ${GEMELOS}.`,
  },
];

type Suceso = { anio: number; tono: "bueno" | "malo"; nombre: string; solo?: "a" };
type Mundo = { sucesos: Suceso[]; a: string; b: string; gana: "a" | "b" };

/** Cuatro mundos de ejemplo. Los sucesos sin `solo` son del mundo: caen igual en las dos vidas. */
const MUNDOS: Mundo[] = [
  { sucesos: [{ anio: 3, tono: "malo", nombre: "recesión" }, { anio: 7, tono: "bueno", nombre: "ascenso" }], a: "$2,6 M", b: "$2,2 M", gana: "a" },
  { sucesos: [{ anio: 2, tono: "malo", nombre: "despido" }], a: "$1,7 M", b: "$1,9 M", gana: "b" },
  { sucesos: [], a: "$2,4 M", b: "$2,1 M", gana: "a" },
  { sucesos: [{ anio: 3, tono: "malo", nombre: "cierra la empresa nueva", solo: "a" }, { anio: 8, tono: "bueno", nombre: "ascenso" }], a: "$1,5 M", b: "$2,5 M", gana: "b" },
];

const X0 = 74;
const PASO_X = 19.5;
const ALTO_MUNDO = 62;
const x = (anio: number) => X0 + anio * PASO_X;

/**
 * Lo que hace el motor en cada mundo, a la vista: el mismo gemelo vive los 10 años dos veces, una por opción,
 * y lo que le pasa al mundo (recesión, despido) cae en el mismo año en las dos vidas.
 */
function DosVidas() {
  const [anio, setAnio] = useState(0);
  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setAnio(10);
      return;
    }
    let cuadro = 0;
    let inicio = 0;
    const paso = (t: number) => {
      if (!inicio) inicio = t + 500;
      const k = Math.min(1, Math.max(0, (t - inicio) / 6000));
      setAnio(k * 10);
      if (k < 1) cuadro = requestAnimationFrame(paso);
    };
    cuadro = requestAnimationFrame(paso);
    return () => cancelAnimationFrame(cuadro);
  }, []);
  const fin = anio >= 10;

  return (
    <svg
      className="jg-vidas"
      viewBox={`0 0 340 ${MUNDOS.length * ALTO_MUNDO + 22}`}
      role="img"
      aria-label="Cuatro mundos de ejemplo. En cada uno, tu gemelo vive diez años dos veces: cambiándose y quedándose. La recesión o el despido de ese mundo caen el mismo año en las dos vidas. Al final se compara con cuál terminó ganando más."
    >
      <text className="jg-vidas-chico" x={x(1)} y={10} textAnchor="middle">año 1</text>
      <text className="jg-vidas-chico" x={x(10)} y={10} textAnchor="middle">año 10</text>
      {MUNDOS.map((m, i) => {
        const y0 = 20 + i * ALTO_MUNDO;
        const ya = y0 + 22;
        const yb = y0 + 46;
        return (
          <g key={i}>
            <text className="jg-vidas-mundo" x={0} y={y0 + 8}>Mundo {i + 1}</text>
            <text className="jg-vidas-chico" x={0} y={ya + 3}>te cambias</text>
            <text className="jg-vidas-chico" x={0} y={yb + 3}>te quedas</text>
            {[ya, yb].map((y) => (
              <g key={y}>
                <line className="jg-vidas-riel" x1={X0} x2={x(10)} y1={y} y2={y} />
                <line className="jg-vidas-vida" x1={X0} x2={x(anio)} y1={y} y2={y} />
              </g>
            ))}
            {m.sucesos.map((s) => (
              <g key={s.anio} className="jg-vidas-suceso" data-visible={anio >= s.anio} data-tono={s.tono}>
                {!s.solo && <line className="jg-vidas-dado" x1={x(s.anio)} x2={x(s.anio)} y1={ya} y2={yb} />}
                <circle cx={x(s.anio)} cy={ya} r={5.5} />
                {!s.solo && <circle cx={x(s.anio)} cy={yb} r={5.5} />}
                <text className="jg-vidas-chico" x={x(s.anio) + 9} y={s.solo ? ya - 7 : (ya + yb) / 2 + 3}>
                  {s.nombre}
                </text>
              </g>
            ))}
            {m.sucesos.length === 0 && (
              <text className="jg-vidas-chico jg-vidas-suceso" data-visible={anio >= 5} x={x(5)} y={(ya + yb) / 2 + 3} textAnchor="middle">
                sin sobresaltos
              </text>
            )}
            <g className="jg-vidas-final" data-visible={fin}>
              <text className={m.gana === "a" ? "jg-vidas-gana" : "jg-vidas-pierde"} x={x(10) + 10} y={ya + 4}>{m.a}</text>
              <text className={m.gana === "b" ? "jg-vidas-gana" : "jg-vidas-pierde"} x={x(10) + 10} y={yb + 4}>{m.b}</text>
            </g>
          </g>
        );
      })}
    </svg>
  );
}

/** Cómo funciona, en cinco pasos: qué significa "simulamos los mundos" y por qué se puede comparar una opción con otra. */
export function ComoFunciona({ onListo, onVolver, textoListo = "Armar mi perfil" }: { onListo: () => void; onVolver: () => void; textoListo?: string }) {
  const [paso, setPaso] = useState(0);
  const ultimo = paso === PASOS.length - 1;
  const finales = paso >= 3 ? ORDENADOS : FINALES;
  return (
    <Screen gap={16}>
      <ScreenHeader
        left={
          <IconButton label={paso === 0 ? "Volver" : "Paso anterior"} onClick={() => (paso === 0 ? onVolver() : setPaso(paso - 1))}>
            <ChevronLeftIcon />
          </IconButton>
        }
        right={<Pill>Cómo funciona</Pill>}
      />

      {paso === 2 ? (
        <div className="jg-como jg-como--vidas">
          <DosVidas />
        </div>
      ) : (
        <div className="jg-como" data-paso={paso} aria-hidden="true">
          <div className="jg-como-tu">
            <span />
            <b>Tú</b>
          </div>
          <div className="jg-como-gemelos" style={cssVars({ "--jg-cols": COLUMNAS })}>
            {finales.map((f, i) => (
              <i key={i} data-final={f} style={cssVars({ "--jg-i": (i % COLUMNAS) + Math.floor(i / COLUMNAS) })} />
            ))}
          </div>
          <div className="jg-como-dado">
            <span>⚄</span>
          </div>
        </div>
      )}

      <div className="jg-como-leyenda" data-visible={paso === 2 || paso === 3}>
        {paso === 2 ? (
          <>
            <span><i data-suceso="malo" />mala suerte</span>
            <span><i data-suceso="bueno" />buena suerte</span>
            <span><i data-suceso="dado" />le pasa al mundo: cae en las dos vidas</span>
          </>
        ) : (
          <>
            <span><i data-final="mas" /><b>{CUENTA.mas}</b> mundos: ganas más con una</span>
            <span><i data-final="igual" /><b>{CUENTA.igual}</b> igual</span>
            <span><i data-final="menos" /><b>{CUENTA.menos}</b> ganas más con la otra</span>
          </>
        )}
      </div>

      <Stack gap={8} key={paso} className="vd-subir" aria-live="polite">
        <Meta>
          Paso {paso + 1} de {PASOS.length}
        </Meta>
        <Heading level={2} as="h1">
          {PASOS[paso].titulo}
        </Heading>
        <Text>{PASOS[paso].texto}</Text>
        {(paso === 2 || paso === 3) && <Text size="sm">Los mundos y los números de este dibujo son un ejemplo. Los tuyos salen de tu perfil.</Text>}
      </Stack>

      <ScreenFooter>
        <div className="jg-como-pasos" aria-hidden="true">
          {PASOS.map((_, i) => (
            <i key={i} data-activo={i === paso} />
          ))}
        </div>
        <Button onClick={() => (ultimo ? onListo() : setPaso(paso + 1))}>{ultimo ? textoListo : "Siguiente"}</Button>
        {!ultimo && (
          <Button variant="quiet" onClick={onListo}>
            Saltar la explicación
          </Button>
        )}
      </ScreenFooter>
    </Screen>
  );
}
