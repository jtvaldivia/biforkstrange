import { useState } from "react";
import { BifurcaLogo, Button, Heading, LifePathHero, Screen, ScreenFooter, ScreenHeader, Stack, Text, cssVars } from "@/shared/ui";
import { GEMELOS } from "../api";
import { Cargando, ErrorCaja } from "./piezas";

/** Portada. Viene de la pantalla "1 · Inicio" del kit. */
export function Inicio({
  hayPartida,
  terminada = false,
  cargando,
  error,
  aviso = null,
  onEmpezar,
  onContinuar,
  onComoFunciona,
  onOtraDuda,
}: {
  hayPartida: boolean;
  /** La partida guardada ya llegó al final: se ofrece ver el resultado, no seguirla. */
  terminada?: boolean;
  cargando: boolean;
  error: string | null;
  /** Algo que la persona tiene que saber antes de seguir (su partida guardada ya no sirve). */
  aviso?: string | null;
  onEmpezar: () => void;
  onContinuar: () => void;
  onComoFunciona: () => void;
  /** Con el mismo perfil, a elegir otra duda. */
  onOtraDuda?: () => void;
}) {
  /** Empezar con otro perfil borra la partida y el perfil guardados: se pide confirmar en la misma pantalla. */
  const [confirmando, setConfirmando] = useState(false);
  return (
    <Screen>
      <ScreenHeader left={<BifurcaLogo size={20} />} />
      <LifePathHero past={["Estudios", "Tu trabajo"]} today="Tú, hoy" chosen="Lo que eliges" alternatives={["Otra opción", "Seguir igual"]} />
      <Stack gap={12}>
        <Heading level={1}>Vive tu decisión antes de tomarla.</Heading>
        <Text>Una copia tuya prueba cada opción en {GEMELOS} mundos.</Text>
      </Stack>
      <div className="jg-mini" aria-hidden="true">
        {Array.from({ length: GEMELOS }, (_, i) => (
          <i key={i} data-final={((i * 7919 + 104729) % 1000) / 1000 < 0.46 ? "mas" : ((i * 7919 + 104729) % 1000) / 1000 < 0.8 ? "igual" : "menos"} style={cssVars({ "--jg-i": i })} />
        ))}
      </div>
      <ScreenFooter>
        {aviso && (
          <div className="jg-error" role="status">
            {aviso}
          </div>
        )}
        {error && <ErrorCaja error={error} onReintentar={hayPartida ? onContinuar : undefined} />}
        {cargando && <Cargando>Retomando tu partida…</Cargando>}
        {confirmando ? (
          <>
            <div className="vd-caja" role="alert">
              <Text size="sm">Se borran tu partida y tu perfil. Vas a armar un perfil nuevo desde cero.</Text>
            </div>
            <Button onClick={onEmpezar}>Sí, empezar con otro perfil</Button>
            <Button variant="white" onClick={() => setConfirmando(false)}>
              No, volver
            </Button>
          </>
        ) : (
          <>
            {hayPartida && (
              <Button onClick={onContinuar} disabled={cargando}>
                {terminada ? "Ver mi resultado" : "Seguir mi partida"}
              </Button>
            )}
            {hayPartida && onOtraDuda && (
              <Button variant="white" onClick={onOtraDuda} disabled={cargando}>
                Probar otra duda
              </Button>
            )}
            <Button variant={hayPartida ? "white" : "primary"} onClick={hayPartida ? () => setConfirmando(true) : onEmpezar} disabled={cargando}>
              {hayPartida ? "Empezar con otro perfil" : "Empezar"}
            </Button>
            <Button variant="quiet" onClick={onComoFunciona} disabled={cargando}>
              ¿Cómo funciona?
            </Button>
          </>
        )}
      </ScreenFooter>
    </Screen>
  );
}
