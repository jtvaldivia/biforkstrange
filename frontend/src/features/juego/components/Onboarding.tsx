import "./onboarding.css";
import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import {
  Button, ChevronLeftIcon, Chip, Heading, IconButton, Meta, Pill, Row, Screen, ScreenFooter, ScreenHeader, Segmented, Slider, Stack, Tag, Text,
} from "@/shared/ui";
import { getPrompt, textoError } from "../api";
import { MANUAL, type Onboarding as OnboardingEstado } from "../hooks/useBorrador";
import { EDUCACION, TIPO_EMPLEADOR, pesos } from "../textos";
import type { Catalogo, DudaSugerida, Perfil, Sexo } from "../types";
import { Cargando, ErrorCaja } from "./piezas";
import { PerfilForm, RUBROS_TOP, SLIDER_MAX, SLIDER_MIN, TuPega, banda } from "./PerfilForm";

/** Las elecciones de cada tarjeta: parten vacías y hay que tocarlas para seguir. */
const ELEGIR: Record<string, (keyof Perfil)[]> = { tu: ["sexo", "edu"], pega: ["tipo_empleador", "nivel", "rubro"], plata: ["ingles"] };
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
 * El estado vive en `usePartida` (`o`): volver desde las dudas lo encuentra igual.
 */
