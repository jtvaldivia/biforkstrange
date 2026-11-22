"""El loop anual: una vida simulada año a año con las reglas del paquete.

Un año tiene siempre los mismos pasos (README del paquete):

1. El mundo: se sortea si hay recesión, para que el resto del año ya la vea.
2. La decisión del año: primero las forzadas que aplican (estás cesante, sales
   del colegio); si no hay, y quien decide recibe cartas, una carta por sorteo.
3. El dado del resultado: cada opción tiene resultados con probabilidad.
4. Los eventos: despido, ascenso, oferta, cierre de la startup.
5. El cierre: cumples un año, ahorras, vencen los efectos con duración.

La vida no sabe quién decide: recibe un decisor (`politicas.py`). Los pasos
pendientes del año viven en una cola, así que una vida se puede detener a mitad
de año esperando una decisión, copiar, y seguir con otra suerte u otra elección.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

from app.sim.motor import empresas, ia
from app.sim.motor.narrativa import titular_ia
from app.sim.motor.azar import Dados
from app.sim.motor.paquete import Paquete
from app.sim.motor.perfil import NIVELES, estudio_sin_carrera, tipo_institucion_de

# "Solo lo laboral": el cáncer queda en el paquete, pero el juego no lo sortea. Lo de familia, pareja,
# vivienda y herencia se sacó del paquete: estaba fuera del juego y no movía lo que se compara.
EVENTOS_PERSONALES = frozenset({"cancer"})
EVENTO_MUNDO = "recesion"
ALZAS = frozenset({"alza_anual"})
SOLO_IPC = "Este año solo te reajustaron por inflación: en pesos de hoy, tu sueldo quedó igual."
# Lo del mundo se sortea al inicio del año, antes de la decisión, para que el año entero ya lo vea. La burbuja y
# el auge del cobre solo pasan con la incertidumbre de IA prendida (su `cuando` lee ia_v2).
EVENTOS_MUNDO = (EVENTO_MUNDO, "burbuja_ia", "auge_cobre")
# Decisiones cuya historia nombra a la empresa que te ofrece trabajo
DECISIONES_CON_OFERTA = empresas.DECISIONES_CON_OFERTA
# Cesante, quien elige buscar vive el resto del año mes a mes: cada mes pueden pasar los eventos con
# paso "mes" del paquete (llega una oferta, pasa un mes más buscando). Ver docs/COMO-FUNCIONA.md.
BUSCAR_MES_A_MES = {("cesantia", "buscar"), ("cesantia", "informal")}  # informal: trabaja sin contrato y sigue postulando
OFERTA_MES = "oferta_cesante"   # su probabilidad la multiplica p_encontrar, como antes la de encontrar en el año
MES_BUSCANDO = "mes_buscando"

# La suerte en la pega (ascenso, despido, oferta, alza) va con el trabajo: dos vidas de un mismo mundo
# la comparten mientras están en la misma pega, y deja de ser la misma cuando una se cambia.
# La recesión (EVENTO_MUNDO) siempre es igual para todas. Ver docs/DECISIONES.md, decisión 3.
SUERTE_POR_PEGA = True
EVENTOS_DE_LA_PEGA = frozenset({"alza_anual", "ascenso", "separacion_empleo", "oferta_llega", "startup_cierra",
                                "ia_empresa_adopta", "ia_reestructura"})

# Cada año: si la vida te obliga, decides eso. Si no, a veces te llega algo (LLEGAN). Si lo que sale es algo
# que la gente busca por su cuenta, el año es tranquilo: la persona puede buscar lo que quiera o seguir igual,
# y el gemelo considera lo que salió y responde como la gente real. Ver docs/DECISIONES.md, decisión 13.
TRANQUILO = "anio_tranquilo"
LLEGAN = frozenset({"oferta_externa", "unirse_a_startup", "jefatura", "remoto_para_afuera", "practica",
                    "intercambio", "volver_a_chile", "liderar_adopcion_ia"})
_DECISION_TRANQUILO = {
    "id": TRANQUILO, "nombre": "Año tranquilo", "categoria": "trabajo", "calidad": "supuesto",
    "pregunta": "Este año no te llegó ninguna propuesta. ¿Quieres mover algo tú?",
    "cuando": "1", "aparicion": {"tipo": "tranquilo"}, "opciones": [], "evidencia": [],
}
EDAD_MAXIMA = 60

# Reglas del cierre de año que el paquete deja al simulador. Supuestos del equipo.
SKILL_POR_ANIO = 1.5            # oficio que suma un año trabajado
PAGO_DEUDA_ESTUDIOS = 0.10      # parte del sueldo que paga el crédito (regla del CAE)
PRIMA_MIN, PRIMA_MAX = 0.6, 3.0  # supuesto: cuánto de tu nivel viaja contigo a una pega nueva
REPETIR_CARTA = 0.3             # supuesto: en tu partida, cada vez que ya te tocó una carta pesa 0,3 veces
ANIOS_HUECO = 2                # cuánto pesa una pausa elegida al buscar trabajo
EDU_AL_TITULARSE = {"U": "universitaria", "IP": "tecnica", "CFT": "tecnica"}
# Decisiones donde el modificador p_encontrar multiplica la probabilidad de quedar
BUSQUEDAS = frozenset({"primera_pega"})
# El paquete no tiene salida del trabajo por cuenta propia. Sin ella nadie vuelve a ser
# empleado y la cohorte termina con la mitad de independientes (en Chile, 13% a 24%).
P_INDEPENDIENTE_BUSCA_EMPLEO = 0.055
# Según su historia (del CV, si la trae). Supuesto del equipo, sin dato detrás: quien ya volvió una vez
# de trabajar por su cuenta a un empleo vuelve el doble de seguido; quien lleva 5 años o más por su
# cuenta, la mitad. Sin historia, la tasa de arriba, calibrada para la cohorte.
INDEPENDIENTE_DE_PASO = 2.0
INDEPENDIENTE_VETERANO, ANOS_VETERANO = 0.5, 5


def p_independiente_busca_empleo(e: dict) -> float:
    """Chance anual de que un independiente salga a buscar empleo. Lee la historia del CV que trae el estado
    (`freelance_entre_pegas`: ya volvió una vez a la planilla; `anos_independiente`), que no es del paquete."""
    if e.get("freelance_entre_pegas"):
        return P_INDEPENDIENTE_BUSCA_EMPLEO * INDEPENDIENTE_DE_PASO
    if e.get("anos_independiente", 0) >= ANOS_VETERANO:
        return P_INDEPENDIENTE_BUSCA_EMPLEO * INDEPENDIENTE_VETERANO
    return P_INDEPENDIENTE_BUSCA_EMPLEO
# Sitio del sorteo del escenario de IA: uno por gemelo, igual en todas sus opciones
SITIO_IA = "mundo:ia"
# un sueldo nuevo calculado desde el anterior (una oferta estando cesante también: sale de lo que ganabas)
_USA_SUELDO = re.compile(r"\b(sueldo(_ref)?|oferta_sueldo)\b")


class FaltaEleccion(Exception):
    """El decisor no tiene respuesta para esta decisión: la vida queda detenida ahí."""

    def __init__(self, decision: dict, opciones: list["Opcion"]):
        super().__init__(decision["id"])
        self.decision = decision
        self.opciones = opciones


@dataclass
class Opcion:
    id: str
    nombre: str
    detalle: str
    resultados: list[dict]
    costo: list[dict] = field(default_factory=list)
    calidad: str = ""
    fila: dict = field(default_factory=dict)  # columnas de la tabla como fila_<columna>


def _numero(txt: str):
    try:
        v = float(txt)
    except ValueError:
        return txt
    return int(v) if v.is_integer() else v


class Vida:
    def __init__(self, estado: dict, dados: Dados, pq: Paquete, alcance: str = "laboral"):
        self.pq = pq
        self.e = dict(estado)
        self.dados = dados
        self.alcance = alcance
        self.anio = 0                     # años ya cerrados
        self.cola: list[tuple] = []       # pasos pendientes del año en curso
        self.temporales: list[dict] = []  # efectos con duración, para revertirlos
        self.diferidos: list[dict] = []   # efectos que se cumplen años después (`en_anios`): un título de noche
        self.historia: list[dict] = []
        self.registro: dict | None = None
        self.anios_buscando = 0
        self.meses_buscando = 0           # meses sin trabajo buscando, en toda la vida
        self._meses_buscando_anio = 0     # los de este año: esos meses no hay sueldo
        self._antes_del_despido = (0, 0.0)  # si te despidieron este año: meses que alcanzaste a trabajar y con qué sueldo
        self.mes: int | None = None       # el mes en curso (1 a 12) cuando el año se vive mes a mes
        self.ingreso_total = 0.0
        self._anios_con_hueco = 0
        self.variedad = 1.0               # peso de una carta ya vista; la partida de la persona usa REPETIR_CARTA
        # empleo actual: cuánto paga respecto del nivel de referencia (empresa × cargo); 1 = neutro
        self._factor_empleo = 1.0
        self._origen = "inicio"         # qué decisión o evento trajo el empleador que viene
        self._espera_tipo = False       # el resultado sigue en tipo_de_empleador: la empresa se asigna ahí
        self._nuevo_empleador = False
        self._oferta_fija: dict | None = None  # empresa y cargo que trajo la decisión: son los que se viven
        self._sortear_ia()
        self.pega = 0                     # sube cada vez que esta vida entra a un trabajo nuevo
        self.sugerida: str | None = None  # en un año tranquilo, lo que la gente como tú suele buscar
        self.primer_anio_con_propuesta = False  # la persona: su partida no parte con un año tranquilo
        self._derivar()
        self.reparto: dict | None = None

    # ------------------------------------------------------------------ copia
    def clonar(self, dados: Dados | None = None) -> "Vida":
        otra = copy.copy(self)
        otra.e = dict(self.e)
        otra.cola = list(self.cola)
        otra.temporales = [dict(t) for t in self.temporales]
        otra.diferidos = [dict(t) for t in self.diferidos]
        otra.historia = list(self.historia)
        otra.registro = copy.deepcopy(self.registro)
        if dados is not None:
            otra.dados = dados
            otra._sortear_ia()
        return otra

    def _sortear_ia(self) -> None:
        """Qué tan rápido llega la IA en este mundo: se sortea una vez por gemelo, al nacer o al clonarlo
        con otros dados.

        Con la incertidumbre de IA prendida (ia.py), el sorteo da el ritmo con los pesos del FRI (P_RITMO_IA) y el
        golpe a los jóvenes lo lleva ia_encontrar, así que ia_castigo_joven queda neutro. Apagada, recorre el rango
        con fuente de IA_JOVEN (Brynjolfsson 2025): 0,9 lento, 0,75 rápido, y el ritmo es el tercil."""
        if "ia_adopcion" not in self.e:
            return  # estado sin las variables del escenario (paquete viejo)
        u = self.dados.u(0, SITIO_IA)
        self.e["ia_adopcion"] = u
        if ia.activa():
            self.e["ia_ritmo"] = ia.ritmo(self.pq, u)
            self.e["ia_castigo_joven"] = 1.0
            return
        bajo, alto = self.pq.parametros["IA_JOVEN"].get("rango") or (self.pq.k("IA_JOVEN"),) * 2
        self.e["ia_castigo_joven"] = alto - (alto - bajo) * u
        self.e["ia_ritmo"] = "lento" if u < 1 / 3 else "medio" if u < 2 / 3 else "rapido"

    # ------------------------------------------------------------------ alcance
    def _evento_en_alcance(self, id_: str) -> bool:
        return self.alcance != "laboral" or id_ not in EVENTOS_PERSONALES

    # ------------------------------------------------------------------ estado derivado
    def _derivar(self) -> None:
        self.e = self.pq.derivar(self.e)
        self.e["prima_personal"] = self._prima_personal()
        self._exposicion_del_puesto()
        self._derivar_ia()
        ascenso = self.pq.eventos["ascenso"]
        aplica = self.pq.evaluar(ascenso["cuando"], self.e)
        self.e["prob_ascenso"] = self.pq.evaluar(ascenso["prob_anual"], self.e) if aplica else 0.0

    def _derivar_ia(self) -> None:
        """Lo que la incertidumbre de IA necesita cada año (ver ia.py). Con la flag apagada todo queda neutro."""
        e = self.e
        e["ia_v2"] = 1 if ia.activa() else 0
        e.setdefault("ia_ritmo", "medio")
        e["ia_anios"] = self.anio
        e["ia_rampa"] = min(1.0, self.anio / self.pq.k("IA_RAMPA_ANIOS")) if e["ia_v2"] else 0.0
        e["ia_tipo"] = ia.tipo(self.pq, e)
        e["adaptabilidad"] = ia.adaptabilidad(self.pq, e)
        e["ia_encontrar"] = ia.encontrar(self.pq, e)

    def _prima_personal(self) -> float:
        """Cuánto gana la persona sobre la mediana de su edad y educación. Las reglas que fijan
        un sueldo desde una tabla nacional (informal, otra ocupación, por tu cuenta) la usan para
        que alguien que ya gana bien no caiga a la mediana del país. Supuesto del equipo."""
        e = self.e
        if e["sueldo_ref"] <= 0:
            return 1.0
        try:
            p50 = self.pq.evaluar(
                "tabla_o(tabla('esi_perfil_edad_edu', 'p50', 'educacion', edu, 'banda', banda7), "
                "'esi_ingreso_sexo_edad_edu', 'p50', 'sexo', sexo_txt, 'banda_edad', banda7, 'educacion', edu_esi)", e)
        except Exception:
            return 1.0
        return min(PRIMA_MAX, max(PRIMA_MIN, e["sueldo_ref"] / p50)) if p50 else 1.0

    def _veces_vista(self, decision_id: str) -> int:
        anios = self.historia + ([self.registro] if self.registro else [])
        return sum(1 for a in anios for d in a["decisiones"] if d["decision"] == decision_id and d.get("origen") == "carta")

    def _exposicion_del_puesto(self) -> None:
        """Quien trabaja está expuesto a la IA según su cargo; sin cargo, según el rubro de su empresa;
        sin empresa del catálogo, según su carrera (lo que deriva el paquete)."""
        e = self.e
        if e.get("estado") != "empleado":
            return
        car = empresas.cargo(self.pq, e.get("cargo_id", -1))
        if car is not None:
            e["exposicion_ia"] = car["exposicion_ia"]
            return
        emp = empresas.empresa(self.pq, e.get("empresa_id", -1))
        if emp is not None:
            e["exposicion_ia"] = emp["exposicion_ia"]

    def terminada(self) -> bool:
        return self.e["edad"] >= EDAD_MAXIMA

    # ------------------------------------------------------------------ año
    def iniciar_anio(self, con_cartas: bool, carta: str | None = None) -> None:
        """Sortea el mundo y arma la cola del año. `carta` (la duda inicial) va primero, antes de las forzadas."""
        if self.cola:
            raise RuntimeError("el año en curso no ha terminado")
        self.registro = {"anio": self.anio + 1, "edad": self.e["edad"], "recesion": False,
                         "decisiones": [], "eventos": [],
                         "sueldo_inicio": round(self.e["sueldo"]), "ahorro_inicio": round(self.e["ahorro"])}
        if ia.activa():
            self.registro["ia"] = {"ritmo": self.e.get("ia_ritmo", "medio"),
                                   "titular": titular_ia(self.e.get("ia_ritmo", "medio"), self.anio + 1)}
        self.mes, self._meses_buscando_anio, self._antes_del_despido = None, 0, (0, 0.0)
        self.reparto = None  # cómo se sorteó la carta de este año, si hubo sorteo
        self.sugerida = None
        self._derivar()
        for id_ in EVENTOS_MUNDO:
            if id_ in self.pq.eventos:
                self._evento(id_)
        self.registro["recesion"] = bool(self.e["recesion"])
        if "ia" in self.registro:
            self.registro["ia"].update(burbuja=bool(self.e.get("ia_burbuja")), auge_cobre=bool(self.e.get("auge_cobre")))
        decisiones = self._forzadas()
        if carta is not None:
            # la duda va primero (es la carta que la persona eligió), pero no tapa las forzadas: quien está
            # cesante igual tiene que buscar pega ese año y al fundador igual le toca seguir con su empresa.
            # Si la duda las resuelve (encuentra trabajo), al llegarles su turno ya no aplican y se saltan.
            decisiones = [carta] + [d for d in decisiones if d != carta]
        else:
            if not decisiones and con_cartas:
                sorteada = self._sortear_carta()
                if sorteada and sorteada not in LLEGAN | self._huecos() and self.primer_anio_con_propuesta and self.anio == 0:
                    # la partida no parte con un año tranquilo: el primer año te llega algo que decidir
                    llegan = [(id_, peso) for id_, peso in self.cartas_posibles() if id_ in LLEGAN]
                    if llegan:
                        sorteada = llegan[self.dados.elegir(self.anio, "carta:primera", [p for _, p in llegan])][0]
                        self.reparto = {"carta": sorteada, "prob": dict(llegan)[sorteada] / sum(p for _, p in llegan),
                                        "posibles": len(llegan)}
                if sorteada in self._huecos() and not (self.primer_anio_con_propuesta and self.anio == 0):
                    # una carta que solo llega por su evento (la oferta): ocupa su lugar en el sorteo, para no
                    # inflar a las demás, pero como carta no trae nada: año tranquilo sin sugerencia
                    decisiones = [TRANQUILO]
                elif sorteada and sorteada not in LLEGAN:
                    self.sugerida = sorteada  # no te llegó nada: año tranquilo, puedes buscar algo
                    decisiones = [TRANQUILO]
                else:
                    decisiones = [sorteada] if sorteada else []
        self.cola = self.cola + [("decision", d, "carta") for d in decisiones]
        if self.e["busca_mientras_informal"]:
            if self.e["estado"] == "independiente":
                self.cola += [("mes", m) for m in range(1, 13)]  # sigue informal: otro año postulando mes a mes
            else:
                self.e["busca_mientras_informal"] = 0  # ya no está en lo informal (volvió a buscar, emprendió...)
        self.cola += [("evento", id_) for id_, ev in self.pq.eventos.items()
                      if id_ not in EVENTOS_MUNDO and ev.get("paso", "año") != "mes" and self._evento_en_alcance(id_)]
        self.cola.append(("cierre",))

    def avanzar(self, decisor) -> dict | None:
        """Corre los pasos pendientes. Devuelve el registro del año si se cerró.

        Si el decisor levanta FaltaEleccion, la vida queda intacta y detenida en esa decisión.
        """
        while self.cola:
            paso = self.cola[0]
            if paso[0] == "decision":
                self._decidir(paso[1], paso[2], decisor)
            elif paso[0] == "evento":
                self.cola.pop(0)
                self.mes = paso[2] if len(paso) > 2 else None
                self._evento(paso[1])
            elif paso[0] == "mes":
                # un mes de búsqueda: sus eventos van primero; lo que encadenen (una oferta) se intercala
                self.cola.pop(0)
                self.registro.setdefault("meses_busqueda", []).append(paso[1])
                self.cola[0:0] = [("evento", id_, paso[1]) for id_, ev in self.pq.eventos.items()
                                  if ev.get("paso") == "mes" and self._evento_en_alcance(id_)]
            elif paso[0] == "evento_directo":
                self.cola.pop(0)
                self._evento(paso[1], directo=True)
            else:
                self.cola.pop(0)
                return self._cerrar()
        return None

    def vivir_anio(self, decisor, carta: str | None = None) -> dict:
        if not self.cola:
            self.iniciar_anio(decisor.con_cartas, carta)
        return self.avanzar(decisor)

    def vivir(self, decisor, anios: int) -> "Vida":
        for _ in range(anios):
            if self.terminada():
                break
            self.vivir_anio(decisor)
        return self

    # ------------------------------------------------------------------ decisiones
    def decision(self, decision_id: str) -> dict:
        return _DECISION_TRANQUILO if decision_id == TRANQUILO else self.pq.decisiones[decision_id]

    def buscables(self) -> list[str]:
        """Lo que esta persona podría buscar por su cuenta este año."""
        return [id_ for id_, _ in self.cartas_posibles() if id_ not in LLEGAN]

    def aplica(self, decision_id: str) -> bool:
        if decision_id == TRANQUILO:
            return True
        d = self.pq.decisiones[decision_id]
        return bool(self.pq.evaluar(d["cuando"], self.e)) and bool(self.opciones(decision_id))

    def _forzadas(self) -> list[str]:
        return [id_ for id_, d in self.pq.decisiones.items()
                if d["aparicion"]["tipo"] == "forzada" and self.aplica(id_)]

    def cartas_posibles(self) -> list[tuple[str, float]]:
        """Cartas que podrían salir este año, con su peso."""
        salida = []
        for id_, d in self.pq.decisiones.items():
            if d["aparicion"]["tipo"] != "carta" or not self.aplica(id_):
                continue
            peso = self.pq.evaluar(d["aparicion"]["peso"], self.e)
            if id_ == "renunciar":
                peso *= self.e["p_renuncia"]
            if self.variedad != 1.0:  # solo en tu partida: la población calibrada no se toca
                peso *= self.variedad ** self._veces_vista(id_)
            if peso > 0:
                salida.append((id_, float(peso)))
        return salida

    def _huecos(self) -> frozenset[str]:
        """Cartas que solo ocupan su lugar en el sorteo: lo que traen llega por un evento (ver `solo_por_evento`)."""
        return frozenset(id_ for id_, d in self.pq.decisiones.items() if d["aparicion"].get("solo_por_evento"))

    def _sortear_carta(self) -> str | None:
        cartas = self.cartas_posibles()
        if not cartas:
            return None
        elegida = cartas[self.dados.elegir(self.anio, "carta", [p for _, p in cartas])][0]
        total = sum(p for _, p in cartas)
        self.reparto = {"carta": elegida, "prob": dict(cartas)[elegida] / total, "posibles": len(cartas)}
        return elegida

    def opciones(self, decision_id: str) -> list[Opcion]:
        if decision_id == TRANQUILO:
            seguir = Opcion("seguir", "Seguir igual", "Este año no cambias nada.",
                            [{"id": "sigue", "prob": 1, "texto": "Sigues igual.", "tono": "neutro", "efectos": []}])
            return [seguir] + [
                Opcion(id_, self.pq.decisiones[id_]["nombre"], self.pq.decisiones[id_]["pregunta"],
                       [{"id": "busca", "prob": 1, "texto": f"Decides moverte: {self.pq.decisiones[id_]['nombre'].lower()}.",
                         "tono": "neutro", "efectos": []}])
                for id_ in self.buscables()
            ]
        d = self.pq.decisiones[decision_id]
        salida = [
            Opcion(o["id"], o["nombre"], o.get("detalle", ""), o["resultados"], o.get("costo", []), o.get("calidad", ""))
            for o in d["opciones"]
            if not o.get("requisito") or self.pq.evaluar(o["requisito"], self.e)
        ]
        desde = d.get("opciones_desde_tabla")
        if desde:
            for fila in self.pq.filas(desde["tabla"]):
                f = {f"fila_{c}": _numero(v) for c, v in fila.items()}
                if self.pq.evaluar(desde["filtro"], {**self.e, **f}):
                    salida.append(Opcion(str(fila[desde["id"]]), fila[desde["nombre"]],
                                         desde.get("detalle", "").format(**fila), desde["resultados"], fila=f))
        return salida

    def _decidir(self, decision_id: str, origen: str, decisor) -> None:
        d = self.decision(decision_id)
        vigente = origen != "carta" or self.pq.evaluar(d["cuando"], self.e)
        opciones = self.opciones(decision_id) if vigente else []
        if not opciones:
            self.cola.pop(0)
            return
        if d["aparicion"]["tipo"] == "interna":
            opcion_id, parametros = opciones[0].id, {}
        else:
            opcion_id, parametros = decisor.elegir(self, d, opciones)  # puede levantar FaltaEleccion
        opcion = next((o for o in opciones if o.id == opcion_id), None)
        if opcion is None:
            raise ValueError(f"opción {opcion_id!r} no disponible en {decision_id}")
        self.cola.pop(0)
        for var, valor in (parametros or {}).items():
            if self.pq.variables.get(var, {}).get("tipo") != "eleccion":
                raise ValueError(f"{var!r} no es algo que se elija dentro de una opción")
            self.e[var] = valor
        # la segunda vez que sale la misma decisión en un año (carta y evento oferta_llega) tira dados nuevos
        ocurrencia = sum(1 for x in self.registro["decisiones"] if x["decision"] == decision_id)
        sitio = f"dec:{decision_id}:{opcion_id}" + (f":{ocurrencia}" if ocurrencia else "") + (f":mes{self.mes}" if self.mes else "")
        contexto = {k: self.e[k] for k in ("edad", "rubro", "tipo_empleador", "nivel", "region", "ocupacion", "estado", "antiguedad", "validado", "edu", "sexo", "recesion",
                                            "meses_cesante")}
        contexto.update(self.contexto_empleo())
        if decision_id != "tipo_de_empleador":
            self._oferta_fija = None
        if decision_id in DECISIONES_CON_OFERTA:
            contexto["oferta"] = self.oferta_de(decision_id, ocurrencia)
            self._oferta_fija = contexto["oferta"]  # la historia nombra esta empresa y este cargo: son los que vives
        elif decision_id != "tipo_de_empleador":
            # cada opción trae su empresa (la cesantía): si la carta la mostró, es la que vives
            self._oferta_fija = self.oferta_de(decision_id, ocurrencia, opcion_id)
        if decision_id == "tipo_de_empleador":
            self._nuevo_empleador = True  # cambiarse de empresa aunque sea al mismo tipo
        else:
            self._origen = empresas.origen_decision(decision_id, ocurrencia, opcion_id)
        plata_antes = self._plata()
        if opcion.costo:
            self._aplicar(opcion.costo, sitio + ":costo", opcion.fila)
        resultado, prob = self._sortear(opcion.resultados, sitio, decision_id)
        self._espera_tipo = bool(resultado) and resultado.get("luego") == "tipo_de_empleador"
        self.registro["decisiones"].append({
            "decision": decision_id, "nombre": d["nombre"], "pregunta": d["pregunta"], "origen": origen,
            "opcion": opcion.id, "opcion_nombre": opcion.nombre,
            "resultado": resultado["id"] if resultado else None,
            "texto": resultado["texto"] if resultado else "", "tono": (resultado or {}).get("tono", "neutro"),
            "prob": prob, "ocurrencia": ocurrencia, "contexto": contexto,
            **({"mes": self.mes} if self.mes else {}),
        })
        if decision_id == "tipo_de_empleador" and self._oferta_fija:
            del self.registro["decisiones"][-1]  # la oferta ya dijo a qué empresa entras: el sorteo no es noticia
        if decision_id == TRANQUILO:
            del self.registro["decisiones"][-1]["contexto"]  # no tiene historia que narrar
            if opcion.id != "seguir":
                self.cola.insert(0, ("decision", opcion.id, "buscada"))
            return
        if resultado:
            self._aplicar(resultado["efectos"], sitio + ":" + resultado["id"], opcion.fila)
            self._encolar_luego(resultado.get("luego"))
        self._espera_tipo = False
        self._anotar_plata(self.registro["decisiones"][-1], plata_antes)
        if (decision_id, opcion.id) in BUSCAR_MES_A_MES and (self.e["estado"] == "buscando" or self.e["busca_mientras_informal"]):
            self._buscar_mes_a_mes(origen)

    def _buscar_mes_a_mes(self, origen: str) -> None:
        """El resto del año pasa de a un mes. Al empezar el año, los 12; si te despidieron este año, desde el
        mes del despido (sorteado con la suerte de la pega: tus copias en el mismo trabajo pierden la pega el mismo mes)."""
        desde = 1
        if origen == "luego":
            desde = 1 + int(12 * self.dados.u(self.anio, f"{self._sitio_evento('separacion_empleo')}:mes"))
            self._antes_del_despido = (desde - 1, self.e["sueldo_ref"])  # esos meses sí cobraste tu sueldo de antes
        self.cola[0:0] = [("mes", m) for m in range(desde, 13)]

    def _plata(self) -> tuple[float, float]:
        return self.e["sueldo"], self.e["ahorro"]

    def _anotar_plata(self, anotado: dict, antes: tuple[float, float]) -> None:
        """Si la decisión o el evento movió el sueldo o el ahorro, lo deja escrito para poder explicarlo."""
        sueldo, ahorro = antes
        if round(self.e["sueldo"]) != round(sueldo):
            anotado["sueldo_antes"], anotado["sueldo_despues"] = round(sueldo), round(self.e["sueldo"])
        if round(self.e["ahorro"]) != round(ahorro):
            anotado["ahorro_cambio"] = round(self.e["ahorro"] - ahorro)

    def resultado_previsto(self, decision_id: str, opcion_id: str) -> str | None:
        """El resultado que saldría si elige esa opción ahora: los dados ya están echados (mismo sitio que `_decidir`)."""
        opcion = next((o for o in self.opciones(decision_id) if o.id == opcion_id), None)
        if opcion is None:
            return None
        ocurrencia = sum(1 for x in (self.registro or {}).get("decisiones", []) if x["decision"] == decision_id)
        sitio = f"dec:{decision_id}:{opcion_id}" + (f":{ocurrencia}" if ocurrencia else "") + (f":mes{self.mes}" if self.mes else "")
        resultado, _ = self._sortear(opcion.resultados, sitio, decision_id)
        return resultado["id"] if resultado else None

    def sueldo_si_elige(self, decision_id: str, opcion_id: str) -> float | None:
        """El sueldo con que quedaría si elige esa opción ahora, con la empresa nueva incluida.

        Se vive la decisión en una copia de la vida (mismos dados y mismo paquete), así que es exactamente lo
        que pasará si la elige: sirve para mostrar el sueldo de una oferta antes de aceptarla.
        """
        if not self.cola or self.cola[0][:2] != ("decision", decision_id):
            return None
        copia = copy.deepcopy(self, memo={id(self.pq): self.pq, id(self.dados): self.dados})

        class _Elige:
            def elegir(self_, vida, decision, opciones):
                return opcion_id, {}

        copia._decidir(decision_id, copia.cola[0][2], _Elige())
        while copia.cola and copia.cola[0][:2] == ("decision", "tipo_de_empleador"):
            copia._decidir("tipo_de_empleador", copia.cola[0][2], _Elige())
        return float(copia.e["sueldo"])

    def contexto_empleo(self) -> dict:
        """Empresa, cargo e institución de hoy, para contar la historia con nombres."""
        e = self.e
        return {"empresa_id": e.get("empresa_id", -1), "cargo_id": e.get("cargo_id", -1),
                "empresa": self._nombre_empresa(), "rol": self._nombre_cargo(), "universidad_id": e.get("universidad_id", "")}

    def oferta_de(self, decision_id: str, ocurrencia: int, opcion_id: str | None = None) -> dict | None:
        """La empresa y el cargo que trae la decisión, o esa opción (la misma que muestra la carta)."""
        for o in self.opciones(decision_id):
            if opcion_id is not None and o.id != opcion_id:
                continue
            ficha = empresas.oferta(self, decision_id, o.id, ocurrencia)
            if ficha is not None:
                return {k: ficha[k] for k in ("empresa_id", "cargo_id", "nombre", "cargo", "tipo", "rubro", "pais")}
        return None

    def _encolar_luego(self, luego: str | None) -> None:
        if not luego:
            return
        if luego in self.pq.decisiones:
            self.cola.insert(0, ("decision", luego, "luego"))
        elif self._evento_en_alcance(luego):
            self.cola.insert(0, ("evento_directo", luego))

    # ------------------------------------------------------------------ sorteos y efectos
    def _sortear(self, resultados: list[dict], sitio: str, decision_id: str | None = None):
        probs, resto = [], None
        for i, r in enumerate(resultados):
            if r["prob"] == "resto":
                resto = i
                probs.append(0.0)
                continue
            p = float(self.pq.evaluar(r["prob"], self.e))
            if i == 0 and decision_id in BUSQUEDAS:
                p *= self.e["p_encontrar"] * self.e.get("ia_encontrar", 1.0)
            probs.append(min(max(p, 0.0), 1.0))
        if resto is not None:
            probs[resto] = max(0.0, 1.0 - sum(probs))
        u, acumulado = self.dados.u(self.anio, sitio), 0.0
        for r, p in zip(resultados, probs):
            acumulado += p
            if u < acumulado:
                return r, p
        return None, max(0.0, 1.0 - acumulado)

    def _aplicar(self, efectos: list[dict], sitio: str, extra: dict | None = None) -> None:
        """Aplica efectos en orden. Los valores y condiciones se leen del estado de antes
        del resultado: así 'sueldo queda en 0' y 'el finiquito es sueldo por años' conviven."""
        if not efectos:
            return
        antes = {**self.e, **(extra or {})}
        flujo = None
        base_referencia = False  # el sueldo nuevo sale de una tabla (nivel de referencia), no del sueldo anterior
        for ef in efectos:
            if ef.get("en_anios"):
                # se cumple al cerrar el año número `en_anios` (este incluido), con el estado de ese momento
                self.diferidos.append({"quedan": int(ef["en_anios"]), "sitio": sitio,
                                       "ef": {k: v for k, v in ef.items() if k != "en_anios"}})
                continue
            exprs = [x for x in (ef.get("cuando"), ef["valor"]) if x is not None]
            if flujo is None and any(self.pq.compilar(x)[1] for x in exprs):
                flujo = self.dados.flujo(self.anio, sitio)
            if ef.get("cuando") and not self.pq.evaluar(ef["cuando"], antes, flujo):
                continue
            valor = self.pq.evaluar(ef["valor"], antes, flujo)
            var = ef["var"]
            if var == "sueldo" and ef["op"] == "fija":
                base_referencia = not _USA_SUELDO.search(str(ef["valor"]))
            if self.pq.variables[var]["inicio"] == "deriva":
                continue  # las derivadas se recalculan; el paquete las mueve solo como referencia
            previo = self.e[var]
            if ef["op"] == "suma":
                self.e[var] = previo + valor
            elif ef["op"] == "multiplica":
                self.e[var] = previo * valor
            else:
                self.e[var] = valor
            self.e[var] = self._acotar(var, self.e[var])
            if (var == "estado" and self.e[var] == "empleado" and previo != "empleado") or (
                var == "antiguedad" and ef["op"] == "fija" and self.e[var] == 0 and previo != 0
            ) or (var == "tipo_empleador" and self.e[var] != previo):
                self.pega += 1  # trabajo nuevo: desde aquí, su suerte en la pega es otra
                if "ia_empresa" in self.e:
                    self.e["ia_empresa"] = 0  # la empresa nueva todavía no adopta IA
            if ef.get("duracion"):
                self.temporales.append({"quedan": ef["duracion"], "var": var, "op": ef["op"],
                                        "valor": valor, "previo": previo})
        self._completar_empleo(ref_movido=self.e["sueldo_ref"] != antes["sueldo_ref"], antes=antes,
                               base_referencia=base_referencia)
        self._derivar()

    def _completar_empleo(self, ref_movido: bool = False, antes: dict | None = None,
                          base_referencia: bool = False) -> None:
        """El paquete no dice en qué rubro ni en qué empresa cae quien entra a un empleo: la empresa se
        sortea del catálogo (su peso es cuánta gente ocupada hay en su rubro, ESI) y fija el rubro."""
        e = self.e
        if e["estado"] in ("buscando", "inactivo", "estudiando") and e["sueldo"] > 0:
            # varias reglas del paquete dejan sin trabajo sin llevar el sueldo a cero; si el mismo
            # resultado ya movió el sueldo de referencia (premio del doctorado), se respeta
            if not ref_movido:
                e["sueldo_ref"] = e["sueldo"]
            e["sueldo"] = 0.0
        if e["estado"] == "buscando" and e["sueldo_ref"] <= 0:
            # nunca tuvo un sueldo de empleado (partió por cuenta propia o emprendiendo): busca como
            # quien busca su primera pega; si no, la cesantía le pagaría un factor de cero para siempre
            e["primer_empleo"] = 1
        if e["estado"] != "empleado":
            # se suelta la empresa; el cargo y el factor del último empleo se guardan: la próxima oferta sigue
            # en su línea de trabajo y su sueldo parte de lo que ganaba
            e["empresa_id"] = -1
            e["empresa_inicial"], e["cargo_inicial"] = "", ""
            return
        if not e["tipo_empleador"] and not self._espera_tipo and ("decision", "tipo_de_empleador", "luego") not in self.cola[:1]:
            # reglas como bootcamp/colocado emplean sin decir en qué tipo de empresa: se sortea. Si el resultado
            # ya sigue en tipo_de_empleador (`_espera_tipo`), no se encola otro: el segundo sorteo cambiaba
            # la empresa que mostró la carta
            self.cola.insert(0, ("decision", "tipo_de_empleador", "luego"))
            self._espera_tipo = True
        if antes is not None:
            self._asignar_empresa(antes, base_referencia)
        if e["tipo_empleador"] == "publico":
            e["rubro"] = "Administración pública"
        elif not e["rubro"] or e["rubro"] == "Administración pública":
            rubros, pesos = self._rubros_privados()
            e["rubro"] = rubros[self.dados.elegir(self.anio, "rubro", pesos)]

    def _cumplir_diferidos(self) -> None:
        """Los efectos con `en_anios` que vencen este año. El primero con `aviso` sale como noticia del año."""
        quedan, vencen = [], []
        for d in self.diferidos:
            d["quedan"] -= 1
            (vencen if d["quedan"] <= 0 else quedan).append(d)
        self.diferidos = quedan
        for d in vencen:
            ef = d["ef"]
            if ef.get("cuando") and not self.pq.evaluar(ef["cuando"], self.e, self.dados.flujo(self.anio, d["sitio"] + ":diferido")):
                continue
            aviso = ef.get("aviso")
            self._aplicar([{k: v for k, v in ef.items() if k != "aviso"}], d["sitio"] + ":diferido")
            if aviso and self.registro is not None:
                self.registro["eventos"].append({
                    "evento": "diferido", "nombre": aviso["nombre"], "resultado": "cumple", "texto": aviso["texto"],
                    "tono": aviso.get("tono", "bueno"), "prob": 1.0, "prob_evento": 1.0, "directo": True, "rutina": False})

    def _asignar_empresa(self, antes: dict, base_referencia: bool) -> None:
        """Al entrar a un empleador nuevo: empresa y cargo del catálogo, y el sueldo pasa de lo que pagaba
        el empleo anterior a lo que paga este (razón de sus factores)."""
        e = self.e
        if not e["tipo_empleador"] or self._espera_tipo:
            return
        cambio = (self._nuevo_empleador or antes.get("estado") != "empleado"
                  or antes.get("tipo_empleador") != e["tipo_empleador"]
                  or (antes.get("rubro") and antes.get("rubro") != e["rubro"]))
        self._nuevo_empleador = False
        if not cambio:
            if antes.get("nivel") != e["nivel"]:
                e["cargo_inicial"] = ""  # con un ascenso, el nombre del cargo que tenía ya no es el suyo
            self._revisar_cargo()
            return
        e["empresa_inicial"], e["cargo_inicial"] = "", ""
        e["antiguedad"] = 0  # empleador nuevo: la antigüedad parte de cero (la startup no la fijaba)
        if e["tipo_empleador"] == "publico":
            rubro = empresas.rubro_publico(self.pq, antes)  # el sector del Estado según dónde venía
        else:
            rubro = empresas.rubro_actual(e)
        sitio = empresas.sitio_empresa(self._origen)
        fija, self._oferta_fija = self._oferta_fija, None
        emp = empresas.empresa(self.pq, fija["empresa_id"]) if fija else None
        if emp is not None and emp["tipo"] == e["tipo_empleador"]:
            car = empresas.cargo(self.pq, fija.get("cargo_id", -1))  # la que te ofrecieron, no otra sorteada
        else:
            emp = empresas.sortear_empresa(self.pq, self.dados, self.anio, sitio, e["tipo_empleador"], rubro, e)
            car = None
        if emp is not None and e["tipo_empleador"] != "publico":
            e["rubro"] = emp["rubro"]  # sin rubro, o startup/remota de otro rubro: la empresa lo fija
        if car is None:
            car = empresas.sortear_cargo(self.pq, self.dados, self.anio, sitio + ":cargo", emp, e)
        nuevo = empresas.factor_sueldo(emp, car)
        # El resultado de la decisión ya dijo cuánto cambia el sueldo respecto del anterior ("sueldo 10% menor",
        # "ganas lo mismo o menos"), con su fuente: la empresa y el cargo no se apilan encima. Solo cuando el
        # sueldo sale de una tabla (nivel promedio de referencia) la empresa y el cargo lo ubican.
        if base_referencia and e["sueldo"] > 0:
            e["sueldo"] = self._acotar("sueldo", e["sueldo"] * nuevo)
        if car is not None:
            e["ocupacion"] = car["ciuo08_1d"]
        self._factor_empleo = nuevo if emp is not None else 1.0
        e["empresa_id"] = emp["empresa_id"] if emp else -1
        e["cargo_id"] = car["cargo_id"] if car else -1
        if emp is not None and not e.get("parcial") and e.get("horas", 44) != 22:
            e["horas"] = int(emp["horas"])

    def _revisar_cargo(self) -> None:
        """Tras un ascenso el cargo puede quedar chico: se busca otro en la misma empresa (mismo grupo)."""
        e = self.e
        car, emp = empresas.cargo(self.pq, e.get("cargo_id", -1)), empresas.empresa(self.pq, e.get("empresa_id", -1))
        if emp is None or car is None or car["nivel_min"] <= e["nivel"] <= car["nivel_max"]:
            return
        nuevo = empresas.sortear_cargo(self.pq, self.dados, self.anio, f"cargo:{e['nivel']}", emp, e)
        if nuevo is None:
            return
        # el alza del ascenso ya la pagó el evento ascenso: el nombre nuevo del cargo no mueve el sueldo otra vez
        self._factor_empleo = empresas.factor_sueldo(emp, nuevo)
        e["cargo_id"] = nuevo["cargo_id"]

    def _rubros_privados(self) -> tuple[list[str], list[float]]:
        if not hasattr(self.pq, "_rubros_privados"):
            validos = set(self.pq.variables["rubro"]["dominio"]) - {"", "Administración pública"}
            filas = [f for f in self.pq.filas("esi_ingreso_rubro_edad")
                     if f["banda_edad"] == "18-54" and f["rubro"] in validos]
            self.pq._rubros_privados = ([f["rubro"] for f in filas], [float(f["share_ocupados_banda"] or 0) for f in filas])
        return self.pq._rubros_privados

    def _acotar(self, var: str, valor):
        v = self.pq.variables[var]
        dom = v["dominio"]
        if v["tipo"] in ("categoria", "eleccion") or len(dom) != 2 or isinstance(valor, str):
            return valor
        valor = min(max(valor, dom[0]), dom[1])
        return int(round(valor)) if v["tipo"] in ("entero", "bool") else valor

    def _sitio_evento(self, id_: str) -> str:
        """Lo del mundo (la recesión) se comparte entre las vidas de un mundo. Lo de la pega
        (ascenso, despido, oferta, alza) se comparte mientras están en el mismo trabajo:
        al cambiarse de pega, esa vida pasa a tener otra suerte."""
        if not SUERTE_POR_PEGA or id_ not in EVENTOS_DE_LA_PEGA:
            return f"evento:{id_}"  # lo del país y lo personal (la salud) es igual en todas las vidas
        return f"evento:{id_}@{self.pega}"

    def _evento(self, id_: str, directo: bool = False) -> None:
        ev = self.pq.eventos[id_]
        mensual = ev.get("paso") == "mes"
        sitio = f"evento:{id_}:mes{self.mes}" if mensual and self.mes else self._sitio_evento(id_)
        prob = 1.0
        if not directo:
            if not self.pq.evaluar(ev["cuando"], self.e):
                return
            prob = min(max(float(self.pq.evaluar(ev["prob_mensual" if mensual else "prob_anual"], self.e)), 0.0), 1.0)
            if id_ == OFERTA_MES:
                prob *= self.e["p_encontrar"] * self.e.get("ia_encontrar", 1.0)
            if self.dados.u(self.anio, sitio) >= prob:
                return
        resultado, prob_resultado = self._sortear(ev["resultados"], f"{sitio}:res")
        if resultado is None:
            return
        self._origen = f"evento:{id_}"
        self._espera_tipo = resultado.get("luego") == "tipo_de_empleador"
        anotado = {
            "evento": id_, "nombre": ev["nombre"], "resultado": resultado["id"], "texto": resultado["texto"],
            "tono": resultado.get("tono", "neutro"),
            "prob": prob * prob_resultado,  # de que pase el evento y salga este resultado
            "prob_evento": prob, "directo": directo,
            "rutina": ev.get("prob_mensual" if mensual else "prob_anual") == 1,  # pasa siempre (alza anual, ánimo, un mes más)
            **({"mes": self.mes} if mensual and self.mes else {}),
        }
        self.registro["eventos"].append(anotado)
        antes = self._plata()
        sueldo_antes = self.e["sueldo"]
        self._aplicar(resultado["efectos"], f"{sitio}:{resultado['id']}")
        self._anotar_plata(anotado, antes)
        if id_ in ALZAS and sueldo_antes > 0 and abs(self.e["sueldo"] - sueldo_antes) < 1:
            # el sueldo es en pesos de hoy: un alza de 0 es un año en que solo te reajustaron por inflación.
            # Se cuenta como noticia, para que el sueldo igual al peso no parezca un error.
            anotado.update(texto=SOLO_IPC, rutina=False, directo=True)
        if id_ == MES_BUSCANDO:
            self.meses_buscando += 1
            self._meses_buscando_anio += 1
        self._encolar_luego(resultado.get("luego"))
        self._espera_tipo = False

    # ------------------------------------------------------------------ cierre
    def _cerrar(self) -> dict:
        e = self.e
        trabaja = e["estado"] in ("empleado", "independiente", "fundador")
        # cómo se movió la plata al cerrar el año, para explicársela a la persona
        plata = {"tasa_ahorro": e["tasa_ahorro"], "retorno_real": self.pq.k("RETORNO_REAL")}
        if e["estado"] == "empleado" and e["alza_extra_anual"]:
            plata["alza_extra"] = e["alza_extra_anual"]
            e["sueldo"] = self._acotar("sueldo", e["sueldo"] * (1 + e["alza_extra_anual"]))

        # plata: los meses que pasaste buscando no hubo sueldo (lo que se gastó esos meses ya salió del ahorro, mes a mes)
        meses_antes, sueldo_antes = self._antes_del_despido
        meses_con_sueldo = max(0, 12 - min(12, self._meses_buscando_anio) - meses_antes)
        if self._meses_buscando_anio:
            plata["meses_sin_sueldo"] = min(12, self._meses_buscando_anio)
        if e["estado"] == "buscando" and not self._meses_buscando_anio:
            self.meses_buscando += 12  # un año buscando sin vivirlo mes a mes (la primera pega)
        ganado = meses_con_sueldo * e["sueldo"] + meses_antes * sueldo_antes
        self.ingreso_total += ganado
        plata["ganado"] = round(ganado)
        if ganado > 0:
            plata["ahorrado"] = round(ganado * e["tasa_ahorro"])
            e["ahorro"] += ganado * e["tasa_ahorro"]
        if e["deuda_estudios"] > 0 and e["estado"] != "estudiando" and e["sueldo"] > 0:
            pago = min(e["deuda_estudios"], meses_con_sueldo * e["sueldo"] * PAGO_DEUDA_ESTUDIOS)
            plata["deuda_estudios"] = round(pago)
            e["deuda_estudios"] -= pago
            e["ahorro"] -= pago
        if e["ahorro"] > 0:
            plata["retorno"] = round(e["ahorro"] * self.pq.k("RETORNO_REAL"))
            e["ahorro"] *= 1 + self.pq.k("RETORNO_REAL")
        self.registro["plata"] = plata

        # trabajo
        if trabaja:
            e["skill"] = self._acotar("skill", e["skill"] + SKILL_POR_ANIO * e["aprendizaje"])
        if e["estado"] == "empleado":
            e["antiguedad"] = self._acotar("antiguedad", e["antiguedad"] + 1)
            e["anos_en_startup"] = e["anos_en_startup"] + 1 if e["tipo_empleador"] == "startup" else 0
            if e["sueldo"] > 0:
                e["sueldo_ref"] = e["sueldo"]
        else:
            e["antiguedad"] = 0
            e["anos_en_startup"] = 0
        if e["cierra_en"] > 0:
            e["cierra_en"] -= 1
            if e["cierra_en"] == 0 and e["estado"] == "empleado" and e["tipo_empleador"] == "startup":
                self._evento("startup_cierra", directo=True)
                e = self.e
        if e["estado"] == "independiente" and self.dados.u(self.anio, "independiente:vuelve") < p_independiente_busca_empleo(e):
            e.update(estado="buscando", sueldo=0.0, primer_empleo=1 if e["sueldo_ref"] <= 0 else 0)
        if e["deja_de_trabajar"]:
            if e["sueldo"] > 0:
                e["sueldo_ref"] = e["sueldo"]
            e.update(estado="inactivo", sueldo=0.0, deja_de_trabajar=0)

        # estudios
        # sin carrera del catálogo, estudia lo que supone perfil.estudio_sin_carrera (semestres puestos al partir)
        if e["estado"] == "estudiando" and (e["carrera_id"] >= 0 or e["semestres_restantes"] > 0):
            e["semestres_restantes"] -= 2
            e["anos_en_carrera"] += 1
            if e["semestres_restantes"] <= 0:
                titulo = EDU_AL_TITULARSE.get(e["tipo_institucion"]) or estudio_sin_carrera(
                    e["edu"], tipo_institucion_de(self.pq, e.get("universidad_id", "")))[0]
                # recién titulado de pregrado: su primera pega parte en Junior (el cargo que traía era el del
                # perfil, por omisión semi senior). Quien termina un postgrado conserva el cargo que declaró.
                nivel = e["nivel"] if titulo == "postgrado" else 0
                e.update(edu=titulo, estado="buscando", nivel=nivel,
                         primer_empleo=1, anos_titulado=0, semestres_restantes=0, anos_en_carrera=0)
        elif e["estado"] != "estudiando":
            e["anos_titulado"] = self._acotar("anos_titulado", e["anos_titulado"] + 1)
        if e["estado"] == "inactivo" and e["edad"] + 1 == e["edad_decide_estudios"]:
            e.update(estado="buscando", primer_empleo=1)  # tras la pausa del colegio, sale a trabajar

        # una pausa elegida pesa dos años
        self._anios_con_hueco = self._anios_con_hueco + 1 if e["hueco"] else 0
        if self._anios_con_hueco >= ANIOS_HUECO:
            e["hueco"], self._anios_con_hueco = 0, 0

        # efectos con duración
        vigentes = []
        for t in self.temporales:
            t["quedan"] -= 1
            if t["quedan"] > 0:
                vigentes.append(t)
            elif t["op"] == "suma":
                e[t["var"]] -= t["valor"]
            elif t["op"] == "multiplica":
                e[t["var"]] = e[t["var"]] / t["valor"] if t["valor"] else t["previo"]
            else:
                e[t["var"]] = t["previo"]
        self.temporales = vigentes
        self._cumplir_diferidos()
        e = self.e  # aplicar efectos re-deriva el estado (otro dict)

        if e["estado"] == "buscando":
            self.anios_buscando += 1
        e["edad"] += 1
        self.anio += 1
        self._derivar()
        self.registro["fin"] = self.resumen()
        self.historia.append(self.registro)
        cerrado, self.registro = self.registro, None
        return cerrado

    # ------------------------------------------------------------------ lectura
    def sueldo_o_ultimo(self) -> float:
        """El sueldo actual o, si está sin trabajo, el último que tuvo. Para mostrar, no para comparar."""
        return self.e["sueldo"] if self.e["sueldo"] > 0 else self.e["sueldo_ref"]

    def sueldo_al_final(self) -> float:
        """Lo que gana hoy: 0 si está sin trabajo o estudiando. Es lo que se compara entre opciones, para
        que terminar cesante no empate con terminar empleado con el último sueldo."""
        return self.e["sueldo"]

    def resumen(self) -> dict:
        e = self.e
        return {
            "edad": e["edad"], "estado": e["estado"], "sueldo": round(e["sueldo"]),
            "sueldo_ref": round(e["sueldo_ref"]), "nivel": e["nivel"], "cargo": NIVELES[e["nivel"]],
            "tipo_empleador": e["tipo_empleador"], "rubro": e["rubro"], "edu": e["edu"],
            "ocupacion": e["ocupacion"], "antiguedad": e["antiguedad"], "ahorro": round(e["ahorro"]),
            "tasa_ahorro": e["tasa_ahorro"], "meses_cesante": e["meses_cesante"],
            "ingreso_total": round(self.ingreso_total),  # lo ganado en sueldos desde que empezó la partida
            "percentil": e["percentil"], "exposicion_ia": e["exposicion_ia"],
            "primer_empleo": e["primer_empleo"],
            "empresa_id": e.get("empresa_id", -1), "empresa": self._nombre_empresa(), "rol": self._nombre_cargo(),
            "ia_adopcion": round(e.get("ia_adopcion", 0.5), 3),
            "ia_ritmo": e.get("ia_ritmo", "medio"), "ia_tipo": e.get("ia_tipo", "no_afectado"),
            "adaptabilidad": e.get("adaptabilidad", 0.5), "usa_ia": e.get("usa_ia", 0),
        }

    def _nombre_empresa(self) -> str | None:
        """La empresa del catálogo o, mientras siga en el empleo con que partió, la que contó la persona."""
        emp = empresas.empresa(self.pq, self.e.get("empresa_id", -1))
        return emp["nombre"] if emp else self.e.get("empresa_inicial") or None

    def _nombre_cargo(self) -> str | None:
        if self.e.get("estado") != "empleado":
            return None
        car = empresas.cargo(self.pq, self.e.get("cargo_id", -1))
        return car["nombre"] if car else self.e.get("cargo_inicial") or None
