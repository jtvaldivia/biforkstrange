import { useState } from "react";
import { Button, Heading, Meta, Pill, Screen, ScreenFooter, ScreenHeader, Stack, Text } from "@/shared/ui";
import { GEMELOS } from "../api";
import { TIPO_EMPLEADOR, plata } from "../textos";
import type { Anio, Eleccion, Vista } from "../types";
import { ErrorCaja, Salir } from "./piezas";
import { Logo } from "./Logo";

/**
 * Sin trabajo, el tiempo cambia de ritmo: un año con trabajo pasa en una pantalla; un año buscando, mes a mes.
 * Cada mes el motor tira un dado y a veces llega una oferta (paquete: oferta_cesante). Los meses vacíos se ven en
 * la tira. Cuando llega una, la aceptas o la rechazas y sigues buscando; tu copia diría qué haría con su regla fija.
 * Lo que cuesta esperar se ve en lo que dejas de ganar: los meses sin tu sueldo.
 */

export const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

type Celda = "trabajo" | "vacio" | "rechazada" | "aceptada" | "ahora" | "futuro";

/** Los meses que se buscó trabajo ese año: los anota el motor; si no vienen, se deducen de lo que pasó cada mes. */

/** Qué pasó cada mes de un año que se vivió mes a mes. Sin meses vividos así, null. */
export function mesesDelAnio(a: Anio, mesActual?: number): Celda[] | null {
  const conMes = [...a.eventos, ...a.decisiones].filter((x) => x.mes);
  const buscados = a.meses_busqueda ?? [];
  if (!conMes.length && !buscados.length && !mesActual) return null;
  const desde = Math.min(...conMes.map((x) => x.mes!), ...buscados, mesActual ?? 13);
  const celdas: Celda[] = MESES.map((_, i) => (i + 1 < desde ? "trabajo" : "futuro"));
  // un mes que se buscó y ya pasó sin oferta es un mes vacío (también si trabajabas informal mientras buscabas)
  for (const m of buscados) if (!mesActual || m < mesActual) celdas[m - 1] = "vacio";
  for (const x of a.eventos) if (x.mes && x.evento === "mes_buscando") celdas[x.mes - 1] = "vacio";
  for (const d of a.decisiones) {
    if (d.mes && d.decision === "oferta_en_cesantia") celdas[d.mes - 1] = d.opcion === "aceptar" ? "aceptada" : "rechazada";
  }
  // después de aceptar, el resto del año ya es con trabajo
  const acepto = celdas.indexOf("aceptada");
  if (acepto >= 0) for (let i = acepto + 1; i < 12; i++) if (celdas[i] === "futuro") celdas[i] = "trabajo";
  if (mesActual) celdas[mesActual - 1] = "ahora";
  return celdas;
}

const ETIQUETA: Record<Celda, string> = {
  trabajo: "con trabajo",
  vacio: "sin ofertas",
  rechazada: "oferta rechazada",
  aceptada: "oferta aceptada",
  ahora: "te llegó una oferta",
  futuro: "por venir",
};

export function TiraMeses({ celdas }: { celdas: Celda[] }) {
  const presentes = (["vacio", "rechazada", "aceptada", "ahora", "trabajo"] as Celda[]).filter((c) => celdas.includes(c));
  return (
    <Stack gap={6}>
      <ol className="jg-meses" aria-label="Los 12 meses del año">
        {celdas.map((c, i) => (
          <li key={i} data-celda={c} aria-label={`${MESES_LARGOS[i]}: ${ETIQUETA[c]}`}>
            <span>{MESES[i]}</span>
          </li>
        ))}
      </ol>
      <div className="jg-meses-leyenda" aria-hidden="true">
        {presentes.map((c) => (
          <span key={c}>
            <i data-celda={c} />
            {ETIQUETA[c]}
          </span>
        ))}
      </div>
    </Stack>
  );
}

/** "marzo y abril", "marzo, abril y mayo". */
function enumerar(xs: string[]): string {
  return xs.length <= 1 ? (xs[0] ?? "") : `${xs.slice(0, -1).join(", ")} y ${xs[xs.length - 1]}`;
}

const mesesTxt = (m: number) => `${m} ${m === 1 ? "mes" : "meses"}`;

