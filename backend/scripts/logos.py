"""Baja una vez el ícono del sitio de cada empresa y universidad del catálogo y lo guarda como PNG chico.

Lee la columna dominio de simulador/tablas/empresas_catalogo.csv y universidades.csv. Por cada dominio pide
https://www.google.com/s2/favicons?domain=<dominio>&sz=128 (respaldo: https://icons.duckduckgo.com/ip3/<dominio>.ico),
guarda la respuesta cruda en <carpeta datos_laborales>/crudos_catalogos/logos/ (fuera del repo) y escribe
frontend/public/logos/{empresas,universidades}/<id>.png de 10 KB o menos. Descarta el globo genérico que
Google entrega cuando el sitio no tiene ícono (responde 404, o el mismo archivo que para un dominio inexistente)
y los íconos de menos de 32 px.

Después hay que volver a correr empresas_catalogo.py y universidades.py para que la columna logo refleje los archivos.

Uso: uv run --with pillow python -I backend/scripts/logos.py <carpeta datos_laborales>
"""

from __future__ import annotations

import csv
import hashlib
import io
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

BACKEND = Path(__file__).resolve().parents[1]
TABLAS = BACKEND / "simulador" / "tablas"
PUBLICO = BACKEND.parent / "frontend" / "public" / "logos"
MAX_BYTES = 10 * 1024
MAX_TOTAL = 3 * 1024 * 1024
MIN_PX = 32
FUENTES = ("https://www.google.com/s2/favicons?domain={}&sz=128", "https://icons.duckduckgo.com/ip3/{}.ico")
AGENTE = {"User-Agent": "Mozilla/5.0 (catalogo-logos)"}


def bajar(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=AGENTE), timeout=15) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, b""


def logo(dominio: str, cache: Path, genericos: set[str]) -> bytes | None:
    """PNG del primer servicio que entregue un ícono no genérico y de al menos MIN_PX; la respuesta cruda
    se guarda para no volver a pedirla."""
    for i, plantilla in enumerate(FUENTES):
        ruta = cache / f"{dominio}.{i}.bin"
        if not ruta.exists():
            estado, datos = bajar(plantilla.format(dominio))
            ruta.write_bytes(datos if estado == 200 else b"")
            time.sleep(0.2)
        datos = ruta.read_bytes()
        if datos and hashlib.sha256(datos).hexdigest() not in genericos:
            png = a_png(datos)
            if png:
                return png
    return None


def a_png(datos: bytes) -> bytes | None:
    try:
        img = Image.open(io.BytesIO(datos))
        if getattr(img, "n_frames", 1) > 1 or img.format == "ICO":
            img.size = max(img.info.get("sizes", [img.size]))  # el tamaño más grande del .ico
        img = img.convert("RGBA")
    except Exception:
        return None
    if min(img.size) < MIN_PX:
        return None
    for lado in (128, 96, 64, 48):
        x = img.copy()
        x.thumbnail((lado, lado), Image.LANCZOS)
        for colores in (None, 64, 32):
            y = x if colores is None else x.quantize(colors=colores, method=Image.Quantize.FASTOCTREE)
            buf = io.BytesIO()
            y.save(buf, format="PNG", optimize=True)
            if buf.tell() <= MAX_BYTES:
                return buf.getvalue()
    return None


def main(crudos: Path) -> None:
    cache = crudos / "crudos_catalogos" / "logos"
    cache.mkdir(parents=True, exist_ok=True)
    # huella del ícono genérico: lo que entregan los servicios para un dominio que no existe
    genericos = set()
    for i, plantilla in enumerate(FUENTES):
        estado, datos = bajar(plantilla.format("dominio-que-no-existe-catalogo.invalid"))
        if datos:
            genericos.add(hashlib.sha256(datos).hexdigest())
    print("huellas genéricas:", len(genericos))

    total, hechos, sin = 0, 0, []
    escritos: dict[str, list[tuple[Path, str]]] = {}  # huella del PNG -> [(archivo, dominio)]
    for tabla, carpeta, col_id in (("empresas_catalogo", "empresas", "empresa_id"), ("universidades", "universidades", "universidad_id")):
        destino = PUBLICO / carpeta
        destino.mkdir(parents=True, exist_ok=True)
        for f in csv.DictReader(open(TABLAS / f"{tabla}.csv", encoding="utf-8")):
            salida = destino / f"{f[col_id]}.png"
            if not f["dominio"]:
                salida.unlink(missing_ok=True)
                continue
            png = logo(f["dominio"], cache, genericos)
            if png is None:
                sin.append(f["dominio"])
                salida.unlink(missing_ok=True)
                continue
            assert total + len(png) <= MAX_TOTAL, "los logos superan 3 MB"
            salida.write_bytes(png)
            escritos.setdefault(hashlib.sha256(png).hexdigest(), []).append((salida, f["dominio"]))
            total += len(png)
            hechos += 1
    # El mismo ícono para dominios distintos es un genérico (globo por defecto, plantilla de gob.cl): se descarta.
    for grupo in escritos.values():
        if len({d for _, d in grupo}) > 1:
            for archivo, d in grupo:
                archivo.unlink()
                hechos -= 1
                sin.append(d)
    total = sum(p.stat().st_size for p in PUBLICO.rglob("*.png"))
    print(f"logos escritos: {hechos} ({total / 1024:.0f} KB); sin ícono usable: {len(sin)} {sorted(set(sin))}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
