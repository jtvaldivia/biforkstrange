"""Utilidades de los tests del motor nuevo (`tests/test_motor_*.py`).

Regla de estos tests: nada se compara contra el mismo código que usa el motor. Los
oráculos son valores literales del paquete, el evaluador de referencia o propiedades.
Por eso aquí hay dobles de laboratorio propios (dados con guion, decisor con guion)
y un generador de estados que no pasa por `perfil.py`.

`MOTOR_N` escala los tamaños de muestra (1 por omisión; 5 para una corrida larga).
"""

import math
import os
import re
import random

from app.sim.motor.azar import Dados
from app.sim.motor.motor import Vida
from app.sim.motor.paquete import paquete
from app.sim.motor.perfil import Perfil, estado_inicial

ESCALA = float(os.environ.get("MOTOR_N", "1"))

# Literales del reglamento del motor (TICKETS.md), para no importarlos del código bajo prueba.
DECISIONES_PERSONALES = {"tener_hijo", "formalizar_pareja", "separarse", "buscar_pareja", "cuidar_familiar",
                         "comprar_vivienda"}
EVENTOS_PERSONALES = {"cancer", "muere_madre", "muere_padre", "enferma_familiar", "forma_pareja", "termina_pareja",
                      "hijo_no_planificado", "herencia"}
NADA = 0.999999  # un dado que no gatilla ningún sorteo con probabilidad menor que 1

# Pesos literales de las cartas del perfil por omisión (30 años, universitaria, pyme de Servicios
# profesionales, nivel 1, antigüedad 2, red 30, oficio 50, riesgo 50, sin carrera: exposición 0,143).
CARTAS_PERFIL_BASE = {
    "magister": 0.4, "doctorado": 0.15, "bootcamp": 0.4, "oferta_externa": 8 * 0.1377 * 1.3,
    "buscar_estando_empleado": 0.4, "renunciar": 0.5 * 0.0478, "pedir_aumento": 0.6, "trabajar_mas_horas": 0.8,
    "remoto_para_afuera": 0.4, "pedir_hibrido": 0.4, "media_jornada": 0.2, "cambiar_de_rubro": 0.3,
    "cambiar_de_ocupacion": 0.25, "aprender_ia": 0.3 + 0.143, "invertir_en_red": 0.4,
    "unirse_a_startup": 0.04 + 50 / 1500, "independizarse": 0.3, "emprender": 0.08 + 50 / 500, "emigrar": 0.25,
    "mudarse_de_region": 0.3, "sabatico": 0.1, "ahorro": 0.2,
}


def n(base: int) -> int:
    """Tamaño de muestra escalado por MOTOR_N."""
    return max(1, int(base * ESCALA))


def pq():
    return paquete()


def z_binomial(observados: int, total: int, p: float) -> float:
    """Desvíos estándar entre una frecuencia observada y su probabilidad teórica."""
    return (observados - total * p) / math.sqrt(total * p * (1 - p))


# ---------------------------------------------------------------------------- dobles de laboratorio
class DadosGuion:
    """Dados de laboratorio: cada sitio recibe el número que dice el guion.

    La clave del guion es el sitio (`'evento:recesion'`) o `(año, sitio)`. Lo que no
    está en el guion recibe `defecto` (por omisión, un número que no gatilla nada).
    Los flujos de las expresiones con azar salen de dados reales con semilla fija.
    """

    def __init__(self, guion: dict | None = None, defecto: float = NADA, semilla: int = 0, gemelo=0):
        self.guion = dict(guion or {})
        self.defecto = defecto
        self.pedidos: list[tuple[int, str]] = []
        self._reales = Dados(semilla, gemelo)

    def u(self, anio: int, sitio: str) -> float:
        self.pedidos.append((anio, re.sub(r"@\d+", "", sitio)))  # los tests nombran los sitios sin el número de pega
        if (anio, sitio) in self.guion:
            return self.guion[(anio, sitio)]
        if sitio in self.guion:
            return self.guion[sitio]
        # la suerte de la pega lleva el número de pega (`evento:ascenso@2`); el guion la nombra sin él
        sin_pega = re.sub(r"@\d+", "", sitio)
        if (anio, sin_pega) in self.guion:
            return self.guion[(anio, sin_pega)]
        return self.guion.get(sin_pega, self.defecto)

    def flujo(self, anio: int, sitio: str):
        return self._reales.flujo(anio, sitio)

    def elegir(self, anio: int, sitio: str, pesos: list[float]) -> int:
        x = self.u(anio, sitio) * sum(pesos)
        acumulado = 0.0
        for i, p in enumerate(pesos):
            acumulado += p
            if x < acumulado:
                return i
        return len(pesos) - 1

    def sitios(self) -> set[str]:
        return {s for _, s in self.pedidos}


