import { type DragEvent, useEffect, useId, useMemo, useRef, useState } from "react";
import {
  Button, ChevronLeftIcon, Chip, Heading, IconButton, Meta, Panel, Pill, Row, Screen, ScreenFooter, ScreenHeader, Segmented, Slider, Stack, SunCard, Tag, Text,
} from "@/shared/ui";
import { ErrorApi, leerPerfil } from "../api";
import { EDUCACION, TIPO_EMPLEADOR, pesos } from "../textos";
import type { Catalogo, DudaSugerida, Perfil, PerfilLeido, Sexo } from "../types";
import { Logo } from "./Logo";
import { Info } from "./graficos";
import { Cargando, ErrorCaja } from "./piezas";
import { Trayectoria, type EstadoLectura } from "./Trayectoria";

const SUELDO_MAX = 30_000_000;
export const SLIDER_MIN = 300_000;
export const SLIDER_MAX = 8_000_000;
/** Los rubros que se muestran como chips; el resto queda en "Otro". */
export const RUBROS_TOP = ["Comercio", "Información y comunicaciones", "Servicios profesionales", "Salud", "Enseñanza", "Finanzas y seguros"];
const RIESGOS = [
  { value: "2", label: "Prefiero lo seguro" },
  { value: "5", label: "Depende" },
  { value: "8", label: "Me la juego" },
];
const riesgoCercano = (r: number) => (r <= 3 ? "2" : r >= 7 ? "8" : "5");

/** Banda de edad de la ESI (18-24, 25-29, …, 50-54). */
export function banda(edad: number): string {
  if (edad <= 24) return "18-24";
  const desde = Math.min(50, Math.floor(edad / 5) * 5);
  return `${desde}-${desde + 4}`;
}
/** Marca de un campo que el texto de la persona no decía y quedó con un valor por defecto. */
function Revisa({ si }: { si: boolean }) {
  return si ? (
    <Tag tone="sol" className="jg-revisa">
      Supuesto: revísalo
    </Tag>
  ) : null;
}

/** El atajo: subes tu CV o el PDF de tu LinkedIn y Claude llena el formulario. */
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

