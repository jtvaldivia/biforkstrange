"""La incertidumbre de la IA (app/sim/motor/ia.py): el ritmo de cada mundo, el tipo de tu cargo y lo que mueven.

Los tests con @pytest.mark.ia corren con la flag prendida; los demás, apagada (conftest.py).
"""

from collections import Counter

import pytest

from _motor_util import Guion, pq, vida
from app.sim.motor import gemelos, ia, partida
from app.sim.motor.azar import Dados
from app.sim.motor.perfil import Perfil

ATENCION_CLIENTE = 77  # Ejecutivo de atención al cliente: Contact Centre Information Clerks, la OIT la pone en automatización
PROFESOR_MEDIA = 49    # Secondary Education Teachers: aumento


# ------------------------------------------------------------------ flag apagada: el juego de antes
def test_apagada_no_cambia_nada():
    v = vida(Perfil(edad=24), Dados(0, 0), cargo_id=ATENCION_CLIENTE)
    assert v.e["ia_v2"] == 0 and v.e["ia_encontrar"] == 1.0 and v.e["ia_rampa"] == 0.0
    assert 0.75 <= v.e["ia_castigo_joven"] <= 0.9
    assert [o.id for o in v.opciones("aprender_ia")] == ["aprender", "ignorar"]
    for _ in range(5):
        reg = v.vivir_anio(_Quieta())
        assert "ia" not in reg
        assert not {"burbuja_ia", "auge_cobre", "ia_empresa_adopta", "ia_reestructura"} & {x["evento"] for x in reg["eventos"]}


class _Quieta:
    """Elige siempre la última opción (no hacer nada) y no recibe cartas."""
    con_cartas = False

    def elegir(self, vida, decision, opciones):
        return opciones[-1].id, {}


# ------------------------------------------------------------------ el ritmo del mundo
@pytest.mark.ia
def test_el_ritmo_sale_con_los_pesos_del_fri_y_es_igual_entre_opciones():
    base = vida(Perfil(), Dados(5, "tu"))
    mundos = [base.clonar(Dados(5, g)) for g in range(2000)]
    cuenta = Counter(m.e["ia_ritmo"] for m in mundos)
    pesos = pq().k("P_RITMO_IA")
    for r in ia.RITMOS:
        assert cuenta[r] / 2000 == pytest.approx(pesos[r], abs=0.035)
    assert all(m.e["ia_castigo_joven"] == 1.0 for m in mundos[:50])  # el golpe joven lo lleva ia_encontrar
    assert base.clonar(Dados(5, 7)).e["ia_ritmo"] == mundos[7].e["ia_ritmo"]  # el mismo mundo en otra opción


@pytest.mark.ia
def test_el_ritmo_corta_en_los_pesos_acumulados():
    assert ia.ritmo(pq(), 0.0) == "lento" and ia.ritmo(pq(), 0.41) == "lento"
    assert ia.ritmo(pq(), 0.43) == "medio" and ia.ritmo(pq(), 0.86) == "medio"
    assert ia.ritmo(pq(), 0.88) == "rapido" and ia.ritmo(pq(), 0.999) == "rapido"


# ------------------------------------------------------------------ cómo te toca
@pytest.mark.ia
def test_el_tipo_sale_del_cargo_y_un_programa_largo_lo_vuelve_complementado(monkeypatch):
    e = vida(Perfil(), Dados(0, 0), cargo_id=ATENCION_CLIENTE).e
    assert e["ia_tipo"] == "automatiza"
    assert vida(Perfil(), Dados(0, 0), cargo_id=PROFESOR_MEDIA).e["ia_tipo"] == "aumenta"
    assert ia.tipo(pq(), {**e, "ia_reconvertido": 1}) == "aumenta"
    # sin cargo del catálogo, el empleo de hoy toma el tipo de los cargos que calzan con él desde el año 0
    oficinista = vida(Perfil(edad=24, edu="media", ocupacion=4, rubro="Comercio", nivel=0, sueldo=600000), Dados(0, 0)).e
    assert oficinista["cargo_id"] == -1 and oficinista["ia_tipo"] == "automatiza"
    # respaldo, solo si ningún cargo calza
    monkeypatch.setattr(ia, "tipo_de_hoy", lambda pq_, e_: None)
    assert ia.tipo(pq(), {"cargo_id": -1, "exposicion_ia": 0.5}) == "incognita"
    assert ia.tipo(pq(), {"cargo_id": -1, "exposicion_ia": 0.05}) == "no_afectado"


