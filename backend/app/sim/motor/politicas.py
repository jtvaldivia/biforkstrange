"""Quién decide en una vida.

- `Jugador`: responde con una lista de elecciones; cuando se acaba, la vida se detiene.
- `Inercia`: los gemelos después de una carta. No reciben cartas ("si después de
  esto no haces nada especial"), pero cuando la vida los obliga a elegir (quedan
  cesantes, les llega una oferta) responden como la gente suele responder.
- `Poblacion`: además recibe cartas y las responde con la frecuencia con que la
  gente toma esas decisiones. Es la cohorte de validación.
- `Fija`: toma una opción dada en la primera decisión y después delega.

Los pesos son supuestos del equipo, calibrados contra las frecuencias de las
encuestas (ver `validacion.py`); no son datos.
"""

from app.sim.motor.motor import TRANQUILO, FaltaEleccion, Opcion, Vida
from app.sim.motor.paquete import ref as referencia

# Respuesta cuando la vida obliga a elegir: {decisión: {opción: peso}}
PESOS_FORZADAS: dict[str, dict[str, float]] = {
    "salir_del_colegio": {"universidad": 0.36, "instituto": 0.10, "cft": 0.07, "trabajar": 0.43, "pausa": 0.04},
    "financiar_estudios": {"gratuidad": 0.55, "cae": 0.25, "familia": 0.20},
    "seguir_o_desertar": {"seguir": 0.90, "cambiarse": 0.04, "dejar": 0.06},
    "primera_pega": {"grande": 0.32, "pyme": 0.47, "startup": 0.02, "estado": 0.12, "independiente": 0.05, "emprender": 0.02},
    # buscar junta a quienes antes tomaban lo primero (0,48) o esperaban algo de su nivel (0,40): ahora eso
    # sale de qué ofertas aceptan mes a mes (`acepta_oferta_cesante`)
    "cesantia": {"buscar": 0.88, "informal": 0.09, "bootcamp": 0.01, "emprender": 0.02},
    "oferta_externa": {"cambiar": 0.34, "contraoferta": 0.09, "quedarse": 0.57},
    "seguir_con_tu_empresa": {"seguir": 0.86, "levantar": 0.04, "vender": 0.05, "cerrar": 0.05},
    "licencia_salud_mental": {"pedir": 0.70, "seguir": 0.30},
}
# Respuesta a las cartas: la opción que no aparece aquí pesa lo que sobra (no hacer nada).
PESOS_CARTAS: dict[str, dict[str, float]] = {
    "trabajar_mientras_estudias": {"si": 0.40},
    "practica": {"tomar": 0.70},
    "intercambio": {"ir": 0.08},
    "magister": {"beca": 0.08, "vespertino": 0.20},
    "doctorado": {"ir": 0.03},
    "bootcamp": {"hacer": 0.08},
    "volver_a_estudiar": {"estudiar": 0.10},
    "buscar_estando_empleado": {"buscar": 0.30},
    "renunciar": {"renunciar": 0.50},
    "pedir_aumento": {"pedir": 0.70},
    "trabajar_mas_horas": {"si": 0.25},
    "jefatura": {"aceptar": 0.75},
    "remoto_para_afuera": {"postular": 0.10},
    "pedir_hibrido": {"pedir": 0.40},
    "media_jornada": {"pedir": 0.12},
    "cambiar_de_rubro": {"cambiar": 0.15},
    "cambiar_de_ocupacion": {"cambiar": 0.15},
    # con la incertidumbre de IA prendida aprender_ia trae curso corto y programa largo en vez de aprender (ia.py)
    "aprender_ia": {"aprender": 0.45, "curso_corto": 0.35, "programa_largo": 0.10},
    # tu empresa adopta IA: NY Fed (2026) ve que más de un tercio de las empresas recapacita a su gente; el
    # reparto es supuesto del equipo
    "liderar_adopcion_ia": {"liderar": 0.15, "aprender": 0.45, "buscar": 0.05},
    "invertir_en_red": {"si": 0.35},
    "unirse_a_startup": {"ir": 0.25},
    "independizarse": {"formal": 0.30},
    "volver_a_contrato": {"buscar": 0.40},  # supuesto: más que buscar estando empleado (0,30), por el ingreso flojo
    "emprender": {"emprender": 0.08, "lado": 0.12},
    "emigrar": {"irse": 0.04},
    "mudarse_de_region": {"a_santiago": 0.08, "a_region": 0.05},
    "volver_a_chile": {"volver": 0.15},
    "sabatico": {"irse": 0.05},
}
# Cuántos años dura una pega en Chile, en la mediana (supuesto del equipo, en línea con la EPS)
ANOS_POR_EMPLEO_TIPICO = 3.0


