import { BigNumber, Meta, Panel, Stack, SunCard, Text } from "@/shared/ui";
import type { TwinState } from "../hooks/useTwin";
import { clarityOf, DimBar } from "./parts";

/** Columna derecha en escritorio: lo que el gemelo sabe de ti, siempre a la vista. */
export function Snapshot({ twin }: { twin: TwinState }) {
  const { profile, catalog, summary, lastDeltas } = twin;
  if (!profile || !catalog) return null;
  const c = clarityOf(profile.dims);
  const name = (k: string) => catalog.dims.find((d) => d.key === k)?.nombre ?? k;
  const desc = (k: string) => catalog.dims.find((d) => d.key === k)?.descripcion;

  const entries = Object.entries(profile.dims);
  const clearest = entries.filter(([, d]) => d.n > 0).sort((a, b) => a[1].sd - b[1].sd).slice(0, 5);
  const ex = summary?.examen;

  return (
    <Stack gap={16}>
      <SunCard>
        <Meta>Claridad del perfil</Meta>
        <BigNumber value={c.pct} unit="%" />
        <Text size="sm">{c.measured} de {c.total} rasgos medidos</Text>
      </SunCard>

      <Panel>
        <Meta>Examen a ciegas</Meta>
        {ex && ex.n > 0 ? (
          <Text size="sm">
            Acierta <strong>{ex.acierto}%</strong> contra {ex.azar}% al azar, en {ex.n}{" "}
            {ex.n === 1 ? "pregunta" : "preguntas"}.
          </Text>
        ) : (
          <Text size="sm">Aún no lo pones a prueba.</Text>
        )}
      </Panel>

      {lastDeltas.length > 0 && (
        <Panel>
          <Meta>Lo último que aprendió</Meta>
          {lastDeltas.map((d) => (
            <DimBar key={d.key} nombre={d.nombre} dim={profile.dims[d.key]} previous={d.antes} hint={desc(d.key)} />
          ))}
        </Panel>
      )}

      <Stack gap={10}>
        <Meta>Lo que tiene más claro</Meta>
        {clearest.length === 0 ? (
          <Text size="sm">Todavía nada: responde unas preguntas.</Text>
        ) : (
          clearest.map(([k, d]) => <DimBar key={k} nombre={name(k)} dim={d} hint={desc(k)} />)
        )}
      </Stack>
    </Stack>
  );
}
