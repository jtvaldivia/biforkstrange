"""Baja una vez el logo de cada empresa y universidad del catálogo y lo guarda como PNG chico.

Lee la columna dominio de simulador/tablas/empresas_catalogo.csv y universidades.csv. Para cada dominio prueba,
en este orden, y se queda con la primera imagen de al menos 64×64 que no sea genérica:

Un logo apaisado vale si su lado largo mide 128 px o más; se centra en un lienzo cuadrado transparente.

a) el ícono del propio sitio: los <link rel="apple-touch-icon"> y <link rel="icon" sizes=...> de la portada,
   del más grande al más chico, y después /apple-touch-icon.png;
b) el logo de Wikidata (propiedad P154, archivo de Wikimedia Commons) del ítem cuyo sitio oficial (P856) es el
   dominio (consulta SPARQL); Commons lo entrega rasterizado a PNG de 128 px aunque el original sea SVG;
c) https://www.google.com/s2/favicons?domain=<dominio>&sz=256, solo si la imagen real mide 64 px o más.

Genérico = la misma imagen (huella de los píxeles a 24×24) aparece en dos o más dominios distintos (globo por
defecto, plantilla de gob.cl, ícono de WordPress), o una imagen casi de un solo color.

Las respuestas crudas quedan en <carpeta datos_laborales>/crudos_catalogos/logos_v2/ (fuera del repo) y la
fuente elegida por dominio en crudos_catalogos/logos_v2_fuentes.csv. Escribe
frontend/public/logos/{empresas,universidades}/<id>.png de 15 KB o menos (4 MB en total) y borra los PNG de
ids que ya no existen o que se quedaron sin logo. En universidades solo mejora: si no encuentra uno nuevo, conserva
el PNG anterior.

Después hay que volver a correr empresas_catalogo.py y universidades.py para que la columna logo refleje los archivos.

Uso: uv run --with pillow python -I backend/scripts/logos.py <carpeta datos_laborales> [--probar lista.csv]
--probar recibe un CSV con columnas nombre,dominio, imprime la fuente que saldría para cada uno y no escribe logos.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image

BACKEND = Path(__file__).resolve().parents[1]
TABLAS = BACKEND / "simulador" / "tablas"
PUBLICO = BACKEND.parent / "frontend" / "public" / "logos"
MAX_BYTES = 15 * 1024
MAX_TOTAL = 4 * 1024 * 1024
MIN_PX = 64
LADO = 128
AGENTE = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36", "Accept-Language": "es-CL,es;q=0.9,en;q=0.8"}
AGENTE_WIKI = {"User-Agent": "catalogo-logos/2.0 (proyecto educativo; python-urllib)"}
FUENTES = ("sitio", "wikidata", "google")
_WIKI = threading.Lock()  # Wikimedia limita la tasa: sus pedidos van de a uno, con pausa


# ---------------------------------------------------------------- red con caché

def bajar(url: str, cache: Path, wiki: bool = False) -> tuple[bytes, str]:
    """Cuerpo y URL final de una respuesta 200; b'' si falla. Cada URL se pide una sola vez (las respuestas
    429 y 5xx de Wikimedia no se guardan, para reintentar en otra corrida)."""
    clave = hashlib.sha256(url.encode()).hexdigest()[:24]
    cuerpo, meta = cache / f"{clave}.bin", cache / f"{clave}.url"
    if meta.exists():
        return cuerpo.read_bytes(), meta.read_text(encoding="utf-8")
    datos, final, guardar = b"", url, True
    try:
        req = urllib.request.Request(url, headers=AGENTE_WIKI if wiki else AGENTE)
        if wiki:
            with _WIKI:
                time.sleep(0.6)
                r = urllib.request.urlopen(req, timeout=20)
        else:
            r = urllib.request.urlopen(req, timeout=12)
        with r:
            if r.status == 200:
                datos, final = r.read(3_000_000), r.geturl()
    except urllib.error.HTTPError as e:
        guardar = not (wiki and (e.code == 429 or e.code >= 500))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        guardar = not wiki
    if not guardar:
        return b"", url
    cuerpo.write_bytes(datos)
    meta.write_text(final, encoding="utf-8")
    return datos, final


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.iconos: list[tuple[int, str]] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta" and a.get("name", "").lower() == "msapplication-tileimage" and a.get("content"):
            self.iconos.append((144, a["content"]))
        if tag != "link":
            return
        rel, href = a.get("rel", "").lower(), a.get("href", "")
        if not href or "icon" not in rel or href.lower().split("?")[0].endswith(".svg") or "mask-icon" in rel:
            return
        lados = [int(x) for x in re.findall(r"(\d+)x\d+", a.get("sizes", ""))]
        lado = max(lados) if lados else (180 if "apple-touch" in rel else 1)
        self.iconos.append((lado, href))  # el tamaño declarado solo ordena; el real se mide al abrir


def candidatos_sitio(dominio: str, cache: Path) -> list[bytes]:
    html, final = b"", ""
    for base in (f"https://{dominio}/", f"https://www.{dominio}/" if not dominio.startswith("www.") else ""):
        if base:
            html, final = bajar(base, cache)
            if html:
                break
    urls = []
    if html:
        p = _Links()
        try:
            p.feed(html.decode("utf-8", "ignore"))
        except Exception:
            pass
        for _, href in sorted(p.iconos, key=lambda t: -t[0]):
            urls.append(urllib.parse.urljoin(final, href))
        urls.append(urllib.parse.urljoin(final, "/apple-touch-icon.png"))
        urls.append(urllib.parse.urljoin(final, "/favicon.ico"))
    else:
        urls += [f"https://{dominio}/apple-touch-icon.png", f"https://{dominio}/favicon.ico"]
    vistos, salida = set(), []
    for u in urls:
        if u not in vistos and u.startswith("http"):
            vistos.add(u)
            datos, _ = bajar(u, cache)
            if datos:
                salida.append(datos)
    return salida


def _host(url: str) -> str:
    h = urllib.parse.urlparse(url if "//" in url else "//" + url).hostname or ""
    return h.lower().removeprefix("www.")


def archivos_wikidata(dominios: list[str], cache: Path) -> dict[str, str]:
    """Archivo de logo (P154) de los ítems de Wikidata cuyo sitio oficial (P856) es exactamente el dominio
    (con o sin www, http o https, con o sin / final). Una consulta SPARQL por cada 8 dominios (URL corta)."""
    salida: dict[str, str] = {}
    for k in range(0, len(dominios), 8):
        lote = dominios[k:k + 8]
        iris = " ".join(f"<{esq}://{w}{d}{fin}>" for d in lote for esq in ("http", "https")
                        for w in ("", "www.") for fin in ("", "/"))
        consulta = ("SELECT ?site ?logo WHERE { VALUES ?site { " + iris + " } ?item wdt:P856 ?site . "
                    "?item wdt:P154 ?logo . } ORDER BY ?site ?logo")
        url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": consulta, "format": "json"})
        datos, _ = bajar(url, cache, wiki=True)
        try:
            filas = json.loads(datos or b"{}").get("results", {}).get("bindings", [])
        except ValueError:
            filas = []
        for f in filas:
            d = _host(f["site"]["value"])
            archivo = urllib.parse.unquote(f["logo"]["value"].rsplit("/", 1)[-1])
            salida.setdefault(d, archivo)
    return salida


def candidatos_wikidata(archivo: str | None, cache: Path) -> list[bytes]:
    if not archivo:
        return []
    url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(archivo) + f"?width={LADO}"
    img, _ = bajar(url, cache, wiki=True)
    return [img] if img else []


def candidatos_google(dominio: str, cache: Path) -> list[bytes]:
    datos, _ = bajar(f"https://www.google.com/s2/favicons?domain={dominio}&sz=256", cache)
    return [datos] if datos else []


def candidatos(dominio: str, archivo: str | None, cache: Path) -> dict[str, list[bytes]]:
    return {"sitio": candidatos_sitio(dominio, cache), "wikidata": candidatos_wikidata(archivo, cache),
            "google": candidatos_google(dominio, cache)}


# ---------------------------------------------------------------- imágenes

def abrir(datos: bytes) -> Image.Image | None:
    try:
        img = Image.open(io.BytesIO(datos))
        if img.format == "ICO":
            img.size = max(img.info.get("sizes", [img.size]))  # el tamaño más grande del .ico
        img.load()
        return img.convert("RGBA")
    except Exception:
        return None


def tamano_ok(img: Image.Image) -> bool:
    """Ícono de al menos 64×64, o logo apaisado (o vertical) de 128 px o más en su lado largo: este se centra
    en un lienzo cuadrado transparente al guardarlo."""
    return min(img.size) >= MIN_PX or (max(img.size) >= 2 * MIN_PX and min(img.size) >= 24)


def cuadrado(img: Image.Image) -> Image.Image:
    lado = max(img.size)
    if img.width == img.height:
        return img
    lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    lienzo.paste(img, ((lado - img.width) // 2, (lado - img.height) // 2))
    return lienzo


def huella(img: Image.Image) -> str:
    fondo = Image.new("RGBA", img.size, (255, 255, 255, 255))
    x = Image.alpha_composite(fondo, img).convert("L").resize((24, 24), Image.LANCZOS)
    return hashlib.sha256(bytes(v // 32 for v in x.tobytes())).hexdigest()


def plano(img: Image.Image) -> bool:
    """Casi de un solo color (o transparente): no sirve como logo."""
    fondo = Image.new("RGBA", img.size, (255, 255, 255, 255))
    x = Image.alpha_composite(fondo, img).convert("L").resize((32, 32))
    lo, hi = x.getextrema()
    return hi - lo < 24


def a_png(img: Image.Image) -> bytes | None:
    img = cuadrado(img)
    for lado in (LADO, 112, 96, 80, 64):
        x = img.copy()
        x.thumbnail((lado, lado), Image.LANCZOS)
        for colores in (None, 128, 64, 32):
            y = x if colores is None else x.quantize(colors=colores, method=Image.Quantize.FASTOCTREE)
            buf = io.BytesIO()
            y.save(buf, format="PNG", optimize=True)
            if buf.tell() <= MAX_BYTES:
                return buf.getvalue()
    return None


def elegir(todos: dict[str, dict[str, list[bytes]]]) -> dict[str, tuple[str, Image.Image] | None]:
    """Por dominio, la primera imagen válida en el orden de FUENTES. Genéricas: huella repetida entre dominios."""
    abiertas: dict[str, list[tuple[str, Image.Image, str]]] = {}
    por_huella: dict[str, set[str]] = {}
    for dominio, cands in todos.items():
        lista = []
        for fuente in FUENTES:
            for datos in cands[fuente]:
                img = abrir(datos)
                if img is None or not tamano_ok(img) or plano(img):
                    continue
                h = huella(img)
                lista.append((fuente, img, h))
                por_huella.setdefault(h, set()).add(dominio)
        abiertas[dominio] = lista
    salida = {}
    for dominio, lista in abiertas.items():
        buenas = [(f, img) for f, img, h in lista if len({_base(d) for d in por_huella[h]}) == 1]
        salida[dominio] = buenas[0] if buenas else None
    return salida


def _base(dominio: str) -> str:
    """Dominio registrable aproximado: los subdominios de un mismo sitio no cuentan como dominios distintos."""
    partes = dominio.removeprefix("www.").split(".")
    n = 3 if len(partes) >= 3 and partes[-2] in ("gob", "com", "co", "edu", "org", "ac") else 2
    return ".".join(partes[-n:])


# ---------------------------------------------------------------- principal

def buscar(pares: list[tuple[str, str]], crudos: Path) -> dict[str, tuple[str, Image.Image] | None]:
    cache = crudos / "crudos_catalogos" / "logos_v2"
    cache.mkdir(parents=True, exist_ok=True)
    unicos = sorted({d for _, d in pares if d})
    wiki = archivos_wikidata(unicos, cache)
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(lambda d: candidatos(d, wiki.get(_host(d)), cache), unicos))
    return elegir(dict(zip(unicos, res)))


def main(crudos: Path) -> None:
    tablas = (("empresas_catalogo", "empresas", "empresa_id"), ("universidades", "universidades", "universidad_id"))
    filas = {t: list(csv.DictReader(open(TABLAS / f"{t}.csv", encoding="utf-8"))) for t, _, _ in tablas}
    elegidos = buscar([(f["nombre"], f["dominio"]) for fs in filas.values() for f in fs], crudos)
    total, cuenta, sin, registro = 0, {}, [], []
    for tabla, carpeta, col_id in tablas:
        destino = PUBLICO / carpeta
        destino.mkdir(parents=True, exist_ok=True)
        validos = set()
        for f in filas[tabla]:
            r = elegidos.get(f["dominio"]) if f["dominio"] else None
            png = a_png(r[1]) if r else None
            salida = destino / f"{f[col_id]}.png"
            if png is None:
                if carpeta == "universidades" and salida.exists():
                    # universidades: solo se mejora; si no hay uno nuevo se conserva el logo anterior
                    validos.add(salida.name)
                    total += salida.stat().st_size
                    cuenta[(carpeta, "anterior")] = cuenta.get((carpeta, "anterior"), 0) + 1
                    continue
                sin.append(f"{carpeta}:{f['nombre']}")
                continue
            salida.write_bytes(png)
            validos.add(salida.name)
            total += len(png)
            cuenta[(carpeta, r[0])] = cuenta.get((carpeta, r[0]), 0) + 1
            registro.append((carpeta, f[col_id], f["nombre"], f["dominio"], r[0], len(png)))
        for viejo in destino.glob("*.png"):
            if viejo.name not in validos:
                viejo.unlink()
    assert total <= MAX_TOTAL, f"los logos suman {total} bytes"
    with open(crudos / "crudos_catalogos" / "logos_v2_fuentes.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["carpeta", "id", "nombre", "dominio", "fuente", "bytes"])
        w.writerows(registro)
    print(f"logos: {len(registro)} ({total / 1024:.0f} KB); por fuente: {dict(sorted(cuenta.items()))}")
    print(f"sin logo usable: {len(sin)} {sin}")


def probar(crudos: Path, lista: Path) -> None:
    filas = list(csv.DictReader(open(lista, encoding="utf-8")))
    elegidos = buscar([(f["nombre"], f["dominio"]) for f in filas], crudos)
    for f in filas:
        r = elegidos.get(f["dominio"])
        print(f"{f['nombre']}\t{f['dominio']}\t{r[0] if r else '-'}\t{min(r[1].size) if r else 0}")


if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[2] == "--probar":
        probar(Path(sys.argv[1]), Path(sys.argv[3]))
    else:
        main(Path(sys.argv[1]))
