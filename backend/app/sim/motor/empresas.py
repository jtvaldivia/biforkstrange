"""Empresas y cargos reales que cambian la simulación.

Catálogo: `simulador/tablas/empresas_catalogo.csv` (unas 150 empresas reales de los 16 rubros) y
`cargos_catalogo.csv`. Los nombres son reales (SII, Get on Board, Y Combinator, empleospublicos.cl);
las cifras de cada empresa NO son de la empresa: salen de las tablas de su rubro y tamaño (calidad
`derivado`) o se sortean con semilla fija a partir de ellas (calidad `sintetico`). Se regeneran con
`backend/scripts/empresas_catalogo.py`.

Qué mueve cada empresa, siempre como multiplicador con promedio 1 dentro de su tipo y rubro:
sueldo (`mult_sueldo`), despido (`mult_despido`), cierre de startup (`mult_cierre`), ascenso
(`mult_ascenso`); además fija las horas y, si no hay cargo, la exposición a IA. El cargo fija el grupo
ocupacional, la exposición a IA (la de su ocupación) y, en cargos tech, una prima de Get on Board.

El motor (`motor.py`) y la carta (`partida.py`) usan las mismas funciones y el mismo sitio de dados,
así que la empresa que ves en la oferta es la que vive tu gemelo si la toma.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from app.sim.motor.azar import Dados
from app.sim.motor.paquete import Paquete

TIPOS = ("grande", "pyme", "startup", "publico", "extranjero")
PUBLICA = "Administración pública"
EDU_ORDEN = {"media": 0, "tecnica": 1, "universitaria": 2, "postgrado": 3}
_NUMERICAS_EMPRESA = ("peso", "mult_sueldo", "mult_despido", "mult_cierre", "mult_ascenso", "exposicion_ia", "horas")
_NUMERICAS_CARGO = ("exposicion_ia", "prima_getonbrd", "peso")
DATOS = Path(__file__).resolve().parents[3] / "data" / "empresas"  # nóminas crudas (SII, Get on Board, Estado)
NEUTRA = {"mult_sueldo": 1.0, "mult_despido": 1.0, "mult_cierre": 1.0, "mult_ascenso": 1.0}


@lru_cache
def _filas(nombre: str) -> tuple[dict, ...]:
    """Una nómina cruda de data/empresas (la usa perfil_ia para reconocer la empresa del CV en el SII)."""
    with open(DATOS / nombre, encoding="utf-8") as fh:
        return tuple(csv.DictReader(fh))


def _num(txt: str, defecto: float = 1.0) -> float:
    try:
        return float(txt)
    except (TypeError, ValueError):
        return defecto


def _lista(txt: str) -> frozenset[str] | None:
    """'a|b' -> {'a', 'b'}; '*' o vacío -> None (cualquiera)."""
    txt = (txt or "").strip()
    return None if txt in ("", "*") else frozenset(x.strip() for x in txt.split("|") if x.strip())


def _catalogo(pq: Paquete) -> dict:
    """Las dos tablas ya leídas y con números; se guarda en el paquete (se lee una vez)."""
    cat = getattr(pq, "_catalogo_empresas", None)
    if cat is not None:
        return cat
    try:
        filas_e, filas_c = pq.filas("empresas_catalogo"), pq.filas("cargos_catalogo")
    except (KeyError, OSError):  # paquete sin catálogo: todo neutro
        filas_e, filas_c = [], []
    empresas = []
    for f in filas_e:
        x = dict(f)
        x["empresa_id"] = int(f["empresa_id"])
        x["logo"] = f.get("logo") == "1"
        for c in _NUMERICAS_EMPRESA:
            x[c] = _num(f.get(c), 0.0 if c in ("peso", "exposicion_ia") else 1.0)
        empresas.append(x)
    cargos = []
    for f in filas_c:
        x = dict(f)
        x["cargo_id"], x["ciuo08_1d"] = int(f["cargo_id"]), int(f["ciuo08_1d"])
        x["nivel_min"], x["nivel_max"] = int(f["nivel_min"]), int(f["nivel_max"])
        for c in _NUMERICAS_CARGO:
            x[c] = _num(f.get(c), 0.0 if c == "exposicion_ia" else 1.0)
        x["_areas"], x["_rubros"], x["_tipos"] = _lista(f.get("areas")), _lista(f.get("rubros")), _lista(f.get("tipos"))
        cargos.append(x)
    cat = {"empresas": empresas, "por_id": {x["empresa_id"]: x for x in empresas},
           "cargos": cargos, "cargo_por_id": {x["cargo_id"]: x for x in cargos}, "pools": {}}
    pq._catalogo_empresas = cat
    return cat


def empresa(pq: Paquete, empresa_id: int) -> dict | None:
    return _catalogo(pq)["por_id"].get(int(empresa_id)) if empresa_id is not None and int(empresa_id) >= 0 else None


def cargo(pq: Paquete, cargo_id: int) -> dict | None:
    return _catalogo(pq)["cargo_por_id"].get(int(cargo_id)) if cargo_id is not None and int(cargo_id) >= 0 else None


def pool(pq: Paquete, tipo: str, rubro: str | None) -> list[dict]:
    """Empresas de un tipo (y rubro, si se da) con peso positivo. Sin relajar: si no hay, lista vacía."""
    cat = _catalogo(pq)
    clave = (tipo, rubro)
    if clave not in cat["pools"]:
        cat["pools"][clave] = [x for x in cat["empresas"] if x["tipo"] == tipo and (rubro is None or x["rubro"] == rubro)
                               and x["peso"] > 0]
    return cat["pools"][clave]


def sortear_empresa(pq: Paquete, dados: Dados, anio: int, sitio: str, tipo: str, rubro: str | None) -> dict | None:
    """Una empresa del tipo y rubro, en proporción a `peso`. None si el catálogo no tiene ninguna."""
    if tipo not in TIPOS:
        return None
    filas = pool(pq, tipo, PUBLICA if tipo == "publico" and rubro is None else rubro)
    if not filas and tipo in ("publico", "extranjero", "startup"):
        # servicios del Estado de cualquier rubro; remoto para afuera y startups: casi todo es tecnología,
        # así que si no hay en tu rubro se toma cualquiera y la persona pasa al rubro de esa empresa
        filas = pool(pq, tipo, None)
    if not filas:
        return None
    return filas[dados.elegir(anio, sitio, [x["peso"] for x in filas])]


def compatibles(pq: Paquete, emp: dict, e: dict) -> list[dict]:
    """Cargos que la empresa le ofrecería a esta persona.

    Duro: tipo y rubro de la empresa, nivel actual y educación mínima. Blando, en este orden: mismo grupo
    ocupacional que tiene hoy y área de su carrera; si con ambos no queda ninguno, se suelta el área y
    después el grupo.
    """
    nivel, edu = int(e.get("nivel", 0)), EDU_ORDEN.get(e.get("edu", "media"), 0)
    duros = [c for c in _catalogo(pq)["cargos"]
             if (c["_tipos"] is None or emp["tipo"] in c["_tipos"])
             and (c["_rubros"] is None or emp["rubro"] in c["_rubros"])
             and c["nivel_min"] <= nivel <= c["nivel_max"]
             and EDU_ORDEN.get(c["edu_min"], 0) <= edu and c["peso"] > 0]
    area, ocup = e.get("area") or "", int(e.get("ocupacion", -1))

    def del_area(c):
        return c["_areas"] is None or (area and area in c["_areas"])

    for filtro in (lambda c: c["ciuo08_1d"] == ocup and del_area(c), lambda c: c["ciuo08_1d"] == ocup,
                   del_area, lambda c: True):
        quedan = [c for c in duros if filtro(c)]
        if quedan:
            return quedan
    return []


def sortear_cargo(pq: Paquete, dados: Dados, anio: int, sitio: str, emp: dict | None, e: dict) -> dict | None:
    if emp is None:
        return None
    filas = compatibles(pq, emp, e)
    if not filas:
        return None
    return filas[dados.elegir(anio, sitio, [c["peso"] for c in filas])]


def factor_sueldo(emp: dict | None, car: dict | None) -> float:
    """Cuánto paga este puesto respecto del nivel de referencia del paquete.

    Empresa × prima de Get on Board del cargo. En las extranjeras la prima no se suma: el aviso de Get on
    Board con que se calculó su multiplicador ya trae el área.
    """
    if emp is None:
        return 1.0
    prima = car["prima_getonbrd"] if car is not None and emp["tipo"] != "extranjero" else 1.0
    return emp["mult_sueldo"] * prima


# ---------------------------------------------------------------------- lo que muestra la carta
def rubro_actual(e: dict) -> str | None:
    """El rubro en que se busca la empresa nueva: el de la persona, salvo que no tenga o venga del Estado."""
    actual = e.get("rubro") or ""
    return actual if actual and actual != PUBLICA else None


def sitio_empresa(origen: str) -> str:
    return f"empresa:{origen}"


def _tipo_y_rubro(vida, decision_id: str, opcion_id: str) -> tuple[str, str | None] | None:
    """Con qué tipo de empleador y rubro termina la opción si sale bien; None si no lleva a un empleador.

    Se lee de los efectos del primer resultado que emplea. Si el resultado sigue en `tipo_de_empleador`
    (cesantía, oferta externa), se predice con los mismos dados que usará el motor: sus probabilidades son
    constantes del paquete, así que la predicción es exacta.
    """
    pq, e = vida.pq, vida.e
    opcion = next((o for o in vida.opciones(decision_id) if o.id == opcion_id), None)
    if opcion is None:
        return None
    for r in opcion.resultados:
        tipo, rubro, emplea = None, None, False
        for ef in r.get("efectos", []):
            v = str(ef.get("valor", ""))
            literal = v[1:-1] if v.startswith("'") and v.endswith("'") else None
            if ef["var"] == "tipo_empleador" and ef["op"] == "fija" and literal:
                tipo = literal
            elif ef["var"] == "rubro" and ef["op"] == "fija":
                rubro = literal if literal is not None else e.get(v) if v in e else None
            elif ef["var"] == "estado" and literal == "empleado":
                emplea = True
        if r.get("luego") == "tipo_de_empleador":
            tipo = _predecir_tipo(vida)
        elif tipo is None and emplea:
            tipo = e.get("tipo_empleador") or _predecir_tipo(vida)
        elif tipo is None and rubro is not None and e.get("estado") == "empleado":
            tipo = e.get("tipo_empleador")  # cambiar de rubro: mismo tipo, otra empresa
        if tipo:
            if tipo == "publico":
                rubro = PUBLICA
            elif rubro is None:
                rubro = rubro_actual(e)
            return tipo, rubro
    return None


def _predecir_tipo(vida) -> str | None:
    """El tipo que sortearía la decisión interna `tipo_de_empleador` en este año."""
    d = vida.pq.decisiones["tipo_de_empleador"]
    ocurrencia = sum(1 for x in (vida.registro or {}).get("decisiones", []) if x["decision"] == "tipo_de_empleador")
    opcion = d["opciones"][0]
    sitio = f"dec:tipo_de_empleador:{opcion['id']}" + (f":{ocurrencia}" if ocurrencia else "")
    resultado, _ = vida._sortear(opcion["resultados"], sitio, "tipo_de_empleador")
    if resultado is None:
        return None
    for ef in resultado["efectos"]:
        if ef["var"] == "tipo_empleador":
            return str(ef["valor"]).strip("'")
    return None


def origen_decision(decision_id: str, ocurrencia: int) -> str:
    """La misma oferta en todas las opciones de una decisión (cambiarte o pedir contraoferta)."""
    return f"{decision_id}:{ocurrencia}"


def ficha(pq: Paquete, emp: dict | None, car: dict | None) -> dict | None:
    """Lo que se muestra de una empresa: nombre, logo, cargo y sus cifras relativas al rubro."""
    if emp is None:
        return None
    return {
        "empresa_id": emp["empresa_id"], "nombre": emp["nombre"], "rubro": emp["rubro"], "tipo": emp["tipo"],
        "pais": emp.get("pais", ""), "dominio": emp.get("dominio", ""), "logo": emp["logo"], "origen": emp.get("origen", ""),
        "cargo_id": car["cargo_id"] if car else -1, "cargo": car["nombre"] if car else None,
        "cifras": {
            "sueldo": round(factor_sueldo(emp, car), 3), "despido": round(emp["mult_despido"], 3),
            "ascenso": round(emp["mult_ascenso"], 3), "cierre": round(emp["mult_cierre"], 3),
            "exposicion_ia": round(car["exposicion_ia"] if car else emp["exposicion_ia"], 3), "horas": int(emp["horas"]),
        },
        "calidad": "sintetico",
    }


def oferta(vida, decision_id: str, opcion_id: str, ocurrencia: int) -> dict | None:
    """La empresa y el cargo que trae una opción, calculados como los calculará el motor."""
    destino = _tipo_y_rubro(vida, decision_id, opcion_id)
    if destino is None:
        return None
    tipo, rubro = destino
    sitio = sitio_empresa(origen_decision(decision_id, ocurrencia))
    emp = sortear_empresa(vida.pq, vida.dados, vida.anio, sitio, tipo, rubro)
    car = sortear_cargo(vida.pq, vida.dados, vida.anio, sitio + ":cargo", emp, vida.e)
    return ficha(vida.pq, emp, car)


def universidades(pq: Paquete) -> list[dict]:
    """Instituciones del catálogo (para el perfil y los selectores)."""
    try:
        filas = pq.filas("universidades")
    except (KeyError, OSError):
        return []
    return [{"universidad_id": f["universidad_id"], "nombre": f["nombre"], "sigla": f.get("sigla", ""),
             "pais": f["pais"], "tipo_institucion": f["tipo_institucion"], "logo": f.get("logo") == "1",
             "selectiva": f.get("selectiva") == "1"} for f in filas]
