"""Números del motor → palabras. La historia nunca muestra cifras.

Las palabras son neutras en género: el narrador las copia, y no sabemos cómo se nombra la persona.
"""

from app.story.engine import YearFacts


def plata(f: YearFacts) -> str:
    if f.sin_pega:
        return "sin sueldo fijo"
    r = f.sueldo_rel
    if r < 0.75:
        return "apretada"
    if r < 0.95:
        return "justa"
    if r < 1.15:
        return "como siempre"
    if r < 1.4:
        return "holgada"
    return "sobrada"


def energia(f: YearFacts) -> str:
    d = f.desgaste
    if d < 0.25:
        return "a tope"
    if d < 0.45:
        return "bien"
    if d < 0.6:
        return "con cansancio"
    if d < 0.75:
        return "al límite"
    return "en las últimas"


TRABAJO = {
    "sabatico": "en pausa",
    "estudiar": "estudiando",
    "cambiar_pega": "en una pega nueva",
    "trabajar_mas": "a full",
    "trabajar_menos": "con menos horas",
    "seguir": "en lo mismo",
}


def trabajo(f: YearFacts) -> str:
    return "sin pega" if f.sin_pega else TRABAJO.get(f.decision, "trabajando")


def odds(p: float) -> str:
    """0.12 → 'a 1 de cada 8 personas como tú'."""
    if p <= 0.005:
        return "a casi nadie"
    if p >= 0.5:
        return f"a {round(p * 10)} de cada 10 personas como tú"
    return f"a 1 de cada {max(2, round(1 / p))} personas como tú"


def tone(f: YearFacts) -> str:
    return "noche" if f.sin_pega or f.desgaste >= 0.6 else "dia"


def facts_for_prompt(f: YearFacts) -> str:
    """Lo que el narrador debe respetar, en lenguaje llano (sin cifras para copiar)."""
    lines = [
        f"- Trabajo: {trabajo(f)}." + (" Quedaste sin pega este año." if f.sin_pega else ""),
        f"- Plata: {plata(f)} (comparada con cuando empezaste)."
        + (" Este año ganaste más que el anterior." if f.cambio_sueldo > 0.02 else
           " Este año ganaste menos que el anterior." if f.cambio_sueldo < -0.02 else ""),
        f"- Energía: {energia(f)}." + (" Subió el cansancio." if f.cambio_desgaste > 0.04 else
                                      " Recuperaste energía." if f.cambio_desgaste < -0.04 else ""),
        f"- Qué tan común: quedar sin pega este año le pasó {odds(f.prob_sin_pega)}; "
        f"terminar quemado, {odds(f.prob_quemado)}. "
        + ("A ti te fue mejor que a la mitad." if f.mejor_que_mitad else "A ti te fue peor que a la mitad."),
    ]
    if f.arrastre:
        lines.append("- Lo que arrastras de antes: " + " ".join(f.arrastre))
    if f.factores:
        lines.append("- Por cómo eres: " + "; ".join(x["texto"] for x in f.factores) + ".")
    return "\n".join(lines)
