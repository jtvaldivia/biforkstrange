"""Una partida: la vida que juega la persona.

No se guarda nada entre llamadas. Una partida es (perfil, semilla, duda inicial,
elecciones tomadas) y se vuelve a jugar entera cada vez: con la misma semilla
los dados dan lo mismo, así que el resultado es idéntico. Cuando faltan
elecciones, la partida queda detenida en la decisión pendiente.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from app.sim.motor import empresas, gemelos
from app.sim.motor.azar import Dados
from app.sim.motor.motor import REPETIR_CARTA, FaltaEleccion, Opcion, Vida
from app.sim.motor.paquete import Paquete, paquete
from app.sim.motor.perfil import Perfil, estado_inicial
from app.sim.motor.narrativa import narrar
from app.sim.motor.politicas import Jugador, elecciones_internas

ANIOS = 10
# Cuánto pesa cada carta para esta persona (de su gemelo). Va por contexto para no cruzar todas las firmas.
AFINIDAD: ContextVar[dict[str, float]] = ContextVar("afinidad", default={})


@contextmanager
def con_afinidad(afinidad: dict[str, float]):
    token = AFINIDAD.set(afinidad)
    try:
        yield
    finally:
        AFINIDAD.reset(token)


JUGADOR = "tu"  # nombre de los dados de la persona; los gemelos usan 0, 1, 2...


@dataclass
class Partida:
    vida: Vida
    pendiente: FaltaEleccion | None  # decisión que espera respuesta; None si terminó
    anios: int

    @property
    def terminada(self) -> bool:
        return self.pendiente is None


def dudas_posibles(perfil: Perfil, pq: Paquete | None = None) -> list[dict]:
    """Cartas del banco que esta persona puede elegir como su duda inicial."""
    pq = pq or paquete()
    vida = Vida(estado_inicial(perfil, pq), Dados(0, JUGADOR), pq)
    vida.afinidad = AFINIDAD.get()
    return [
        {"decision": id_, "nombre": pq.decisiones[id_]["nombre"], "pregunta": pq.decisiones[id_]["pregunta"],
         "categoria": pq.decisiones[id_]["categoria"], "calidad": pq.decisiones[id_]["calidad"]}
        # con gemelo, primero las que más te tiran
        for id_, _ in sorted(vida.cartas_posibles(), key=lambda c: -c[1] if vida.afinidad else 0)
    ]


def jugar(perfil: Perfil, semilla: int, elecciones: list[dict], duda: str | None = None, anios: int = ANIOS,
          pq: Paquete | None = None) -> Partida:
    pq = pq or paquete()
    vida = Vida(estado_inicial(perfil, pq), Dados(semilla, JUGADOR), pq)
    vida.variedad = REPETIR_CARTA  # tu vida no te repite la misma pregunta año tras año
    vida.afinidad = AFINIDAD.get()
    if duda is not None and not vida.aplica(duda):
        raise ValueError(f"la decisión {duda!r} no aplica a este perfil")
    jugador = Jugador(elecciones)
    edad_final = perfil.edad + anios  # un doctorado ocupa varios años: se cuenta por edad, no por rondas
    try:
        while vida.e["edad"] < edad_final and not vida.terminada():
            vida.vivir_anio(jugador, carta=duda if vida.anio == 0 and not vida.cola else None)
    except FaltaEleccion as falta:
        return Partida(vida, falta, anios)
    if jugador.usadas < len(elecciones):
        raise ValueError(f"sobran elecciones: la partida usó {jugador.usadas} de {len(elecciones)}")
    return Partida(vida, None, anios)


MAX_OPCIONES_COMPARAR = 6  # elegir carrera tiene 252 opciones: ahí no se simulan gemelos


def comparar_pendiente(partida: Partida, semilla: int, n: int = gemelos.N_GEMELOS,
                       parametros: dict[str, dict] | None = None, crudo: bool = False) -> dict | None:
    """Lo que vivirían los gemelos con cada opción de la decisión pendiente."""
    if partida.pendiente is None or len(partida.pendiente.opciones) > MAX_OPCIONES_COMPARAR or n <= 0:
        return None
    return gemelos.comparar(partida.vida, partida.pendiente.decision["id"], n=n, anios=gemelos.HORIZONTE,
                            semilla=semilla, parametros=parametros, crudo=crudo)


def mundo_pendiente(perfil: Perfil, semilla: int, duda: str | None, elecciones: list[dict], numero: int,
                    parametros: dict[str, dict] | None = None, anios: int = ANIOS, pq: Paquete | None = None) -> dict:
    """Un mundo de la comparación de la decisión pendiente, con su historia completa."""
    partida = jugar(perfil, semilla, elecciones, duda, anios, pq or paquete())
    if partida.pendiente is None:
        raise ValueError("la partida no tiene una decisión pendiente")
    if len(partida.pendiente.opciones) > MAX_OPCIONES_COMPARAR:
        raise ValueError("esta decisión tiene demasiadas opciones para simular mundos")
    return gemelos.mundo(partida.vida, partida.pendiente.decision["id"], numero, anios=gemelos.HORIZONTE,
                         semilla=semilla, parametros=parametros)


def _cierre(perfil: Perfil, semilla: int, duda: str | None, elecciones: list[dict], partida: Partida,
            n: int, pq: Paquete) -> dict:
    """Tu vida frente a los gemelos de la primera decisión."""
    cierre = {"sueldo_final": round(partida.vida.sueldo_o_ultimo()), "estado": partida.vida.resumen(),
              "anios_sin_trabajo": partida.vida.anios_buscando, "primera_decision": None}
    inicio = jugar(perfil, semilla, [], duda, partida.anios, pq)
    comparacion = comparar_pendiente(inicio, semilla, n, crudo=True) if elecciones else None
    if comparacion:
        elegida = str(elecciones[0]["opcion"])
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
    elif origen == "luego":
        por_que = {"tipo": "consecuencia"}
    elif vida.reparto and vida.reparto["carta"] == d["id"]:
        por_que = {"tipo": "sorteo", "prob": vida.reparto["prob"], "posibles": vida.reparto["posibles"]}
    elif duda is not None and d["id"] == duda and vida.anio == 0:
        por_que = {"tipo": "elegida"}
    else:
        por_que = {"tipo": "consecuencia"}
    salida["pendiente"] = {
        "por_que": por_que,
        "narrativa": narrar(d["id"], contexto, semilla, vida.anio, ocurrencia),
        "decision": d["id"], "nombre": d["nombre"], "pregunta": d["pregunta"], "categoria": d["categoria"],
        "calidad": d["calidad"], "creencia_vs_dato": d.get("creencia_vs_dato"), "evidencia": d.get("evidencia", []),
        "opciones": [{**opcion_a_dict(o), "elecciones_internas": elecciones_internas(vida, o),
                      "empresa": ofertas[o.id]}
                     for o in falta.opciones],
        "comparacion": comparar_pendiente(partida, semilla, n_gemelos, parametros),
    }
    return salida


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
