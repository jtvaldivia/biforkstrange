/**
 * Juego conectado al motor (POST /api/juego/turno), armado solo con el kit de @/shared/ui.
 * Cuatro pantallas: inicio, decisión del año, lo que pasó y fin de la partida.
 */
import { useState } from "react";
import {
  BigNumber, Button, DecisionArt, DecisionList, Heading, Indicator, LifePathHero, LinesChart, Meta, Narrative, Panel,
  Pill, Row, Screen, ScreenFooter, ScreenHeader, Segmented, SlowReveal, Stack, SunCard, Tag, Text,
  type DecisionTag,
} from "@/shared/ui";
import { arte, atributos, cargo, indicadores, nivelIA, plata, resumenFicha } from "./formato";
import { PERFIL_EJEMPLO } from "./perfilEjemplo";
import type { Ficha, Opcion, Perfil } from "./types";
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
    juego.empezar(perfil, "base");
  };

  return (
    <Screen>
      <ScreenHeader left={<Pill>Simulador de vida</Pill>} right={<Meta>BiforkStrange</Meta>} />
      <LifePathHero />
      <Stack gap={12}>
        <Heading level={1}>Vive tu vida laboral antes de vivirla.</Heading>
        <Text>Cada año te tocan dos o tres cartas: seguir como vas u otra jugada. Todo lo que pasa sale de datos chilenos.</Text>
      </Stack>
      <Row gap={6}>
        <Tag>Una decisión por año</Tag>
        <Tag>Ofertas, ascensos y logros</Tag>
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
      {(errorPerfil || juego.error) && <Text size="sm">⚠ {errorPerfil || juego.error}</Text>}
      <ScreenFooter>
        <Button onClick={empezar} disabled={juego.cargando}>
          {juego.cargando ? "Simulando…" : "Empezar una vida"}
        </Button>
      </ScreenFooter>
    </Screen>
  );
}

/* Atributos del gemelo: ocho barras; con `antes` muestra cuánto cambió cada una */
function Atributos({ ficha, antes, label }: { ficha: Ficha; antes?: Ficha; label: string }) {
  const previos = antes ? atributos(antes) : undefined;
  return (
    <div className="vd-inds" role="group" aria-label={label}>
      {atributos(ficha).map((a, i) => (
        <Indicator key={a.clave} indicator={a.color} label={a.nombre} value={a.valor} previous={previos?.[i].valor} />
      ))}
    </div>
  );
}

function Trabajo({ f }: { f: Ficha }) {
  const tipo: Record<string, string> = { startup: "Startup", pyme: "Pyme", grande: "Empresa grande", estado: "Estado" };
  return (
    <Panel>
      <Stack gap={6}>
        <Meta>{f.situacion === "con empleo" ? "Tu pega" : "Tu situación"}</Meta>
        {f.situacion === "con empleo" ? (
          <>
            <Heading level={3} as="h2">{`${cargo(f)} · ${f.nivel}`}</Heading>
            <Text size="sm">{`En ${f.empresa} desde hace ${Math.round(f.antiguedad)} ${Math.round(f.antiguedad) === 1 ? "año" : "años"}. ${f.rubro}.`}</Text>
          </>
        ) : (
          <Heading level={3} as="h2">{f.situacion === "emprendiendo" ? "Con tu emprendimiento" : "Sin trabajo, buscando"}</Heading>
        )}
      </Stack>
      <Row gap={6}>
        {f.situacion === "con empleo" && <Tag tone="accent">{`${plata(f.sueldo)} al mes`}</Tag>}
        {f.situacion === "con empleo" && <Tag>{tipo[f.empleador] ?? f.empleador}</Tag>}
        <Tag tone={f.ahorros < 0 ? "minus" : "default"}>{f.ahorros < 0 ? `Deuda ${plata(-f.ahorros)}` : `Ahorros ${plata(f.ahorros)}`}</Tag>
        <Tag>{`${f.pareja ? "Con pareja" : "Sin pareja"} · ${f.hijos} ${f.hijos === 1 ? "hijo" : "hijos"}`}</Tag>
        {f.situacion === "con empleo" && <Tag>{`${Math.round(f.exp_ocupacion)} años en tu ocupación`}</Tag>}
        {f.depresion && <Tag tone="minus">Síntomas depresivos</Tag>}
        <Tag tone={f.ia >= 0.65 ? "minus" : "default"}>{`IA: exposición ${nivelIA(f.ia)}`}</Tag>
        {f.estudia > 0 && <Tag tone="sol">Estudiando magíster</Tag>}
        {f.postgrado && <Tag>Magíster</Tag>}
      </Row>
    </Panel>
  );
}

/* 2 · Decisión del año */
const TONO = { mas: "accent", menos: "minus", neutro: "default" } as const;

function etiquetas(o: Opcion): DecisionTag[] {
  const t: DecisionTag[] = [];
  if (o.tipo === "oportunidad") t.push({ label: "Solo este año", tone: "sol" });
  if (o.gemelos_texto) t.push({ label: o.gemelos_texto, tone: "default" });
  for (const e of o.efectos) t.push({ label: e.texto, tone: TONO[e.tono] });
  return t;
}