# Cuánto peso suma cada rasgo de tu historia a la opción que se le parece cuando quedas cesante
# (supuestos del equipo, sin dato detrás: la dirección sale del CV, el tamaño es nuestro).
CESANTIA_POR_HISTORIA = {
    "volvio_a_su_nivel": ("buscar", 0.15),     # ya esperó más de 6 meses y volvió a un cargo igual o mayor
    "freelance_entre_pegas": ("informal", 0.12),  # ya hizo boletas entre una pega y otra
    "emprendio_antes": ("emprender", 0.06),    # ya tuvo una empresa propia
}
# Dónde hizo la práctica, y cuánto peso suma a buscar la primera pega en ese tipo de empleador (supuesto)
PRIMERA_PEGA_POR_PRACTICA = {"grande": ("grande", 0.13), "publico": ("estado", 0.10)}
# Quien ya cerró empresas sabe cerrar: +0,05 a "cerrar" por cada una, hasta +0,15 (supuesto del equipo)
CERRAR_POR_EMPRESA_CERRADA, CERRAR_MAX = 0.05, 0.15


def _mover(pesos: dict[str, float], opcion: str, cuanto: float) -> dict[str, float]:
    """Suma `cuanto` a una opción y se lo quita a las demás en proporción a su peso (siguen sumando 1)."""
    resto = sum(p for o, p in pesos.items() if o != opcion)
    cuanto = min(cuanto, resto)
    return {o: round(p + cuanto if o == opcion else p * (1 - cuanto / resto), 4) for o, p in pesos.items()}


def pesos_personales(e: dict) -> dict[str, dict[str, float]]:
    """Los gemelos se parecen a ti: responden a lo que la vida les pone delante como tú ya respondiste.

    Cada rasgo viene del CV y pasa por el estado (`perfil.HISTORIA`); sin él quedan los pesos de la
    población, exactamente. Supuestos del equipo:
    - oferta_externa: la probabilidad de cambiarse escala con 3 años / tus años por pega, entre la mitad
      y 1,8 veces.
    - cesantia: cada rasgo de `CESANTIA_POR_HISTORIA` suma peso a la opción que se le parece.
    - primera_pega: una práctica en una empresa grande o en el Estado suma peso a postular ahí
      (`practica` solo llega al estado de quien estudia o busca su primer empleo).
    - seguir_con_tu_empresa: cada empresa que ya cerró suma peso a cerrar la de ahora.
    """
    salida: dict[str, dict[str, float]] = {}
    anos = e.get("anos_por_empleo")
    if anos:
        base = PESOS_FORZADAS["oferta_externa"]
        cambiar = min(0.65, max(0.15, base["cambiar"] * min(1.8, max(0.5, ANOS_POR_EMPLEO_TIPICO / anos))))
        salida["oferta_externa"] = {"cambiar": round(cambiar, 3), "contraoferta": base["contraoferta"],
                                    "quedarse": round(1 - cambiar - base["contraoferta"], 3)}
    cesantia = PESOS_FORZADAS["cesantia"]
    for rasgo, (opcion, cuanto) in CESANTIA_POR_HISTORIA.items():
        if e.get(rasgo):
            cesantia = _mover(cesantia, opcion, cuanto)
    if cesantia is not PESOS_FORZADAS["cesantia"]:
        salida["cesantia"] = cesantia
    if e.get("practica") in PRIMERA_PEGA_POR_PRACTICA:
        opcion, cuanto = PRIMERA_PEGA_POR_PRACTICA[e["practica"]]
        salida["primera_pega"] = _mover(PESOS_FORZADAS["primera_pega"], opcion, cuanto)
    if e.get("empresas_cerradas"):
        cuanto = min(CERRAR_MAX, CERRAR_POR_EMPRESA_CERRADA * e["empresas_cerradas"])
        salida["seguir_con_tu_empresa"] = _mover(PESOS_FORZADAS["seguir_con_tu_empresa"], "cerrar", cuanto)
    return salida