class Guion:
    """Decisor de laboratorio: responde cada decisión con la opción del guion.

    `respuestas` es {decisión: opción} o {decisión: [opción del 1er año, del 2º...]}.
    Una decisión que no está en el guion es un error del test, salvo que haya `resto`
    (otro decisor al que delegar). No depende de los pesos de `politicas.py`.
    """

    def __init__(self, respuestas: dict | None = None, con_cartas: bool = False, parametros: dict | None = None,
                 resto=None):
        self.respuestas = {k: list(v) if isinstance(v, list) else v for k, v in (respuestas or {}).items()}
        self.con_cartas = con_cartas
        self.parametros = parametros or {}
        self.resto = resto
        self.vistas: list[str] = []

    def elegir(self, vida, decision, opciones):
        id_ = decision["id"]
        self.vistas.append(id_)
        if id_ not in self.respuestas:
            if self.resto is not None:
                return self.resto.elegir(vida, decision, opciones)
            raise AssertionError(f"el guion no esperaba la decisión {id_!r} (opciones: {[o.id for o in opciones]})")
        r = self.respuestas[id_]
        if isinstance(r, list):
            r = r.pop(0) if len(r) > 1 else r[0]
        return r, self.parametros.get(id_, {})


def vida(perfil: Perfil | None = None, dados=None, alcance: str = "laboral", **estado) -> Vida:
    """Una vida desde un perfil, con variables de estado pisadas a mano (`ahorro=0`, `hueco=1`...)."""
    e = estado_inicial(perfil or Perfil(), pq())
    desconocidas = set(estado) - set(e)
    assert not desconocidas, f"variables que no existen: {desconocidas}"
    e.update(estado)
    return Vida(e, dados if dados is not None else Dados(0, 0), pq(), alcance)


def fabrica(perfil: Perfil | None = None, alcance: str = "laboral", **estado):
    """Como `vida`, para muchas vidas iguales: calcula el estado inicial una vez. Devuelve dados -> Vida."""
    e = estado_inicial(perfil or Perfil(), pq())
    assert not set(estado) - set(e)
    e.update(estado)
    return lambda dados: Vida(e, dados, pq(), alcance)


def foto(v: Vida) -> dict:
    """Todo lo que define a una vida, copiado en profundidad, para comparar antes y después."""
    import copy

    return copy.deepcopy({
        "e": v.e, "cola": v.cola, "temporales": v.temporales, "historia": v.historia, "registro": v.registro,
        "anio": v.anio, "anios_buscando": v.anios_buscando, "ingreso_total": v.ingreso_total,
        "hueco": v._anios_con_hueco, "dados": (v.dados.semilla, v.dados.gemelo) if isinstance(v.dados, Dados) else None,
    })


# ---------------------------------------------------------------------------- estados al azar
RUBROS = ["Minería", "Finanzas y seguros", "Información y comunicaciones", "Comercio", "Salud", "Enseñanza",
          "Servicios profesionales", "Construcción", "Industria manufacturera", "Transporte", "Agricultura y pesca",
          "Hoteles y restaurantes", "Artes y entretención", "Servicios administrativos", "Administración pública",
          "Otros servicios"]
REGIONES = ["Valparaíso", "Biobío", "Antofagasta", "Maule", "La Araucanía", "Los Lagos"]


