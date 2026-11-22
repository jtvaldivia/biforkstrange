"""Una partida: la vida que juega la persona.

No se guarda nada entre llamadas. Una partida es (perfil, semilla, duda inicial,
elecciones tomadas) y se vuelve a jugar entera cada vez: con la misma semilla
los dados dan lo mismo, así que el resultado es idéntico. Cuando faltan
elecciones, la partida queda detenida en la decisión pendiente.
"""

import re
from dataclasses import dataclass

from app.sim.motor import empresas, gemelos
from app.sim.motor.azar import Dados
from app.sim.motor.motor import LLEGAN, REPETIR_CARTA, TRANQUILO, FaltaEleccion, Opcion, Vida
from app.sim.motor.paquete import Paquete, paquete
from app.sim.motor.perfil import Perfil, estado_inicial
from app.sim.motor.narrativa import narrar
from app.sim.motor.politicas import Jugador, elecciones_internas

ANIOS = 10
JUGADOR = "tu"  # nombre de los dados de la persona; los gemelos usan 0, 1, 2...


@dataclass
class Partida:
    vida: Vida
    pendiente: FaltaEleccion | None  # decisión que espera respuesta; None si terminó
    anios: int
    edad_final: int = 0  # hasta qué edad se juega; los mundos miran hasta esa misma edad

    @property
    def terminada(self) -> bool:
        return self.pendiente is None

    def horizonte(self) -> int:
        """Cuántos años miran los mundos desde la decisión pendiente: hasta la edad final de la partida."""
        return max(1, self.edad_final - self.vida.e["edad"]) if self.edad_final else gemelos.HORIZONTE


def dudas_posibles(perfil: Perfil, pq: Paquete | None = None) -> list[dict]:
    """Cartas del banco que esta persona puede elegir como su duda inicial."""
    pq = pq or paquete()
    vida = Vida(estado_inicial(perfil, pq), Dados(0, JUGADOR), pq)
    return [
        {"decision": id_, "nombre": pq.decisiones[id_]["nombre"], "pregunta": pq.decisiones[id_]["pregunta"],
         "categoria": pq.decisiones[id_]["categoria"], "calidad": pq.decisiones[id_]["calidad"]}
        for id_, _ in vida.cartas_posibles()
    ]


def jugar(perfil: Perfil, semilla: int, elecciones: list[dict], duda: str | None = None, anios: int = ANIOS,
          pq: Paquete | None = None) -> Partida:
    pq = pq or paquete()
    vida = Vida(estado_inicial(perfil, pq), Dados(semilla, JUGADOR), pq)
    vida.variedad = REPETIR_CARTA  # tu vida no te repite la misma pregunta año tras año
    if duda is not None and not vida.aplica(duda):
        raise ValueError(f"la decisión {duda!r} no aplica a este perfil")
    jugador = Jugador(elecciones)
    vida.primer_anio_con_propuesta = duda is None  # sin duda, el primer año igual trae algo que decidir
    edad_final = perfil.edad + anios  # un doctorado ocupa varios años: se cuenta por edad, no por rondas
    try:
        while vida.e["edad"] < edad_final and not vida.terminada():
            vida.vivir_anio(jugador, carta=duda if vida.anio == 0 and not vida.cola else None)
    except FaltaEleccion as falta:
        return Partida(vida, falta, anios, edad_final)
    if jugador.usadas < len(elecciones):
        raise ValueError(f"sobran elecciones: la partida usó {jugador.usadas} de {len(elecciones)}")
    return Partida(vida, None, anios, edad_final)


MAX_OPCIONES_COMPARAR = 6  # elegir carrera tiene 252 opciones: ahí no se simulan gemelos


def comparar_pendiente(partida: Partida, semilla: int, n: int = gemelos.N_GEMELOS,
                       parametros: dict[str, dict] | None = None, crudo: bool = False) -> dict | None:
    """Lo que vivirían los gemelos con cada opción de la decisión pendiente."""
    if (partida.pendiente is None or partida.pendiente.decision["id"] == TRANQUILO
            or len(partida.pendiente.opciones) > MAX_OPCIONES_COMPARAR or n <= 0):
        return None
    return gemelos.comparar(partida.vida, partida.pendiente.decision["id"], n=n, anios=partida.horizonte(),
                            semilla=semilla, parametros=parametros, crudo=crudo)