# Opción que equivale a no hacer nada, donde no es la última de la lista
STATU_QUO = {"oferta_externa": "quedarse", "liderar_adopcion_ia": "seguir"}
# Respuesta a una decisión que llega encadenada (`luego`) desde una opción que ya la eligió: quien,
# cesante, elige "reconvertirte con un bootcamp" se inscribe ("Te inscribes"); no vuelve a dudar. Sin esto
# los gemelos respondían la carta bootcamp con su peso de carta (Inercia: siempre "no").
PESOS_ENCADENADAS: dict[str, dict[str, float]] = {"bootcamp": {"hacer": 1.0}}


def acepta_oferta_cesante(vida: Vida) -> bool:
    """La regla fija con que las copias responden una oferta estando cesantes (paquete: oferta_en_cesantia).
    Aceptan si paga al menos GEMELO_UMBRAL_OFERTA de lo que ganaban, o cualquiera desde el mes GEMELO_MES_ACEPTA_TODO.
    Con esta regla se calibró K_OFERTA_CESANTE para que la búsqueda dure lo que mide la EPS."""
    e, pq = vida.e, vida.pq
    return (e["oferta_sueldo"] >= pq.k("GEMELO_UMBRAL_OFERTA") * e["sueldo_ref"]
            or e["meses_cesante"] + 1 >= pq.k("GEMELO_MES_ACEPTA_TODO"))


def _llega_encadenada(vida: Vida, decision_id: str) -> bool:
    """Si la decisión que se está respondiendo llegó por el `luego` de otra (es el primer paso de la cola)."""
    return bool(vida.cola) and vida.cola[0] == ("decision", decision_id, "luego")


def opcion_base(decision: dict, opciones: list[Opcion]) -> str:
    """Contra qué se compara: no hacer nada; en las forzadas, lo que la gente hace más seguido."""
    id_ = decision["id"]
    disponibles = {o.id for o in opciones}
    if STATU_QUO.get(id_) in disponibles:
        return STATU_QUO[id_]
    if decision["aparicion"]["tipo"] == "forzada" and id_ in PESOS_FORZADAS:
        candidatas = {o: p for o, p in PESOS_FORZADAS[id_].items() if o in disponibles}
        if candidatas:
            return max(candidatas, key=candidatas.get)
    return opciones[-1].id


def _pesos(decision: dict, opciones: list[Opcion], tabla: dict[str, dict[str, float]]) -> list[float]:
    dados = tabla.get(decision["id"], {})
    quieto = STATU_QUO.get(decision["id"], opciones[-1].id)
    activos = sum(p for o, p in dados.items() if o != quieto and any(x.id == o for x in opciones))
    return [dados[o.id] if o.id in dados and o.id != quieto else (max(0.0, 1 - activos) if o.id == quieto else 0.0)
            for o in opciones]