export function BuscandoTrabajo({ vista, cargando, error, onElegir, onMirar, onSalir }: {
  vista: Vista;
  cargando: boolean;
  error: string | null;
  onElegir: (e: Eleccion) => void;
  onMirar: () => void;
  onSalir?: () => void;
}) {
  const p = vista.pendiente!;
  const b = p.busqueda!;
  const anio = Math.min(vista.anio + 1, vista.anios);
  const enCurso = vista.anio_en_curso;
  const celdas = enCurso ? mesesDelAnio(enCurso, b.mes) : null;
  const vacios = celdas ? celdas.map((c, i) => (c === "vacio" ? MESES_LARGOS[i] : null)).filter((x): x is string => x !== null) : [];
  const empresa = p.opciones.find((o) => o.empresa)?.empresa;
  const tipo = empresa ? (TIPO_EMPLEADOR[empresa.tipo] ?? empresa.tipo) : null;
  const ofrecido = p.oferta_sueldo?.si_aceptas ?? null;
  const antes = p.oferta_sueldo?.hoy ?? 0;
  const cambio = ofrecido !== null && antes > 0 ? Math.round((ofrecido / antes - 1) * 100) : null;
  const aceptar = p.opciones.find((o) => o.opcion === "aceptar");
  const rechazar = p.opciones.find((o) => o.opcion === "rechazar");
  // lo último que se eligió, para repetirlo si el simulador no respondió
  const [ultima, setUltima] = useState<Eleccion | null>(null);
  const elegir = (e: Eleccion) => {
    setUltima(e);
    onElegir(e);
  };

  return (
    <Screen tone="noche" gap={16}>
      <ScreenHeader
        left={<Pill style={{ whiteSpace: "nowrap" }}>Año {anio} · {MESES_LARGOS[b.mes - 1]}</Pill>}
        right={onSalir && <Salir onSalir={onSalir} />}
      />
      <Stack gap={10}>
        <Meta>{b.informal ? "Trabajas informal y sigues buscando" : "Sin trabajo"} · el año pasa mes a mes</Meta>
        <Heading level={2} as="h1">
          {b.informal
            ? "Sigues postulando a un trabajo con contrato"
            : b.meses_cesante === 0
              ? "Empiezas a buscar trabajo"
              : `Llevas ${mesesTxt(b.meses_cesante)} buscando trabajo`}
        </Heading>
        {celdas && <TiraMeses celdas={celdas} />}
        {vacios.length > 0 && (
          <Text size="sm">
            En {enumerar(vacios)} no te llegó ninguna oferta.
            {b.informal ? "" : " Cada mes que pasa te llaman menos y las ofertas pagan algo menos."}
          </Text>
        )}
        {!b.informal && b.meses_cesante > 0 && b.sueldo_ref > 0 && (
          <div className="jg-datos jg-plata">
            <div className="jg-dato">
              <span>
                Dejaste de ganar
                <small>{mesesTxt(b.meses_cesante)} sin tu sueldo de {plata(b.sueldo_ref)}</small>
              </span>
              <span data-tono="menos">{plata(b.meses_cesante * b.sueldo_ref)}</span>
            </div>
          </div>
        )}
      </Stack>

      <Stack gap={10} className="vd-subir">
        <Meta>En {MESES_LARGOS[b.mes - 1]} te llegó una oferta</Meta>
        {p.narrativa?.situacion && (
          <div className="jg-mensaje" data-logo={empresa ? "si" : undefined}>
            {empresa && <Logo carpeta="empresas" id={empresa.empresa_id} nombre={empresa.nombre} grupo={empresa.rubro} hay={empresa.logo} tamano={40} />}
            <p className="jg-mensaje-texto" style={{ animation: "none" }}>{p.narrativa.situacion}</p>
          </div>
        )}
        <Heading level={3} as="h2">
          {empresa?.cargo ? `${empresa.cargo} en ${empresa.nombre}` : "Te ofrecen trabajo"}
        </Heading>
        {empresa && <Text size="sm">{[tipo, empresa.rubro].filter(Boolean).join(" · ")}</Text>}
        <div className="jg-datos">
          {ofrecido !== null && (
            <div className="jg-dato">
              <span>Te ofrecen</span>
              <span>
                {plata(ofrecido)} al mes{" "}
                {cambio !== null && (
                  <span className="jg-delta" data-signo={cambio >= 0 ? "mas" : "menos"}>
                    {cambio > 0 ? "+" : cambio < 0 ? "−" : ""}
                    {Math.abs(cambio)}% de lo que ganabas
                  </span>
                )}
              </span>
            </div>
          )}
          {b.riesgo_despido !== undefined && (
            <div className="jg-dato">
              <span>Riesgo de que te despidan</span>
              <span>{(b.riesgo_despido * 100).toLocaleString("es-CL", { maximumFractionDigits: 1 })}% al año</span>
            </div>
          )}
        </div>
        {b.gemelo_acepta !== undefined && (
          <Text size="sm">
            Tu copia {b.gemelo_acepta ? "la aceptaría" : "la rechazaría"}: acepta si una oferta paga al menos 90% de lo que ganaba, y desde el
            séptimo mes buscando acepta cualquiera.
          </Text>
        )}
        <button type="button" className="jg-ayuda" style={{ alignSelf: "flex-start" }} onClick={onMirar} disabled={cargando}>
          Ver qué pasa en los {GEMELOS} mundos con cada opción
        </button>
      </Stack>

      <ScreenFooter>
        {error && <ErrorCaja error={error} onReintentar={ultima ? () => elegir(ultima) : undefined} />}
        <div className="jg-dos-botones">
          <Button variant="white" onClick={() => rechazar && elegir({ decision: p.decision, opcion: rechazar.opcion })} disabled={cargando || !rechazar}>
            La rechazo y sigo buscando
          </Button>
          <Button variant="white" onClick={() => aceptar && elegir({ decision: p.decision, opcion: aceptar.opcion })} disabled={cargando || !aceptar}>
            La acepto
          </Button>
        </div>
      </ScreenFooter>
    </Screen>
  );
}