def mundo_pendiente(perfil: Perfil, semilla: int, duda: str | None, elecciones: list[dict], numero: int,
                    parametros: dict[str, dict] | None = None, anios: int = ANIOS, pq: Paquete | None = None) -> dict:
    """Un mundo de la comparación de la decisión pendiente, con su historia completa."""
    partida = jugar(perfil, semilla, elecciones, duda, anios, pq or paquete())
    if partida.pendiente is None:
        raise ValueError("la partida no tiene una decisión pendiente")
    if len(partida.pendiente.opciones) > MAX_OPCIONES_COMPARAR or partida.pendiente.decision["id"] == TRANQUILO:
        raise ValueError("esta decisión no tiene mundos para comparar")
    return gemelos.mundo(partida.vida, partida.pendiente.decision["id"], numero, anios=partida.horizonte(),
                         semilla=semilla, parametros=parametros)


def _cierre(perfil: Perfil, semilla: int, duda: str | None, elecciones: list[dict], partida: Partida,
            n: int, pq: Paquete) -> dict:
    """Tu vida frente a los gemelos de la primera decisión que tuvo mundos (un año tranquilo no tiene)."""
    cierre = {"sueldo_final": round(partida.vida.sueldo_o_ultimo()), "estado": partida.vida.resumen(),
              "anios_sin_trabajo": partida.vida.anios_buscando, "primera_decision": None}
    comparacion, elegida = None, None
    for k in range(len(elecciones)):
        hasta = jugar(perfil, semilla, elecciones[:k], duda, partida.anios, pq)
        comparacion = comparar_pendiente(hasta, semilla, n, crudo=True)
        if comparacion:
            elegida = str(elecciones[k]["opcion"])
            break
    if comparacion:
        for o in comparacion["opciones"]:
            sueldos = o.pop("sueldos")
            if o["opcion"] == elegida:
                cierre["mejor_que_gemelos"] = sum(1 for x in sueldos if x < cierre["sueldo_final"]) / len(sueldos)
        cierre["primera_decision"] = {"decision": comparacion["decision"], "pregunta": comparacion["pregunta"],
                                      "elegida": elegida, "comparacion": comparacion}
    return cierre


