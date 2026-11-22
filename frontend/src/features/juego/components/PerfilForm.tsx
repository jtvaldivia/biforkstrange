import { useId, useMemo, useState } from "react";
import {
  Button, ChevronLeftIcon, Chip, Heading, IconButton, Panel, Row, Screen, ScreenFooter, ScreenHeader, Segmented, Slider, Stack, Text,
} from "@/shared/ui";
import { EDUCACION, TIPO_EMPLEADOR, pesos } from "../textos";
import type { Catalogo, Perfil, Sexo } from "../types";
import { Logo } from "./Logo";
import { Info } from "./graficos";
import { Cargando, ErrorCaja } from "./piezas";
import { Espera } from "./Apuesta";

const SUELDO_MAX = 30_000_000;
export const SLIDER_MIN = 300_000;
export const SLIDER_MAX = 8_000_000;
/** Los rubros que se muestran como chips; el resto queda en "Otro". */
export const RUBROS_TOP = ["Comercio", "Información y comunicaciones", "Servicios profesionales", "Salud", "Enseñanza", "Finanzas y seguros"];
export const RIESGOS = [
  { value: "2", label: "Prefiero lo seguro" },
  { value: "5", label: "Depende" },
  { value: "8", label: "Me la juego" },
];
export const riesgoCercano = (r: number) => (r <= 3 ? "2" : r >= 7 ? "8" : "5");

/** Banda de edad de la ESI (18-24, 25-29, …, 50-54). */
export function banda(edad: number): string {
  if (edad <= 24) return "18-24";
  const desde = Math.min(50, Math.floor(edad / 5) * 5);
  return `${desde}-${desde + 4}`;
}
/** Tu empresa y tu cargo de hoy, con su nombre. Opcionales: solo sirven para contar tu historia, no mueven números. */
export function TuPega({ p, set }: { p: Perfil; set: (k: "empresa_nombre" | "cargo_nombre", v: string) => void }) {
  const idEmpresa = useId();
  const idCargo = useId();
  return (
    <Stack gap={8}>
      <label htmlFor={idEmpresa} className="jg-etiqueta">
        Tu empresa
      </label>
      <input
        id={idEmpresa}
        className="jg-campo"
        autoComplete="organization"
        maxLength={120}
        placeholder="Ej. BancoEstado"
        value={p.empresa_nombre ?? ""}
        onChange={(e) => set("empresa_nombre", e.target.value)}
      />
      <label htmlFor={idCargo} className="jg-etiqueta">
        Cómo se llama tu cargo
      </label>
      <input
        id={idCargo}
        className="jg-campo"
        autoComplete="organization-title"
        maxLength={120}
        placeholder="Ej. Analista de riesgo"
        value={p.cargo_nombre ?? ""}
        onChange={(e) => set("cargo_nombre", e.target.value)}
      />
      <Text size="sm">Opcional. Solo sirve para contar tu historia con nombres reales: no cambia tus números.</Text>
    </Stack>
  );
}

