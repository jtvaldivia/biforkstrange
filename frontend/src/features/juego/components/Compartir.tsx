import { useEffect, useRef, useState } from "react";
import { toPng } from "html-to-image";
import QRCode from "qrcode";
import { Button, Meta, Stack, Text } from "@/shared/ui";
import { plata } from "../textos";
import type { Comparacion } from "../types";
import "../demo.css";

/** Los colores de la pantalla, fijos: la imagen se ve igual con tema claro u oscuro. La base va naranja, como en la carta. */
const BASE = "#F08A1C";
const COLORES = ["#17794B", "#D6336C", "#7C5CD6", "#0E9AA7"];
const EMPATE = "#B9BAC0";
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

/** Una elección es robusta si con ella no terminas peor (ganas o empatas) en al menos 70 de 100 mundos. */
const ROBUSTA = 0.7;

function coloresFijos(c: Comparacion): Record<string, string> {
  const salida: Record<string, string> = {};
  let i = 0;
  for (const o of c.opciones) salida[o.opcion] = o.es_base ? BASE : COLORES[i++ % COLORES.length];
  return salida;
}

/** "Robusto" o "apuesta", con los mismos conteos que se ven en los puntos. */
function veredicto(c: Comparacion, elegida: string) {
  const ganadores = c.ganador_por_mundo ?? [];
  const n = ganadores.length || 1;
  const gana = ganadores.filter((g) => g === elegida).length;
  const empata = ganadores.filter((g) => g === null).length;
  const nombre = c.opciones.find((o) => o.opcion === elegida)?.nombre ?? elegida;
  if ((gana + empata) / n >= ROBUSTA) {
    return {
      titulo: "Robusto",
      texto: empata > gana
        ? `Con «${nombre}» no terminas peor en ${gana + empata} de ${n} mundos: en ${empata} da lo mismo y en ${gana} ganas más.`
        : `«${nombre}» gana en ${gana} de ${n} mundos y empata en ${empata}: casi no depende de la suerte.`,
    };
  }
  return { titulo: "Apuesta", texto: `«${nombre}» gana solo en ${gana} de ${n} mundos: en el resto, otra opción te dejaba mejor.` };
}

/**
 * "Compartir mi resultado": arma una imagen con los 100 mundos de tu primera decisión (un punto por mundo,
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
      <Button variant="sol" onClick={() => (imagen ? void compartir(imagen) : setArmando(true))} disabled={armando}>
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
              Bifurca
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
                    {o.opcion === elegida ? " (mi elección)" : ""}: gana en {cuenta(o.opcion)}
                  </span>
                ))}
                {cuenta(null) > 0 && (
                  <span>
                    <i style={{ background: EMPATE }} />
                    Empate: {cuenta(null)}
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
                Mi sueldo en el mundo que viví: {plata(sueldoFinal)} al mes.
                <br />
                Juega tu vida y la de tus 100 copias en {url.replace(/^https?:\/\//, "")}
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
