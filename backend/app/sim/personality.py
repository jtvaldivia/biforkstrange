"""Cómo tus rasgos (medidos por el gemelo) ajustan cada decisión.

Cada decisión tiene tres palancas: crecimiento del sueldo, riesgo de quedar sin pega y desgaste.
Un rasgo mueve una palanca en proporción a qué tan lejos estás del promedio (z) y a qué tan seguro
está el gemelo de ese rasgo (peso). Un rasgo sin medir (sd 30) no mueve nada.

Los coeficientes son supuestos razonables para la demo, no estimaciones: calibrar con datos reales.
"""

from dataclasses import dataclass

from app.twin.dims import DIMS

SD_UNKNOWN = 30.0
SD_FULL = 12.0
MIN_EFFECT = 0.002  # bajo esto (0,2 puntos) no vale la pena mencionarlo


@dataclass(frozen=True)
class Params:
    growth: float  # crecimiento esperado del sueldo (0.03 = +3%)
    risk: float  # probabilidad base de quedar sin pega ese año
    wear: float  # cambio de desgaste (0.05 = +5 puntos de 100)


@dataclass(frozen=True)
class Modifier:
    dim: str
    param: str  # growth | risk | wear
    per_z: float  # efecto con el rasgo en 100 (z = 1) y certeza total
    alto: str  # explicación cuando estás sobre el promedio
    bajo: str  # cuando estás bajo el promedio


GLOBAL = [
    Modifier("est", "wear", -0.04, "Tu estabilidad amortigua el desgaste", "Con estabilidad baja, el desgaste te pega más"),
    Modifier("ind", "growth", 0.015, "Tu empuje suma crecimiento", "Con menos empuje, creces algo menos"),
]

BY_DECISION: dict[str, list[Modifier]] = {
    "seguir": [
        Modifier("vcon", "wear", -0.02, "Valoras la estabilidad: quedarte te pesa poco", "Valoras poco la estabilidad: quedarte igual te pesa"),
        Modifier("pro", "wear", 0.03, "Eres proactivo: quedarte quieto te frustra", "No te urge cambiar las cosas: quedarte te cuesta poco"),
    ],
    "cambiar_pega": [
        Modifier("rcar", "growth", 0.03, "Toleras el riesgo de carrera: apuestas por mejores ofertas",
                 "Te cuesta arriesgar en tu carrera: tiendes a cambios más conservadores"),
        Modifier("rcar", "risk", -0.02, "Con tu tolerancia al riesgo, el cambio te desordena menos",
                 "El cambio te pone más nervioso y aumenta el riesgo de que no resulte"),
        Modifier("ase", "growth", 0.02, "Tu asertividad ayuda a negociar el sueldo", "Negociar no es tu fuerte: dejas plata en la mesa"),
    ],
    "trabajar_mas": [
        Modifier("ind", "growth", 0.02, "Tu empuje convierte las horas extra en resultados", "Las horas extra rinden menos con poco empuje"),
        Modifier("vrel", "wear", 0.03, "Valoras mucho tus relaciones: sacrificarlas te desgasta más",
                 "Las relaciones no son tu prioridad: trabajar más te cuesta menos"),
    ],
    "trabajar_menos": [
        Modifier("vrel", "wear", -0.03, "Valoras tus relaciones: el tiempo que recuperas te llena más",
                 "Las relaciones no son tu prioridad: el tiempo libre te rinde menos"),
        Modifier("vlog", "wear", 0.02, "Te importa mucho lograr cosas: bajar el ritmo te inquieta",
                 "No te mueve tanto el logro: bajar el ritmo te sienta bien"),
    ],
    "sabatico": [
        Modifier("ope", "wear", -0.05, "Tu apertura a experiencias hace que el año fuera te recargue más",
                 "Con poca apertura, el año fuera te recarga menos"),
        Modifier("rcar", "risk", -0.03, "Toleras el riesgo de carrera: vuelves sin miedo y te reubicas antes",
                 "Volver te inquieta: te cuesta más reubicarte"),
    ],
    "estudiar": [
        Modifier("int", "growth", 0.03, "Tu curiosidad intelectual le saca más provecho al estudio",
                 "Estudiar sin mucho gusto por las ideas rinde menos"),
        Modifier("I", "growth", 0.02, "Te interesa investigar y analizar: estudiar calza contigo", "Lo analítico no te atrae tanto"),
    ],
}


@dataclass(frozen=True)
class Trait:
    m: float
    sd: float


def weight(sd: float) -> float:
    """0 con un rasgo sin medir (sd 30), 1 con uno bien medido (sd ≤ 12)."""
    return max(0.0, min(1.0, (SD_UNKNOWN - sd) / (SD_UNKNOWN - SD_FULL)))


def personalize(key: str, base: Params, rasgos: dict[str, Trait] | None) -> tuple[Params, list[dict]]:
    """Ajusta las palancas de una decisión con tus rasgos. Devuelve los parámetros y por qué cambiaron."""
    if not rasgos:
        return base, []
    vals = {"growth": base.growth, "risk": base.risk, "wear": base.wear}
    factores = []
    specific = BY_DECISION.get(key, [])
    for mod in GLOBAL + specific:
        t = rasgos.get(mod.dim)
        if t is None:
            continue
        z = (t.m - 50) / 50
        delta = mod.per_z * z * weight(t.sd)
        if abs(delta) < MIN_EFFECT:
            continue
        vals[mod.param] += delta
        factores.append({
            "fuente": "rasgo",
            "rasgo": DIMS[mod.dim].nombre,
            "valor": round(t.m),
            "texto": f"{mod.alto if z > 0 else mod.bajo} ({DIMS[mod.dim].nombre} {t.m:.0f})",
            "param": mod.param,
            "delta": delta,
            "especifico": mod in specific,
        })
    vals["risk"] = max(0.0, min(1.0, vals["risk"]))
    return Params(**vals), factores
