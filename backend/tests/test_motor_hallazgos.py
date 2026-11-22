"""Hallazgos de la revisión M5: cada test describe lo que debería pasar y hoy no pasa.

Los pendientes están marcados `xfail(strict=True)`: la suite queda en verde mientras el error
exista y avisa (XPASS) el día que se corrija, para sacar la marca. Los que se corrigieron
durante la revisión quedaron como tests normales, de regresión. El detalle está en el informe M5.
"""

import pytest
from _motor_util import NADA, DadosGuion, Guion, pq, vida

from app.sim.motor import gemelos, partida
from app.sim.motor.azar import Dados
from app.sim.motor.motor import Opcion
from app.sim.motor.perfil import Perfil
from app.sim.motor.politicas import PESOS_FORZADAS, Fija, _pesos

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


def test_dos_ofertas_en_el_mismo_anio_se_sortean_por_separado():
    pares = []
    for g in range(400):
        v = vida(Perfil(edad=24), DadosGuion({"evento:oferta_llega": 0.0, "evento:separacion_empleo": NADA},
                                             defecto=0.5, semilla=6, gemelo=g))
        v.dados.u = lambda anio, sitio, _d=v.dados: _d.guion.get(sitio, Dados(6, _d._reales.gemelo).u(anio, sitio))
        reg = v.vivir_anio(Guion({"oferta_externa": "cambiar"}, con_cartas=True), carta="oferta_externa")
        ofertas = [x["resultado"] for x in reg["decisiones"] if x["decision"] == "oferta_externa"]
        assert len(ofertas) == 2
        pares.append(ofertas[0] == ofertas[1])
    # independientes coincidirían cerca de la mitad de las veces (0,54² + 0,46²)
    assert sum(pares) < 0.6 * len(pares)


@pytest.mark.xfail(strict=True, reason="motor.py _sortear: p_encontrar multiplica el primer resultado de toda opción de "
                   "cesantia y primera_pega, también de las que no son buscar trabajo (informal, bootcamp, emprender, "
                   "independiente: un solo resultado con prob 1 y sin resto). Con p_encontrar < 1 a veces no sale "
                   "ningún resultado y el registro queda con resultado None")
def test_p_encontrar_no_deja_sin_resultado_a_las_opciones_que_no_buscan_empleo():
    d = DadosGuion({"dec:cesantia:informal": 0.9})
    v = vida(CESANTE, d, p_encontrar=0.81)
    reg = v.vivir_anio(Guion({"cesantia": "informal"}))
    assert reg["decisiones"][0]["resultado"] == "trabaja" and v.e["estado"] == "independiente"


@pytest.mark.xfail(strict=True, reason="titularse_en_recesion pide anos_titulado == 0 y el motor deja anos_titulado en 0 "
                   "durante toda la carrera: cada recesión mientras estudia le suma +0,9% anual por 10 años (se apilan) "
                   "sin haber recibido el golpe de -9% (su sueldo era 0)")
def test_una_recesion_mientras_estudia_no_es_titularse_en_recesion():
    estudiante = Perfil(estado="estudiando", edad=19, edu="media", carrera_id=11, sueldo=0)
    v = vida(estudiante, DadosGuion({"evento:recesion": 0.0}), semestres_restantes=8, anos_en_carrera=1,
             financia="familia", anos_titulado=0)  # entró a los 18: el motor no mueve anos_titulado mientras estudia
    reg = v.vivir_anio(Guion({"seguir_o_desertar": "seguir"}))
    assert "titularse_en_recesion" not in [x["evento"] for x in reg["eventos"]]
    assert v.e["alza_extra_anual"] == 0


@pytest.mark.xfail(strict=True, reason="motor.py _cerrar: el cierre de la startup por plazo (cierra_en) corre después de "
                   "sumar la antigüedad; queda 'buscando' con antigüedad > 0 y, si encuentra trabajo al año siguiente, "
                   "el empleo nuevo hereda esos años (finiquito y ascenso)")
def test_al_cerrar_la_startup_la_antiguedad_vuelve_a_cero():
    v = vida(Perfil(edad=35, tipo_empleador="startup", antiguedad=3), DadosGuion(), cierra_en=1)
    v.vivir_anio(Guion(QUIETA))
    assert v.e["estado"] == "buscando"
    assert v.e["antiguedad"] == 0