def estado_al_azar(R: random.Random) -> dict:
    """Un estado completo y verosímil (misma idea que `referencia/validar.py`, sin pasar por `perfil.py`).

    Se deriva con el paquete de referencia. Los modificadores también varían, para
    que las fórmulas que los usan no se evalúen siempre en su valor neutro.
    """
    p = pq()
    carreras = p.ref.filas("mifuturo_carreras")
    edad = R.randint(18, 59)
    edu = R.choice(["media", "media", "tecnica", "universitaria", "postgrado"]) if edad >= 22 else "media"
    est = "estudiando" if (edad <= 24 and R.random() < 0.4) else R.choice(
        ["empleado", "empleado", "empleado", "buscando", "independiente", "fundador", "inactivo"])
    c = R.choice(carreras) if (edu != "media" or est == "estudiando") and R.random() < 0.9 else None
    pareja = R.choice(["no", "pololeo", "convive", "casado"])
    hijos = R.choice([0, 0, 1, 2]) if edad >= 22 else 0
    tipo = R.choice(["grande", "pyme", "startup", "publico", "extranjero"]) if est == "empleado" else ""
    if R.random() < 0.03:
        tipo = ""  # estado incoherente a propósito: ambos evaluadores deben fallar igual
    sueldo = round(R.lognormvariate(math.log(800000), 0.6)) if est in ("empleado", "independiente", "fundador") else 0
    madre = edad + R.randint(18, 42) if R.random() < 0.9 else -1
    e = {
        "edad": edad, "sexo": R.choice(["h", "m"]), "edu": edu, "estado": est,
        "primer_empleo": 1 if (est == "buscando" and R.random() < 0.3) else 0,
        "carrera_id": int(c["carrera_id"]) if c else -1, "area": c["area"] if c else "",
        "tipo_institucion": c["tipo_institucion"] if c else R.choice(["", "U", "IP", "CFT"]),
        "semestres_restantes": R.randint(0, 10) if est == "estudiando" else 0, "anos_titulado": R.randint(0, 20),
        "tipo_empleador": tipo, "rubro": "Administración pública" if tipo == "publico" else R.choice(RUBROS + [""]),
        "nivel": R.randint(0, 4), "sueldo": sueldo,
        "sueldo_ref": sueldo or round(R.lognormvariate(math.log(800000), 0.5)),
        "antiguedad": R.randint(0, 14), "meses_cesante": R.choice([0, 6, 12, 24, 48]) if est == "buscando" else 0,
        "hueco": R.randint(0, 1), "horas": R.choice([22, 44, 55]), "parcial": R.randint(0, 1),
        "remoto": R.randint(0, 1), "formal": R.randint(0, 1), "pais": R.choice(["chile", "chile", "afuera"]),
        "region": R.choice(["rm", "otra"]), "region_perfil": R.choice(REGIONES), "pareja": pareja, "hijos": hijos,
        "edad_hijo_menor": R.randint(0, 15) if hijos else -1, "ahorro": round(R.uniform(-5e6, 6e7)),
        "deuda_estudios": R.choice([0, 0, 8e6]), "animo": R.uniform(20, 90), "energia": R.uniform(10, 95),
        "salud": R.choice(["bien", "bien", "licencia", "cancer", "cronica"]), "red": R.uniform(0, 100),
        "skill": R.uniform(0, 100), "riesgo": R.uniform(0, 100), "ambicion": R.uniform(0, 100),
        "usa_ia": R.randint(0, 1), "empresa_anos": R.randint(0, 8),
        "base_empresa": R.choice([0, 0, round(R.lognormvariate(math.log(600000), 0.6))]), "empresa_fondos": R.randint(0, 1),
        "madre_edad": madre, "padre_edad": madre + 2 if madre > 0 and R.random() < 0.85 else -1,
        "familiar_enfermo": R.choice(["", "", "", "madre", "padre"]), "recesion": 1 if R.random() < 0.2 else 0,
        "anos_en_carrera": R.randint(0, 5), "anos_en_startup": R.randint(0, 6),
        "financia": R.choice(["", "cae", "gratuidad", "familia"]), "ingles": R.randint(0, 1),
        "isapre": R.randint(0, 1), "marcado": R.randint(0, 1), "validado": R.randint(0, 1),
        "propietario": R.randint(0, 1), "primer_grande": R.randint(0, 1), "oferta_al_titularse": R.randint(0, 1),
        "ocupacion": R.randint(0, 9), "edad_decide_estudios": R.choice([18, 19]), "cierra_en": R.choice([0, 0, 1, 3]),
        "rubro_destino": R.choice(RUBROS), "region_destino": R.choice(REGIONES), "ocupacion_destino": R.randint(0, 9),
        "quien_enferma": R.choice(["madre", "padre"]),
        "universidad_destino": R.choice([f["universidad_id"] for f in p.filas("universidades")
                                         if f["tipo_institucion"] in ("U", "EXT")]),
        "universidad_id": R.choice([""] + [f["universidad_id"] for f in p.filas("universidades")]),
        "institucion_destino": R.choice([f["universidad_id"] for f in p.filas("universidades") if f["tipo_institucion"] != "EXT"]),
        "empresa_id": R.choice([-1, R.randint(0, len(p.filas("empresas_catalogo")) - 1)]),
        "cargo_id": R.choice([-1, R.randint(0, len(p.filas("cargos_catalogo")) - 1)]),
        "ia_adopcion": R.random(), "ia_castigo_joven": R.uniform(0.75, 0.9),
    }
    for v in p.variables.values():
        if v["tipo"] == "modificador":
            lo, hi = v["dominio"]
            neutro = float(v["inicio"]) if str(v["inicio"]).lstrip("-").replace(".", "", 1).isdigit() else lo
            e[v["nombre"]] = neutro if R.random() < 0.5 else R.uniform(lo, hi)
    e = p.ref.derivar(e)
    e["prob_ascenso"] = R.choice([0.0, 0.05, R.uniform(0, 0.4)])
    e["prima_personal"] = R.choice([1.0, R.uniform(0.6, 3.0)])  # la calcula el motor, no el paquete de referencia
    faltan = set(p.variables) - set(e)
    assert not faltan, f"el generador no cubre {faltan}"
    return e


