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
    familias: dict[tuple[str, str], list[str]] = {}
    try:
        for f in pq.filas("familias"):
            familias[(f["tipo"], f["clave"])] = [x.strip() for x in f["familias"].split("|") if x.strip()]
    except (KeyError, OSError):
        pass
    cat = {"empresas": empresas, "por_id": {x["empresa_id"]: x for x in empresas},
           "cargos": cargos, "cargo_por_id": {x["cargo_id"]: x for x in cargos}, "pools": {},
           "familias": familias}
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


def sortear_empresa(pq: Paquete, dados: Dados, anio: int, sitio: str, tipo: str, rubro: str | None,
                    e: dict | None = None) -> dict | None:
    """Una empresa del tipo y rubro, en proporción a `peso`. None si el catálogo no tiene ninguna.

    Con la persona (`e`), solo entre las empresas que tienen algún cargo de su línea de trabajo: así la
    oferta no le propone a un desarrollador ser periodista. Si ninguna tiene, cualquiera del tipo y rubro.
    """
    if tipo not in TIPOS:
        return None
    filas = pool(pq, tipo, PUBLICA if tipo == "publico" and rubro is None else rubro)
    if not filas and tipo in ("publico", "extranjero", "startup"):
        # servicios del Estado de cualquier rubro; remoto para afuera y startups: casi todo es tecnología,
        # así que si no hay en tu rubro se toma cualquiera y la persona pasa al rubro de esa empresa
        filas = pool(pq, tipo, None)
    if e is not None and filas:
        familias = set(familias_de(pq, e))
        de_su_linea = [x for x in filas if familias and any(c.get("familia") in familias for c in _duros(pq, x, e))]
        filas = de_su_linea or filas
    if not filas:
        return None
    return filas[dados.elegir(anio, sitio, [x["peso"] for x in filas])]


# Palabras que, en el cargo que escribió la persona, dicen su línea de trabajo aunque el catálogo no tenga
# ese nombre exacto ("Ingeniero de software" -> tecnología). Las genéricas (analista, jefe...) no deciden solas.
_PISTAS = {
    "software": "tecnologia", "programador": "tecnologia", "developer": "tecnologia", "desarrollador": "tecnologia",
    "informatico": "tecnologia", "sistemas": "tecnologia", "devops": "tecnologia", "frontend": "tecnologia",
    "backend": "tecnologia", "fullstack": "tecnologia", "datos": "datos", "data": "datos", "marketing": "marketing_comunicaciones",
    "ventas": "comercial_ventas", "comercial": "comercial_ventas", "contador": "finanzas", "finanzas": "finanzas",
    "financiero": "finanzas", "abogado": "legal", "abogada": "legal", "rrhh": "personas_rrhh", "personas": "personas_rrhh",
    "profesor": "educacion", "profesora": "educacion", "docente": "educacion", "enfermero": "salud", "enfermera": "salud",
    "medico": "salud", "medica": "salud", "disenador": "diseno_arte", "disenadora": "diseno_arte", "ux": "diseno_arte",
}
_GENERICAS = {"analista", "jefe", "jefa", "gerente", "ingeniero", "ingeniera", "supervisor", "asistente", "ejecutivo",
              "ejecutiva", "tecnico", "tecnica", "encargado", "encargada", "administrador", "senior", "junior", "semi",
              "lider", "lead", "coordinador", "coordinadora", "especialista", "de", "del", "la", "el", "en", "y"}


def _palabras(texto: str) -> set[str]:
    import unicodedata

    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return {p for p in "".join(c if c.isalnum() else " " for c in texto).split() if p}


def familia_por_nombre(pq: Paquete, nombre: str | None) -> str | None:
    """La familia del cargo que escribió la persona: por una palabra clave o por el cargo del catálogo que
    más palabras propias comparte con el suyo. None si no se reconoce."""
    palabras = _palabras(nombre or "")
    for p in palabras:
        if p in _PISTAS:
            return _PISTAS[p]
    propias = palabras - _GENERICAS
    mejor, puntos = None, 0
    for c in _catalogo(pq)["cargos"]:
        n = len(propias & (_palabras(c["nombre"]) - _GENERICAS))
        if n > puntos and c.get("familia"):
            mejor, puntos = c["familia"], n
    return mejor