@pytest.mark.xfail(strict=True, reason="meses_cesante solo se reinicia en cesantia/encuentra. Quien falla una "
                   "primera_pega (+12) y después consigue trabajo queda empleado con meses_cesante > 0; años después, "
                   "si queda cesante, parte con +0,1 de probabilidad de encontrar rápido por cada 12 meses viejos")
def test_al_conseguir_trabajo_los_meses_cesante_vuelven_a_cero():
    d = DadosGuion({(1, "dec:primera_pega:pyme"): 0.0})
    v = vida(Perfil.a_los_18(), d)
    guion = Guion({"salir_del_colegio": "trabajar", "primera_pega": "pyme", **QUIETA})
    v.vivir_anio(guion)
    assert v.e["estado"] == "buscando" and v.e["meses_cesante"] == 12
    v.vivir_anio(guion)
    assert v.e["estado"] == "empleado"
    assert v.e["meses_cesante"] == 0


def test_terminar_el_doctorado_conserva_el_premio_en_el_sueldo_de_referencia():
    """Corregido durante la revisión: al quedar 'buscando' con sueldo, el motor pisaba sueldo_ref y
    borraba el premio del doctorado (x 1,13) que el mismo resultado acababa de aplicar."""
    v = vida(Perfil(edad=30, sueldo=1_000_000), DadosGuion({"dec:doctorado:ir": 0.0}))
    v.vivir_anio(Guion({"doctorado": "ir"}), carta="doctorado")
    assert v.e["edu"] == "postgrado" and v.e["estado"] == "buscando" and v.e["sueldo"] == 0
    assert v.e["sueldo_ref"] == pytest.approx(1_000_000 * 1.13)


@pytest.mark.xfail(strict=True, reason="motor.py _cerrar no acota lo que mueve a mano (ahorro, sueldo): el pago del "
                   "crédito puede dejar el ahorro bajo el mínimo del dominio (-100 millones)")
def test_el_cierre_respeta_el_dominio_del_ahorro():
    v = vida(Perfil(edad=35, estado="independiente", sueldo=5_000_000), DadosGuion(), ahorro=-99_500_000.0,
             deuda_estudios=20_000_000.0, tasa_ahorro=0.0)
    v.vivir_anio(Guion())
    assert v.e["ahorro"] >= -100_000_000


# ------------------------------------------------------------------ efectos con duración
@pytest.mark.xfail(strict=True, reason="motor.py _cerrar: al vencer un efecto con duración no se acota el resultado. "
                   "energía 95, -15 por un año, +25 permanente (queda en 100 por el tope) y al revertir sube a 115")
def test_revertir_un_efecto_no_saca_la_variable_de_su_dominio():
    v = vida(Perfil(estado="inactivo", edad=40), DadosGuion(), energia=95)
    v.iniciar_anio(con_cartas=False)
    v._aplicar([{"var": "energia", "op": "suma", "valor": -15, "duracion": 1}], "lab")
    v._aplicar([{"var": "energia", "op": "suma", "valor": 25}], "lab2")
    v.avanzar(Guion())
    assert 0 <= v.e["energia"] <= 100


@pytest.mark.xfail(strict=True, reason="motor.py _aplicar guarda el valor pedido, no lo que de verdad cambió: energía 10, "
                   "-15 por un año queda en 0 (tope) y al revertir sube a 15. El efecto temporal deja +5 permanente")
def test_revertir_deshace_lo_que_el_efecto_cambio_de_verdad():
    v = vida(Perfil(estado="inactivo", edad=40), DadosGuion(), energia=10)
    v.iniciar_anio(con_cartas=False)
    v._aplicar([{"var": "energia", "op": "suma", "valor": -15, "duracion": 1}], "lab")
    assert v.e["energia"] == 0
    v.avanzar(Guion())
    assert v.e["energia"] == 10


# ------------------------------------------------------------------ alcance completo
@pytest.mark.xfail(strict=True, reason="nada limpia familiar_enfermo: después de que muere la madre enferma, la forzada "
                   "cuidar_familiar vuelve todos los años (y por ser forzada tapa todas las cartas), y el padre ya no "
                   "puede enfermar. Solo en alcance completo")
