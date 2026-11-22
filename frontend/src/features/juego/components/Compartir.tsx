import { useEffect, useRef, useState } from "react";
import { toPng } from "html-to-image";
import QRCode from "qrcode";
import { Button, Meta, Stack, Text } from "@/shared/ui";
import { plata } from "../textos";
import { leerRetrato } from "../retrato";
import type { Comparacion, Perfil } from "../types";
import "../demo.css";

/** Los colores de la pantalla, fijos: la imagen se ve igual con tema claro u oscuro. La base va naranja, como en la carta. */
const BASE = "#F08A1C";
const COLORES = ["#17794B", "#2447F9", "#D6336C", "#7C5CD6", "#0E9AA7"];
const EMPATE = "#B9BAC0";
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
 * Se descarga como PNG.
 */
export function CompartirResultado({
  comparacion, elegida, sueldoFinal, perfil,
}: {
  comparacion: Comparacion;
  elegida: string;
  sueldoFinal: number;
  perfil?: Perfil;
}) {
  const [qr, setQr] = useState<string | null>(null);
  const [armando, setArmando] = useState(false);
  const [imagen, setImagen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const tarjeta = useRef<HTMLDivElement>(null);
  const url = window.location.origin;
  const ganadores = comparacion.ganador_por_mundo ?? [];
  const colores = coloresFijos(comparacion);
  const v = veredicto(comparacion, elegida);
  const retrato = leerRetrato(perfil);

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
        descargar(png);
      })
      .catch((e: unknown) => vigente && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => vigente && setArmando(false));
    return () => {
      vigente = false;
    };
  }, [armando, qr]);

  if (ganadores.length === 0) return null;

  return (
    <Stack as="section" gap={10} className="jg-compartir">
      <Meta>Comparte tu resultado</Meta>
      <Button variant="sol" onClick={() => (imagen ? descargar(imagen) : setArmando(true))} disabled={armando}>
        {armando ? "Armando tu tarjeta…" : imagen ? "Descargar de nuevo" : "Compartir mi resultado"}
      </Button>
      {error && <Text size="sm">No pudimos armar la imagen: {error}</Text>}
      {imagen && <img className="jg-compartir-vista" src={imagen} alt={`Tu resultado: ${v.titulo}. ${v.texto}`} />}

      {armando && (
        <div className="jg-tarjeta-lienzo" aria-hidden="true">
          <div className="jg-tarjeta" ref={tarjeta}>
            <div className="jg-tarjeta-marca">
              Agarrar la pala
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
                Mi sueldo en el mundo que viví: {plata(sueldoFinal)} al mes.
                <br />
                Juega tu vida y la de tus 100 gemelos en {url.replace(/^https?:\/\//, "")}
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
  a.download = "agarrar-la-pala-mi-resultado.png";
  document.body.appendChild(a);
  a.click();
  a.remove();
}
