import { Meta, Panel, Stack, Text } from "@/shared/ui";
import { conSigno, pesos, plata, sinSueldo } from "../textos";
import type { Anio, DecisionTomada, Estado, Evento } from "../types";
import { Info } from "./graficos";

/**
 * La plata del año, explicada: cómo pasó tu sueldo de lo que era a lo que es, y cuánto has ganado en total.
 * Los montos vienen del motor (cada decisión y cada evento anota cuánto movió el sueldo); aquí solo se ordenan.
 */

type Fila = { clave: string; nombre: string; detalle?: string; monto: number; nota?: string; cuantos?: number };

const pct = (antes: number, despues: number) => {
  if (antes <= 0 || despues <= 0) return undefined;
  const p = (despues / antes - 1) * 100;
  return `${p >= 0 ? "+" : "−"}${Math.abs(p).toLocaleString("es-CL", { maximumFractionDigits: 1 })}%`;
};

const tono = (n: number) => (Math.abs(n) < 1000 ? "igual" : n > 0 ? "mas" : "menos");

function porQueSueldo(x: DecisionTomada | Evento, despues: number): string | undefined {
  if ("evento" in x) {
    if (x.evento === "alza_anual") return "Lo que sube el sueldo de alguien de tu edad y estudios, más tu suerte del año.";
    if (x.evento === "ascenso") return "Un ascenso sube el sueldo entre 5% y 10%.";
    if (x.evento === "separacion_empleo")
      return despues <= 0 ? "Sin trabajo, sin sueldo." : "En la pega nueva entras ganando entre 85% y 102% de lo que ganabas.";
    return x.texto || undefined;
  }
  return eligioTu(x) ? `Elegiste «${x.opcion_nombre}». ${x.texto}`.trim() : x.texto || undefined;
}

/** Algunas "decisiones" las sortea el juego por ti (a qué tipo de empleador entras): ahí no hay un «Elegiste». */
const eligioTu = (x: DecisionTomada) => x.opcion_nombre !== "Sorteo";

function Filas({ filas }: { filas: Fila[] }) {
  return (
    <>
      {filas.map((f) => (
        <div className="jg-dato" key={f.clave}>
          <span>
            {f.nombre}
            {f.detalle && <small>{f.detalle}</small>}
          </span>
          <span data-tono={tono(f.monto)}>
            {conSigno(f.monto)}
            {f.nota && <small>{f.nota}</small>}
          </span>
        </div>
      ))}
    </>
  );
}