def elecciones_internas(vida: Vida, opcion: Opcion) -> list[dict]:
    """Lo que hay que elegir dentro de una opción (a qué rubro, a qué ocupación), con sus alternativas."""
    pq, e = vida.pq, vida.e
    usadas = _variables_usadas(opcion)
    if not usadas & {"rubro_destino", "rubro_emprendimiento", "ocupacion_destino", "region_destino", "universidad_destino", "institucion_destino"}:
        return []
    salida = []
    if "rubro_destino" in usadas:
        # peso: cuánta gente ocupada hay en cada rubro (ESI)
        filas = {f["rubro"]: f for f in pq.filas("esi_ingreso_rubro_edad") if f["banda_edad"] == "18-54"}
        salida.append({"variable": "rubro_destino", "pregunta": "¿A qué rubro?", "alternativas": [
            {"valor": r, "nombre": r, "prob": float(filas[r]["share_ocupados_banda"] or 0) if r in filas else 0.0,
             # la carta pregunta por "un rubro que paga más": por defecto, el de mayor sueldo mediano,
             # salvo que la persona haya contado a qué rubro se cambiaría
             "preferencia": (1e12 if r == e.get("rubro_sonado") else
                             float(filas[r]["p50"] or 0) if r in filas else 0.0)}
            for r in pq.variables["rubro"]["dominio"] if r and r != e["rubro"]]})
    if "rubro_emprendimiento" in usadas:
        # peso: cuánta gente ocupada hay en cada rubro (ESI). Por defecto, el rubro de su proyecto según su
        # Claude; si no, el que soñó; si no, el suyo de hoy
        filas = {f["rubro"]: f for f in pq.filas("esi_ingreso_rubro_edad") if f["banda_edad"] == "18-54"}
        orden = [r for r in (e.get("rubro_proyecto"), e.get("rubro_sonado"), e["rubro"]) if r]
        salida.append({"variable": "rubro_emprendimiento", "pregunta": "¿De qué rubro es tu empresa?", "alternativas": [
            {"valor": r, "nombre": r, "prob": float(filas[r]["share_ocupados_banda"] or 0) if r in filas else 0.0,
             "preferencia": 1e12 * (len(orden) - orden.index(r)) if r in orden else 0.0}
            for r in pq.variables["rubro"]["dominio"] if r]})
    if "ocupacion_destino" in usadas:
        nombres = {int(f["origen"]): f["origen_nombre"] for f in pq.filas("jobhop_transiciones")}
        salida.append({"variable": "ocupacion_destino", "pregunta": "¿A qué tipo de trabajo?", "alternativas": [
            {"valor": d, "nombre": nombres[d],
             "prob": pq.tabla("jobhop_transiciones", "prob", "origen", e["ocupacion"], "destino", d)}
            for d in range(1, 10) if d != e["ocupacion"]]})
    if "region_destino" in usadas:
        # peso: parte de los ocupados del país que trabaja en cada región (ESI)
        gente = {f["region"]: float(f["share_nacional"] or 0) for f in pq.filas("esi_ingreso_region")
                 if f["educacion"] == "todas" and f["region"] not in ("Metropolitana", "Nacional")}
        salida.append({"variable": "region_destino", "pregunta": "¿A qué región?", "alternativas": [
            {"valor": r, "nombre": r, "prob": p} for r, p in sorted(gente.items())]})
    if "universidad_destino" in usadas:
        # peso: cuántos magísteres vigentes tiene cada universidad (SIES 2026); las extranjeras, el peso
        # chico y sintético de universidades.peso_magister (en la misma escala de programas)
        alternativas = [
            {"valor": f["universidad_id"], "nombre": _universidad(f), "prob": float(f["programas"]),
             "selectiva": f["selectiva"] == "1", "arancel_anual": float(f["arancel_anual"]), "anios": float(f["anios"]),
             "pais": "Chile"}
            for f in pq.filas("sies_magister_2026")]
        usd = pq.k("USD")
        alternativas += [
            {"valor": f["universidad_id"], "nombre": f"{f['sigla'] or f['nombre']} ({f['pais']})",
             "prob": float(f.get("peso_magister") or 0), "selectiva": True,
             "arancel_anual": round(float(f.get("arancel_magister_usd") or 0) * usd), "anios": float(f.get("anios_magister") or 1),
             "pais": f["pais"], "calidad": "sintetico"}
            for f in _universidades(pq) if f["tipo_institucion"] == "EXT"]
        salida.append({"variable": "universidad_destino", "pregunta": "¿En qué universidad?", "alternativas": alternativas})
    if "institucion_destino" in usadas:
        # peso: matrícula de pregrado de cada institución (SIES); solo chilenas y del tipo de la opción
        tipo = _tipo_institucion(opcion)
        alternativas = [
            {"valor": f["universidad_id"], "nombre": f["sigla"] or f["nombre"], "prob": float(f.get("matricula") or 0),
             "selectiva": f.get("selectiva") == "1", "arancel_anual": float(f.get("arancel_anual_pregrado") or 0)}
            for f in _universidades(pq)
            if f["tipo_institucion"] != "EXT" and (tipo is None or f["tipo_institucion"] == tipo)
            and float(f.get("matricula") or 0) > 0]
        if alternativas:
            salida.append({"variable": "institucion_destino", "pregunta": "¿Dónde estudias?", "alternativas": alternativas})
    return salida