def vista(perfil: Perfil, semilla: int = 0, duda: str | None = None, elecciones: list[dict] | None = None,
          n_gemelos: int = gemelos.N_GEMELOS, parametros: dict[str, dict] | None = None,
          anios: int = ANIOS, pq: Paquete | None = None) -> dict:
    """Todo lo que una pantalla o el terminal necesita para mostrar la partida en su punto actual."""
    pq = pq or paquete()
    elecciones = elecciones or []
    partida = jugar(perfil, semilla, elecciones, duda, anios, pq)
    vida, falta = partida.vida, partida.pendiente
    salida = {
        "terminada": partida.terminada, "anio": min(anios, vida.e["edad"] - perfil.edad), "anios": anios,
        "edad_final": perfil.edad + anios, "semilla": semilla, "duda": duda,
        "elecciones": elecciones, "estado": vida.resumen(), "historia": vida.historia,
        "anio_en_curso": vida.registro, "pendiente": None, "cierre": None,
    }
    _narrar_historia(salida, semilla)
    if falta is None:
        salida["cierre"] = _cierre(perfil, semilla, duda, elecciones, partida, n_gemelos, pq)
        return salida
    d = falta.decision
    if d["id"] == TRANQUILO:
        salida["pendiente"] = {
            "por_que": {"tipo": "tranquilo"}, "narrativa": None,
            "decision": d["id"], "nombre": d["nombre"], "pregunta": d["pregunta"], "categoria": d["categoria"],
            "calidad": d["calidad"], "creencia_vs_dato": None, "evidencia": [],
            "sugerida": vida.sugerida,  # lo que más suele buscar la gente como tú este año
            # la propuesta del año: la decisión sugerida, con un dato del paquete que la respalda
            "sugerencia": _sugerencia(pq, _sugerible(vida)),
            "opciones": [{**opcion_a_dict(o), "elecciones_internas": [], "ejemplo_real": None} for o in falta.opciones],
            "comparacion": None,
        }
        return salida
    ocurrencia = sum(1 for x in vida.registro["decisiones"] if x["decision"] == d["id"]) if vida.registro else 0
    contexto = {k: vida.e[k] for k in ("edad", "rubro", "tipo_empleador", "nivel", "region", "ocupacion", "estado", "antiguedad")}
    contexto.update(vida.contexto_empleo())
    ofertas = {o.id: empresas.oferta(vida, d["id"], o.id, ocurrencia) for o in falta.opciones}
    primera = next((f for f in ofertas.values() if f is not None), None)
    if primera is not None:
        contexto["oferta"] = {k: primera[k] for k in ("empresa_id", "nombre", "cargo", "tipo", "rubro", "pais")}
    # por qué te tocó esta decisión: sorteada entre las cartas posibles, obligada por tu situación, o consecuencia
    origen = vida.cola[0][2] if vida.cola and vida.cola[0][0] == "decision" and vida.cola[0][1] == d["id"] else None
    if d["aparicion"]["tipo"] == "forzada":
        por_que = {"tipo": "obligada"}
    elif origen == "luego" and d["id"] in LLEGAN:
        por_que = {"tipo": "llega"}  # una oferta que llegó sin buscarla
    elif origen == "luego":
        por_que = {"tipo": "consecuencia"}
    elif origen == "buscada":
        por_que = {"tipo": "buscada"}
    elif vida.reparto and vida.reparto["carta"] == d["id"]:
        por_que = {"tipo": "llega", "prob": vida.reparto["prob"], "posibles": vida.reparto["posibles"]}
    elif duda is not None and d["id"] == duda and vida.anio == 0:
        por_que = {"tipo": "elegida"}
    else:
        por_que = {"tipo": "consecuencia"}
    salida["pendiente"] = {
        "por_que": por_que,
        # lo que buscaste tú no se cuenta como algo que te llegó ("te llega la convocatoria..."): se cuenta como tu idea
        "narrativa": ({"situacion": f"Es un año tranquilo y decides mirar en serio una idea: {d['nombre'].lower()}. "
                                    f"Nadie te lo propuso: lo buscaste tú."}
                      if por_que["tipo"] == "buscada" else narrar(d["id"], contexto, semilla, vida.anio, ocurrencia)),
        "decision": d["id"], "nombre": d["nombre"], "pregunta": d["pregunta"], "categoria": d["categoria"],
        "calidad": d["calidad"], "creencia_vs_dato": d.get("creencia_vs_dato"), "evidencia": d.get("evidencia", []),
        "opciones": [{**opcion_a_dict(o), "elecciones_internas": elecciones_internas(vida, o),
                      "empresa": ofertas[o.id], "respaldo": respaldo(vida.pq, o)}
                     for o in falta.opciones],
        "comparacion": comparar_pendiente(partida, semilla, n_gemelos, parametros),
        # una oferta llega con su sueldo, como en la vida: el que tendrías si la aceptas (empresa incluida)
        "oferta_sueldo": ({"hoy": vida.e["sueldo"], "si_aceptas": vida.sueldo_si_elige(d["id"], "cambiar")}
                          if d["id"] == "oferta_externa" else None),
    }
    return salida


# Decisiones drásticas: siguen en "ver más", pero no se destacan como la idea del año (nadie las pidió)
NO_SUGERIR = frozenset({"renunciar", "sabatico", "emigrar"})


def _sugerible(vida: Vida) -> str | None:
    """La idea que se muestra en un año tranquilo: la que sorteó el motor, salvo que sea drástica; entonces, la
    más frecuente de las que no lo son. Solo cambia lo que se muestra: las copias siguen con lo que se sorteó."""
    if vida.sugerida and vida.sugerida not in NO_SUGERIR:
        return vida.sugerida
    otras = [(id_, peso) for id_, peso in vida.cartas_posibles() if id_ in vida.buscables() and id_ not in NO_SUGERIR]
    return max(otras, key=lambda x: x[1])[0] if otras else None


def _cita_corta(cita: str) -> str:
    """Lo primero de la cita, sin el detalle: "Subsecretaría de Previsión Social" en vez de la ronda y el módulo."""
    return cita.split(",")[0].strip()