def familias_de(pq: Paquete, e: dict) -> list[str]:
    """La línea de trabajo de la persona, de lo más seguro a lo menos: la familia de su cargo del catálogo
    (el actual o el último que tuvo); el cargo que escribió; las afines a su carrera; y sin nada de eso, las
    dos más comunes de su rubro (tabla `familias`, cruce curado). El rubro solo no alcanza: en él trabaja
    gente de casi todas las líneas."""
    car = cargo(pq, e.get("cargo_id", -1))
    if car is not None and car.get("familia"):
        return [car["familia"]]
    if e.get("bootcamp"):
        return list(FAMILIAS_BOOTCAMP)  # recién salido del bootcamp: entra a tecnología
    if e.get("familia_inicial"):
        return [e["familia_inicial"]]
    fam = _catalogo(pq)["familias"]
    if e.get("area"):
        return fam.get(("area", e["area"]), [])
    if e.get("rubro"):
        return fam.get(("rubro", e["rubro"]), [])[:2]
    return []


def _duros(pq: Paquete, emp: dict, e: dict) -> list[dict]:
    """Cargos que la empresa podría ofrecerle: tipo y rubro de la empresa, nivel actual y educación mínima."""
    nivel, edu = int(e.get("nivel", 0)), EDU_ORDEN.get(e.get("edu", "media"), 0)
    return [c for c in _catalogo(pq)["cargos"]
            if (c["_tipos"] is None or emp["tipo"] in c["_tipos"])
            and (c["_rubros"] is None or emp["rubro"] in c["_rubros"])
            and c["nivel_min"] <= nivel <= c["nivel_max"]
            and (EDU_ORDEN.get(c["edu_min"], 0) <= edu or _por_bootcamp(c, e)) and c["peso"] > 0]


FAMILIAS_BOOTCAMP = ("tecnologia", "datos")


def _por_bootcamp(c: dict, e: dict) -> bool:
    """Un bootcamp abre los cargos de tecnología y datos que piden título técnico, aunque no lo tengas."""
    return bool(e.get("bootcamp")) and c.get("familia") in FAMILIAS_BOOTCAMP and EDU_ORDEN.get(c["edu_min"], 0) <= 1


def ocupacion_tipica(pq: Paquete, rubro: str, edu: str, nivel: int, area: str = "") -> int | None:
    """El oficio (CIUO a 1 dígito) más probable de quien trabaja en ese rubro con esa educación y ese nivel.

    Recorre las líneas de trabajo de su carrera (si se sabe) y luego las de su rubro, en el orden de la tabla
    `familias`, y toma del catálogo un cargo que podría tener (rubro, educación, nivel y, en las profesiones de
    una sola carrera, que sea la suya): entre los que piden la educación más cercana a la suya, el oficio que
    suma más peso. None si nada calza.
    """
    cat = _catalogo(pq)
    familias = (cat["familias"].get(("area", area), []) if area else []) + cat["familias"].get(("rubro", rubro), [])
    nivel_edu = EDU_ORDEN.get(edu, 0)
    respaldo = None  # la primera línea con algo, si ninguna pide una educación cercana a la suya
    for familia in familias:
        posibles = [c for c in cat["cargos"]
                    if c.get("familia") == familia and c["peso"] > 0
                    and (c["_rubros"] is None or rubro in c["_rubros"])
                    and EDU_ORDEN.get(c["edu_min"], 0) <= nivel_edu and c["nivel_min"] <= nivel <= c["nivel_max"]
                    and not (c["_areas"] is not None and len(c["_areas"]) == 1 and area not in c["_areas"])]
        if posibles:
            # los cargos que piden la educación más cercana a la suya (un universitario no queda de peoneta), y de
            # ellos el oficio que suma más peso (albañil, electricista y soldador son todos operarios, CIUO 7)
            tope = max(EDU_ORDEN.get(c["edu_min"], 0) for c in posibles)
            por_oficio: dict[int, float] = {}
            for c in posibles:
                if EDU_ORDEN.get(c["edu_min"], 0) == tope:
                    por_oficio[int(c["ciuo08_1d"])] = por_oficio.get(int(c["ciuo08_1d"]), 0.0) + c["peso"]
            oficio = max(por_oficio, key=por_oficio.get)
            if tope >= nivel_edu - 1:  # un universitario en hotelería no queda de camarera si el rubro tiene más
                return oficio
            respaldo = oficio if respaldo is None else respaldo
    return respaldo