def _universidades(pq) -> list[dict]:
    try:
        return pq.filas("universidades")
    except (KeyError, OSError):
        return []


def _tipo_institucion(opcion: Opcion) -> str | None:
    """U, IP o CFT: lo que fija la opción en tipo_institucion."""
    for r in opcion.resultados:
        for ef in r.get("efectos", []):
            if ef["var"] == "tipo_institucion" and ef["op"] == "fija":
                return str(ef["valor"]).strip("'")
    return None


def _universidad(f: dict) -> str:
    """Nombre corto para el selector: sigla o nombre, arancel y si es selectiva.

    El arancel dice que es arancel y va en millones, escrito como los textos del paquete ("$9 millones"): al lado de los sueldos de la carta, "$8.546.030 al año"
    se leía como lo que ibas a ganar."""
    nombre = f["sigla"] or f["universidad"].replace("Universidad ", "U. ")
    millones = f"{float(f['arancel_anual']) / 1e6:.1f}".replace(".", ",")
    return f"{nombre} · arancel ${millones} millones al año" + (" · selectiva" if f["selectiva"] == "1" else "")


_USADAS: dict[int, frozenset[str]] = {}


def _variables_usadas(opcion: Opcion) -> frozenset[str]:
    """Variables que leen las fórmulas de una opción (se calcula una vez: la lista viene del paquete)."""
    clave = id(opcion.resultados)
    if clave not in _USADAS:
        usadas: set[str] = set()
        for r in opcion.resultados:
            for ef in r["efectos"]:
                for expr in (ef["valor"], ef.get("cuando"), r["prob"]):
                    if isinstance(expr, str) and expr != "resto":
                        usadas |= referencia.nombres(referencia.parsear(expr))
        _USADAS[clave] = frozenset(usadas)
    return _USADAS[clave]


def parametros_por_defecto(vida: Vida, opcion: Opcion) -> dict:
    """Si la persona aún no eligió dentro de la opción: la alternativa donde hay más gente
    (en rubro, la que mejor paga, porque la carta pregunta por un rubro que paga más)."""
    salida = {}
    for el in elecciones_internas(vida, opcion):
        alternativas = el["alternativas"]
        salida[el["variable"]] = max(alternativas, key=lambda a: a.get("preferencia", a.get("prob", 0)))["valor"]
    return salida


def parametros_al_azar(vida: Vida, opcion: Opcion, sitio: str) -> dict:
    """Lo que un gemelo elige dentro de la opción: en proporción a dónde hay o va más gente."""
    salida = {}
    for el in elecciones_internas(vida, opcion):
        alternativas = el["alternativas"]
        pesos = [a.get("prob", 1.0) for a in alternativas]
        salida[el["variable"]] = alternativas[vida.dados.elegir(vida.anio, f"{sitio}:{el['variable']}", pesos)]["valor"]
    return salida