def test_cuando_muere_el_familiar_enfermo_se_deja_de_cuidarlo():
    d = DadosGuion({(0, "evento:muere_madre"): 0.0})
    v = vida(Perfil(edad=45), d, alcance="completo", familiar_enfermo="madre")
    guion = Guion({"cuidar_familiar": "pagar", **QUIETA})
    v.vivir_anio(guion)
    assert v.e["madre_edad"] == -1
    reg = v.vivir_anio(guion)
    assert "cuidar_familiar" not in [x["decision"] for x in reg["decisiones"]]


@pytest.mark.xfail(strict=True, reason="quien_enferma se fija en 'madre' al crear el estado y nunca se sortea (estado.json: "
                   "'lo sortea el evento enferma_familiar en proporción al riesgo de cada uno'). Con la madre muerta, "
                   "enferma_familiar enferma a la madre muerta")
def test_enferma_un_familiar_que_esta_vivo():
    d = DadosGuion({"evento:enferma_familiar": 0.0})
    v = vida(Perfil(edad=45), d, alcance="completo", madre_edad=-1)
    v.vivir_anio(Guion({"cuidar_familiar": "pagar", **QUIETA}))
    assert v.e["familiar_enfermo"] == "padre"


@pytest.mark.xfail(strict=True, reason="el cierre del año no mueve estas variables del paquete: los padres no envejecen "
                   "(su riesgo de morir queda fijo), el hijo menor no crece (media_jornada pesa como con un hijo de 0 "
                   "años para siempre) y los años de luto no avanzan")
@pytest.mark.parametrize(("variable", "inicial", "esperado"), [
    ("madre_edad", 70, 73), ("padre_edad", 72, 75), ("edad_hijo_menor", 0, 3), ("luto_madre", 0, 3),
])
def test_variables_que_deberian_avanzar_con_los_anios(variable, inicial, esperado):
    extra = {"hijos": 1} if variable == "edad_hijo_menor" else {"madre_edad": -1} if variable == "luto_madre" else {}
    v = vida(Perfil(estado="inactivo", edad=40), DadosGuion(), alcance="completo", **{variable: inicial}, **extra)
    for _ in range(3):
        v.vivir_anio(Guion())
    assert v.e[variable] == esperado


# ------------------------------------------------------------------ decisiones con elección interna
@pytest.mark.xfail(strict=True, reason="la región de destino no llega a region_nombre: el evaluador de referencia la lee de "
                   "'region_perfil', que el motor nunca escribe. Quien se muda a Antofagasta queda en 'Valparaíso' y al "
                   "volver a Santiago su sueldo se multiplica por RM/Valparaíso en vez de RM/Antofagasta")
def test_mudarse_a_una_region_deja_esa_region_en_el_estado():
    v = vida(Perfil(edad=35), DadosGuion())
    v.vivir_anio(Guion({"mudarse_de_region": "a_region", **QUIETA},
                       parametros={"mudarse_de_region": {"region_destino": "Antofagasta"}}), carta="mudarse_de_region")
    assert v.e["region"] == "otra"
    assert v.e["region_nombre"] == "Antofagasta"


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="motor.py _decidir acepta cualquier valor en los parámetros de una opción. Un rubro que no "
                   "existe revienta a mitad de los efectos con ErrorExpresion (500 en la API) en vez de un ValueError "
                   "claro antes de tocar el estado")
def test_un_parametro_con_valor_invalido_da_un_error_claro():
    try:
        partida.jugar(Perfil(), 0, [{"opcion": "cambiar", "parametros": {"rubro_destino": "Inventado"}}],
                      duda="cambiar_de_rubro")
    except ValueError:
        return
    except Exception as x:  # noqa: BLE001
        raise AssertionError(f"error poco claro: {type(x).__name__}: {x}") from x
    for u in (0.0, 0.5):
        v = vida(Perfil(), DadosGuion({"dec:cambiar_de_rubro:cambiar": u}))
        try:
            v.vivir_anio(Guion({"cambiar_de_rubro": "cambiar", **QUIETA},
                               parametros={"cambiar_de_rubro": {"rubro_destino": "Inventado"}}), carta="cambiar_de_rubro")
        except ValueError:
            return
        except Exception as x:  # noqa: BLE001
            raise AssertionError(f"error poco claro: {type(x).__name__}: {x}") from x
        assert v.e["rubro"] in pq().variables["rubro"]["dominio"]


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="partida.jugar: una duda fuera del alcance laboral (buscar_pareja) pasa el chequeo `aplica` y "
                   "después se descarta en silencio; una duda que no existe da KeyError en vez de ValueError")