function SubirCv({
  estado, empresa, catalogo, onPdf,
}: {
  estado: EstadoLectura;
  empresa: PerfilLeido["empresa"];
  catalogo?: PerfilLeido["empresa_catalogo"];
  onPdf: (pdfBase64: string) => void;
}) {
  const entrada = useRef<HTMLInputElement>(null);
  const [errorArchivo, setErrorArchivo] = useState<string | null>(null);
  const leyendo = estado.fase === "leyendo";

  const subir = (f: File | undefined) => {
    if (!f) return;
    setErrorArchivo(null);
    if (f.type !== "application/pdf" && !/\.pdf$/i.test(f.name)) return setErrorArchivo("Sube un PDF.");
    if (f.size > 10_000_000) return setErrorArchivo("El PDF pesa más de 10 MB.");
    const lector = new FileReader();
    lector.onload = () => typeof lector.result === "string" && onPdf(lector.result);
    lector.onerror = () => setErrorArchivo("No pudimos abrir el archivo.");
    lector.readAsDataURL(f);
  };

  return (
    <Panel
      className="jg-subir-cv"
      onDragOver={(e: DragEvent) => e.preventDefault()}
      onDrop={(e: DragEvent) => {
        e.preventDefault();
        subir(e.dataTransfer.files?.[0]);
      }}
    >
      <Stack gap={4}>
        <Heading level={3} as="h2">
          Llénalo con tu CV
        </Heading>
        <Text size="sm">O tu LinkedIn: perfil → Recursos → Guardar como PDF.</Text>
      </Stack>
      <input
        ref={entrada}
        type="file"
        accept="application/pdf,.pdf"
        hidden
        onChange={(e) => {
          subir(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      <Button onClick={() => entrada.current?.click()} disabled={leyendo}>
        {leyendo ? "Leyendo tu CV…" : "Subir PDF"}
      </Button>
      {leyendo && <Cargando frases={["Claude está leyendo tu CV…", "Mientras, revisa abajo."]} cada={3000} />}
      {errorArchivo && (
        <div className="jg-error" role="alert">
          {errorArchivo}
        </div>
      )}
      {estado.fase === "error" && (
        <div className="jg-error" role="alert">
          No pudimos leer tu CV. {estado.detalle} Llénalo a mano abajo.
        </div>
      )}
      {estado.fase === "listo" && (
        <Stack gap={2} role="status">
          <Text size="sm" className={catalogo ? "jg-con-logo" : undefined}>
            {catalogo && <Logo carpeta="empresas" id={catalogo.empresa_id} nombre={catalogo.nombre} grupo={catalogo.rubro} hay={catalogo.logo} tamano={28} />}
            <strong>Listo, llenamos lo que decía tu CV.</strong>
          </Text>
          {empresa && (
            <Text size="sm">
              {empresa.nombre}: {empresa.tamano === "grande" ? "empresa grande" : "pyme"}, {empresa.trabajadores.toLocaleString("es-CL")} personas (SII).
            </Text>
          )}
          <Text size="sm">{estado.supuestos.length > 0 ? "Revisa lo marcado abajo." : "Revisa que calce."}</Text>
        </Stack>
      )}
    </Panel>
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
  onLeido,
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
  /** Lo que leyó Claude aquí (tu CV o lo de tu Claude): para el retrato y las dudas sugeridas. */
  onLeido?: (r: PerfilLeido, origen: "pdf" | "texto") => void;
  /** Empieza la partida: la primera carta sale al azar, como todas. */
  onListo: (p: Perfil) => void;
  /** Para quien prefiere partir por una duda concreta. */
  onElegirDuda: (p: Perfil, sugeridas: DudaSugerida[]) => void;
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
  const [lectura, setLectura] = useState<EstadoLectura>({ fase: "nada" });
  /** La duda que trajo el documento de tu Claude: se propone en la pantalla siguiente. */
  const [sugeridas, setSugeridas] = useState<DudaSugerida[]>([]);
  /** Campos con valor por defecto que la persona todavía no revisa. */
  const [marcados, setMarcados] = useState<ReadonlySet<string>>(new Set());
  /** Campos que la persona tocó desde que le pidió a Claude leer: esos no se pisan cuando llega la respuesta. */
  const tocados = useRef(new Set<string>());
  const pedido = useRef(0);
  /** "Lo que tu gemelo sabe de ti": una línea que arma Claude con hechos del CV. */
  const [retrato, setRetrato] = useState<string | null>(null);
  const [empresa, setEmpresa] = useState<PerfilLeido["empresa"]>(null);
  const [empresaCatalogo, setEmpresaCatalogo] = useState<PerfilLeido["empresa_catalogo"]>(null);
  /** De dónde vino lo que se está leyendo: el PDF de arriba o el texto del panel de Claude. */
  const [origen, setOrigen] = useState<"pdf" | "texto">("pdf");
  useEffect(() => () => void pedido.current++, []);

  const set = <K extends keyof Perfil>(k: K, v: Perfil[K]) => {
    tocados.current.add(k);
    setMarcados((m) => (m.has(k) ? new Set([...m].filter((x) => x !== k)) : m));
    setP((x) => ({ ...x, [k]: v }));
  };
  const marca = (k: keyof Perfil) => (marcados.has(k) ? "jg-marcado" : undefined);

  const llenarConClaude = async (entrada: string | { pdf: string }) => {
    const mio = ++pedido.current;
    tocados.current = new Set();
    setOrigen(typeof entrada === "string" ? "texto" : "pdf");
    setLectura({ fase: "leyendo", documento: typeof entrada === "string" && entrada.includes("```gemelo-laboral") });
    try {
      const r = await leerPerfil(entrada);
      if (mio !== pedido.current) return;
      // lo que la persona editó mientras Claude leía se respeta
      const nuevos = Object.fromEntries(Object.entries(r.perfil).filter(([k]) => !tocados.current.has(k))) as Partial<Perfil>;
      const pendientes = r.supuestos.filter((x) => !tocados.current.has(x.campo));
      setP((x) => ({ ...x, ...nuevos }));
      setBusca("");
      setMarcados(new Set(pendientes.map((x) => x.campo)));
      setSugeridas(r.dudas_sugeridas?.length ? r.dudas_sugeridas : r.duda ? [{ decision: r.duda, por_que: "La trajo tu Claude." }] : []);
      setRetrato(r.retrato ?? null);
      setEmpresa(r.empresa ?? null);
      onLeido?.(r, typeof entrada === "string" ? "texto" : "pdf");
      setEmpresaCatalogo(r.empresa_catalogo ?? null);
      setLectura({
        fase: "listo", inferido: r.inferido, supuestos: pendientes.map((x) => x.nombre), avisos: r.avisos ?? [],
        documento: r.via === "documento", duda: r.duda,
      });
    } catch (e) {
      if (mio !== pedido.current) return;
      const err = e instanceof ErrorApi ? e : new ErrorApi(0, e instanceof Error ? e.message : String(e));
      setLectura({ fase: "error", status: err.status, detalle: err.detalle });
    }
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
        right={<Pill>Tu perfil</Pill>}
      />
      <Heading level={1}>Cuéntanos de ti.</Heading>

      {errorCatalogo && <ErrorCaja error={errorCatalogo} onReintentar={onReintentarCatalogo} />}
      {!catalogo && !errorCatalogo && <Cargando>Cargando opciones…</Cargando>}

      {retrato && (
        <SunCard className="jg-retrato">
          <Meta>Tu gemelo</Meta>
          <Text>«{retrato}»</Text>
        </SunCard>
      )}

      <SubirCv estado={origen === "pdf" ? lectura : { fase: "nada" }} empresa={empresa} catalogo={empresaCatalogo} onPdf={(pdf) => void llenarConClaude({ pdf })} />

      <details className="jg-plegable" open={origen === "texto" && lectura.fase !== "nada"}>
        <summary>Pegar tu CV en texto o armarlo con Claude</summary>
        <Trayectoria estado={origen === "texto" ? lectura : { fase: "nada" }} onLlenar={(t) => void llenarConClaude(t)} />
      </details>

      {catalogo && (
        <>
          <Stack gap={6} className={marca("edad")}>
            <Revisa si={marcados.has("edad")} />
            <Slider label="Edad" value={p.edad} min={18} max={50} onChange={(n) => set("edad", n)} display={`${p.edad} años`} />
          </Stack>

          <Stack as="section" className={marca("sexo")}>
            <span className="jg-etiqueta">Sexo</span>
            <Revisa si={marcados.has("sexo")} />
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

          <Stack as="section" className={marca("edu")}>
            <span className="jg-etiqueta">Estudios terminados</span>
            <Revisa si={marcados.has("edu")} />
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

          <Stack as="section" className={marca("ingles")}>
            <span className="jg-etiqueta">¿Podrías trabajar en inglés?</span>
            <Revisa si={marcados.has("ingles")} />
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

          <Stack as="section" className={marca("rubro")}>
            <label htmlFor={idRubro} className="jg-etiqueta">
              Rubro
            </label>
            <Revisa si={marcados.has("rubro")} />
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

          <Stack as="section" className={marca("tipo_empleador")}>
            <span className="jg-etiqueta">Tipo de empresa</span>
            <Revisa si={marcados.has("tipo_empleador")} />
            <Row>
              {catalogo.tipos_empleador.map((t) => (
                <Chip key={t} pressed={p.tipo_empleador === t} onToggle={() => set("tipo_empleador", t)}>
                  {TIPO_EMPLEADOR[t] ?? t}
                </Chip>
              ))}
            </Row>
          </Stack>

          <Stack as="section" className={marca("nivel")}>
            <span className="jg-etiqueta">Nivel de tu cargo</span>
            <Revisa si={marcados.has("nivel")} />
            <Row>
              {catalogo.niveles.map((n) => (
                <Chip key={n.nivel} pressed={p.nivel === n.nivel} onToggle={() => set("nivel", n.nivel)}>
                  {n.nombre}
                </Chip>
              ))}
            </Row>
          </Stack>

          <Stack as="section" className={marca("sueldo")}>
            <Revisa si={marcados.has("sueldo")} />
            <Slider
              label="Sueldo líquido al mes"
              value={Math.min(SLIDER_MAX, Math.max(SLIDER_MIN, p.sueldo))}
              min={SLIDER_MIN}
              max={SLIDER_MAX}
              step={50_000}
              color="var(--dinero)"
              onChange={(n) => set("sueldo", n)}
              display={sueldoValido ? pesos(p.sueldo) : "entre $1 y $30.000.000"}
            />
            {ref && (
              <Row gap={8} style={{ alignItems: "center", flexWrap: "wrap" }}>
                <Text size="sm">
                  Mediana para tu edad y estudios: <strong>{pesos(ref.p50)}</strong>
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

          <Stack as="section" gap={4} className={marca("riesgo")}>
            <Revisa si={marcados.has("riesgo")} />
            <span className="jg-etiqueta">Si te ofrecen algo incierto…</span>
            <Segmented<string> label="Tolerancia al riesgo" value={riesgoCercano(p.riesgo)} onChange={(v) => set("riesgo", Number(v))} options={RIESGOS} />
          </Stack>
        </>
      )}

      <ScreenFooter>
        {error && <ErrorCaja error={error} onReintentar={onReintentar} />}
        {cargando && <Cargando frases={["Simulando tus mundos…", "Sorteando tu primera carta…"]} />}
        <Button onClick={() => onElegirDuda(p, sugeridas)} disabled={!catalogo || !sueldoValido || cargando}>
          {sugeridas.length ? "Ver mis dudas" : "Elegir mi duda"}
        </Button>
        <Button variant="quiet" onClick={() => onListo(p)} disabled={!catalogo || !sueldoValido || cargando}>
          Que me toque una al azar
        </Button>
      </ScreenFooter>
    </Screen>
  );
}
