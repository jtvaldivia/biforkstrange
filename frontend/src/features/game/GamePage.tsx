/**
 * Juego conectado al motor (POST /api/juego/turno), armado solo con el kit de @/shared/ui.
 * Cuatro pantallas: inicio, decisión del año, lo que pasó y fin de la partida.
 */
import { useState } from "react";
import {
  BigNumber, Button, DecisionArt, DecisionList, Heading, IndicatorGrid, LifePathHero, LinesChart, Meta, Narrative, NightBand, Panel,
  Pill, RangeCompare, Row, Screen, ScreenFooter, ScreenHeader, Segmented, SlowReveal, Stack, SunCard, Tag, Text,
  type DecisionTag,
} from "@/shared/ui";
import { arte, indicadores, nivelIA, plata, porc, rangoIngreso, resumenFicha } from "./formato";
import { PERFIL_EJEMPLO } from "./perfilEjemplo";
import type { EscenarioIA, Ficha, Opcion, Perfil } from "./types";
import { useGame } from "./useGame";

const CLAVE_PERFIL = "biforkstrange.perfil";
type Juego = ReturnType<typeof useGame>;

function leerPerfilGuardado(): string {
  try {
    return localStorage.getItem(CLAVE_PERFIL) ?? "";
  } catch {
    return "";
  }
}

/* 1 · Inicio */
function Inicio({ juego }: { juego: Juego }) {
  const [fuente, setFuente] = useState<"ejemplo" | "mio">(leerPerfilGuardado() ? "mio" : "ejemplo");
  const [texto, setTexto] = useState(leerPerfilGuardado());
  const [ia, setIa] = useState<EscenarioIA>("base");
  const [errorPerfil, setErrorPerfil] = useState("");

  const empezar = () => {
    let perfil: Perfil = PERFIL_EJEMPLO;
    if (fuente === "mio") {
      try {
        perfil = JSON.parse(texto);
      } catch {
        setErrorPerfil("El perfil no es un JSON válido.");
        return;
      }
      try {
        localStorage.setItem(CLAVE_PERFIL, texto);   // queda solo en este navegador
      } catch {
        /* sin almacenamiento: se juega igual */
      }
    }
    setErrorPerfil("");
    juego.empezar(perfil, ia);
  };

  return (
    <Screen>
      <ScreenHeader left={<Pill>Simulador de vida</Pill>} right={<Meta>BiforkStrange</Meta>} />
      <LifePathHero />
      <Stack gap={12}>
        <Heading level={1}>Vive tu vida laboral antes de vivirla.</Heading>
        <Text>Cada año eliges tú. Antes de vivirlo ves qué pasaría con cada camino en mil futuros posibles.</Text>
      </Stack>
      <Row gap={6}>
        <Tag>Una decisión por año</Tag>
        <Tag>1.000 futuros por opción</Tag>
        <Tag>Datos de Chile</Tag>
      </Row>
      <Panel>
        <Stack gap={10}>
          <Heading level={3} as="h2">
            ¿Quién juega?
          </Heading>
          <Segmented
            label="Qué perfil usar"
            value={fuente}
            onChange={setFuente}
            options={[
              { value: "ejemplo", label: "Camila (ejemplo)" },
              { value: "mio", label: "Mi perfil" },
            ]}
          />
          {fuente === "ejemplo" ? (
            <Text size="sm">28 años, analista en un banco, $1,4 M al mes, ansiosa y cautelosa. Perfil ficticio.</Text>
          ) : (
            <Stack gap={6}>
              <Text size="sm">Pega tu perfil en formato bifurca.perfil. Se guarda solo en este navegador.</Text>
              <textarea
                aria-label="Tu perfil en JSON"
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
                rows={7}
                spellCheck={false}
                placeholder='{"nombre": "…", "edad": 25, "sueldo_liquido_mensual": 2000000, …}'
                style={{
                  width: "100%", boxSizing: "border-box", padding: 10, borderRadius: 12, border: "2px solid var(--linea)",
                  background: "var(--papel)", color: "var(--tinta)", fontFamily: "ui-monospace, monospace", fontSize: 12, resize: "vertical",
                }}
              />
            </Stack>
          )}
        </Stack>
      </Panel>
      <Stack gap={8}>
        <Heading level={3} as="h2">
          ¿Qué tan rápido llega la IA?
        </Heading>
        <Segmented
          label="Velocidad de adopción de la IA"
          value={ia}
          onChange={setIa}
          options={[
            { value: "lenta", label: "Lenta" },
            { value: "base", label: "Normal" },
            { value: "rapida", label: "Rápida" },
          ]}
        />
      </Stack>
      {(errorPerfil || juego.error) && <Text size="sm">⚠ {errorPerfil || juego.error}</Text>}
      <ScreenFooter>
        <Button onClick={empezar} disabled={juego.cargando}>
          {juego.cargando ? "Simulando…" : "Empezar una vida"}
        </Button>
      </ScreenFooter>
    </Screen>
  );
}