const sinTildes = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Tu perfil: los 9 campos. Viene de la pantalla "2 · Sobre ti" del kit. */
export function PerfilForm({
  inicial,
  catalogo,
  errorCatalogo,
  onReintentarCatalogo,
  onReintentar,
  onVolver,
  onListo,
  onElegirDuda,
  cargando = false,
  error = null,
}: {
  inicial: Perfil;
  catalogo: Catalogo | null;
  errorCatalogo: string | null;
  onReintentarCatalogo?: () => void;
  /** Repite lo que falló al empezar la partida. */
  onReintentar?: () => void;
  /** Vuelve atrás con lo editado: no se pierde. */
  onVolver: (p: Perfil) => void;
  /** Empieza sin una duda: la primera carta sale al azar, como todas. */
  onListo: (p: Perfil) => void;
  /** Sigue a elegir la duda con el perfil corregido. */
  onElegirDuda: (p: Perfil) => void;
  cargando?: boolean;
  error?: string | null;
}) {
  const [p, setP] = useState<Perfil>(inicial);
  const [busca, setBusca] = useState("");
  const [buscaU, setBuscaU] = useState("");
  const idCarrera = useId();
  const idUniversidad = useId();
  const idRubro = useId();
  const idSueldo = useId();
  const set = <K extends keyof Perfil>(k: K, v: Perfil[K]) => {
    setP((x) => ({ ...x, [k]: v }));
  };
  const carrera = catalogo?.carreras.find((c) => c.carrera_id === p.carrera_id);
  const universidad = catalogo?.universidades?.find((u) => u.universidad_id === p.universidad_id);
  const universidadesEncontradas = useMemo(() => {
    const q = sinTildes(buscaU.trim());
    if (!catalogo?.universidades || q.length < 2) return [];
    // con carrera elegida: instituciones de su tipo (U, IP o CFT) y las extranjeras
    return catalogo.universidades
      .filter((u) => !carrera || u.tipo_institucion === carrera.tipo_institucion || u.tipo_institucion === "EXT")
      .filter((u) => sinTildes(`${u.nombre} ${u.sigla} ${u.pais}`).includes(q))
      .slice(0, 8);
  }, [catalogo, buscaU, carrera]);
  const encontradas = useMemo(() => {
    const q = sinTildes(busca.trim());
    if (!catalogo || q.length < 2) return [];
    return catalogo.carreras.filter((c) => sinTildes(`${c.carrera} ${c.area} ${c.tipo_institucion}`).includes(q)).slice(0, 8);
  }, [catalogo, busca]);

  const sueldoValido = p.sueldo > 0 && p.sueldo <= SUELDO_MAX;
  const rubroOtro = !RUBROS_TOP.includes(p.rubro);
  const ref = catalogo?.sueldos_ref?.find((f) => f.educacion === p.edu && f.banda === banda(p.edad));

  return (
    <Screen>
      <ScreenHeader
        left={
          <IconButton label="Volver" onClick={() => onVolver(p)}>
            <ChevronLeftIcon />
          </IconButton>
        }
      />
      <Heading level={1}>Cuéntanos de ti.</Heading>

      {errorCatalogo && <ErrorCaja error={errorCatalogo} onReintentar={onReintentarCatalogo} />}
      {!catalogo && !errorCatalogo && <Cargando>Cargando opciones…</Cargando>}

      {catalogo && (
        <>
          <Stack gap={6}>
            <Slider label="Edad" value={p.edad} min={18} max={50} onChange={(n) => set("edad", n)} display={`${p.edad} años`} />
          </Stack>

          <Stack as="section">
            <span className="jg-etiqueta">Sexo</span>
            <Segmented<Sexo>
              label="Sexo"
              value={p.sexo}
              onChange={(s) => set("sexo", s)}
              options={[
                { value: "m", label: "Mujer" },
                { value: "h", label: "Hombre" },
              ]}
            />
          </Stack>

          <Stack as="section">
            <span className="jg-etiqueta">Estudios terminados</span>
            <Row>
              {catalogo.educacion.map((e) => (
                <Chip key={e} pressed={p.edu === e} onToggle={() => set("edu", e)}>
                  {EDUCACION[e] ?? e}
                </Chip>
              ))}
            </Row>
          </Stack>

          <Panel>
            <Stack gap={4}>
              <label htmlFor={idCarrera} className="vd-h3">
                Tu carrera <span className="jg-chico">(opcional)</span>
              </label>
              <Info pregunta="¿Para qué?">Si la encuentras, usamos lo que ganan sus titulados.</Info>
            </Stack>
            {carrera ? (
              <Row style={{ alignItems: "center" }}>
                <Chip pressed onToggle={() => set("carrera_id", -1)}>
                  {carrera.carrera} · {carrera.tipo_institucion} ✕
                </Chip>
              </Row>
            ) : (
              <>
                <input
                  id={idCarrera}
                  className="jg-campo"
                  type="search"
                  placeholder="Ej.: enfermería, ingeniería civil…"
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                />
                {encontradas.length > 0 && (
                  <div className="jg-resultados">
                    {encontradas.map((c) => (
                      <button
                        key={c.carrera_id}
                        type="button"
                        onClick={() => {
                          set("carrera_id", c.carrera_id);
                          setBusca("");
                        }}
                      >
                        {c.carrera}
                        <small>
                          {c.tipo_institucion} · {c.area}
                        </small>
                      </button>
                    ))}
                  </div>
                )}
                {busca.trim().length >= 2 && encontradas.length === 0 && <Text size="sm">No está. Puedes seguir sin carrera.</Text>}
              </>
            )}
          </Panel>

          {catalogo.universidades && catalogo.universidades.length > 0 && (
            <Panel>
              <Stack gap={4}>
                <label htmlFor={idUniversidad} className="vd-h3">
                  Dónde estudiaste <span className="jg-chico">(opcional)</span>
                </label>
                <Text size="sm">Universidad, instituto o CFT, en Chile o afuera. Cuenta para tu primer trabajo y para un magíster.</Text>
              </Stack>
              {universidad ? (
                <Row style={{ alignItems: "center" }}>
                  <Logo carpeta="universidades" id={universidad.universidad_id} nombre={universidad.nombre} grupo={universidad.pais} hay={universidad.logo} tamano={28} />
                  <Chip pressed onToggle={() => set("universidad_id", "")}>
                    {universidad.sigla || universidad.nombre} · {universidad.pais} ✕
                  </Chip>
                </Row>
              ) : (
                <>
                  <input
                    id={idUniversidad}
                    className="jg-campo"
                    type="search"
                    placeholder="Busca: Universidad de Chile, Duoc, Stanford…"
                    value={buscaU}
                    onChange={(e) => setBuscaU(e.target.value)}
                  />
                  {universidadesEncontradas.length > 0 && (
                    <div className="jg-resultados">
                      {universidadesEncontradas.map((u) => (
                        <button
                          key={u.universidad_id}
                          type="button"
                          onClick={() => {
                            set("universidad_id", u.universidad_id);
                            setBuscaU("");
                          }}
                        >
                          {u.nombre}
                          <small>
                            {u.tipo_institucion === "EXT" ? "Extranjera" : u.tipo_institucion} · {u.pais}
                          </small>
                        </button>
                      ))}
                    </div>
                  )}
                </>
              )}
            </Panel>
          )}

          <Stack as="section">
            <span className="jg-etiqueta">¿Podrías trabajar en inglés?</span>
            <Segmented<string>
              label="Inglés"
              value={String(p.ingles ?? 0)}
              onChange={(v) => set("ingles", v === "1" ? 1 : 0)}
              options={[
                { value: "0", label: "No" },
                { value: "1", label: "Sí, intermedio o más" },
              ]}
            />
          </Stack>

          <Stack as="section">
            <label htmlFor={idRubro} className="jg-etiqueta">
              Rubro
            </label>
            <Row>
              {RUBROS_TOP.filter((r) => catalogo.rubros.includes(r)).map((r) => (
                <Chip key={r} pressed={p.rubro === r} onToggle={() => set("rubro", r)}>
                  {r}
                </Chip>
              ))}
              <Chip pressed={rubroOtro} onToggle={() => !rubroOtro && set("rubro", catalogo.rubros.find((r) => !RUBROS_TOP.includes(r)) ?? p.rubro)}>
                Otro
              </Chip>
            </Row>
            {rubroOtro && (
              <select id={idRubro} className="jg-campo" value={p.rubro} onChange={(e) => set("rubro", e.target.value)}>
                {catalogo.rubros
                  .filter((r) => !RUBROS_TOP.includes(r))
                  .map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
              </select>
            )}
          </Stack>

          <Stack as="section">
            <TuPega p={p} set={set} />
          </Stack>

          <Stack as="section">
            <span className="jg-etiqueta">Tipo de empresa</span>
            <Row>
              {catalogo.tipos_empleador.map((t) => (
                <Chip key={t} pressed={p.tipo_empleador === t} onToggle={() => set("tipo_empleador", t)}>
                  {TIPO_EMPLEADOR[t] ?? t}
                </Chip>
              ))}
            </Row>
          </Stack>

          <Stack as="section">
            <span className="jg-etiqueta">Nivel de tu cargo</span>
            <Row>
              {catalogo.niveles.map((n) => (
                <Chip key={n.nivel} pressed={p.nivel === n.nivel} onToggle={() => set("nivel", n.nivel)}>
                  {n.nombre}
                </Chip>
              ))}
            </Row>
          </Stack>

          <Stack as="section">
            <Slider
              label="Sueldo líquido al mes"
              value={Math.min(SLIDER_MAX, Math.max(SLIDER_MIN, p.sueldo))}
              min={SLIDER_MIN}
              max={SLIDER_MAX}
              step={50_000}
              onChange={(n) => set("sueldo", n)}
              display={sueldoValido ? pesos(p.sueldo) : "entre $1 y $30.000.000"}
            />
            {ref && (
              <Row gap={8} style={{ alignItems: "center", flexWrap: "wrap" }}>
                <Text size="sm">
                  Lo típico para tu edad y estudios: <strong>{pesos(ref.p50)}</strong>
                </Text>
                {p.sueldo !== ref.p50 && (
                  <Chip pressed={false} onToggle={() => set("sueldo", ref.p50)}>
                    No sé, usa {pesos(ref.p50)}
                  </Chip>
                )}
              </Row>
            )}
            <details className="jg-plegable">
              <summary>Escribir el monto exacto</summary>
              <input
                id={idSueldo}
                className="jg-campo"
                inputMode="numeric"
                autoComplete="off"
                aria-label="Sueldo líquido exacto"
                value={p.sueldo ? p.sueldo.toLocaleString("es-CL") : ""}
                onChange={(e) => set("sueldo", Number(e.target.value.replace(/\D/g, "").slice(0, 9)))}
                aria-invalid={!sueldoValido}
              />
            </details>
          </Stack>

          <Stack as="section" gap={4}>
            <span className="jg-etiqueta">Si te ofrecen algo incierto…</span>
            <Segmented<string> label="Tolerancia al riesgo" value={riesgoCercano(p.riesgo)} onChange={(v) => set("riesgo", Number(v))} options={RIESGOS} />
          </Stack>

          {/* lo mismo que pregunta el onboarding: los años de la partida y de los mundos */}
          <Slider
            label="¿Hasta qué edad quieres jugar?"
            value={Math.min(60, Math.max(p.edad + 1, p.edad_final ?? p.edad + 10))}
            min={p.edad + 1}
            max={60}
            step={1}
            onChange={(n) => set("edad_final", n)}
            display={`${Math.min(60, Math.max(p.edad + 1, p.edad_final ?? p.edad + 10))} años`}
          />
        </>
      )}

      <ScreenFooter>
        {error && <ErrorCaja error={error} onReintentar={onReintentar} />}
        {cargando && <Espera frases={["Simulando tus mundos…", "Sorteando tu primera decisión…"]} />}
        <Button onClick={() => onElegirDuda(p)} disabled={!catalogo || !sueldoValido || cargando}>
          Elegir mi duda
        </Button>
        <button type="button" className="ob-link" onClick={() => onListo(p)} disabled={!catalogo || !sueldoValido || cargando}>
          Empezar sin una duda
        </button>
      </ScreenFooter>
    </Screen>
  );
}