def _sugerencia(pq: Paquete, decision_id: str | None) -> dict | None:
    """La propuesta de un año tranquilo. No es un modelo nuevo: es la decisión que el motor ya sorteó según qué tan
    seguido le pasa a gente como tú (el peso del paquete), con la primera cifra de su evidencia."""
    if not decision_id:
        return None
    d = pq.decisiones[decision_id]
    evidencia = d.get("evidencia") or []
    # primero la estadística oficial de qué tan seguido la gente hace esto (evidencia con uso "frecuencia");
    # si no hay, la primera cifra de su evidencia
    frecuencias = [e for e in evidencia if str(e.get("uso", "")).lower().startswith("frecuencia")]
    dato = (frecuencias or evidencia or [None])[0]
    fuente = pq.fuentes.get(dato["fuente"], {}) if dato else {}
    return {"decision": decision_id, "nombre": d["nombre"], "pregunta": d["pregunta"],
            "dato": dato["cifra"] if dato else None, "fuente": _cita_corta(fuente.get("cita", "")) if dato else None,
            "es_frecuencia": bool(frecuencias), "creencia_vs_dato": d.get("creencia_vs_dato")}


def _narrar_historia(salida: dict, semilla: int) -> None:
    """Le pone su historia a cada decisión ya tomada, con el contexto que tenía la persona en ese momento."""
    def narrado(a: dict) -> dict:  # copia: la historia de la vida no se toca
        return {**a, "decisiones": [
            {**d, "narrativa": narrar(d["decision"], d["contexto"], semilla, a["anio"] - 1, d.get("ocurrencia", 0))}
            if "contexto" in d else d for d in a["decisiones"]]}

    salida["historia"] = [narrado(a) for a in salida["historia"]]
    if salida["anio_en_curso"]:
        salida["anio_en_curso"] = narrado(salida["anio_en_curso"])


def opcion_a_dict(o: Opcion) -> dict:
    return {"opcion": o.id, "nombre": o.nombre, "detalle": o.detalle, "calidad": o.calidad}


def respaldo(pq: Paquete, o: Opcion) -> list[dict]:
    """De dónde sale la probabilidad de cada resultado de la opción, para explicarla en pantalla.

    Si la probabilidad usa parámetros del paquete (`k('YC_CERRADA')`), van su fuente y su calidad. Si es
    "resto", es lo que queda después de los otros. Si es un número fijo o una fórmula sin parámetros, queda
    con la calidad de la opción.
    """
    salida = []
    for r in o.resultados:
        prob = str(r.get("prob", ""))
        nombres = list(dict.fromkeys(re.findall(r"k\('([A-Z0-9_]+)'", prob)))
        fuentes, calidades = [], []
        for n in nombres:
            p = pq.parametros.get(n)
            if not p:
                continue
            fid = p.get("fuente", "")
            cita = "Supuesto del equipo" if fid == "equipo" else pq.fuentes.get(fid, {}).get("cita", fid)
            if cita and cita not in fuentes:
                fuentes.append(cita)
            calidades.append(p.get("calidad", ""))
        peor = next((c for c in ("supuesto", "mixto", "dato") if c in calidades), None)
        solo = re.fullmatch(r"k\('([A-Z0-9_]+)'\)", prob.strip())
        valor = pq.parametros.get(solo.group(1), {}).get("valor") if solo else None
        try:
            valor = float(prob) if valor is None and prob not in ("", "resto") else valor
        except ValueError:
            valor = None  # una fórmula: depende de tu situación
        salida.append({"resultado": r["id"], "texto": r.get("texto", ""), "fuentes": fuentes,
                       "calidad": peor or o.calidad, "es_resto": prob == "resto",
                       "valor": valor if isinstance(valor, (int, float)) else None})
    conocidos = [x["valor"] for x in salida if not x["es_resto"]]
    if all(v is not None for v in conocidos):
        otros = [x for x in salida if not x["es_resto"]]
        for x in salida:
            if x["es_resto"]:
                # lo que queda hereda el respaldo de los demás: sale de la misma cuenta
                x["valor"] = max(0.0, 1 - sum(conocidos))
                x["fuentes"] = list(dict.fromkeys(f for y in otros for f in y["fuentes"])) or x["fuentes"]
                cal = [y["calidad"] for y in otros if y["fuentes"]]
                x["calidad"] = next((c for c in ("supuesto", "mixto", "dato") if c in cal), x["calidad"])
    return salida