/* 2 · Decisión del año */
function etiquetas(o: Opcion): DecisionTag[] {
  const t: DecisionTag[] = [{ label: `${plata(o.ingreso[1])} al mes` }];
  if (o.decision !== "seguir") {
    if (o.p_mejor >= o.p_peor && o.p_mejor > 0.02) t.push({ label: `Ganas más en ${porc(o.p_mejor)}`, tone: "accent" });
    else if (o.p_peor > 0.02) t.push({ label: `Ganas menos en ${porc(o.p_peor)}`, tone: "minus" });
  }
  if (o.p_deuda >= 0.2) t.push({ label: `Deuda ${porc(o.p_deuda)}`, tone: "minus" });
  if (o.p_cesantia >= 0.3) t.push({ label: `Sin pega ${porc(o.p_cesantia)}`, tone: "minus" });
  if (o.energia_min < 45) t.push({ label: `Energía baja a ${Math.round(o.energia_min)}`, tone: "minus" });
  if (o.p_burnout >= 0.05) t.push({ label: `Agotamiento ${porc(o.p_burnout)}`, tone: "minus" });
  return t;
}

function subtitulo(o: Opcion): string {
  const gemelos = `Lo elegiría el ${porc(o.gemelos)} de tus gemelos`;
  if (o.extra.afinidad !== undefined && o.extra.logra !== undefined && o.extra.ia_destino !== undefined)
    return `Afinidad ${porc(o.extra.afinidad)}, lo logras con ${porc(o.extra.logra)}. IA ${nivelIA(o.extra.ia_destino)}. ${gemelos}.`;
  return `${gemelos}.`;
}

function Decision({ juego, sueldo0 }: { juego: Juego; sueldo0: number }) {
  const { yo, menu, perfil, historial } = juego.partida!;
  const [elegida, setElegida] = useState<string | null>(null);
  const seguir = menu.find((o) => o.decision === "seguir") ?? menu[0];
  const op = menu.find((o) => o.decision === elegida);
  const techo = 1.15 * Math.max(...menu.map((o) => o.ingreso[2]));

  return (
    <Screen>
      <ScreenHeader left={<Pill>{`${yo.anio} · ${yo.edad} años`}</Pill>} right={<Meta>{`Año ${historial.length + 1}`}</Meta>} />
      <Stack>
        <Heading level={1}>{`${perfil.nombre}, ¿qué haces este año?`}</Heading>
        <Text>{resumenFicha(yo)}</Text>
      </Stack>
      <IndicatorGrid values={indicadores(yo, sueldo0)} label="Cómo estás hoy" />
      <Row gap={6}>
        <Tag>{perfil.arquetipo}</Tag>
        <Tag tone={yo.ia >= 0.65 ? "minus" : "default"}>{`Exposición a IA ${nivelIA(yo.ia)}`}</Tag>
        <Tag>{`${Math.round(yo.contactos)} contactos`}</Tag>
        {yo.estudia > 0 && <Tag tone="sol">Estudiando magíster</Tag>}
      </Row>
      <Stack gap={4}>
        <Heading level={3} as="h2">
          Tus caminos
        </Heading>
        <Text size="sm">Cada uno se simuló 1.000 veces a 5 años, con la misma suerte. El monto es el ingreso mensual típico.</Text>
      </Stack>
      <DecisionList
        label="Decisión del año"
        value={elegida}
        onChange={setElegida}
        options={menu.map((o) => ({ id: o.decision, art: <DecisionArt kind={arte(o.decision)} />, title: o.nombre, subtitle: subtitulo(o), tags: etiquetas(o) }))}
      />
      {op && op.decision !== "seguir" && (
        <Stack as="section" gap={10}>
          <Heading level={3} as="h2">
            Seguir igual contra este camino
          </Heading>
            <Stack gap={6}>
              <span className="vd-camino">
                <Tag tone="accent">A</Tag>Seguir igual
              </span>
              <span className="vd-camino">
                <Tag>B</Tag>
                {op.nombre}
              </span>
            </Stack>
            <RangeCompare indicator="dinero" label="Ingreso mensual a 5 años: caso malo, típico y bueno" a={rangoIngreso(seguir, techo)} b={rangoIngreso(op, techo)} />
            <Text size="sm">
              {`A: ${plata(seguir.ingreso[0])} a ${plata(seguir.ingreso[2])}. B: ${plata(op.ingreso[0])} a ${plata(op.ingreso[2])}. `}
              {`Ahorros a 5 años: ${plata(seguir.ahorros[1])} contra ${plata(op.ahorros[1])}. Con la misma suerte, B gana más en ${porc(op.p_mejor)} de los futuros y menos en ${porc(op.p_peor)}.`}
            </Text>
        </Stack>
      )}
      {juego.error && <Text size="sm">⚠ {juego.error}</Text>}
      <ScreenFooter>
        <Stack gap={10}>
          <Button disabled={!elegida || juego.cargando} onClick={() => elegida && juego.decidir(elegida)}>
            {juego.cargando ? "Viviendo el año…" : elegida ? "Vivir este año" : "Elige un camino"}
          </Button>
          {historial.length > 0 && (
            <Button variant="quiet" onClick={juego.terminar}>
              Terminar la partida
            </Button>
          )}
        </Stack>
      </ScreenFooter>
    </Screen>
  );
}

