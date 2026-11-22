"""Tu relato libre: el narrador (`narrador_ia`) lo recibe como trasfondo al reescribir la carta pendiente y
tu historia, con sus mismas reglas (sin cifras, largo máximo, caché). No toca reglas, cartas ni resultados."""

import re

RELATO_CHARS = 6000

# Bloques entre cercas (```gemelo-laboral … ```): traen sueldo y otros datos del formulario, no el relato.
_CERCAS = re.compile(r"```.*?(```|$)", re.DOTALL)


def limpiar_relato(texto: str) -> str:
    """El relato sin los bloques de datos que pegó junto a él, recortado a lo que entra al prompt."""
    return re.sub(r"\n{3,}", "\n\n", _CERCAS.sub("", texto or "")).strip()[:RELATO_CHARS]


def desde(relato: str) -> str:
    """Lo que el narrador sabe de la persona en sus palabras ("" si no escribió nada)."""
    return limpiar_relato(relato)
