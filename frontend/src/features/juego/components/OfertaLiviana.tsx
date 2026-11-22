import { Button, Heading, Meta, Pill, Screen, ScreenFooter, ScreenHeader, Stack, Text } from "@/shared/ui";
import { EMPRESA_EJEMPLO, TIPO_EMPLEADOR, plata } from "../textos";
import type { Eleccion, SinNovedad, Vista } from "../types";
import { ErrorCaja, FranjaSinNovedad, Hoy, Salir } from "./piezas";
import { Logo } from "./Logo";

/**
 * Una oferta que te llegó, en corto: quién te escribe y qué te ofrece. Como en la vida, casi todas se
 * descartan en segundos; solo si quieres mirarla se abre la comparación con los 100 mundos.
 * Trae su sueldo, como en la vida: el que tendrías si la aceptas (el motor ya tiró esos dados).
 * Decir "No, sigo" es lo mismo que elegir "Quedarte".
 * Los dos botones pesan igual, para que la pantalla no empuje a quedarse.
 */
export function OfertaLiviana({ vista, cargando, error, onMirar, onElegir, onSalir, sinNovedad }: {
  vista: Vista;
  sinNovedad?: SinNovedad | null;
  cargando: boolean;
  error: string | null;
  onMirar: () => void;
  onElegir: (e: Eleccion) => void;
  onSalir?: () => void;
}) {
  const p = vista.pendiente!;
  const anio = Math.min(vista.anio + 1, vista.anios);
  const empresa = p.opciones.find((o) => o.empresa)?.empresa;
  const quedarse = p.opciones.find((o) => o.opcion === "quedarse");
  const tipo = empresa ? (TIPO_EMPLEADOR[empresa.tipo] ?? empresa.tipo) : null;
  const ofrecido = p.oferta_sueldo?.si_aceptas ?? null;
  const hoy = p.oferta_sueldo?.hoy ?? 0;
  const cambio = ofrecido !== null && hoy > 0 ? Math.round((ofrecido / hoy - 1) * 100) : null;

  return (
    <Screen gap={16}>
      <ScreenHeader left={<Pill style={{ whiteSpace: "nowrap" }}>Año {anio} · {vista.estado.edad} años</Pill>} right={onSalir && <Salir onSalir={onSalir} />} />
      <FranjaSinNovedad s={sinNovedad} />
      <Hoy e={vista.estado} />
      <Stack gap={10} className="vd-subir">
        <Meta>Te llegó una oferta</Meta>
        {p.narrativa?.situacion && (
          <div className="jg-mensaje" data-logo={empresa ? "si" : undefined}>
            {empresa && <Logo carpeta="empresas" id={empresa.empresa_id} nombre={empresa.nombre} grupo={empresa.rubro} hay={empresa.logo} tamano={40} />}
            <p className="jg-mensaje-texto" style={{ animation: "none" }}>{p.narrativa.situacion}</p>
          </div>
        )}
        <Heading level={2} as="h1">
          {empresa?.cargo ? `${empresa.cargo} en ${empresa.nombre}` : "Otra empresa te ofrece trabajo"}
        </Heading>
        {empresa && (
          <Text size="sm">
            {[tipo, empresa.rubro].filter(Boolean).join(" · ")}
          </Text>
        )}
        {empresa && <Text size="sm">{EMPRESA_EJEMPLO}</Text>}
        {ofrecido !== null && cambio !== null && (
          <Text>
            Te ofrecen <strong>{plata(ofrecido)} al mes</strong>{" "}
            <span className="jg-delta" data-signo={cambio > 0 ? "mas" : "menos"}>
              {cambio > 0 ? "+" : ""}
              {cambio}% de tu sueldo
            </span>
          </Text>
        )}
        <Text>¿La miras en serio, o sigues donde estás?</Text>
      </Stack>
      <ScreenFooter>
        {error && <ErrorCaja error={error} />}
        <div className="jg-dos-botones">
          <Button variant="white" onClick={() => quedarse && onElegir({ decision: p.decision, opcion: quedarse.opcion })} disabled={cargando || !quedarse}>
            No, sigo
          </Button>
          <Button variant="white" onClick={onMirar} disabled={cargando}>
            Mirarla
          </Button>
        </div>
      </ScreenFooter>
    </Screen>
  );
}