/* 3 · Lo que pasó */
function Resultado({ juego, sueldo0, antes }: { juego: Juego; sueldo0: number; antes: Ficha }) {
  const { historial } = juego.partida!;
  const t = historial[historial.length - 1];
  const duro = t.yo.situacion === "sin trabajo" || t.eventos.some((e) => /despidieron|agotaste|separaste|endeudarte|cerró/.test(e));
  const n = t.nube_eventos;
  const dif = t.yo.ahorros - t.sombra.ahorros;

  return (
    <Screen tone={duro ? "noche" : "dia"} key={historial.length}>
      <ScreenHeader left={<Pill tone="sol">{`${t.yo.anio - 1} · ${t.yo.edad - 1} años`}</Pill>} right={<Meta>Lo que pasó</Meta>} />
      <Stack gap={6}>
        <Meta>Elegiste</Meta>
        <Heading level={1}>{t.nombre.replace("→ ", "Pasar a ")}</Heading>
      </Stack>
      <Stack gap={10}>
        {t.eventos.map((e, i) => (
          <SlowReveal key={e} delay={0.3 + i * 0.7}>
            <Narrative strong={i === 0}>{e}</Narrative>
          </SlowReveal>
        ))}
      </Stack>
      <IndicatorGrid values={indicadores(t.yo, sueldo0)} previous={indicadores(antes, sueldo0)} label="Cómo cambió tu año" />
      <Text size="sm">{resumenFicha(t.yo)}</Text>
      <NightBand>
        <Stack gap={6}>
          <Meta>Tu sombra</Meta>
          <Text size="sm">
            {`El gemelo que nunca cambia nada, con tu misma suerte: ${resumenFicha(t.sombra)} `}
            {Math.abs(dif) < 500_000 ? "Van a la par." : `Tú vas ${plata(Math.abs(dif))} ${dif > 0 ? "arriba" : "abajo"} en ahorros.`}
          </Text>
        </Stack>
      </NightBand>
      {n.despido + n.cambio + n.ascenso + n.burnout > 0 && <Text size="sm">
        {`En los 1.000 futuros de este año: despido ${porc(n.despido)}, cambio de pega ${porc(n.cambio)}, ascenso ${porc(n.ascenso)}, agotamiento ${porc(n.burnout)}.`}
      </Text>}
      <ScreenFooter>
        <Stack gap={10}>
          <Button onClick={juego.seguir}>{t.yo.edad >= 50 ? "Ver el final" : `Decidir ${t.yo.anio}`}</Button>
          <Button variant="quiet" onClick={juego.terminar}>
            Terminar la partida
          </Button>
        </Stack>
      </ScreenFooter>
    </Screen>
  );
}

