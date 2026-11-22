"""Catálogo de dimensiones del gemelo (26). Para agregar una, súmala a DIMS con su grupo."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DimDef:
    key: str
    nombre: str
    grupo: str
    descripcion: str


PERSONALIDAD, INTERESES, VALORES, RIESGO = "personalidad", "intereses", "valores", "riesgo"

GROUP_LABELS = {
    PERSONALIDAD: "Personalidad en el trabajo",
    INTERESES: "Intereses (RIASEC)",
    VALORES: "Valores laborales",
    RIESGO: "Tolerancia al riesgo",
}

GROUP_WEIGHT = {PERSONALIDAD: 1.1, INTERESES: 1.0, VALORES: 1.0, RIESGO: 0.9}

_RAW = [
    # Personalidad: 10 aspectos Big Five (DeYoung) + Honestidad-Humildad (HEXACO) + proactividad
    ("ind", "Empuje", PERSONALIDAD, "Industriosidad: esfuerzo, constancia, terminar lo que empieza"),
    ("ord", "Orden", PERSONALIDAD, "Planificación, estructura, detalle"),
    ("ent", "Energía social", PERSONALIDAD, "Entusiasmo: sociabilidad, energía con otros"),
    ("ase", "Asertividad", PERSONALIDAD, "Tomar la palabra, liderar, influir"),
    ("com", "Compasión", PERSONALIDAD, "Empatía, cuidar a otros"),
    ("cor", "Cortesía", PERSONALIDAD, "Respeto a normas y autoridad, evitar el conflicto"),
    ("int", "Intelecto", PERSONALIDAD, "Curiosidad por ideas, pensamiento abstracto"),
    ("ope", "Apertura estética", PERSONALIDAD, "Arte, imaginación, experiencias nuevas"),
    ("est", "Estabilidad", PERSONALIDAD, "Calma bajo presión, poca preocupación (inverso de neuroticismo)"),
    ("hh", "Honestidad-humildad", PERSONALIDAD, "Sinceridad, justicia, modestia, poco interés en el estatus"),
    ("pro", "Proactividad", PERSONALIDAD, "Cambiar el entorno, buscar oportunidades sin que se lo pidan"),
    # Intereses RIASEC (Holland / O*NET)
    ("R", "Realista", INTERESES, "Trabajo práctico, con las manos, herramientas, máquinas o al aire libre"),
    ("I", "Investigador", INTERESES, "Analizar, investigar, resolver problemas con datos e ideas"),
    ("A", "Artístico", INTERESES, "Crear, diseñar, expresarse, trabajo poco estructurado"),
    ("S", "Social", INTERESES, "Enseñar, ayudar, acompañar, trabajar con personas"),
    ("E", "Emprendedor", INTERESES, "Vender, persuadir, liderar proyectos y negocios"),
    ("C", "Convencional", INTERESES, "Organizar información, procesos claros, datos y registros"),
    # Valores laborales (O*NET Work Importance Locator)
    ("vlog", "Logro", VALORES, "Usar sus habilidades y ver resultados de su trabajo"),
    ("vind", "Independencia", VALORES, "Autonomía, decidir cómo y cuándo trabajar"),
    ("vrec", "Reconocimiento", VALORES, "Avanzar, prestigio, que se note su aporte"),
    ("vrel", "Relaciones", VALORES, "Buen ambiente con compañeros, servir a otros"),
    ("vapo", "Apoyo", VALORES, "Jefaturas que respaldan, empresa que cuida a su gente"),
    ("vcon", "Condiciones", VALORES, "Estabilidad, buen sueldo, seguridad laboral, buen horario"),
    # Tolerancia al riesgo por dominio (inspirada en DOSPERT)
    ("rfin", "Riesgo financiero", RIESGO, "Invertir, apostar plata, aceptar ingresos variables"),
    ("rcar", "Riesgo de carrera", RIESGO, "Cambiarse de pega, emprender, dejar lo seguro"),
    ("rsoc", "Riesgo social", RIESGO, "Llevar la contraria, exponerse en público, decir lo impopular"),
]

DIMS: dict[str, DimDef] = {k: DimDef(k, n, g, d) for k, n, g, d in _RAW}
DIM_KEYS = list(DIMS)

TEMAS = ["trabajo", "plata", "gustos", "relaciones", "tiempo_libre", "valores"]
TEMA_LABELS = {
    "trabajo": "Trabajo y carrera",
    "plata": "Plata",
    "gustos": "Gustos",
    "relaciones": "Relaciones",
    "tiempo_libre": "Tiempo libre",
    "valores": "Valores y dilemas",
}

# Pesos de ajuste por tipo de trabajo (sección 5.4 del spec; ajustables)
FIT_WEIGHTS: dict[str, dict[str, float]] = {
    "Investigación / PhD": {"int": 3, "I": 3, "ind": 2, "vind": 2, "ope": 1, "est": 1, "pro": 1, "vlog": 1, "ord": 0.5},
    "Data science en empresa": {"I": 3, "int": 2, "ind": 2, "ord": 1, "C": 1, "est": 1, "hh": 1, "vlog": 1, "vcon": 1},
    "Liderar equipos": {"ase": 3, "est": 2, "ind": 2, "ent": 2, "E": 2, "pro": 2, "com": 1, "S": 1, "hh": 1, "vrec": 1, "vlog": 1},
    "Consultoría": {"ind": 3, "ase": 2, "est": 2, "int": 2, "E": 2, "vlog": 2, "ent": 1, "vrec": 1, "vcon": -1},
    "Emprender": {"pro": 3, "rcar": 3, "E": 3, "vind": 3, "rfin": 2, "ase": 2, "est": 2, "ope": 1, "int": 1, "com": -1, "vcon": -1},
    "Sector público": {"hh": 2, "ord": 2, "C": 2, "vapo": 2, "vcon": 2, "cor": 1, "S": 1, "vrel": 1, "est": 1, "ind": 1, "rcar": -1},
    "Freelance remoto": {"ind": 3, "vind": 3, "ord": 2, "pro": 2, "est": 1, "rfin": 1, "ent": -1, "vrel": -1},
}
