"""Hallazgos de la revisión M5 que se corrigieron: quedan como tests de regresión.

Los pendientes estaban marcados `xfail` y se sacaron para acelerar la suite; la lista está en
docs/motor/TICKETS.md (M12). El detalle está en el informe M5.
"""

import re

import pytest
from _motor_util import NADA, DadosGuion, Guion, pq, vida

from app.sim.motor import gemelos, partida
from app.sim.motor.azar import Dados
from app.sim.motor.perfil import Perfil
from app.sim.motor.politicas import Fija

QUIETA = {"oferta_externa": "quedarse"}
CESANTE = Perfil(edad=30, estado="buscando", sueldo=1_000_000)


# ------------------------------------------------------------------ errores del año y del cierre
def test_quien_vuelve_del_trabajo_por_cuenta_propia_no_queda_empleado_con_sueldo_cero():
    """Corregido durante la revisión (era el error más grave: 13% de la cohorte terminaba empleada con
    sueldo 0). Quien nunca fue empleado y deja el trabajo por cuenta propia no tiene sueldo de
    referencia: ahora busca como primera pega en vez de cobrar sueldo_ref (0) x azar para siempre."""
    d = DadosGuion({"independiente:vuelve": 0.0, "dec:cesantia:rapido": 0.0, "dec:tipo_de_empleador:sorteo": 0.5,
                    (1, "dec:primera_pega:pyme"): 0.0})
    v = vida(Perfil.a_los_18(), d)
    guion = Guion({"salir_del_colegio": "trabajar", "primera_pega": ["independiente", "pyme"], "cesantia": "rapido",
                   **QUIETA})
    v.vivir_anio(guion)
    assert v.e["estado"] == "buscando" and v.registro is None  # trabajó por su cuenta y ese año lo dejó
    v.vivir_anio(guion)
    assert v.e["estado"] == "empleado"
    assert v.e["sueldo"] > 0


def test_bootcamp_desde_la_cesantia_no_revienta_el_anio():
    """Corregido durante la revisión. bootcamp/colocado dejaba 'empleado' sin tipo de empleador a quien
    nunca tuvo uno y el evento separacion_empleo reventaba (clave '' no está en MULT_DESPIDO_TIPO)."""
    d = DadosGuion({"dec:bootcamp:hacer": 0.0})
    v = vida(CESANTE, d)
    v.vivir_anio(Guion({"cesantia": "bootcamp", "bootcamp": "hacer", **QUIETA}))
    assert v.e["estado"] == "empleado" and v.e["tipo_empleador"] != ""


def test_mas_meses_cesante_nunca_ayuda_a_encontrar_trabajo():
    """Corregido. cesantia/rapido sumaba 0,1 x min(3, meses/12): con 7 meses encontraba más rápido (0,84) que
    recién despedido (0,78), con 8 caía a 0,51 por el hueco y con 36 volvía a 0,75. Ahora la cesantía se vive
    mes a mes: la oferta de cada mes (oferta_cesante) baja de forma lineal hasta PENAL_HUECO a los 8 meses
    (Kroft 2013) y el hueco en el CV la castiga otra vez; nunca sube con los meses."""
    from dataclasses import replace
    from itertools import pairwise

    base = Perfil(edad=30, estado="buscando", sueldo=1_400_000)
    prob = pq().eventos["oferta_cesante"]["prob_mensual"]
    ps = [pq().evaluar(prob, vida(replace(base, meses_cesante=m)).e) for m in range(61)]
    assert all(b <= a for a, b in pairwise(ps))
    # también dentro de la simulación, sin el hueco del CV: los meses que lleva no la suben
    sin_hueco = [pq().evaluar(prob, vida(base, meses_cesante=m).e) for m in range(61)]
    assert all(b <= a for a, b in pairwise(sin_hueco))
    assert ps[0] == pytest.approx(1.8 / 10.5)  # recién despedido a los 30-44: K_OFERTA_CESANTE / MESES_CESANTIA


@pytest.mark.parametrize("estado", ["fundador", "independiente", "buscando"])
def test_emigrar_es_para_quien_se_va_con_trabajo(estado):
    """Corregido. emigrar no pedía estar empleado: a un fundador "irse" le multiplicaba por 3,5 el sueldo y lo
    dejaba fundador en EE.UU.; a un cesante, buscando afuera con sueldo 0. El premio de Clemens es sobre el
    sueldo de un trabajador idéntico: la carta ahora pide estado == 'empleado' (decisiones.json)."""
    v = vida(Perfil(edad=30, estado=estado, sueldo=1_400_000, ingles=1))
    assert not v.aplica("emigrar") and "emigrar" not in dict(v.cartas_posibles())
    assert "emigrar" not in [d["decision"] for d in partida.dudas_posibles(Perfil(edad=30, estado=estado, ingles=1))]
    empleada = vida(Perfil(edad=30, ingles=1), DadosGuion({"dec:emigrar:irse": 0.0}))
    assert empleada.aplica("emigrar")
    empleada.vivir_anio(Guion({"emigrar": "irse", **QUIETA}), carta="emigrar")
    assert (empleada.e["estado"], empleada.e["pais"], empleada.e["tipo_empleador"]) == ("empleado", "afuera", "extranjero")


