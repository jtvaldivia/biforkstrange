import { useState, type ReactNode } from "react";
import {
  Avatar,
  BigNumber,
  Button,
  ChevronLeftIcon,
  Chip,
  DecisionArt,
  DecisionCard,
  DECISION_ART_KINDS,
  DotLegend,
  DotRow,
  Heading,
  IconButton,
  Indicator,
  IndicatorGrid,
  LifePathHero,
  Meta,
  MissedList,
  NightBand,
  Notification,
  Panel,
  Pill,
  RangeCompare,
  Row,
  Segmented,
  Slider,
  Stack,
  SunCard,
  Tag,
  Text,
  Narrative,
} from "@/shared/ui";
import { SCREENS, SCREEN_COMPONENTS, type ScreenId } from "./screens";
import { Espera, type Variante } from "@/features/juego/components/Apuesta";

const VARIANTES_ESPERA: Variante[] = ["ruleta", "tragamonedas", "caballos", "dado", "naipes"];

/** Catálogo vivo del kit de UI: componentes sueltos y las 8 pantallas del diseño. */
export function UiKitPage() {
  const [tab, setTab] = useState<"pantallas" | "componentes">("pantallas");
  return (
    <div className="vd" style={{ minHeight: "100dvh", background: "var(--niebla)" }}>
      <div style={{ maxWidth: 960, margin: "0 auto", padding: "56px 20px 32px", display: "flex", flexDirection: "column", gap: 24 }}>
        <Stack gap={12}>
          <Row gap={12} style={{ alignItems: "center", justifyContent: "space-between" }}>
            <Pill>Bifurca · UI kit</Pill>
            <a href="/" className="vd-meta">
              Ir a la app
            </a>
          </Row>
          <Heading level={1}>Componentes del simulador de vida</Heading>
          <Text>
            Todo vive en <code>@/shared/ui</code>. Las pantallas de abajo están armadas solo con esos componentes.
          </Text>
          <div style={{ maxWidth: 420 }}>
            <Segmented
              label="Qué ver"
              value={tab}
              onChange={setTab}
              options={[
                { value: "pantallas", label: "Pantallas" },
                { value: "componentes", label: "Componentes" },
              ]}
            />
          </div>
        </Stack>
        {tab === "pantallas" ? <ScreensGallery /> : <ComponentsGallery />}
      </div>
    </div>
  );
}

function ScreensGallery() {
  const [id, setId] = useState<ScreenId>("inicio");
  const [run, setRun] = useState(0);
  const Current = SCREEN_COMPONENTS[id];
  const go = (next: ScreenId) => {
    setId(next);
    setRun((r) => r + 1);
  };
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 24, alignItems: "flex-start" }}>
      <nav aria-label="Pantallas" style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 220 }}>
        {SCREENS.map((s) => (
          <Chip key={s.id} pressed={s.id === id} onToggle={() => go(s.id)}>
            {s.title}
          </Chip>
        ))}
        <Button variant="quiet" onClick={() => setRun((r) => r + 1)}>
          Repetir animación
        </Button>
      </nav>
      <div
        style={{
          width: 390,
          maxWidth: "100%",
          border: "2px solid var(--tinta)",
          borderRadius: 28,
          overflow: "hidden",
          boxShadow: "0 6px 0 var(--sombra)",
          background: "var(--papel)",
        }}
      >
        <Current key={`${id}-${run}`} go={go} />
      </div>
    </div>
  );
}

function Section({ title, children, note }: { title: string; note?: string; children: ReactNode }) {
  return (
    <section style={{ background: "var(--papel)", border: "2px solid var(--tinta)", borderRadius: 20, padding: 20 }}>
      <Stack gap={14}>
        <Stack gap={4}>
          <Heading level={3} as="h2">
            {title}
          </Heading>
          {note && <Text size="sm">{note}</Text>}
        </Stack>
        {children}
      </Stack>
    </section>
  );
}

const grid = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 } as const;