class _PorPesos:
    con_cartas = False
    tablas: tuple[dict, ...] = (PESOS_FORZADAS,)

    def __init__(self, pesos: dict[str, dict[str, float]] | None = None):
        self.pesos = pesos or {}

    def elegir(self, vida: Vida, decision: dict, opciones: list[Opcion]) -> tuple[str, dict]:
        id_ = decision["id"]
        if id_ == TRANQUILO:
            # como la gente real: considera lo que suele buscar alguien como él, y esa decisión la responde con sus pesos
            return (vida.sugerida if any(o.id == vida.sugerida for o in opciones) else "seguir"), {}
        if id_ == "oferta_en_cesantia" and {o.id for o in opciones} >= {"aceptar", "rechazar"}:
            return ("aceptar" if acepta_oferta_cesante(vida) else "rechazar"), {}
        ocurrencia = sum(1 for x in (vida.registro or {}).get("decisiones", []) if x["decision"] == id_)
        sitio = f"elige:{id_}" + (f":{ocurrencia}" if ocurrencia else "")
        if decision.get("opciones_desde_tabla") and not decision["opciones"]:
            pesos = [1.0] * len(opciones)  # carrera: al azar entre las de su tipo de institución
        elif id_ in PESOS_ENCADENADAS and _llega_encadenada(vida, id_):
            pesos = _pesos(decision, opciones, PESOS_ENCADENADAS)
        else:
            tabla = next((t for t in (self.pesos, *self.tablas) if id_ in t), {})
            pesos = _pesos(decision, opciones, {id_: tabla.get(id_, {})})
        if id_ == "oferta_externa":
            # la gente ve el sueldo de la oferta antes de decidir: acepta más seguido la que paga más
            # la chance de aceptar sube exactamente ACEPTA_SI_PAGA_MAS veces (no el peso, que compite con las demás)
            for i, o in enumerate(opciones):
                if o.id == "cambiar" and vida.resultado_previsto(id_, "cambiar") == "mejora":
                    total = sum(pesos)
                    a = pesos[i] / total if total > 0 else 0.0
                    q = min(0.95, a * vida.pq.k("ACEPTA_SI_PAGA_MAS"))
                    if 0 < a < 1:
                        pesos[i] = q * (total - pesos[i]) / (1 - q)
        opcion = opciones[vida.dados.elegir(vida.anio, sitio, pesos)]
        return opcion.id, parametros_al_azar(vida, opcion, sitio)


class Inercia(_PorPesos):
    """No busca cambios; responde a lo que la vida le pone delante."""


class Poblacion(_PorPesos):
    """Recibe cartas y decide con la frecuencia de la población."""

    con_cartas = True
    tablas = (PESOS_FORZADAS, PESOS_CARTAS)


class Fija:
    """Toma `opcion` en la primera decisión `decision_id` que le toque y después delega."""

    def __init__(self, decision_id: str, opcion: str, parametros: dict | None = None, despues=None):
        self.decision_id, self.opcion, self.parametros = decision_id, opcion, parametros or {}
        self.despues = despues or Inercia()
        self.usada = False

    @property
    def con_cartas(self) -> bool:
        return self.despues.con_cartas

    def elegir(self, vida: Vida, decision: dict, opciones: list[Opcion]) -> tuple[str, dict]:
        if not self.usada and decision["id"] == self.decision_id:
            self.usada = True
            return self.opcion, self.parametros
        return self.despues.elegir(vida, decision, opciones)


class Jugador:
    """Responde en orden con las elecciones que ya tomó la persona."""

    con_cartas = True

    def __init__(self, elecciones: list[dict]):
        self.elecciones = list(elecciones)
        self.usadas = 0

    def elegir(self, vida: Vida, decision: dict, opciones: list[Opcion]) -> tuple[str, dict]:
        if self.usadas >= len(self.elecciones):
            raise FaltaEleccion(decision, opciones)
        eleccion = self.elecciones[self.usadas]
        if eleccion.get("decision") not in (None, decision["id"]):
            raise ValueError(f"la elección {self.usadas + 1} es para {eleccion['decision']!r}, "
                             f"pero la partida está en {decision['id']!r}")
        self.usadas += 1
        opcion = next((o for o in opciones if o.id == str(eleccion["opcion"])), None)
        defecto = parametros_por_defecto(vida, opcion) if opcion else {}
        return str(eleccion["opcion"]), {**defecto, **(eleccion.get("parametros") or {})}