/* 4 · Fin de la partida */
function Resumen({ juego, sueldo0, inicial }: { juego: Juego; sueldo0: number; inicial: Ficha }) {
  const { historial, yo, sombra } = juego.partida!;
  const fichas = [inicial, ...historial.map((t) => t.yo)];
  const inds = fichas.map((f) => indicadores(f, sueldo0));
  const mios = indicadores(yo, sueldo0);
  const suyos = indicadores(sombra, sueldo0);
  const felicidad = Math.round((mios.dinero + mios.carrera + mios.bienestar + mios.vida) / 4);
  const felicidadSombra = Math.round((suyos.dinero + suyos.carrera + suyos.bienestar + suyos.vida) / 4);
  const anios = historial.length;

  return (
    <Screen gap={28}>
      <Stack gap={12}>
        <ScreenHeader left={<Pill tone="sol">Fin de la partida</Pill>} right={<Meta>{`${inicial.anio} – ${yo.anio}`}</Meta>} />
        <Heading level={1}>{`${anios} ${anios === 1 ? "año" : "años"} en la vida que elegiste.`}</Heading>
      </Stack>
      <SunCard>
        <Meta>Tu vida, en un número</Meta>
        <BigNumber value={felicidad} unit="/ 100" animate />
        <Text>
          {`Promedio de dinero, carrera, bienestar y vida personal. Tu sombra, que no cambió nada, quedó en ${felicidadSombra}. `}
          {felicidad > felicidadSombra ? "Tus decisiones sumaron." : felicidad < felicidadSombra ? "Sin moverte te habría ido mejor." : "Quedaron iguales."}
        </Text>
      </SunCard>
      {anios >= 1 && (
        <Stack as="section" gap={10}>
          <Heading level={3} as="h2">
            Tu vida en cuatro líneas
          </Heading>
          <LinesChart
            label="Evolución de dinero, carrera, bienestar y vida personal durante la partida"
            startYear={inicial.anio}
            endYear={yo.anio}
            series={{ dinero: inds.map((i) => i.dinero), carrera: inds.map((i) => i.carrera), bienestar: inds.map((i) => i.bienestar), vida: inds.map((i) => i.vida) }}
          />
        </Stack>
      )}
      <Stack as="section" gap={12}>
        <Stack gap={4}>
          <Heading level={3} as="h2">
            Tú contra tu sombra
          </Heading>
          <Text size="sm">Misma persona y misma suerte. La única diferencia son tus decisiones.</Text>
        </Stack>
        <Stack gap={6}>
          <span className="vd-camino">
            <Tag tone="accent">Tú</Tag>
            {resumenFicha(yo)}
          </span>
          <span className="vd-camino">
            <Tag>Sombra</Tag>
            {resumenFicha(sombra)}
          </span>
        </Stack>
        <IndicatorGrid values={mios} previous={suyos} label="Tus indicadores contra los de tu sombra" />
      </Stack>
      <Stack as="section" gap={10}>
        <Heading level={3} as="h2">
          Lo que decidiste
        </Heading>
        <Stack gap={12}>
          {historial.map((t) => (
            <Stack key={t.yo.anio} gap={2}>
              <Meta>{`${t.yo.anio - 1} · ${t.yo.edad - 1} años · ${t.nombre.replace("→ ", "Pasar a ")}`}</Meta>
              <Text size="sm">{t.eventos.join(" ")}</Text>
            </Stack>
          ))}
        </Stack>
      </Stack>
      <Stack gap={10}>
        <Button onClick={juego.repetir} disabled={juego.cargando}>
          Misma suerte, otras decisiones
        </Button>
        <Button variant="white" onClick={juego.reiniciar}>
          Empezar otra vida
        </Button>
      </Stack>
    </Screen>
  );
}

export function GamePage() {
  const juego = useGame();
  const { fase, partida, inicial } = juego;
  if (fase === "inicio" || !partida || !inicial) return <Inicio juego={juego} />;

  const sueldo0 = Math.max(inicial.sueldo || inicial.ingreso_mes || 1_000_000, 1);
  const h = partida.historial;
  if (fase === "resultado" && h.length > 0) return <Resultado juego={juego} sueldo0={sueldo0} antes={h.length > 1 ? h[h.length - 2].yo : inicial} />;
  if (fase === "resumen") return <Resumen juego={juego} sueldo0={sueldo0} inicial={inicial} />;
  return <Decision key={h.length} juego={juego} sueldo0={sueldo0} />;
}