def compatibles(pq: Paquete, emp: dict, e: dict) -> list[dict]:
    """Cargos que la empresa le ofrecería a esta persona.

    Duro: tipo y rubro de la empresa, nivel actual, educación mínima, su grupo ocupacional de hoy (un cambio de
    trabajo no te cambia de oficio: eso lo hacen "cambiar de oficio" o un bootcamp, que mueven la ocupación
    antes) y las profesiones de una sola carrera (no se le ofrece "Abogado" a quien no estudió Derecho).
    Blando, en este orden: su familia (finanzas, tecnología, salud...) y el área de su carrera. Si nada calza,
    no hay cargo y la historia dice "un cargo parecido al tuyo".
    """
    area, ocup = e.get("area") or "", int(e.get("ocupacion", -1))

    def profesion_ajena(c):  # el cargo pide una sola carrera y no es la tuya (un bootcamp abre los de tecnología)
        return (c["_areas"] is not None and len(c["_areas"]) == 1 and area not in c["_areas"]
                and not _por_bootcamp(c, e))

    todos = [c for c in _duros(pq, emp, e) if not profesion_ajena(c)]
    duros = [c for c in todos if ocup < 0 or c["ciuo08_1d"] == ocup]
    familias = set(familias_de(pq, e))

    def del_area(c):
        return c["_areas"] is None or (area and area in c["_areas"])

    de_su_familia = (lambda c: c.get("familia") in familias and del_area(c), lambda c: c.get("familia") in familias)
    tandas = [(duros, f) for f in de_su_familia]
    if familia_propia(pq, e):
        # Su línea de trabajo sale de su propio cargo (el que escribió o uno del catálogo). Si ningún cargo de esa
        # línea tiene su grupo ocupacional, el grupo se infirió mal (sin dato, `ocupacion_por_omision` lo saca del
        # rubro: una analista de datos en Comercio queda en CIUO 3) y pesa más su cargo: se le ofrece uno de su
        # línea antes que uno de otra (a esa analista le ofrecían "Asistente de gerencia").
        tandas += [(todos, f) for f in de_su_familia]
    tandas += [(duros, del_area), (duros, lambda c: True)]
    for grupo, filtro in tandas:
        quedan = [c for c in grupo if filtro(c)]
        if quedan:
            return quedan
    return []


def familia_propia(pq: Paquete, e: dict) -> bool:
    """Si la línea de trabajo de la persona sale de su cargo (del catálogo o el que escribió) y no solo de su
    carrera o de su rubro."""
    car = cargo(pq, e.get("cargo_id", -1))
    return bool((car is not None and car.get("familia")) or e.get("familia_inicial"))


def sortear_cargo(pq: Paquete, dados: Dados, anio: int, sitio: str, emp: dict | None, e: dict,
                  otro_que_el_actual: bool = False) -> dict | None:
    """Un cargo compatible, en proporción a `peso`. Con `otro_que_el_actual`, sin el cargo que ya tiene (si
    queda alguno)."""
    if emp is None:
        return None
    filas = compatibles(pq, emp, e)
    if otro_que_el_actual:
        filas = [c for c in filas if c["cargo_id"] != e.get("cargo_id", -1)] or filas
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


def rubro_publico(pq: Paquete, e: dict) -> str:
    """En qué sector del Estado se busca el empleador (un hospital público si vienes de salud).

    La persona queda con rubro Administración pública, como define el paquete; esto solo elige la empresa.
    En orden: el sector de la empresa pública donde está, su rubro si no es Administración pública, y el
    rubro típico de su familia de cargo o de carrera. Si el catálogo no tiene empleadores públicos ahí,
    Administración pública.
    """
    emp = empresa(pq, e.get("empresa_id", -1))
    if emp is not None and emp["tipo"] == "publico" and pool(pq, "publico", emp["rubro"]):
        return emp["rubro"]
    rubro = e.get("rubro") or ""
    if rubro and rubro != PUBLICA and pool(pq, "publico", rubro):
        return rubro
    fam = _catalogo(pq)["familias"]
    for familia in familias_de(pq, e):
        for (tipo, clave), lista in fam.items():
            if tipo == "rubro" and lista and lista[0] == familia and pool(pq, "publico", clave):
                return clave
    return PUBLICA


def sitio_empresa(origen: str) -> str:
    return f"empresa:{origen}"


