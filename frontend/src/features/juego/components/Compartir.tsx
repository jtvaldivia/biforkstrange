import { useEffect, useRef, useState } from "react";
import { toPng } from "html-to-image";
import QRCode from "qrcode";
import { BifurcaLogo, Button, Meta, Stack, Text } from "@/shared/ui";
import { plata } from "../textos";
import type { Comparacion } from "../types";
import { COLOR_EMPATE, coloresDeOpciones } from "../colores";
import "../demo.css";

/** Los colores de opción de la carta, en su valor claro fijo: la imagen se ve igual con tema claro u oscuro. */
const EMPATE = COLOR_EMPATE.claro;
const NOMBRE = "bifurca-mi-resultado.png";

/** Si el navegador puede compartir imágenes (el menú de compartir del celular): si no, se descarga. */
function puedeCompartirArchivos(): boolean {
  try {
    return typeof navigator.canShare === "function" && navigator.canShare({ files: [new File([""], NOMBRE, { type: "image/png" })] });
  } catch {
    return false;
  }
}

/** El PNG (data URL) como archivo, sin esperas: `navigator.share` pide que el toque de la persona sea reciente. */
function comoArchivo(png: string): File {
  const binario = atob(png.slice(png.indexOf(",") + 1));
  const bytes = new Uint8Array(binario.length);
  for (let i = 0; i < binario.length; i++) bytes[i] = binario.charCodeAt(i);
  return new File([bytes], NOMBRE, { type: "image/png" });
}

/**
 * Una elección es robusta si en al menos 7 de cada 10 mundos ninguna otra opción te deja mejor (es la mejor o da lo
 * mismo). Se cuenta con el ganador de cada mundo, el mismo número que "Es la mejor en X de 50" de la carta y que los
 * puntos de la imagen; el veredicto de la carta frente a la opción base es otra pregunta.
 */
const ROBUSTA = 0.7;

const coloresFijos = (c: Comparacion) => coloresDeOpciones(c.opciones, "claro");

/** "Robusto" o "apuesta", con los mismos conteos que se ven en los puntos: es la mejor, da lo mismo u otra te deja mejor, y suman los mundos. */
function veredicto(c: Comparacion, elegida: string) {
  const ganadores = c.ganador_por_mundo ?? [];
  const n = ganadores.length || 1;
  const gana = ganadores.filter((g) => g === elegida).length;
  const empata = ganadores.filter((g) => g === null).length;
  const pierde = ganadores.length - gana - empata;
  const nombre = c.opciones.find((o) => o.opcion === elegida)?.nombre ?? elegida;
  const resto = [
    pierde > 0 && `en ${pierde} otra opción te dejaba mejor`,
    empata > 0 && `en ${empata} daba lo mismo`,
  ].filter(Boolean).join(" y ");
  const mejor = gana === 0 ? `«${nombre}» no es la mejor en ningún mundo` : `«${nombre}» es la mejor en ${gana} de ${n} mundos`;
  return {
    titulo: (gana + empata) / n >= ROBUSTA ? "Robusto" : "Apuesta",
    texto: resto ? `${mejor}; ${resto}.` : `${mejor}.`,
  };
}

/**
 * "Compartir mi resultado": arma una imagen con los mundos de tu primera decisión (un punto por mundo,
 * del color de la opción que gana en él), tu retrato si Claude leyó tu CV, el veredicto y un QR al juego.
 * Se comparte con el menú del navegador (en el celular: WhatsApp, Instagram…) y, si no se puede, se descarga como PNG.
 */