@pytest.mark.ia
def test_la_brecha_de_contratacion_crece_con_el_ritmo_y_tiene_piso():
    e = {"ia_v2": 1, "edad": 24, "ia_tipo": "automatiza", "ia_anios": 4}
    lento, medio, rapido = (ia.encontrar(pq(), {**e, "ia_ritmo": r}) for r in ia.RITMOS)
    assert 1 > lento > medio > rapido >= pq().k("IA_PISO_ENCONTRAR")
    assert ia.encontrar(pq(), {**e, "ia_ritmo": "lento", "ia_anios": 0}) == pytest.approx(pq().k("IA_JOVEN"))
    rapido_2030 = ia.encontrar(pq(), {**e, "ia_ritmo": "rapido", "ia_anios": pq().k("IA_RAMPA_ANIOS")})
    assert ia.encontrar(pq(), {**e, "ia_ritmo": "rapido", "ia_anios": 60}) == rapido_2030  # después de 2030 no crece
    assert ia.encontrar(pq(), {**e, "ia_ritmo": "rapido", "edad": 40}) == 1.0
    assert ia.encontrar(pq(), {**e, "ia_ritmo": "rapido", "ia_tipo": "aumenta"}) == 1.0
    assert ia.encontrar(pq(), {**e, "ia_v2": 0, "ia_ritmo": "rapido"}) == 1.0


@pytest.mark.ia
def test_la_adaptabilidad_baja_con_la_edad_y_sube_con_estudios_y_ahorro():
    base = {"edad": 28, "edu": "universitaria", "region": "rm", "sueldo_ref": 1_000_000, "ahorro": 6_000_000, "usa_ia": 1}
    alta = ia.adaptabilidad(pq(), base)
    assert alta == pytest.approx(1.0, abs=0.15)
    assert ia.adaptabilidad(pq(), {**base, "edad": 55}) < alta
    assert ia.adaptabilidad(pq(), {**base, "edu": "media", "ahorro": 0, "usa_ia": 0, "region": "otra"}) < 0.5


# ------------------------------------------------------------------ eventos
@pytest.mark.ia
def test_la_reestructuracion_solo_pasa_con_ia_rapida_y_donde_la_ia_automatiza():
    ev = pq().eventos["ia_reestructura"]
    e = dict(vida(Perfil(edad=35), Dados(0, 0), cargo_id=ATENCION_CLIENTE).e, ia_rampa=1.0)
    prob = {r: pq().evaluar(ev["prob_anual"], {**e, "ia_ritmo": r}) for r in ia.RITMOS}
    assert prob["lento"] == 0 and prob["medio"] == 0 and prob["rapido"] > 0
    aumenta = {**e, "ia_tipo": "aumenta", "ia_ritmo": "rapido"}
    assert not pq().evaluar(ev["cuando"], aumenta)


@pytest.mark.ia
def test_tu_empresa_adopta_ia_te_trae_la_decision_y_se_olvida_al_cambiarte():
    from _motor_util import DadosGuion

    v = vida(Perfil(edad=30), DadosGuion({"evento:ia_empresa_adopta@0": 0.0}), tipo_empleador="pyme", rubro="Comercio")
    v.iniciar_anio(con_cartas=False)
    with pytest.raises(Exception) as falta:
        v.avanzar(Guion({}))
    assert "liderar_adopcion_ia" in str(falta.value)
    assert v.e["ia_empresa"] == 1
    v.e["antiguedad"] = 3
    v._aplicar([{"var": "antiguedad", "op": "fija", "valor": 0}], "x")  # entra a una pega nueva
    assert v.e["ia_empresa"] == 0


@pytest.mark.ia
def test_la_habilidad_de_ia_paga_al_cambiarte_una_vez_y_menos_en_el_estado():
    r = next(r for o in pq().decisiones["oferta_externa"]["opciones"] if o["id"] == "cambiar" for r in o["resultados"])
    ef = next(x for x in r["efectos"] if x["var"] == "sueldo")
    factor = ef["valor"].split(" * ", 1)[1]  # lo que se suma al azar_uniforme de la oferta
    e = dict(vida(Perfil(), Dados(0, 0)).e, ia_v2=1, tipo_empleador="pyme", ia_reconvertido_anio=0,
             ia_anios=pq().k("IA_PRIMA_ANIOS_MIN"))
    assert pq().evaluar(factor, {**e, "ia_reconvertido": 1, "ia_anios": 1}) == 1  # antes de IA_PRIMA_ANIOS_MIN no paga
    sin, con = pq().evaluar(factor, {**e, "ia_reconvertido": 0}), pq().evaluar(factor, {**e, "ia_reconvertido": 1})
    publico = pq().evaluar(factor, {**e, "ia_reconvertido": 1, "tipo_empleador": "publico"})
    assert sin == 1 and con == pytest.approx(1 + pq().k("IA_PRIMA_SKILL")) and 1 < publico < con
    assert pq().evaluar(factor, {**e, "ia_reconvertido": 0, "usa_ia": 1}) == 1  # un curso corto no la da
    assert pq().evaluar(factor, {**e, "ia_reconvertido": 1, "ia_prima_cobrada": 1}) == 1  # se cobra una vez
    assert pq().evaluar(factor, {**e, "ia_reconvertido": 1, "ia_v2": 0}) == 1