def expresiones_del_paquete() -> list[tuple[str, str, object, bool]]:
    """(categoría, dónde, expresión, usa columnas de la fila) de todo el catálogo, leído de los JSON."""
    p = pq()
    salida: list[tuple[str, str, object, bool]] = []

    def de_resultados(donde, resultados, fila=False):
        for r in resultados:
            if r["prob"] != "resto":
                salida.append(("prob", f"{donde}/{r['id']}", r["prob"], fila))
            for ef in r["efectos"]:
                salida.append(("valor", f"{donde}/{r['id']}:{ef['var']}", ef["valor"], fila))
                if ef.get("cuando"):
                    salida.append(("efecto_cuando", f"{donde}/{r['id']}:{ef['var']}", ef["cuando"], fila))

    for d in p.decisiones.values():
        salida.append(("cuando", d["id"], d["cuando"], False))
        salida.append(("peso", d["id"], d["aparicion"]["peso"], False))
        for o in d["opciones"]:
            if o.get("requisito"):
                salida.append(("requisito", f"{d['id']}/{o['id']}", o["requisito"], False))
            for ef in o.get("costo", []):
                salida.append(("valor", f"{d['id']}/{o['id']}:costo:{ef['var']}", ef["valor"], False))
            de_resultados(f"{d['id']}/{o['id']}", o["resultados"])
        desde = d.get("opciones_desde_tabla")
        if desde:
            salida.append(("filtro", d["id"], desde["filtro"], True))
            de_resultados(f"{d['id']}/fila", desde["resultados"], fila=True)
    for ev in p.eventos.values():
        salida.append(("cuando", f"evento {ev['id']}", ev["cuando"], False))
        salida.append(("prob_anual", f"evento {ev['id']}", ev["prob_anual"], False))
        de_resultados(f"evento {ev['id']}", ev["resultados"])
    return salida