def _tipo_y_rubro(vida, decision_id: str, opcion_id: str) -> tuple[str, str | None] | None:
    """Con qué tipo de empleador y rubro termina la opción si sale bien; None si no lleva a un empleador.

    Se lee del resultado principal (el primero): "Usarla para negociar" no trae la empresa, aunque uno de
    sus resultados sea irte a ella. Si el resultado sigue en `tipo_de_empleador`
    (cesantía, oferta externa), se predice con los mismos dados que usará el motor: sus probabilidades son
    constantes del paquete, así que la predicción es exacta.
    """
    pq, e = vida.pq, vida.e
    opcion = next((o for o in vida.opciones(decision_id) if o.id == opcion_id), None)
    if opcion is None:
        return None
    for r in opcion.resultados[:1]:
        tipo, rubro, emplea = None, None, False
        for ef in r.get("efectos", []):
            v = str(ef.get("valor", ""))
            literal = v[1:-1] if v.startswith("'") and v.endswith("'") else None
            if ef["var"] == "tipo_empleador" and ef["op"] == "fija" and literal:
                tipo = literal
            elif ef["var"] == "tipo_empleador" and ef["op"] == "fija" and e.get(v):
                tipo = e[v]  # el de una oferta ya sorteada (oferta_tipo_empleador)
            elif ef["var"] == "rubro" and ef["op"] == "fija":
                rubro = literal if literal is not None else e.get(v) if v in e else None
            elif ef["var"] == "estado" and literal == "empleado":
                emplea = True
            elif ef["var"] == "estado" and literal in ("fundador", "independiente"):
                return None  # tu empresa o por tu cuenta: nadie te contrata
        if r.get("luego") == "tipo_de_empleador":
            tipo = _predecir_tipo(vida)
        elif tipo is None and emplea:
            tipo = e.get("tipo_empleador") or _predecir_tipo(vida)
        elif tipo is None and rubro is not None and e.get("estado") == "empleado":
            tipo = e.get("tipo_empleador")  # cambiar de rubro: mismo tipo, otra empresa
        if tipo:
            if tipo == "publico":
                rubro = rubro_publico(pq, e)
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


# Decisiones que tratan de una sola oferta: todas sus opciones hablan de la misma empresa (cambiarte o
# usarla para negociar). En las demás, cada opción es otra búsqueda y trae su propia empresa: en la
# cesantía, "esperar algo de tu nivel" no es la misma pega que "tomar lo primero que salga".
DECISIONES_CON_OFERTA = frozenset({"oferta_externa", "unirse_a_startup", "remoto_para_afuera", "emigrar",
                                   "oferta_en_cesantia"})  # la oferta que llega estando cesante: una sola empresa


def origen_decision(decision_id: str, ocurrencia: int, opcion_id: str = "") -> str:
    """De dónde sale el empleador que trae una opción: uno por decisión si es una sola oferta, uno por opción si no."""
    if decision_id in DECISIONES_CON_OFERTA or not opcion_id:
        return f"{decision_id}:{ocurrencia}"
    return f"{decision_id}:{opcion_id}:{ocurrencia}"


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
    sitio = sitio_empresa(origen_decision(decision_id, ocurrencia, opcion_id))
    emp = sortear_empresa(vida.pq, vida.dados, vida.anio, sitio, tipo, rubro, vida.e)
    # quien tiene trabajo no recibe una oferta para el mismo cargo que ya tiene (le llegaba "Asistente de
    # gerencia" otra vez, en otra empresa y pagando menos); cesante, el mismo cargo es justo lo que busca
    car = sortear_cargo(vida.pq, vida.dados, vida.anio, sitio + ":cargo", emp, vida.e,
                        otro_que_el_actual=vida.e.get("estado") == "empleado")
    return ficha(vida.pq, emp, car)


def _normal(texto: str) -> str:
    """'Walmart Chile (Lider)' -> 'walmartchile'; sin tildes, mayúsculas ni signos."""
    import unicodedata

    texto = unicodedata.normalize("NFKD", texto.split("(")[0]).encode("ascii", "ignore").decode()
    return "".join(c for c in texto.lower() if c.isalnum())


def buscar(pq: Paquete, nombre: str | None) -> dict | None:
    """La empresa del catálogo con ese nombre (o con el que va entre paréntesis), para mostrar su logo."""
    if not nombre or len(nombre.strip()) < 2:
        return None
    buscado = _normal(nombre)
    for emp in _catalogo(pq)["empresas"]:
        alias = {_normal(emp["nombre"])}
        if "(" in emp["nombre"]:
            alias.add(_normal(emp["nombre"].split("(", 1)[1].rstrip(")")))
        if buscado in alias:
            return emp
    return None


def universidades(pq: Paquete) -> list[dict]:
    """Instituciones del catálogo (para el perfil y los selectores)."""
    try:
        filas = pq.filas("universidades")
    except (KeyError, OSError):
        return []
    return [{"universidad_id": f["universidad_id"], "nombre": f["nombre"], "sigla": f.get("sigla", ""),
             "pais": f["pais"], "tipo_institucion": f["tipo_institucion"], "logo": f.get("logo") == "1",
             "selectiva": f.get("selectiva") == "1"} for f in filas]
