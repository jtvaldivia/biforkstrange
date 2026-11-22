import { BifurcaLogo, Button, Heading, LifePathHero, Meta, Row, Screen, ScreenFooter, ScreenHeader, Stack, Tag, Text, cssVars } from "@/shared/ui";
import { GEMELOS } from "../api";
import { Cargando, ErrorCaja } from "./piezas";

/** Portada. Viene de la pantalla "1 · Inicio" del kit. */
export function Inicio({
  hayPartida,
  cargando,
  error,
  aviso = null,
  onEmpezar,
  onContinuar,
  onComoFunciona,
}: {
  hayPartida: boolean;
  cargando: boolean;
  error: string | null;
  /** Algo que la persona tiene que saber antes de seguir (su partida guardada ya no sirve). */
  aviso?: string | null;
  onEmpezar: () => void;
  onContinuar: () => void;
  onComoFunciona: () => void;
}) {
  return (
    <Screen>
      <ScreenHeader left={<BifurcaLogo size={20} />} right={<Meta>10 años</Meta>} />
      <LifePathHero past={["Estudios", "Tu trabajo"]} today="Tú, hoy" chosen="Lo que eliges" alternatives={["Otra opción", "Seguir igual"]} />
      <Stack gap={12}>
        <Heading level={1}>Vive tu decisión antes de tomarla.</Heading>
        <Text>Un gemelo tuyo prueba cada opción en {GEMELOS} mundos.</Text>
      </Stack>
      <div className="jg-mini" aria-hidden="true">
        {Array.from({ length: 100 }, (_, i) => (
          <i key={i} data-final={((i * 7919 + 104729) % 1000) / 1000 < 0.46 ? "mas" : ((i * 7919 + 104729) % 1000) / 1000 < 0.8 ? "igual" : "menos"} style={cssVars({ "--jg-i": i })} />
        ))}
      </div>
      <Row gap={6}>
        <Tag>1 · Tu perfil</Tag>
        <Tag>2 · Tu duda</Tag>
        <Tag>3 · Vives el mundo {GEMELOS + 1}</Tag>
      </Row>
      <ScreenFooter>
        {aviso && (
          <div className="jg-error" role="status">
            {aviso}
          </div>
        )}
        {error && <ErrorCaja error={error} onReintentar={hayPartida ? onContinuar : undefined} />}
        {cargando && <Cargando>Retomando tu partida…</Cargando>}
        {hayPartida && (
          <Button onClick={onContinuar} disabled={cargando}>
            Seguir mi partida
          </Button>
        )}
        <Button variant={hayPartida ? "white" : "primary"} onClick={onEmpezar} disabled={cargando}>
          {hayPartida ? "Empezar otra vida" : "Empezar"}
        </Button>
        <Button variant="quiet" onClick={onComoFunciona} disabled={cargando}>
          ¿Cómo funciona?
        </Button>
      </ScreenFooter>
    </Screen>
  );
}