function Decision({ juego }: { juego: Juego }) {
  const { yo, menu, perfil, historial, logros } = juego.partida!;
  const [elegida, setElegida] = useState<string | null>(null);

  return (
    <Screen>
      <ScreenHeader left={<Pill>{`${yo.anio} · ${yo.edad} años`}</Pill>} right={<Meta>{`Año ${historial.length + 1} · ${logros.length} logros`}</Meta>} />
      <Heading level={1}>{`${perfil.nombre}, ¿qué haces este año?`}</Heading>
      <Trabajo f={yo} />
      <Atributos ficha={yo} label="Tus atributos hoy" />
      <Heading level={3} as="h2">{`Tu jugada de ${yo.anio}`}</Heading>
      <DecisionList
        label="Jugada del año"
        value={elegida}
        onChange={setElegida}
        options={menu.map((o) => ({
          id: o.decision,
          art: <DecisionArt kind={arte(o.decision)} />,
          title: o.nombre,
          subtitle: o.descripcion,
          tags: etiquetas(o),
        }))}
      />
      {juego.error && <Text size="sm">⚠ {juego.error}</Text>}
      <ScreenFooter>
        <Stack gap={10}>
          <Button disabled={!elegida || juego.cargando} onClick={() => elegida && juego.decidir(elegida)}>
            {juego.cargando ? "Viviendo el año…" : elegida ? "Vivir este año" : "Elige tu jugada"}
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
function Resultado({ juego, antes }: { juego: Juego; antes: Ficha }) {
  const { historial } = juego.partida!;
  const t = historial[historial.length - 1];
  const duro = t.yo.situacion === "sin trabajo" || t.eventos.some((e) => /despidieron|depresivos|separaste|endeudarte|cerró/.test(e));

  return (
    <Screen tone={duro ? "noche" : "dia"} key={historial.length}>
      <ScreenHeader left={<Pill tone="sol">{`${t.yo.anio - 1} · ${t.yo.edad - 1} años`}</Pill>} right={<Meta>Lo que pasó</Meta>} />
      <Stack gap={6}>
        <Meta>Tu jugada</Meta>
        <Heading level={1}>{t.nombre}</Heading>
      </Stack>
      <Stack gap={10}>
        {t.eventos.map((e, i) => (
          <SlowReveal key={e} delay={0.3 + i * 0.7}>
            <Narrative strong={i === 0}>{e}</Narrative>
          </SlowReveal>
        ))}
      </Stack>
      {t.logros.length > 0 && (
        <SunCard>
          <Meta>{t.logros.length === 1 ? "Logro desbloqueado" : "Logros desbloqueados"}</Meta>
          <Heading level={2} as="h2">{t.logros.join(" · ")}</Heading>
        </SunCard>
      )}
      <Trabajo f={t.yo} />
      <Atributos ficha={t.yo} antes={antes} label="Cómo cambiaron tus atributos" />
      <ScreenFooter>
        <Stack gap={10}>
          <Button onClick={juego.seguir}>{t.yo.edad >= 50 ? "Ver el final" : `Jugar ${t.yo.anio}`}</Button>
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
  const { historial, yo, logros } = juego.partida!;
  const fichas = [inicial, ...historial.map((t) => t.yo)];
  const inds = fichas.map((f) => indicadores(f, sueldo0));
  const mios = indicadores(yo, sueldo0);
  const felicidad = Math.round((mios.dinero + mios.carrera + mios.bienestar + mios.vida) / 4);
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
        <Text>Promedio de dinero, carrera, bienestar y vida personal al cierre de la partida.</Text>
      </SunCard>
      <Stack as="section" gap={10}>
        <Heading level={3} as="h2">{`Logros: ${logros.length}`}</Heading>
        {logros.length > 0 ? (
          <Row gap={6}>
            {logros.map((l) => (
              <Tag key={l} tone="sol">
                {l}
              </Tag>
            ))}
          </Row>
        ) : (
          <Text size="sm">Ninguno todavía. Prueba otra vida.</Text>
        )}
      </Stack>
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
      <Stack as="section" gap={10}>
        <Heading level={3} as="h2">
          Cómo terminas
        </Heading>
        <Trabajo f={yo} />
        <Atributos ficha={yo} antes={inicial} label="Tus atributos al final contra cómo partiste" />
      </Stack>
      <Stack as="section" gap={10}>
        <Heading level={3} as="h2">
          Lo que jugaste
        </Heading>
        <Stack gap={12}>
          {historial.map((t) => (
            <Stack key={t.yo.anio} gap={2}>
              <Meta>{`${t.yo.anio - 1} · ${t.yo.edad - 1} años · ${t.nombre}`}</Meta>
              <Text size="sm">{t.eventos.join(" ")}</Text>
            </Stack>
          ))}
        </Stack>
      </Stack>
      <Stack gap={10}>
        <Button onClick={juego.repetir} disabled={juego.cargando}>
          Misma suerte, otras jugadas
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
  if (fase === "resultado" && h.length > 0) return <Resultado juego={juego} antes={h.length > 1 ? h[h.length - 2].yo : inicial} />;
  if (fase === "resumen") return <Resumen juego={juego} sueldo0={sueldo0} inicial={inicial} />;
  return <Decision key={h.length} juego={juego} />;
}
