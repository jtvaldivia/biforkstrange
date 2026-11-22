import "./onboarding.css";
import { useEffect, useId, useRef, useState } from "react";
import {
  Button, ChevronLeftIcon, Chip, Heading, IconButton, Meta, Pill, Row, Screen, ScreenFooter, ScreenHeader, Segmented, Slider, Stack, Tag, Text,
} from "@/shared/ui";
import { ErrorApi, getPrompt, leerPerfil } from "../api";
import { EDUCACION, TIPO_EMPLEADOR, pesos } from "../textos";
import type { Catalogo, DudaSugerida, Perfil, PerfilLeido } from "../types";
import { ErrorCaja } from "./piezas";
import { Prueba } from "./Prueba";
import { PerfilForm, RUBROS_TOP, SLIDER_MAX, SLIDER_MIN, TuPega, banda } from "./PerfilForm";

type Paso = "entrada" | "leyendo" | "tu" | "pega" | "plata" | "prueba";
/** Los pasos de cada camino: con CV se salta lo que el CV ya contestó. */
const MANUAL: Paso[] = ["tu", "pega", "plata"];
/** Las elecciones de cada tarjeta: parten vacías y hay que tocarlas para seguir. */
const ELEGIR: Record<string, (keyof Perfil)[]> = { tu: ["edu"], pega: ["tipo_empleador", "nivel", "rubro"], plata: ["ingles"] };
/** Los sliders siempre tienen un valor: cuentan como respuesta al pasar de tarjeta. */
const DESLIZAR: Record<string, (keyof Perfil)[]> = { tu: ["edad"], plata: ["sueldo"] };
const SITUACION: Record<string, string> = {
  independiente: "Independiente", fundador: "Fundador", buscando: "Buscando trabajo", estudiando: "Estudiando",
};
const FRASES = ["Leyendo tu experiencia…", "Buscando tu empresa en el SII…", "Contando tus años de trabajo…", "Eligiendo tus dudas…"];

/**
 * Onboarding en 3 pantallas: subes tu CV (o el PDF de LinkedIn) o contestas unas pocas preguntas, después solo
 * lo que falta, y vas a tu duda. Arriba, la ficha de tu gemelo se arma con cada dato.
 * El formulario completo queda detrás de "Revisar todos mis datos".
 */