export function Onboarding({
  o,
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
  o: OnboardingEstado;
  catalogo: Catalogo | null;
  errorCatalogo: string | null;
  onReintentarCatalogo?: () => void;
  onReintentar?: () => void;
  onVolver: () => void;
  onListo: (p: Perfil) => void;
  onElegirDuda: (p: Perfil, sugeridas: DudaSugerida[]) => void;
  cargando?: boolean;
  error?: string | null;
}) {
  const { perfil: p, paso, faltan, leido, claude: extra, completo } = o.borrador;
  const sabidos = new Set(Object.keys(o.borrador.fuentes));
  const cv = o.leyendoCv ? "leyendo" : leido ? "listo" : "nada";
  const claudeListo = extra !== null;
  const [otroRubro, setOtroRubro] = useState(false);
  const [conClaude, setConClaude] = useState(false);
  const set = o.set;
  const sugeridas = o.sugeridas;

  const leerTuClaude = async (texto: string) => {
    if (await o.leerTuClaude(texto)) setConClaude(false);
  };
  const usoFuentes = cv === "listo" || claudeListo;
  /** Las tarjetas de lo que tus fuentes no dijeron (todas, si no usaste fuentes). */
  const pasosQueFaltan = usoFuentes
    ? MANUAL.filter((x) => [...(ELEGIR[x] ?? []), ...(DESLIZAR[x] ?? [])].some((k) => !sabidos.has(k)))
    : MANUAL;
  /** Seguir: solo las tarjetas de lo que tus fuentes no dijeron; si dijeron todo, directo a tus dudas. */
  const seguir = () => {
    o.soltarLecturas();
    const pasos = pasosQueFaltan;
    if (pasos.length === 0) return onElegirDuda(p, sugeridas);
    o.irA(pasos[0], pasos);
  };

  if (completo) {
    return (
      <PerfilForm
        inicial={p}
        catalogo={catalogo}
        errorCatalogo={errorCatalogo}
        onReintentarCatalogo={onReintentarCatalogo}
        onReintentar={onReintentar}
        onVolver={(perfil) => {
          o.aplicarFormulario(perfil);
          o.verCompleto(false);
        }}
        onLeido={o.anotarLectura}
        onListo={(perfil) => {
          o.aplicarFormulario(perfil, true);
          onListo(perfil);
        }}
        onElegirDuda={(perfil, suyas) => {
          o.aplicarFormulario(perfil, true);
          // las que trajo el formulario primero, después las de tus fuentes, sin repetir
          const todas = [...suyas, ...sugeridas].filter((d, k, xs) => xs.findIndex((x) => x.decision === d.decision) === k).slice(0, 3);
          onElegirDuda(perfil, todas);
        }}
        cargando={cargando}
        error={error}
      />
    );
  }

  const i = faltan.indexOf(paso);
  const ultimo = i === faltan.length - 1;
  const atras = () => (i > 0 ? o.irA(faltan[i - 1]) : o.irA("entrada", MANUAL));
  const siguiente = () => {
    o.marcar(DESLIZAR[paso] ?? []);
    if (ultimo) onElegirDuda(p, sugeridas);
    else o.irA(faltan[i + 1]);
  };
  /** Saltar: a tus dudas con lo que ya sabemos; lo que falta queda como supuesto. */
  const saltarTodo = () => {
    o.soltarLecturas(); // si Claude estaba leyendo, esa respuesta ya no se usa
    onElegirDuda(p, sugeridas);
  };
  /** Saltar esta pregunta: sigue sin elegir; el valor queda como supuesto. */
  const saltarEsta = () => (ultimo ? onElegirDuda(p, sugeridas) : o.irA(faltan[i + 1]));
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
              <div
                className="ob-puntos"
                role="progressbar"
                aria-label="Preguntas"
                aria-valuemin={1}
                aria-valuemax={faltan.length}
                aria-valuenow={i + 1}
                aria-valuetext={`Pregunta ${i + 1} de ${faltan.length}`}
              >
                {faltan.map((f, k) => (
                  <i key={f} data-hecho={k <= i || undefined} />
                ))}
              </div>
            ) : (
              <Pill>Tu copia</Pill>
            )}
          </Row>
        }
      />

      {(paso !== "entrada" || sabidos.size > 0) && (
        <Ficha p={p} sabidos={sabidos} catalogo={catalogo} retrato={extra?.retrato ?? leido?.retrato ?? null} intereses={extra?.intereses} proyecto={extra?.proyecto} />
      )}

      {errorCatalogo && <ErrorCaja error={errorCatalogo} onReintentar={onReintentarCatalogo} />}
      {!catalogo && !errorCatalogo && i >= 0 && <Cargando>Cargando las alternativas…</Cargando>}

      {paso === "entrada" && (
        <Entrada
          cv={cv}
          error={o.errorCv}
          onPdf={(pdf) => void o.leerPdf(pdf)}
          claudeListo={claudeListo}
          claudeAbierto={conClaude}
          onAbrirClaude={() => setConClaude((x) => !x)}
          claude={<TuClaude leyendo={o.leyendoClaude} error={o.errorClaude} onTexto={(t) => void leerTuClaude(t)} />}
          onSeguir={seguir}
          faltaAlgo={pasosQueFaltan.length > 0}
          onSaltar={saltarTodo}
          onRevisar={() => o.verCompleto(true)}
          cargando={cargando}
        />
      )}

      {catalogo && paso === "tu" && (
        <Tarjeta key="tu" titulo="Primero, tú.">
          <Slider label="Edad" value={p.edad} min={18} max={50} onChange={(n) => set("edad", n)} display={`${p.edad} años`} />
          <Stack gap={8}>
            <span className="jg-etiqueta">Sexo</span>
            <Segmented<string>
              label="Sexo"
              value={elegido("sexo") ? p.sexo : ""}
              onChange={(v) => set("sexo", v as Sexo)}
              options={[
                { value: "m", label: "Mujer" },
                { value: "h", label: "Hombre" },
              ]}
            />
          </Stack>
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
            onChange={(n) => set("sueldo", n)}
            display={pesos(p.sueldo)}
          />
          {ref && (
            <Text size="sm">
              Mediana para tu edad y estudios: <strong>{pesos(ref.p50)}</strong>
            </Text>
          )}
          <Slider
            label="¿Hasta qué edad quieres jugar?"
            value={Math.min(60, Math.max(p.edad + 1, p.edad_final ?? p.edad + 10))}
            min={p.edad + 1}
            max={60}
            step={1}
            onChange={(n) => set("edad_final", n)}
            display={`${p.edad_final ?? p.edad + 10} años`}
          />
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

      {i >= 0 && (
        <ScreenFooter>
          {error && <ErrorCaja error={error} onReintentar={onReintentar} />}
          <Button onClick={siguiente} disabled={!catalogo || cargando || faltaElegir}>
            {ultimo ? (sugeridas.length ? "Ver mis dudas" : "Elegir mi duda") : "Siguiente"}
          </Button>
          <Button variant="white" onClick={saltarEsta} disabled={cargando}>
            Saltar
          </Button>
          {ultimo && (
            <button type="button" className="ob-link" onClick={() => o.verCompleto(true)}>
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
  cv, error, onPdf, claudeListo, claudeAbierto, onAbrirClaude, claude, onSeguir, faltaAlgo, onSaltar, onRevisar, cargando,
}: {
  cv: "nada" | "leyendo" | "listo";
  error: string | null;
  onPdf: (pdf: string) => void;
  claudeListo: boolean;
  claudeAbierto: boolean;
  onAbrirClaude: () => void;
  claude: React.ReactNode;
  onSeguir: () => void;
  /** Si tus fuentes no contestaron todo, Seguir lleva a las preguntas que faltan; si no, a tus dudas. */
  faltaAlgo: boolean;
  onSaltar: () => void;
  /** El formulario completo, para corregir lo que leyeron tus fuentes. */
  onRevisar: () => void;
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
        <Heading level={1}>Armemos tu copia.</Heading>
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
            <span className="ob-chico">{claudeListo ? "Listo. Lo que contó ya está en tu copia." : "Sabe de tus proyectos y lo que te apasiona."}</span>
          </span>
          <Marca listo={claudeListo} accion={claudeAbierto ? "Cerrar" : "Abrir"} />
        </button>
        {claudeAbierto && claude}

        {/* con alguna fuente cargada, esto mismo es el botón de abajo: no se repite */}
        {!algo && (
          <button type="button" className="ob-fuente" onClick={onSeguir} disabled={cv === "leyendo" || cargando}>
            <span className="ob-icono ob-icono--tu" aria-hidden="true">✎</span>
            <span className="ob-fuente-texto">
              <strong>Contesto yo unas preguntas</strong>
              <span className="ob-chico">Edad, sexo, estudios, tu trabajo y tu sueldo. Un toque cada una.</span>
            </span>
            <Marca listo={false} accion="Empezar" />
          </button>
        )}
      </Stack>


      <ScreenFooter>
        {algo && (
          <>
            <Button onClick={onSeguir} disabled={cv === "leyendo" || cargando}>
              {faltaAlgo ? "Completar lo que falta" : "Elegir mi duda"}
            </Button>
            {faltaAlgo && <span className="ob-chico">Solo lo que tus fuentes no dijeron.</span>}
          </>
        )}
        {algo && (
          <button type="button" className="ob-link" onClick={onRevisar} disabled={cv === "leyendo" || cargando}>
            Revisar todos mis datos
          </button>
        )}
        <button type="button" className="ob-link" onClick={onSaltar} disabled={cargando}>
          {algo ? "Saltar las preguntas" : "Jugar sin datos"}
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
    ["sexo", p.sexo === "h" ? "Hombre" : "Mujer"],
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
  const cosas = [
    ...visibles.map(([k, v]) => ({ clave: k, texto: v!, tuyo: false })),
    ...(proyecto ? [{ clave: "proyecto", texto: `Proyecto: ${proyecto.length > 40 ? `${proyecto.slice(0, 40)}…` : proyecto}`, tuyo: true }] : []),
    ...intereses.map((x) => ({ clave: `interes:${x}`, texto: x, tuyo: true })),
  ];
  // si caben en una fila quedan quietas; si no, pasan en una cinta. Nunca bajan a otra fila: la ficha no
  // cambia de alto mientras respondes, y lo que está debajo no se mueve justo cuando vas a tocarlo
  const caja = useRef<HTMLDivElement>(null);
  const [cinta, setCinta] = useState(false);
  const firma = cosas.map((c) => c.texto).join("|");
  useLayoutEffect(() => {
    const el = caja.current;
    if (!el) return;
    const medir = () => {
      const tags = [...el.querySelectorAll<HTMLElement>(".ob-tag:not(.ob-cinta-copia)")];
      const ancho = tags.reduce((s, t) => s + t.offsetWidth, 0) + Math.max(0, tags.length - 1) * 6;
      setCinta(ancho > el.clientWidth - 14);
    };
    medir();
    const ro = new ResizeObserver(medir);
    ro.observe(el);
    return () => ro.disconnect();
  }, [firma]);
  return (
    <div className="ob-ficha">
      <Silueta lleno={Math.min(visibles.length + intereses.length, 7) / 7} />
      <Stack gap={6} style={{ minWidth: 0, flex: 1 }}>
        <Meta>{cosas.length > 0 ? `Tu copia sabe ${cosas.length} ${cosas.length === 1 ? "cosa" : "cosas"} de ti` : "Tu copia"}</Meta>
        {retrato && <Text size="sm" className="ob-retrato">«{retrato}»</Text>}
        {cosas.length === 0 && <span className="ob-chico">Se va armando con cada respuesta.</span>}
        {cosas.length > 0 && (
          <div className="ob-cinta" ref={caja} data-mueve={cinta || undefined}>
            <ul className="vd-sr">
              {cosas.map((c) => (
                <li key={c.clave}>{c.texto}</li>
              ))}
            </ul>
            <div className="ob-cinta-pista" aria-hidden="true" style={cinta ? { animationDuration: `${cosas.length * 2.6}s` } : undefined}>
              {(cinta ? [0, 1] : [0]).flatMap((vuelta) =>
                cosas.map((c) => (
                  <Tag key={`${vuelta}:${c.clave}:${c.texto}`} className={`ob-tag${c.tuyo ? " ob-tag--tuyo" : ""}${vuelta ? " ob-cinta-copia" : ""}`}>
                    {c.texto}
                  </Tag>
                )),
              )}
            </div>
          </div>
        )}
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
  const [errorPrompt, setErrorPrompt] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);
  const [texto, setTexto] = useState("");
  const [copiado, setCopiado] = useState(false);
  useEffect(() => {
    let vivo = true;
    setErrorPrompt(null);
    getPrompt()
      .then((r) => vivo && setPrompt(r.prompt + PROMPT_RELATO))
      .catch((e: unknown) => vivo && setErrorPrompt(textoError(e)));
    return () => {
      vivo = false;
    };
  }, [intento]);

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
      {!prompt && !errorPrompt && <span className="ob-chico" role="status">Trayendo el prompt del simulador…</span>}
      {errorPrompt && (
        <ErrorCaja error={`Sin el prompt no hay qué abrir en Claude ni en ChatGPT. ${errorPrompt}`} onReintentar={() => setIntento((n) => n + 1)} />
      )}
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
        {leyendo ? "Leyendo…" : "Sumar a mi copia"}
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