/** De qué sueldo partiste, qué lo movió y con cuánto quedas: la cuenta completa, línea por línea. */
export function ComoCambioTuSueldo({ tramos, antes, ahora }: { tramos: Anio[]; antes: Estado | undefined; ahora: Estado }) {
  const inicio = antes?.sueldo ?? tramos[0]?.sueldo_inicio;
  if (inicio === undefined) return null;
  const filas: Fila[] = [];
  tramos.forEach((a, i) => {
    // fila de la última decisión de este tramo: el sorteo del empleador que viene después es parte de ella
    let deDecision: { fila: Fila; x: DecisionTomada; antes: number } | null = null;
    for (const x of [...a.decisiones, ...a.eventos]) {
      if (x.sueldo_antes === undefined || x.sueldo_despues === undefined) continue;
      if (!("evento" in x) && x.decision === "tipo_de_empleador" && deDecision) {
        // una oferta es un solo sueldo: el que viste al aceptarla, con la empresa nueva incluida. Separarla en
        // "el resultado de la decisión" y "el empleador" mostraba cosas como «ganas lo mismo o menos: +2%» y «pyme: +19%»
        const { fila, x: padre, antes } = deDecision;
        fila.monto = x.sueldo_despues - antes;
        fila.nota = pct(antes, x.sueldo_despues);
        fila.detalle = `${eligioTu(padre) ? `Elegiste «${padre.opcion_nombre}». ` : ""}${x.texto}`.trim();
        continue;
      }
      const cesante = x.sueldo_antes <= 0 && antes && antes.sueldo_ref > 0;
      const fila: Fila = {
        clave: `${i}:${filas.length}`,
        nombre: x.nombre,
        detalle: porQueSueldo(x, x.sueldo_despues),
        monto: x.sueldo_despues - x.sueldo_antes,
        // volver a trabajar después de estar cesante: se compara con lo que ganabas
        nota: cesante ? `${pct(antes!.sueldo_ref, x.sueldo_despues)} de lo que ganabas` : pct(x.sueldo_antes, x.sueldo_despues),
      };
      filas.push(fila);
      deDecision = "evento" in x ? null : { fila, x, antes: x.sueldo_antes };
    }
  });
  const explicado = filas.reduce((s, f) => s + f.monto, 0);
  const resto = ahora.sueldo - inicio - explicado;
  if (Math.abs(resto) >= 1000)
    filas.push({
      clave: "resto",
      nombre: "Otros ajustes",
      detalle: "Efectos de años anteriores que terminan (por ejemplo, una jornada reducida que vuelve a completa) o un alza que se paga año a año.",
      monto: resto,
    });
  if (filas.length === 0) return null;

  return (
    <Panel className="jg-plata">
      <Stack gap={8}>
        <Meta>Cómo cambió tu sueldo</Meta>
        <div className="jg-datos">
          <div className="jg-dato">
            <span>Partiste con</span>
            <span>{inicio > 0 ? pesos(inicio) : "Sin sueldo"}</span>
          </div>
          <Filas filas={filas} />
          <div className="jg-dato jg-plata-total">
            <span>Quedas con</span>
            <span>{sinSueldo(ahora) ? "Sin sueldo" : pesos(ahora.sueldo)}</span>
          </div>
        </div>
        <Info pregunta="¿Cómo se calcula el alza anual?">
          Todos los años, si tienes trabajo, tu sueldo se multiplica por (1 + alza). El alza suma cuatro cosas: (1) lo que sube típicamente el sueldo de
          alguien de tu edad y tus estudios, según la encuesta de ingresos del INE (si te titulaste hace menos de 4 años, lo que sube en tu carrera según
          MiFuturo), un 20% menos en el sector público; (2) menos la parte de eso que viene de ascensos, porque los ascensos se pagan aparte, cuando te
          ascienden; (3) tu suerte: casi todos los años, entre −3% y +3%; uno de cada diez, un año malo cercano a −5%; (4) −1,5% si ese año hay recesión.
          El alza queda entre 0% y 25%: en el mismo trabajo, el sueldo no baja.
        </Info>
      </Stack>
    </Panel>
  );
}

const mesesTxt = (m: number) => `${m} ${m === 1 ? "mes" : "meses"}`;

/**
 * El contador de ingreso: lo que has ganado en sueldos desde que empezaste a jugar. Sale directo de los sueldos
 * del modelo, sin suponer cuánto ahorra ni cuánto gasta cada persona. Los meses sin trabajo se ven como meses que no suman.
 */
export function TuIngreso({ tramos, ahora }: { tramos: Anio[]; ahora: Estado }) {
  if (ahora.ingreso_total === undefined) return null;
  let ganado = 0;
  let mesesSinSueldo = 0;
  let anios = 0;
  for (const a of tramos) {
    if (!a.plata) continue;
    ganado += a.plata.ganado ?? 0;
    mesesSinSueldo += a.plata.meses_sin_sueldo ?? 0;
    anios += 1;
  }
  if (!anios) return null;
  const meses = 12 * anios - mesesSinSueldo;
  const sinTrabajo = sinSueldo(ahora);

  return (
    <Panel className="jg-plata">
      <Stack gap={8}>
        <Meta>Lo que has ganado</Meta>
        <div className="jg-cambio">
          <span className="jg-cambio-num">{pesos(ahora.ingreso_total)}</span>
          {ganado > 0 && (
            <span className="jg-delta" data-signo="mas">
              {conSigno(ganado)}
            </span>
          )}
        </div>
        <Text size="sm">En sueldos, desde que empezaste a jugar.</Text>
        <div className="jg-datos">
          <div className="jg-dato">
            <span>
              {anios === 1 ? "Este año ganaste" : `En estos ${anios} años ganaste`}
              <small>
                {mesesSinSueldo > 0
                  ? `${mesesTxt(meses)} con sueldo. Los ${mesesTxt(mesesSinSueldo)} que buscaste trabajo no sumaron.`
                  : "Tu sueldo, todos los meses."}
              </small>
            </span>
            <span data-tono={ganado > 0 ? "mas" : "igual"}>{conSigno(ganado)}</span>
          </div>
        </div>
        {sinTrabajo && ahora.sueldo_ref > 0 && (
          <Text className="jg-destacado">Sin trabajo, cada mes dejas de ganar {plata(ahora.sueldo_ref)}, lo que ganabas.</Text>
        )}
      </Stack>
    </Panel>
  );
}