@pytest.mark.ia
def test_aprender_ia_trae_curso_corto_y_programa_largo():
    v = vida(Perfil(edad=30), Dados(0, 0))
    assert [o.id for o in v.opciones("aprender_ia")] == ["curso_corto", "programa_largo", "no_por_ahora"]


@pytest.mark.ia
def test_la_burbuja_es_del_mundo():
    base = vida(Perfil(edad=30, tipo_empleador="startup", rubro="Información y comunicaciones"), Dados(2, "tu"))
    por_mundo = []
    for g in range(30):
        a, b = base.clonar(Dados(2, g)), base.clonar(Dados(2, g))
        a.e["nivel"] = 3  # otra vida del mismo mundo
        anios_a, anios_b = [], []
        for _ in range(6):
            anios_a.append(a.vivir_anio(_Quieta())["ia"]["burbuja"])
            anios_b.append(b.vivir_anio(_Quieta())["ia"]["burbuja"])
        assert anios_a == anios_b
        por_mundo.append(any(anios_a))
    assert any(por_mundo)


# ------------------------------------------------------------------ lo que ve la persona
@pytest.mark.ia
def test_la_comparacion_trae_el_ritmo_de_cada_mundo():
    v = vida(Perfil(edad=30), Dados(0, "tu"))
    c = gemelos.comparar(v, "pedir_aumento", n=20)
    assert len(c["ia_por_mundo"]) == 20 and set(c["ia_por_mundo"]) <= set(ia.RITMOS)


def test_apagada_la_comparacion_no_trae_ritmos():
    c = gemelos.comparar(vida(Perfil(edad=30), Dados(0, "tu")), "pedir_aumento", n=5)
    assert c["ia_por_mundo"] is None


@pytest.mark.ia
def test_la_partida_cuenta_el_ritmo_y_los_titulares():
    salida = partida.vista(Perfil(edad=30), 4, None, [], 0)
    anio = salida["anio_en_curso"] or salida["historia"][0]
    assert anio["ia"]["ritmo"] in ia.RITMOS and anio["ia"]["titular"]
    assert salida["estado"]["ia_ritmo"] in ia.RITMOS and 0 <= salida["estado"]["adaptabilidad"] <= 1


@pytest.mark.ia
def test_con_la_ia_prendida_la_cohorte_sigue_cuadrando_y_el_golpe_joven_es_chico():
    """El FRI ve el desempleo juvenil 1 a 2 puntos más alto con más IA: el juego no puede pintar más que eso."""
    from app.sim.motor.validacion import validar

    metas = {m["id"]: m for m in validar(3000, 0)["metas"]}
    validacion = [m for m in metas.values() if m["calidad"] == "validacion"]
    assert sum(m["cumple"] for m in validacion) >= len(validacion) - 1
    for id_ in ("desocupacion_18-24", "desocupacion_25-29"):
        assert -0.01 <= metas[id_]["simulado"] - metas[id_]["meta"] <= 0.035, metas[id_]


@pytest.mark.ia
def test_la_comparacion_separa_por_ritmo():
    v = vida(Perfil(edad=30), Dados(0, "tu"))
    c = gemelos.comparar(v, "pedir_aumento", n=30)
    ritmos = c["ia"]["ritmos"]
    assert sum(r["mundos"] for r in ritmos.values()) == 30
    opciones = {o["opcion"] for o in c["opciones"]}
    for r in ritmos.values():
        assert set(r["gana"]) == opciones and sum(r["gana"].values()) <= r["mundos"]


def test_las_voces_y_los_ritmos_citan_fuentes_que_existen():
    datos = ia.escenarios()
    assert set(datos["ritmos"]) == set(ia.RITMOS)
    assert all(x["fuente"] in pq().fuentes and x["url"] for x in [*datos["ritmos"].values(), *datos["voces"]])
    assert datos["fuera_del_juego_fuente"] in pq().fuentes


@pytest.mark.ia
def test_el_cierre_cuenta_el_ritmo_de_tu_mundo():
    salida = partida.vista(Perfil(edad=30), 4, None, [], n_gemelos=10, anios=1)
    for _ in range(10):
        if salida["terminada"]:
            break
        eleccion = {"opcion": salida["pendiente"]["opciones"][-1]["opcion"]}
        salida = partida.vista(Perfil(edad=30), 4, None, salida["elecciones"] + [eleccion], n_gemelos=10, anios=1)
    assert salida["cierre"]["ia"]["ritmo"] in ia.RITMOS and len(salida["cierre"]["ia"]["voces"]) >= 3