export function CompartirResultado({
  comparacion, elegida, sueldoFinal, retrato = null,
}: {
  comparacion: Comparacion;
  elegida: string;
  sueldoFinal: number;
  /** El retrato del perfil con que se jugó esta partida (no el de quien jugó antes). */
  retrato?: string | null;
}) {
  const [qr, setQr] = useState<string | null>(null);
  const [armando, setArmando] = useState(false);
  const [imagen, setImagen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [compartible] = useState(puedeCompartirArchivos);
  const tarjeta = useRef<HTMLDivElement>(null);
  const url = window.location.origin;
  const ganadores = comparacion.ganador_por_mundo ?? [];
  const colores = coloresFijos(comparacion);
  const v = veredicto(comparacion, elegida);

  // los puntos agrupados por opción, como en la carta; los empates al final
  const orden = new Map<string | null, number>(comparacion.opciones.map((o, i) => [o.opcion, i]));
  const puntos = [...ganadores].sort((a, b) => (orden.get(a) ?? 99) - (orden.get(b) ?? 99));
  const cuenta = (id: string | null) => ganadores.filter((g) => g === id).length;

  useEffect(() => {
    if (!armando || qr) return;
    QRCode.toDataURL(url, { margin: 1, width: 400, color: { dark: "#1D1E22", light: "#FFFFFF" } })
      .then(setQr)
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : String(e));
        setArmando(false);
      });
  }, [armando, qr, url]);

  // con el QR listo (y la imagen del QR cargada en la tarjeta), se fotografía la tarjeta y se descarga
  useEffect(() => {
    if (!armando || !qr || !tarjeta.current) return;
    const nodo = tarjeta.current;
    let vigente = true;
    const foto = (skipFonts: boolean) => toPng(nodo, { pixelRatio: 1, backgroundColor: "#FFFFFF", cacheBust: true, skipFonts });
    // si las fuentes de Google no se dejan leer, sale con la fuente del sistema
    foto(false)
      .catch(() => foto(true))
      .then((png) => {
        if (!vigente) return;
        setImagen(png);
        void compartir(png);
      })
      .catch((e: unknown) => vigente && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => vigente && setArmando(false));
    return () => {
      vigente = false;
    };
  }, [armando, qr]);

  /** Comparte el PNG; si el navegador no puede, lo descarga. Cancelar el menú no es un error. */
  const compartir = async (png: string) => {
    setAviso(null);
    if (!compartible) return descargar(png);
    try {
      await navigator.share({ files: [comoArchivo(png)], title: "Bifurca", text: `${v.titulo}: ${v.texto}` });
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      // armar la imagen toma un rato y el navegador ya no lo cuenta como tu toque: queda lista para otro
      if (e instanceof DOMException && e.name === "NotAllowedError") return setAviso("Tu tarjeta está lista: toca Compartir.");
      descargar(png);
    }
  };

  if (ganadores.length === 0) return null;

  return (
    <Stack as="section" gap={10} className="jg-compartir">
      <Meta>Comparte tu resultado</Meta>
      <Button variant="white" onClick={() => (imagen ? void compartir(imagen) : setArmando(true))} disabled={armando}>
        {armando
          ? "Armando tu tarjeta…"
          : compartible
            ? imagen ? "Compartir" : "Compartir mi resultado"
            : imagen ? "Descargar de nuevo" : "Descargar mi resultado"}
      </Button>
      {aviso && <Text size="sm" role="status">{aviso}</Text>}
      {error && <Text size="sm">No pudimos armar la imagen: {error}</Text>}
      {imagen && <img className="jg-compartir-vista" src={imagen} alt={`Tu resultado: ${v.titulo}. ${v.texto}`} />}

      {armando && (
        <div className="jg-tarjeta-lienzo" aria-hidden="true">
          <div className="jg-tarjeta" ref={tarjeta}>
            <div className="jg-tarjeta-marca">
              <BifurcaLogo size={34} color="#1D1E22" acento="#2447F9" />
              <span>{comparacion.gemelos} mundos, la misma suerte</span>
            </div>
            <p className="jg-tarjeta-pregunta">{comparacion.pregunta}</p>
            {retrato && <p className="jg-tarjeta-retrato">«{retrato}»</p>}
            <div className="jg-tarjeta-cuerpo">
              <div className="jg-tarjeta-puntos">
                {puntos.map((g, i) => (
                  <i key={i} style={{ background: g ? colores[g] : EMPATE }} />
                ))}
              </div>
              <div className="jg-tarjeta-leyenda">
                {comparacion.opciones.map((o) => (
                  <span key={o.opcion}>
                    <i style={{ background: colores[o.opcion] }} />
                    {o.nombre}
                    {o.opcion === elegida ? " (mi elección)" : ""}: la mejor en {cuenta(o.opcion)}
                  </span>
                ))}
                {cuenta(null) > 0 && (
                  <span>
                    <i style={{ background: EMPATE }} />
                    Da lo mismo: {cuenta(null)}
                  </span>
                )}
              </div>
            </div>
            <div className="jg-tarjeta-veredicto">
              <b>{v.titulo}</b>
              <span>{v.texto}</span>
            </div>
            <div className="jg-tarjeta-pie">
              <span>
                {/* la misma base que el cierre: sin trabajo cuenta $0 */}
                Mi sueldo final en el mundo que viví: {sueldoFinal > 0 ? `${plata(sueldoFinal)} al mes` : "$0, terminé sin trabajo"}.
                <br />
                Juega tu vida en {comparacion.gemelos} mundos en {url.replace(/^https?:\/\//, "")}
              </span>
              {qr && <img src={qr} alt="" />}
            </div>
          </div>
        </div>
      )}
    </Stack>
  );
}

function descargar(png: string) {
  const a = document.createElement("a");
  a.href = png;
  a.download = NOMBRE;
  document.body.appendChild(a);
  a.click();
  a.remove();
}
