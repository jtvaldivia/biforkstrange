"""El juego hecho a tu medida: tu relato libre y los rasgos de tu gemelo.

Cada fuente tiene un solo efecto; ninguna toca las reglas, los resultados ni los mundos de comparación:
1. Tu gemelo decide QUÉ cartas te salen: cada carta pesa más o menos según tus rasgos (afinidad).
   Solo en tu partida; la población calibrada y los mundos de comparación no cambian. La afinidad se
   congela al empezar la partida (`POST /juego/afinidad`) para que rejugarla dé siempre las mismas cartas.
2. Tu relato decide CÓMO se cuentan: el narrador (`narrador_ia`) lo recibe como trasfondo al reescribir
   la carta pendiente y tu historia, con sus mismas reglas (sin cifras, largo máximo, caché).
"""

import math
import re
from dataclasses import dataclass, field

from app.twin.profile import TwinProfile

RELATO_CHARS = 6000
FUERZA = 1.2  # supuesto: un rasgo en el extremo, medido con certeza, multiplica el peso por ~e^1.2 ≈ 3,3
SD_SIN_DATO = 25  # sobre esta duda el rasgo no se usa

# Qué rasgos del gemelo hacen más probable cada carta. Un "-" invierte el rasgo.
AFINIDAD: dict[str, list[str]] = {
    "emprender": ["rcar", "rfin", "E", "vind", "pro"],
    "unirse_a_startup": ["rcar", "rfin", "ope", "pro"],
    "independizarse": ["vind", "rcar", "E"],
    "oferta_externa": ["rcar", "pro", "ent"],
    "buscar_estando_empleado": ["rcar", "pro", "-vcon"],
    "renunciar": ["rcar", "-est", "-vcon"],
    "cambiar_de_rubro": ["rcar", "ope", "int"],
    "cambiar_de_ocupacion": ["rcar", "ope", "int"],
    "magister": ["int", "I", "vlog", "vrec"],
    "doctorado": ["int", "I", "-vcon"],
    "bootcamp": ["int", "pro", "I"],
    "volver_a_estudiar": ["int", "I"],
    "aprender_ia": ["int", "I", "pro"],
    "pedir_aumento": ["ase", "vrec", "vcon"],
    "jefatura": ["ase", "vrec", "E", "ent"],
    "trabajar_mas_horas": ["ind", "vlog", "vrec"],
    "media_jornada": ["vind", "-ind", "vrel"],
    "pedir_hibrido": ["vind", "-ent"],
    "remoto_para_afuera": ["vind", "rcar", "int"],
    "sabatico": ["ope", "-vcon", "-ind"],
    "invertir_en_red": ["ent", "E", "vrel"],
    "emigrar": ["ope", "rcar", "-vrel"],
    "mudarse_de_region": ["ope", "rcar"],
    "intercambio": ["ope", "int"],
    "ahorro": ["ord", "vcon", "-rfin"],
    "comprar_vivienda": ["vcon", "ord", "-rfin"],
}

# Bloques entre cercas (```gemelo-laboral … ```): traen sueldo y otros datos del formulario, no el relato.
_CERCAS = re.compile(r"```.*?(```|$)", re.DOTALL)


@dataclass
class Personal:
    relato: str  # lo que el narrador sabe de la persona en sus palabras ("" si no escribió nada)
    afinidad: dict[str, float] = field(default_factory=dict)  # del gemelo: solo qué cartas te salen


def limpiar_relato(texto: str) -> str:
    """El relato sin los bloques de datos que pegó junto a él, recortado a lo que entra al prompt."""
    return re.sub(r"\n{3,}", "\n\n", _CERCAS.sub("", texto or "")).strip()[:RELATO_CHARS]


def _valor(p: TwinProfile, k: str) -> float | None:
    """Rasgo centrado en 0 (−1 a 1), atenuado por la duda; None si el gemelo no sabe."""
    inv = k.startswith("-")
    d = p.dims.get(k.lstrip("-"))
    if d is None or d.sd > SD_SIN_DATO:
        return None
    confianza = 1 - (d.sd - 6) / (SD_SIN_DATO - 6)  # 1 con certeza, 0 en el umbral
    x = (d.m - 50) / 50 * max(0.0, min(1.0, confianza))
    return -x if inv else x


def afinidad(p: TwinProfile) -> dict[str, float]:
    out = {}
    for carta, rasgos in AFINIDAD.items():
        vals = [v for v in (_valor(p, k) for k in rasgos) if v is not None]
        if vals:
            out[carta] = round(math.exp(FUERZA * sum(vals) / len(vals)), 3)
    return out


def acotar_afinidad(af: dict[str, float]) -> dict[str, float]:
    """La afinidad que manda el cliente: solo cartas conocidas y dentro del rango que puede dar un gemelo."""
    lo, hi = math.exp(-FUERZA), math.exp(FUERZA)
    return {k: min(hi, max(lo, float(v))) for k, v in af.items() if k in AFINIDAD and math.isfinite(v)}


def desde(relato: str, gemelo: TwinProfile | None, congelada: dict[str, float] | None = None) -> Personal | None:
    """Lo personal de la partida. `congelada` (la afinidad del inicio) manda sobre el gemelo vivo."""
    relato = limpiar_relato(relato)
    af = congelada if congelada is not None else (afinidad(gemelo) if gemelo else {})
    if not relato and not af:
        return None
    return Personal(relato=relato, afinidad=af)