function ComponentsGallery() {
  const [chip, setChip] = useState(true);
  const [seg, setSeg] = useState<"a" | "b">("a");
  const [slider, setSlider] = useState(6);
  const [card, setCard] = useState(true);
  const [tirada, setTirada] = useState(0);
  return (
    <div style={grid}>
      <Section title="Tipografía" note="Heading 1/2/3, Text, Meta, Pill, BigNumber, Narrative">
        <Heading level={1}>Heading 1</Heading>
        <Heading level={2}>Heading 2</Heading>
        <Heading level={3}>Heading 3</Heading>
        <Text>Texto de párrafo, 16px.</Text>
        <Text size="sm">Texto chico, 14px.</Text>
        <Meta>Meta · 2027 · 23 años</Meta>
        <Row>
          <Pill>2027 · 23 años</Pill>
          <Pill tone="sol">Fin de la partida</Pill>
        </Row>
        <BigNumber value={61} unit="/ 100" />
        <Narrative>Ibas a ir el fin de semana.</Narrative>
        <Narrative strong>Estabas en la oficina.</Narrative>
      </Section>

      <Section title="Botones" note="Button (primary, white, sol, quiet) e IconButton">
        <Button>Empezar una vida</Button>
        <Button variant="white">Volver al inicio</Button>
        <Button variant="sol">Levantar la cabeza</Button>
        <Button variant="quiet">Volver a 2027 y elegir distinto</Button>
        <Button disabled>Deshabilitado</Button>
        <IconButton label="Volver">
          <ChevronLeftIcon />
        </IconButton>
      </Section>

      <Section title="Controles" note="Chip, Segmented, Slider, Tag">
        <Row>
          <Chip pressed={chip} onToggle={() => setChip(!chip)}>
            Familia cerca
          </Chip>
          <Chip pressed={!chip} onToggle={() => setChip(!chip)}>
            Vivir afuera
          </Chip>
        </Row>
        <Segmented
          label="Ejemplo"
          value={seg}
          onChange={setSeg}
          options={[
            { value: "a", label: "Cada 6 meses" },
            { value: "b", label: "Cada año" },
          ]}
        />
        <Slider label="Dinero" value={slider} onChange={setSlider} color="var(--dinero)" />
        <Row gap={4}>
          <Tag tone="accent">Para ti</Tag>
          <Tag>+ Bienestar</Tag>
          <Tag tone="minus">− Familia</Tag>
          <Tag tone="sol">Apuesta</Tag>
        </Row>
      </Section>

      <Section title="Indicadores" note="Indicator e IndicatorGrid: valor, o cambio respecto al año anterior">
        <IndicatorGrid label="Hoy" values={{ dinero: 35, carrera: 30, bienestar: 55, vida: 70 }} />
        <IndicatorGrid
          label="Cambio"
          values={{ dinero: 52, carrera: 38, bienestar: 78, vida: 52 }}
          previous={{ dinero: 35, carrera: 30, bienestar: 55, vida: 70 }}
        />
        <Indicator indicator="vida" value={24} previous={33} />
      </Section>

      <Section title="Tarjeta de decisión" note="DecisionCard / DecisionList + DecisionArt">
        <DecisionCard
          art={<DecisionArt kind="viaje" />}
          title="Irte de work and travel"
          subtitle="Un año en Australia: cosechar, servir café, viajar."
          tags={[{ label: "Para ti", tone: "accent" }, { label: "+ Bienestar" }, { label: "− Familia", tone: "minus" }]}
          selected={card}
          onSelect={() => setCard(!card)}
        />
        <Row>
          {DECISION_ART_KINDS.map((k) => (
            <span key={k} className="vd-opcion-dibujo">
              <DecisionArt kind={k} />
            </span>
          ))}
        </Row>
      </Section>

      <Section title="Esperas" note="Espera (features/juego): un juego por sorteo; gira, se frena y queda en su resultado">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 16 }}>
          {VARIANTES_ESPERA.map((v) => (
            <Espera key={`${v}-${tirada}`} variante={v} texto={v} />
          ))}
        </div>
        <Button variant="quiet" onClick={() => setTirada((t) => t + 1)}>
          Sortear otra vez
        </Button>
      </Section>

      <Section title="Superficies" note="Panel, SunCard, NightBand">
        <Panel>
          <Text size="sm">Panel (niebla) para agrupar controles.</Text>
        </Panel>
        <SunCard>
          <Meta>Tu felicidad</Meta>
          <BigNumber value={61} unit="/ 100" />
        </SunCard>
        <NightBand>
          <Meta>Lo que te perdiste</Meta>
          <MissedList items={["Los 80 de tu abuela"]} />
        </NightBand>
      </Section>

      <Section title="Personas" note="Avatar, Notification, DotRow, DotLegend">
        <Row>
          <Avatar name="Mamá" />
          <Avatar name="Papá" />
        </Row>
        <Notification from="Mamá" message="Te guardé torta del cumpleaños." time="22:30" />
        <DotRow seen={2} missed={6} end />
        <DotLegend
          items={[
            { kind: "seen", label: "Fuiste" },
            { kind: "missed", label: "No fuiste" },
            { kind: "end", label: "Final" },
          ]}
        />
      </Section>

      <Section title="Rangos" note="RangeCompare: resultados de dos caminos (Monte Carlo)">
        <RangeCompare indicator="dinero" a={{ low: 70, high: 95, median: 88 }} b={{ low: 45, high: 70, median: 58 }} />
        <RangeCompare indicator="vida" a={{ low: 15, high: 50, median: 34 }} b={{ low: 60, high: 85, median: 74 }} />
      </Section>

      <Section title="Ilustraciones" note="LifePathHero, TravelScene y OfficeScene (ver pantallas 4 y 5), LinesChart, VisitsTimeline, StationTimeline, YearTicker (pantallas 6–8)">
        <LifePathHero />
      </Section>
    </div>
  );
}