@pytest.mark.parametrize("duda", ["buscar_pareja", "no_existe"])
def test_una_duda_que_no_se_puede_jugar_da_un_error_claro(duda):
    try:
        p = partida.jugar(Perfil(), 0, [], duda=duda)
    except ValueError:
        return
    except Exception as x:  # noqa: BLE001
        raise AssertionError(f"error poco claro: {type(x).__name__}: {x}") from x
    raise AssertionError(f"aceptó la duda y quedó esperando {p.pendiente.decision['id']!r}")


# ------------------------------------------------------------------ gemelos y políticas
@pytest.mark.xfail(strict=True, reason="comparar(cesantia): la opción 'bootcamp' encadena la decisión bootcamp y ahí los "
                   "gemelos (Inercia, sin pesos para esa decisión) eligen siempre 'no'. La columna 'bootcamp' que ve la "
                   "persona es en realidad 'no hacer nada este año'")
def test_los_gemelos_que_eligen_bootcamp_en_la_cesantia_hacen_el_bootcamp():
    hicieron = 0
    for g in range(40):
        v = vida(CESANTE, Dados(0, g), tipo_empleador="pyme", rubro="Comercio")
        v.vivir_anio(Fija("cesantia", "bootcamp"), carta="cesantia")
        hicieron += ("bootcamp", "hacer") in [(d["decision"], d["opcion"]) for d in v.historia[0]["decisiones"]]
    assert hicieron > 0


@pytest.mark.xfail(strict=True, reason="politicas.py _pesos: el peso escrito para la última opción se ignora y se "
                   "reemplaza por 1 - los demás disponibles. Si otra opción no está disponible (vender antes del año 3), "
                   "su peso se va entero a la última: un fundador cierra por decisión propia 10% al año, no el 5% escrito")
def test_el_peso_escrito_para_la_ultima_opcion_se_respeta():
    opciones = [Opcion(id_, id_, "", []) for id_ in ("seguir", "levantar", "cerrar")]  # sin 'vender'
    tabla = {"lab": {"seguir": 0.86, "levantar": 0.04, "vender": 0.05, "cerrar": 0.05}}
    pesos = _pesos({"id": "lab"}, opciones, tabla)
    assert pesos[2] / sum(pesos) == pytest.approx(0.05 / 0.95)
    assert set(PESOS_FORZADAS["seguir_con_tu_empresa"]) == {"seguir", "levantar", "vender", "cerrar"}


def test_comparar_no_cuenta_dos_veces_al_gemelo_que_ya_no_tiene_historia():
    """Guardia: la comparación tolera vidas que terminan antes (60 años)."""
    v = vida(Perfil(edad=50, nivel=2), Dados(0, "tu"))
    c = gemelos.comparar(v, "pedir_aumento", n=10, anios=10, semilla=1)
    assert all(len(o["trayectoria"]) == 10 for o in c["opciones"])


@pytest.mark.xfail(strict=True, reason="motor.py _completar_empleo (cambio hecho durante la revisión): al emplear a alguien "
                   "sin tipo de empleador encola tipo_de_empleador, pero corre antes de que _decidir encole el `luego` "
                   "del mismo resultado; en cesantia/encuentra la decisión interna queda dos veces en el registro del año "
                   "(mismo dado, mismo resultado: no cambia el estado, sí lo que se muestra)")
def test_el_tipo_de_empleador_se_sortea_una_sola_vez_al_encontrar_trabajo():
    d = DadosGuion({"dec:cesantia:rapido": 0.0, "dec:tipo_de_empleador:sorteo": 0.5})
    v = vida(CESANTE, d)
    reg = v.vivir_anio(Guion({"cesantia": "rapido", **QUIETA}))
    assert [x["decision"] for x in reg["decisiones"]] == ["cesantia", "tipo_de_empleador"]
