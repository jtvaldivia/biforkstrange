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
from dataclasses import dataclass, field

from app.sim.motor.azar import Dados
from app.sim.motor.paquete import Paquete
from app.sim.motor.perfil import NIVELES

# "Solo lo laboral": fuera las decisiones de vida personal y los eventos de salud, duelo y pareja.
DECISIONES_PERSONALES = frozenset(
    {"tener_hijo", "formalizar_pareja", "separarse", "buscar_pareja", "cuidar_familiar", "comprar_vivienda"}
)
EVENTOS_PERSONALES = frozenset(
    {"cancer", "muere_madre", "muere_padre", "enferma_familiar", "forma_pareja", "termina_pareja",
     "hijo_no_planificado", "herencia"}
)
EVENTO_MUNDO = "recesion"
EDAD_MAXIMA = 60

# Reglas del cierre de año que el paquete deja al simulador. Supuestos del equipo.
SKILL_POR_ANIO = 1.5            # oficio que suma un año trabajado
PAGO_DEUDA_ESTUDIOS = 0.10      # parte del sueldo que paga el crédito (regla del CAE)
ANIOS_HUECO = 2                 # cuánto pesa una pausa elegida al buscar trabajo
EDU_AL_TITULARSE = {"U": "universitaria", "IP": "tecnica", "CFT": "tecnica"}
# Decisiones donde el modificador p_encontrar multiplica la probabilidad de quedar
BUSQUEDAS = frozenset({"cesantia", "primera_pega"})
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
        self.historia: list[dict] = []
        self.registro: dict | None = None
        self.anios_buscando = 0
        self.ingreso_total = 0.0
        self._anios_con_hueco = 0
        self._derivar(inicio=True)
        self.reparto: dict | None = None

    # ------------------------------------------------------------------ copia
    def clonar(self, dados: Dados | None = None) -> "Vida":
        otra = copy.copy(self)
        otra.e = dict(self.e)
        otra.cola = list(self.cola)
        otra.temporales = [dict(t) for t in self.temporales]
        otra.historia = list(self.historia)
        otra.registro = copy.deepcopy(self.registro)
        if dados is not None:
            otra.dados = dados
        return otra

    # ------------------------------------------------------------------ alcance
    def _decision_en_alcance(self, id_: str) -> bool:
        return self.alcance != "laboral" or id_ not in DECISIONES_PERSONALES

    def _evento_en_alcance(self, id_: str) -> bool:
        return self.alcance != "laboral" or id_ not in EVENTOS_PERSONALES

    # ------------------------------------------------------------------ estado derivado
    def _derivar(self, inicio: bool = False) -> None:
        previa = self.e.get("pareja_previa")
        self.e = self.pq.derivar(self.e)
        if not inicio and previa is not None:
            self.e["pareja_previa"] = previa  # es la situación al inicio del año
        ascenso = self.pq.eventos["ascenso"]
        aplica = self.pq.evaluar(ascenso["cuando"], self.e)
        self.e["prob_ascenso"] = self.pq.evaluar(ascenso["prob_anual"], self.e) if aplica else 0.0

    def terminada(self) -> bool:
        return self.e["edad"] >= EDAD_MAXIMA

    # ------------------------------------------------------------------ año
    def iniciar_anio(self, con_cartas: bool, carta: str | None = None) -> None:
        """Sortea el mundo y arma la cola del año. `carta` fuerza la decisión (la duda inicial)."""
        if self.cola:
            raise RuntimeError("el año en curso no ha terminado")
        self.registro = {"anio": self.anio + 1, "edad": self.e["edad"], "recesion": False,
                         "decisiones": [], "eventos": []}
        self.reparto = None  # cómo se sorteó la carta de este año, si hubo sorteo
        self._derivar(inicio=True)
        self._evento(EVENTO_MUNDO)
        self.registro["recesion"] = bool(self.e["recesion"])
        if carta is not None:
            decisiones = [carta]
        else:
            decisiones = self._forzadas()
            if not decisiones and con_cartas:
                sorteada = self._sortear_carta()
                decisiones = [sorteada] if sorteada else []
        self.cola = self.cola + [("decision", d, "carta") for d in decisiones]
        self.cola += [("evento", id_) for id_ in self.pq.eventos if id_ != EVENTO_MUNDO and self._evento_en_alcance(id_)]
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
                self._evento(paso[1])
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
    def aplica(self, decision_id: str) -> bool:
        d = self.pq.decisiones[decision_id]
        return bool(self.pq.evaluar(d["cuando"], self.e)) and bool(self.opciones(decision_id))

    def _forzadas(self) -> list[str]:
        return [id_ for id_, d in self.pq.decisiones.items()
                if d["aparicion"]["tipo"] == "forzada" and self._decision_en_alcance(id_) and self.aplica(id_)]

    def cartas_posibles(self) -> list[tuple[str, float]]:
        """Cartas que podrían salir este año, con su peso."""
        salida = []
        for id_, d in self.pq.decisiones.items():
            if d["aparicion"]["tipo"] != "carta" or not self._decision_en_alcance(id_) or not self.aplica(id_):
                continue
            peso = self.pq.evaluar(d["aparicion"]["peso"], self.e)
            if id_ == "renunciar":
                peso *= self.e["p_renuncia"]
            if peso > 0:
                salida.append((id_, float(peso)))
        return salida

    def _sortear_carta(self) -> str | None:
        cartas = self.cartas_posibles()
        if not cartas:
            return None
        elegida = cartas[self.dados.elegir(self.anio, "carta", [p for _, p in cartas])][0]
        total = sum(p for _, p in cartas)
        self.reparto = {"carta": elegida, "prob": dict(cartas)[elegida] / total, "posibles": len(cartas)}
        return elegida

    def opciones(self, decision_id: str) -> list[Opcion]:
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
        d = self.pq.decisiones[decision_id]
        vigente = self._decision_en_alcance(decision_id) and (origen != "carta" or self.pq.evaluar(d["cuando"], self.e))
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
        sitio = f"dec:{decision_id}:{opcion_id}" + (f":{ocurrencia}" if ocurrencia else "")
        contexto = {k: self.e[k] for k in ("edad", "rubro", "tipo_empleador", "nivel", "region", "ocupacion", "estado", "antiguedad")}
        if opcion.costo:
            self._aplicar(opcion.costo, sitio + ":costo", opcion.fila)
        resultado, prob = self._sortear(opcion.resultados, sitio, decision_id)
        self.registro["decisiones"].append({
            "decision": decision_id, "nombre": d["nombre"], "pregunta": d["pregunta"], "origen": origen,
            "opcion": opcion.id, "opcion_nombre": opcion.nombre,
            "resultado": resultado["id"] if resultado else None,
            "texto": resultado["texto"] if resultado else "", "tono": (resultado or {}).get("tono", "neutro"),
            "prob": prob, "ocurrencia": ocurrencia, "contexto": contexto,
        })
        if resultado:
            self._aplicar(resultado["efectos"], sitio + ":" + resultado["id"], opcion.fila)
            self._encolar_luego(resultado.get("luego"))

    def _encolar_luego(self, luego: str | None) -> None:
        if not luego:
            return
        if luego in self.pq.decisiones:
            if self._decision_en_alcance(luego):
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
                p *= self.e["p_encontrar"]
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
        for ef in efectos:
            exprs = [x for x in (ef.get("cuando"), ef["valor"]) if x is not None]
            if flujo is None and any(self.pq.compilar(x)[1] for x in exprs):
                flujo = self.dados.flujo(self.anio, sitio)
            if ef.get("cuando") and not self.pq.evaluar(ef["cuando"], antes, flujo):
                continue
            valor = self.pq.evaluar(ef["valor"], antes, flujo)
            var = ef["var"]
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
            if ef.get("duracion"):
                self.temporales.append({"quedan": ef["duracion"], "var": var, "op": ef["op"],
                                        "valor": valor, "previo": previo})
        self._completar_empleo(ref_movido=self.e["sueldo_ref"] != antes["sueldo_ref"])
        self._derivar()

    def _completar_empleo(self, ref_movido: bool = False) -> None:
        """El paquete no dice en qué rubro cae quien entra a un empleo sin venir de uno:
        se sortea según cuánta gente ocupada hay en cada rubro (ESI)."""
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
            return
        if not e["tipo_empleador"] and ("decision", "tipo_de_empleador", "luego") not in self.cola[:1]:
            # reglas como bootcamp/colocado emplean sin decir en qué tipo de empresa: se sortea
            self.cola.insert(0, ("decision", "tipo_de_empleador", "luego"))
        if e["tipo_empleador"] == "publico":
            e["rubro"] = "Administración pública"
        elif not e["rubro"] or e["rubro"] == "Administración pública":
            rubros, pesos = self._rubros_privados()
            e["rubro"] = rubros[self.dados.elegir(self.anio, "rubro", pesos)]

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

    def _evento(self, id_: str, directo: bool = False) -> None:
        ev = self.pq.eventos[id_]
        prob = 1.0
        if not directo:
            if not self.pq.evaluar(ev["cuando"], self.e):
                return
            prob = min(max(float(self.pq.evaluar(ev["prob_anual"], self.e)), 0.0), 1.0)
            if self.dados.u(self.anio, f"evento:{id_}") >= prob:
                return
        resultado, prob_resultado = self._sortear(ev["resultados"], f"evento:{id_}:res")
        if resultado is None:
            return
        self.registro["eventos"].append({
            "evento": id_, "nombre": ev["nombre"], "resultado": resultado["id"], "texto": resultado["texto"],
            "tono": resultado.get("tono", "neutro"),
            "prob": prob * prob_resultado,  # de que pase el evento y salga este resultado
            "prob_evento": prob, "directo": directo,
            "rutina": ev["prob_anual"] == 1,  # pasa todos los años (alza anual, ánimo)
        })
        self._aplicar(resultado["efectos"], f"evento:{id_}:{resultado['id']}")
        self._encolar_luego(resultado.get("luego"))

    # ------------------------------------------------------------------ cierre
    def _cerrar(self) -> dict:
        e = self.e
        trabaja = e["estado"] in ("empleado", "independiente", "fundador")
        if e["estado"] == "empleado" and e["alza_extra_anual"]:
            e["sueldo"] *= 1 + e["alza_extra_anual"]

        # plata
        self.ingreso_total += 12 * e["sueldo"]
        if e["sueldo"] > 0:
            e["ahorro"] += 12 * e["sueldo"] * e["tasa_ahorro"]
        if e["deuda_estudios"] > 0 and e["estado"] != "estudiando" and e["sueldo"] > 0:
            pago = min(e["deuda_estudios"], 12 * e["sueldo"] * PAGO_DEUDA_ESTUDIOS)
            e["deuda_estudios"] -= pago
            e["ahorro"] -= pago
        if e["ahorro"] > 0:
            e["ahorro"] *= 1 + self.pq.k("RETORNO_REAL")

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
        if e["estado"] == "estudiando" and e["carrera_id"] >= 0:
            e["semestres_restantes"] -= 2
            e["anos_en_carrera"] += 1
            if e["semestres_restantes"] <= 0:
                e.update(edu=EDU_AL_TITULARSE.get(e["tipo_institucion"], e["edu"]), estado="buscando",
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

        if e["estado"] == "buscando":
            self.anios_buscando += 1
        e["edad"] += 1
        self.anio += 1
        self._derivar(inicio=True)
        self.registro["fin"] = self.resumen()
        self.historia.append(self.registro)
        cerrado, self.registro = self.registro, None
        return cerrado

    # ------------------------------------------------------------------ lectura
    def sueldo_o_ultimo(self) -> float:
        """El sueldo actual o, si está sin trabajo, el último que tuvo."""
        return self.e["sueldo"] if self.e["sueldo"] > 0 else self.e["sueldo_ref"]

    def resumen(self) -> dict:
        e = self.e
        return {
            "edad": e["edad"], "estado": e["estado"], "sueldo": round(e["sueldo"]),
            "sueldo_ref": round(e["sueldo_ref"]), "nivel": e["nivel"], "cargo": NIVELES[e["nivel"]],
            "tipo_empleador": e["tipo_empleador"], "rubro": e["rubro"], "edu": e["edu"],
            "ocupacion": e["ocupacion"], "antiguedad": e["antiguedad"], "ahorro": round(e["ahorro"]),
            "percentil": e["percentil"], "exposicion_ia": e["exposicion_ia"],
            "primer_empleo": e["primer_empleo"],
        }