export function Onboarding({
  inicial,
  catalogo,
  errorCatalogo,
  onVolver,
  onListo,
  onElegirDuda,
  cargando = false,
  error = null,
}: {
  inicial: Perfil;
  catalogo: Catalogo | null;
  errorCatalogo: string | null;
  onVolver: () => void;
  onListo: (p: Perfil) => void;
  onElegirDuda: (p: Perfil, sugeridas: DudaSugerida[]) => void;
  cargando?: boolean;
  error?: string | null;
}) {
  const [p, setP] = useState<Perfil>(inicial);
  const [paso, setPaso] = useState<Paso>("entrada");
  /** Campos que ya sabemos de la persona (los que contestó o leyó Claude): esos aparecen en la ficha. */
  const [sabidos, setSabidos] = useState<ReadonlySet<string>>(new Set());
  const [faltan, setFaltan] = useState<Paso[]>(MANUAL);
  const [leido, setLeido] = useState<PerfilLeido | null>(null);
  const [errorLectura, setErrorLectura] = useState<string | null>(null);
  const [completo, setCompleto] = useState(false);
  const [otroRubro, setOtroRubro] = useState(false);
  /** Lo que contó tu Claude o ChatGPT: se suma a lo del CV. */
  const [extra, setExtra] = useState<{ intereses: string[]; proyecto: string | null; retrato: string | null; sugeridas: DudaSugerida[] }>({
    intereses: [], proyecto: null, retrato: null, sugeridas: [],
  });
  const [conClaude, setConClaude] = useState(false);
  /** Las dos fuentes, en cualquier orden y combinables: tu LinkedIn o CV, y tu Claude o ChatGPT. */
  const [cv, setCv] = useState<"nada" | "leyendo" | "listo">("nada");
  const [claudeListo, setClaudeListo] = useState(false);
  const [leyendoClaude, setLeyendoClaude] = useState(false);
  const [errorClaude, setErrorClaude] = useState<string | null>(null);
  const pedido = useRef(0);
  useEffect(() => () => void pedido.current++, []);
  useEffect(() => {
    const id = gemeloGuardado();
    if (id && inicial.gemelo_id === undefined) setP((x) => ({ ...x, gemelo_id: id }));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const set = <K extends keyof Perfil>(k: K, v: Perfil[K]) => {
    setP((x) => ({ ...x, [k]: v }));
    setSabidos((s) => new Set(s).add(k));
  };

  const leerPdf = async (pdf: string) => {
    const mio = ++pedido.current;
    setErrorLectura(null);
    setCv("leyendo");
    try {
      const r = await leerPerfil({ pdf });
      if (mio !== pedido.current) return;
      const supuestos = new Set(r.supuestos.map((s) => s.campo));
      // lo que ya contó tu Claude manda; el CV llena el resto
      const delCv = Object.keys(r.perfil).filter((k) => !supuestos.has(k) && !sabidos.has(k));
      setP((x) => ({ ...x, ...Object.fromEntries(delCv.map((k) => [k, r.perfil[k as keyof Perfil]])) }));
      setSabidos((s) => new Set([...s, ...delCv]));
      setLeido(r);
      setCv("listo");
    } catch (e) {
      if (mio !== pedido.current) return;
      setErrorLectura(e instanceof ErrorApi ? e.detalle : "No pudimos leer tu CV.");
      setCv("nada");
    }
  };

  /** Pega la respuesta de tu Claude: lo que dijo se suma a lo que ya sabíamos, sin pisarlo con valores por defecto. */
  const leerTuClaude = async (texto: string) => {
    setErrorClaude(null);
    setLeyendoClaude(true);
    try {
      const r = await leerPerfil(texto);
      const supuestos = new Set(r.supuestos.map((x) => x.campo));
      // un nombre vacío (el texto no traía empresa o cargo) no borra el que ya sabíamos
      const dados = (r.dados ?? Object.keys(r.perfil).filter((k) => !supuestos.has(k))).filter((k) => r.perfil[k as keyof Perfil] !== "");
      const nuevos = Object.fromEntries(dados.map((k) => [k, r.perfil[k as keyof Perfil]])) as Partial<Perfil>;
      const perfil = { ...p, ...nuevos, relato: texto }; // lo que pegaste también es tu relato: el narrador lo usa
      const ahora = new Set([...sabidos, ...dados]);
      const sugeridas = [...(r.dudas_sugeridas ?? []), ...(leido?.dudas_sugeridas ?? [])]
        .filter((d, k, todas) => todas.findIndex((x) => x.decision === d.decision) === k)
        .slice(0, 3);
      setP(perfil);
      setSabidos(ahora);
      setExtra({ intereses: r.intereses ?? [], proyecto: r.proyecto ?? null, retrato: r.retrato ?? null, sugeridas });
      setConClaude(false);
      setClaudeListo(true);
    } catch (e) {
      setErrorClaude(e instanceof ErrorApi ? e.detalle : "No pudimos leer lo que pegaste.");
    } finally {
      setLeyendoClaude(false);
    }
  };
  const sugeridas = extra.sugeridas.length ? extra.sugeridas : leido?.dudas_sugeridas ?? [];
  /** Seguir: solo las tarjetas de lo que tus fuentes no dijeron; si dijeron todo, directo a tus dudas. */
  const seguir = () => {
    pedido.current++;
    const usoFuentes = cv === "listo" || claudeListo;
    const pasos: Paso[] = [
      ...(usoFuentes
        ? MANUAL.filter((x) => [...(ELEGIR[x] ?? []), ...(DESLIZAR[x] ?? [])].some((k) => !sabidos.has(k)))
        : MANUAL),
      "prueba", // al final, tu gemelo apuesta cómo vas a responder y comparan
    ];
    setFaltan(pasos);
    setPaso(pasos[0]);
  };

  if (completo) {
    return (
      <PerfilForm
        inicial={p}
        catalogo={catalogo}
        errorCatalogo={errorCatalogo}
        onVolver={() => setCompleto(false)}
        onListo={onListo}
        onElegirDuda={(perfil) => onElegirDuda(perfil, sugeridas)}
        cargando={cargando}
        error={error}
      />
    );
  }

  const i = faltan.indexOf(paso);
  const ultimo = i === faltan.length - 1;
  const atras = () => (i > 0 ? setPaso(faltan[i - 1]) : (setPaso("entrada"), setFaltan(MANUAL)));
  const siguiente = () => {
    setSabidos((s) => new Set([...s, ...(DESLIZAR[paso] ?? [])]));
    if (ultimo) onElegirDuda(p, sugeridas);
    else setPaso(faltan[i + 1]);
  };
  /** Saltar: a tus dudas con lo que ya sabemos; lo que falta queda como supuesto. */
  const saltarTodo = () => {
    pedido.current++; // si Claude estaba leyendo, esa respuesta ya no se usa
    onElegirDuda(p, sugeridas);
  };
  /** Saltar esta pregunta: sigue sin elegir; el valor queda como supuesto. */
  const saltarEsta = () => (ultimo ? onElegirDuda(p, sugeridas) : setPaso(faltan[i + 1]));
  const elegido = (k: keyof Perfil) => sabidos.has(k);
  const faltaElegir = (ELEGIR[paso] ?? []).some((k) => !elegido(k));
  const ref = catalogo?.sueldos_ref?.find((f) => f.educacion === p.edu && f.banda === banda(p.edad));

  return (
    <Screen gap={18}>
      <ScreenHeader
        left={
          <IconButton label="Volver" onClick={paso === "entrada" ? onVolver : atras}>
            <ChevronLeftIcon />
          </IconButton>
        }
        right={
          <Row gap={10} style={{ alignItems: "center" }}>
            {i >= 0 ? (
              <div className="ob-puntos" aria-label={`Paso ${i + 1} de ${faltan.length}`}>
                {faltan.map((f, k) => (
                  <i key={f} data-hecho={k <= i || undefined} />
                ))}
              </div>
            ) : (
              <Pill>Tu gemelo</Pill>
            )}
          </Row>
        }
      />

      {(paso !== "entrada" || sabidos.size > 0) && (
        <Ficha p={p} sabidos={sabidos} catalogo={catalogo} retrato={extra.retrato ?? leido?.retrato ?? null} intereses={extra.intereses} proyecto={extra.proyecto} />
      )}

      {errorCatalogo && <ErrorCaja error={errorCatalogo} />}

      {paso === "entrada" && (
        <Entrada
          cv={cv}
          error={errorLectura}
          onPdf={(pdf) => void leerPdf(pdf)}
          claudeListo={claudeListo}
          claudeAbierto={conClaude}
          onAbrirClaude={() => setConClaude((x) => !x)}
          claude={<TuClaude leyendo={leyendoClaude} error={errorClaude} onTexto={(t) => void leerTuClaude(t)} />}
          onSeguir={seguir}
          onSaltar={saltarTodo}
          gemelo={<UsarGemelo gemeloId={p.gemelo_id ?? null} onGemelo={(id) => setP((x) => ({ ...x, gemelo_id: id }))} />}
          cargando={cargando}
        />
      )}

      {catalogo && paso === "tu" && (
        <Tarjeta key="tu" titulo="Primero, tú.">
          <Slider label="Edad" value={p.edad} min={18} max={50} onChange={(n) => set("edad", n)} display={`${p.edad} años`} />
          <Stack gap={8}>
            <span className="jg-etiqueta">Estudios terminados</span>
            <Row>
              {catalogo.educacion.map((e) => (
                <Chip key={e} pressed={elegido("edu") && p.edu === e} onToggle={() => set("edu", e)}>
                  {EDUCACION[e] ?? e}
                </Chip>
              ))}
            </Row>
          </Stack>
        </Tarjeta>
      )}

      {catalogo && paso === "pega" && (
        <Tarjeta key="pega" titulo="¿Dónde trabajas hoy?">
          <TuPega p={p} set={set} />
          <Row>
            {catalogo.tipos_empleador.map((t) => (
              <Chip key={t} pressed={elegido("tipo_empleador") && p.tipo_empleador === t} onToggle={() => set("tipo_empleador", t)}>
                {TIPO_EMPLEADOR[t] ?? t}
              </Chip>
            ))}
          </Row>
          <Stack gap={8}>
            <span className="jg-etiqueta">Nivel de tu cargo</span>
            <Row>
              {catalogo.niveles.map((n) => (
                <Chip key={n.nivel} pressed={elegido("nivel") && p.nivel === n.nivel} onToggle={() => set("nivel", n.nivel)}>
                  {n.nombre}
                </Chip>
              ))}
            </Row>
          </Stack>
          <Stack gap={8}>
            <span className="jg-etiqueta">Rubro</span>
            <Row>
              {RUBROS_TOP.filter((r) => catalogo.rubros.includes(r)).map((r) => (
                <Chip
                  key={r}
                  pressed={elegido("rubro") && p.rubro === r}
                  onToggle={() => {
                    set("rubro", r);
                    setOtroRubro(false);
                  }}
                >
                  {r}
                </Chip>
              ))}
              <Chip pressed={otroRubro} onToggle={() => setOtroRubro(true)}>
                Otro
              </Chip>
            </Row>
            {otroRubro && (
              <select
                className="jg-campo"
                aria-label="Otro rubro"
                value={elegido("rubro") && !RUBROS_TOP.includes(p.rubro) ? p.rubro : ""}
                onChange={(e) => set("rubro", e.target.value)}
              >
                <option value="" disabled>
                  Elige tu rubro
                </option>
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
        </Tarjeta>
      )}

      {catalogo && paso === "plata" && (
        <Tarjeta key="plata" titulo={leido ? "Lo que un CV no dice." : "Lo último."}>
          <Slider
            label="Sueldo líquido al mes"
            value={Math.min(SLIDER_MAX, Math.max(SLIDER_MIN, p.sueldo))}
            min={SLIDER_MIN}
            max={SLIDER_MAX}
            step={50_000}
            color="var(--dinero)"
            onChange={(n) => set("sueldo", n)}
            display={pesos(p.sueldo)}
          />
          {ref && (
            <Text size="sm">
              Mediana para tu edad y estudios: <strong>{pesos(ref.p50)}</strong>
            </Text>
          )}
          <Stack gap={8}>
            <span className="jg-etiqueta">¿Podrías trabajar en inglés?</span>
            <Segmented<string>
              label="Inglés"
              value={elegido("ingles") ? String(p.ingles ?? 0) : ""}
              onChange={(v) => set("ingles", v === "1" ? 1 : 0)}
              options={[
                { value: "0", label: "No" },
                { value: "1", label: "Sí" },
              ]}
            />
          </Stack>
        </Tarjeta>
      )}

      {paso === "prueba" && <Prueba perfil={p} onGemelo={(id) => setP((x) => ({ ...x, gemelo_id: id }))} />}

      {i >= 0 && (
        <ScreenFooter>
          {error && <ErrorCaja error={error} />}
          <Button onClick={siguiente} disabled={!catalogo || cargando || faltaElegir}>
            {ultimo ? (sugeridas.length ? "Ver mis dudas" : "Elegir mi duda") : "Siguiente"}
          </Button>
          <Button variant="white" onClick={saltarEsta} disabled={cargando}>
            Saltar
          </Button>
          {ultimo && (
            <button type="button" className="ob-link" onClick={() => setCompleto(true)}>
              Revisar todos mis datos
            </button>
          )}
        </ScreenFooter>
      )}
    </Screen>
  );
}

/**
 * Pantalla 1: tus fuentes, con un check cuando están. Puedes usar las dos, en cualquier orden;
 * después Seguir pregunta solo lo que falta. O juegas sin datos.
 */
function Entrada({
  cv, error, onPdf, claudeListo, claudeAbierto, onAbrirClaude, claude, onSeguir, onSaltar, cargando, gemelo,
}: {
  gemelo: React.ReactNode;
  cv: "nada" | "leyendo" | "listo";
  error: string | null;
  onPdf: (pdf: string) => void;
  claudeListo: boolean;
  claudeAbierto: boolean;
  onAbrirClaude: () => void;
  claude: React.ReactNode;
  onSeguir: () => void;
  onSaltar: () => void;
  cargando: boolean;
}) {
  const entrada = useRef<HTMLInputElement>(null);
  const [encima, setEncima] = useState(false);
  const [errorArchivo, setErrorArchivo] = useState<string | null>(null);

  const subir = (f: File | undefined) => {
    if (!f) return;
    setErrorArchivo(null);
    if (f.type !== "application/pdf" && !/\.pdf$/i.test(f.name)) return setErrorArchivo("Tiene que ser un PDF.");
    if (f.size > 10_000_000) return setErrorArchivo("El PDF pesa más de 10 MB.");
    const lector = new FileReader();
    lector.onload = () => typeof lector.result === "string" && onPdf(lector.result);
    lector.onerror = () => setErrorArchivo("No pudimos abrir el archivo.");
    lector.readAsDataURL(f);
  };
  const algo = cv === "listo" || claudeListo;

  return (
    <>
      <Stack gap={6} className="ob-entra">
        <Heading level={1}>Armemos a tu gemelo.</Heading>
        <Text>Súmale lo que quieras: elige una o combínalas.</Text>
      </Stack>

      <Stack gap={10} className="ob-entra">
        <button
          type="button"
          className="ob-fuente"
          data-listo={cv === "listo" || undefined}
          data-leyendo={cv === "leyendo" || undefined}
          data-encima={encima || undefined}
          disabled={cv === "leyendo"}
          onClick={() => entrada.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setEncima(true);
          }}
          onDragLeave={() => setEncima(false)}
          onDrop={(e) => {
            e.preventDefault();
            setEncima(false);
            subir(e.dataTransfer.files?.[0]);
          }}
        >
          {cv === "leyendo" ? (
            <span className="ob-icono ob-hoja-mini" aria-hidden="true">
              <i />
              <i />
              <i />
              <i />
              <span className="ob-scan" />
            </span>
          ) : (
            <span className="ob-in ob-icono">in</span>
          )}
          <span className="ob-fuente-texto">
            <strong>Tu LinkedIn o CV</strong>
            <span className="ob-chico">
              {cv === "leyendo" ? <LeyendoFrase /> : cv === "listo" ? "Listo. Puedes subir otro." : "PDF. En LinkedIn: tu perfil → Recursos → Guardar como PDF"}
            </span>
          </span>
          <Marca listo={cv === "listo"} accion={cv === "leyendo" ? "" : "Subir"} />
        </button>
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
        {(errorArchivo || error) && (
          <div className="jg-error" role="alert">
            {errorArchivo ?? `No pudimos leer tu CV. ${error}`}
          </div>
        )}

        <button type="button" className="ob-fuente" data-listo={claudeListo || undefined} aria-expanded={claudeAbierto} onClick={onAbrirClaude}>
          <span className="ob-claude-chispa ob-icono" aria-hidden="true">✦</span>
          <span className="ob-fuente-texto">
            <strong>Tu Claude o ChatGPT</strong>
            <span className="ob-chico">{claudeListo ? "Listo. Lo que contó ya está en tu gemelo." : "Sabe de tus proyectos y lo que te apasiona."}</span>
          </span>
          <Marca listo={claudeListo} accion={claudeAbierto ? "Cerrar" : "Abrir"} />
        </button>
        {claudeAbierto && claude}

        <button type="button" className="ob-fuente" onClick={onSeguir} disabled={cv === "leyendo" || cargando}>
          <span className="ob-icono ob-icono--tu" aria-hidden="true">✎</span>
          <span className="ob-fuente-texto">
            <strong>{algo ? "Completar lo que falta" : "Contesto yo unas preguntas"}</strong>
            <span className="ob-chico">{algo ? "Solo lo que tus fuentes no dijeron." : "Edad, estudios, tu trabajo y tu sueldo. Un toque cada una."}</span>
          </span>
          <Marca listo={false} accion="Empezar" />
        </button>
      </Stack>

      {gemelo}

      <ScreenFooter>
        {algo && (
          <Button onClick={onSeguir} disabled={cv === "leyendo" || cargando}>
            Seguir
          </Button>
        )}
        <button type="button" className="ob-link" onClick={onSaltar} disabled={cargando}>
          Jugar sin datos
        </button>
      </ScreenFooter>
    </>
  );
}

/** El check de cada fuente: ✓ cuando está, o la acción que la carga. */
function Marca({ listo, accion }: { listo: boolean; accion: string }) {
  return listo ? (
    <span className="ob-check" aria-label="Listo">
      ✓
    </span>
  ) : (
    <span className="ob-accion">{accion}</span>
  );
}

/** Frases que cambian mientras Claude lee el CV. */
function LeyendoFrase() {
  const [k, setK] = useState(0);
  useEffect(() => {
    const t = window.setInterval(() => setK((x) => (x + 1) % FRASES.length), 2600);
    return () => window.clearInterval(t);
  }, []);
  return (
    <span role="status" key={k} className="ob-frase">
      {FRASES[k]}
    </span>
  );
}

/** La ficha de tu gemelo: cada dato que se sabe aparece con un pop. */
function Ficha({
  p, sabidos, catalogo, retrato, intereses = [], proyecto = null,
}: { p: Perfil; sabidos: ReadonlySet<string>; catalogo: Catalogo | null; retrato: string | null; intereses?: string[]; proyecto?: string | null }) {
  const nivel = catalogo?.niveles.find((n) => n.nivel === p.nivel)?.nombre;
  const datos: [string, string | undefined][] = [
    ["edad", `${p.edad} años`],
    ["edu", EDUCACION[p.edu] ?? p.edu],
    ["cargo_nombre", p.cargo_nombre?.trim() || undefined],
    ["empresa_nombre", p.empresa_nombre?.trim() ? `En ${p.empresa_nombre.trim()}` : undefined],
    ["nivel", nivel],
    ["tipo_empleador", TIPO_EMPLEADOR[p.tipo_empleador] ?? p.tipo_empleador],
    ["rubro", p.rubro],
    ["sueldo", pesos(p.sueldo)],
    ["ingles", p.ingles ? "Inglés" : undefined],
    ["estado", p.estado && p.estado !== "empleado" ? SITUACION[p.estado] : undefined],
    ["remoto", p.remoto ? "Remoto" : undefined],
    ["parcial", p.parcial ? "Media jornada" : undefined],
    ["usa_ia", p.usa_ia ? "Usa IA" : undefined],
    ["rubro_sonado", p.rubro_sonado ? `Sueña con ${p.rubro_sonado}` : undefined],
    ["anos_por_empleo", p.anos_por_empleo ? `Se cambia cada ${p.anos_por_empleo.toLocaleString("es-CL")} años` : undefined],
  ];
  const visibles = datos.filter(([k, v]) => v && sabidos.has(k));
  return (
    <div className="ob-ficha">
      <Silueta lleno={Math.min(visibles.length + intereses.length, 7) / 7} />
      <Stack gap={6}>
        <Meta>Tu gemelo</Meta>
        {retrato && <Text size="sm">«{retrato}»</Text>}
        <div className="ob-tags">
          {visibles.length === 0 && <span className="ob-chico">Se va armando con cada respuesta.</span>}
          {visibles.map(([k, v]) => (
            <Tag key={`${k}:${v}`} className="ob-tag">
              {v}
            </Tag>
          ))}
          {proyecto && (
            <Tag key={`proyecto:${proyecto}`} className="ob-tag ob-tag--tuyo">
              Proyecto: {proyecto.length > 40 ? `${proyecto.slice(0, 40)}…` : proyecto}
            </Tag>
          )}
          {intereses.map((x) => (
            <Tag key={`interes:${x}`} className="ob-tag ob-tag--tuyo">
              {x}
            </Tag>
          ))}
        </div>
      </Stack>
    </div>
  );
}

function Tarjeta({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <Stack gap={18} className="ob-tarjeta">
      <Heading level={2}>{titulo}</Heading>
      {children}
    </Stack>
  );
}

/**
 * Pregúntale a tu Claude o ChatGPT: te conoce mejor que tu CV (tus proyectos, lo que te apasiona).
 * Un toque copia el prompt y lo abre ya escrito; pegas la respuesta y se suma a tu gemelo.
 */
function TuClaude({ leyendo, error, onTexto }: { leyendo: boolean; error: string | null; onTexto: (texto: string) => void }) {
  const [prompt, setPrompt] = useState<string | null>(null);
  const [texto, setTexto] = useState("");
  const [copiado, setCopiado] = useState(false);
  useEffect(() => {
    if (prompt) return;
    let vivo = true;
    getPrompt()
      .then((r) => vivo && setPrompt(r.prompt + PROMPT_RELATO))
      .catch(() => vivo && setPrompt(null));
    return () => {
      vivo = false;
    };
  }, [prompt]);

  const abrir = async (url: string) => {
    if (!prompt) return;
    try {
      await navigator.clipboard.writeText(prompt);
      setCopiado(true);
    } catch {
      /* sin portapapeles: el link ya lleva el prompt escrito */
    }
    window.open(`${url}${encodeURIComponent(prompt)}`, "_blank", "noopener");
  };

  return (
    <Stack gap={10} className="ob-claude">
      <Text size="sm">
        <strong>1.</strong> Ábrelo con el prompt ya escrito. Tu Claude te muestra la respuesta y tú decides qué pegar: no le pedimos salud, pareja
        ni familia.
      </Text>
      <Row gap={8}>
        <Button variant="quiet" onClick={() => void abrir("https://claude.ai/new?q=")} disabled={!prompt}>
          Abrir Claude
        </Button>
        <Button variant="quiet" onClick={() => void abrir("https://chatgpt.com/?q=")} disabled={!prompt}>
          Abrir ChatGPT
        </Button>
      </Row>
      {copiado && <span className="ob-chico">También quedó copiado, por si no aparece escrito.</span>}
      <label className="ob-chico" htmlFor="ob-claude-texto">
        <strong>2.</strong> Pega aquí lo que te respondió
      </label>
      <textarea
        id="ob-claude-texto"
        className="jg-campo ob-claude-texto"
        rows={5}
        placeholder="Pega lo que te respondió, o cuéntanos de ti con tus palabras: qué haces, qué te cansa, cómo decides, qué te importa…"
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
      />
      {error && (
        <div className="jg-error" role="alert">
          {error}
        </div>
      )}
      <Button onClick={() => onTexto(texto.trim())} disabled={!texto.trim() || leyendo}>
        {leyendo ? "Leyendo…" : "Sumar a mi gemelo"}
      </Button>
    </Stack>
  );
}

/** Tu gemelo como silueta: se va llenando (de abajo hacia arriba) con cada dato que se sabe. */
function Silueta({ lleno }: { lleno: number }) {
  const id = useId();
  const cuerpo = "M10 50c0-12 7-18 16-18s16 6 16 18z";
  return (
    <svg className="ob-avatar" viewBox="0 0 52 52" aria-hidden="true">
      <defs>
        <clipPath id={id}>
          <rect className="ob-nivel" x="0" y="0" width="52" height="52" style={{ transform: `translateY(${(1 - lleno) * 100}%)` }} />
        </clipPath>
      </defs>
      <circle cx="26" cy="19" r="9" className="ob-silueta-vacia" />
      <path d={cuerpo} className="ob-silueta-vacia" />
      <g clipPath={`url(#${id})`}>
        <circle cx="26" cy="19" r="9" className="ob-silueta-llena" />
        <path d={cuerpo} className="ob-silueta-llena" />
      </g>
    </svg>
  );
}

/** Lo que se suma al prompt del equipo: el relato libre que usa el narrador para contar tus cartas. */
const PROMPT_RELATO = `

4. Después del bloque, agrega una sección "## Sobre mí, en mis palabras" escrita en primera persona, como si yo me presentara (150–300 palabras): qué hago y qué me cansa de mi pega, cómo decido frente al riesgo y los cambios, cómo soy trabajando con otras personas, lo que me importa fuera del trabajo y las dudas o planes que tengo hoy. Solo lo que sabes de verdad.`;

const CLAVE_GEMELO = "biforkstrange.twinProfileId"; // la misma que usa /gemelo

function gemeloGuardado(): string | null {
  try {
    return localStorage.getItem(CLAVE_GEMELO);
  } catch {
    return null;
  }
}

/** Usar tu gemelo digital: sus rasgos afinados deciden qué cartas te salen (nada más). */
function UsarGemelo({ gemeloId, onGemelo }: { gemeloId: string | null; onGemelo: (id: string | null) => void }) {
  const guardado = gemeloGuardado();
  return (
    <div className="ob-usar-gemelo ob-entra">
      {guardado ? (
        <label>
          <input type="checkbox" checked={gemeloId === guardado} onChange={(e) => onGemelo(e.target.checked ? guardado : null)} />
          <span>
            <strong>Usar mi gemelo digital.</strong> Sus rasgos afinados deciden qué cartas te salen.{" "}
            <a href="/gemelo" target="_blank" rel="noreferrer">Afinarlo</a>
          </span>
        </label>
      ) : (
        <span className="ob-chico">
          ¿Quieres que las cartas sigan tu personalidad? Al final tu gemelo se pone a prueba, o{" "}
          <a href="/gemelo" target="_blank" rel="noreferrer">ármalo con más preguntas</a>.
        </span>
      )}
    </div>
  );
}