def test_dos_ofertas_en_el_mismo_anio_se_sortean_por_separado():
    pares = []
    for g in range(400):
        v = vida(Perfil(edad=24), DadosGuion({"evento:oferta_llega": 0.0, "evento:separacion_empleo": NADA},
                                             defecto=0.5, semilla=6, gemelo=g))
        # el guion nombra los eventos sin el número de pega: al aceptar la primera oferta, la oferta pasa a `@1`
        v.dados.u = lambda anio, sitio, _d=v.dados: _d.guion.get(re.sub(r"@\d+", "", sitio),
                                                                 Dados(6, _d._reales.gemelo).u(anio, sitio))
        reg = v.vivir_anio(Guion({"oferta_externa": "cambiar"}, con_cartas=True), carta="oferta_externa")
        ofertas = [x["resultado"] for x in reg["decisiones"] if x["decision"] == "oferta_externa"]
        assert len(ofertas) == 2
        pares.append(ofertas[0] == ofertas[1])
    # independientes coincidirían cerca de la mitad de las veces (0,54² + 0,46²)
    assert sum(pares) < 0.6 * len(pares)


def test_terminar_el_doctorado_conserva_el_premio_en_el_sueldo_de_referencia():
    """Corregido durante la revisión: al quedar 'buscando' con sueldo, el motor pisaba sueldo_ref y
    borraba el premio del doctorado (x 1,13) que el mismo resultado acababa de aplicar."""
    v = vida(Perfil(edad=30, sueldo=1_000_000), DadosGuion({"dec:doctorado:ir": 0.0}))
    v.vivir_anio(Guion({"doctorado": "ir"}), carta="doctorado")
    assert v.e["edu"] == "postgrado" and v.e["estado"] == "buscando" and v.e["sueldo"] == 0
    assert v.e["sueldo_ref"] == pytest.approx(1_000_000 * 1.13)


# ------------------------------------------------------------------ efectos con duración
# ------------------------------------------------------------------ alcance completo
# ------------------------------------------------------------------ decisiones con elección interna
# ------------------------------------------------------------------ gemelos y políticas
def test_los_gemelos_que_eligen_bootcamp_en_la_cesantia_hacen_el_bootcamp():
    """Corregido. comparar(cesantia): la opción 'bootcamp' encadena la decisión bootcamp y ahí los gemelos
    (Inercia, sin pesos para esa decisión) elegían siempre 'no': la columna 'bootcamp' era en realidad 'no
    hacer nada este año'. Ahora la decisión encadenada respeta lo que ya eligieron (PESOS_ENCADENADAS)."""
    hicieron = 0
    for g in range(40):
        v = vida(CESANTE, Dados(0, g), tipo_empleador="pyme", rubro="Comercio")
        v.vivir_anio(Fija("cesantia", "bootcamp"), carta="cesantia")
        hicieron += ("bootcamp", "hacer") in [(d["decision"], d["opcion"]) for d in v.historia[0]["decisiones"]]
    assert hicieron == 40


def test_el_bootcamp_como_carta_suelta_sigue_respondiendose_con_su_peso_de_carta():
    """Lo encadenado no se filtra a la carta: si el bootcamp sale como carta, Inercia no lo busca (no hace
    nada) y la población lo hace con su peso de carta."""
    from app.sim.motor.politicas import Inercia, Poblacion

    v = vida(CESANTE, Dados(0, 0), tipo_empleador="pyme", rubro="Comercio")
    v.iniciar_anio(False, carta="bootcamp")
    d = pq().decisiones["bootcamp"]
    assert Inercia().elegir(v, d, v.opciones("bootcamp"))[0] == "no"
    hacen = 0
    for g in range(400):
        v = vida(CESANTE, Dados(0, g), tipo_empleador="pyme", rubro="Comercio")
        v.iniciar_anio(True, carta="bootcamp")
        hacen += Poblacion().elegir(v, d, v.opciones("bootcamp"))[0] == "hacer"
    assert 0.03 < hacen / 400 < 0.15  # PESOS_CARTAS: 0,08


def test_comparar_no_cuenta_dos_veces_al_gemelo_que_ya_no_tiene_historia():
    """Guardia: la comparación tolera vidas que terminan antes (60 años)."""
    v = vida(Perfil(edad=50, nivel=2), Dados(0, "tu"))
    c = gemelos.comparar(v, "pedir_aumento", n=10, anios=10, semilla=1)
    assert all(len(o["trayectoria"]) == 10 for o in c["opciones"])


