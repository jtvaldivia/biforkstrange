"""Empresas, cargos, universidades y el escenario de IA por mundo.

Oráculos: las tablas del catálogo (leídas aquí con csv, no con el código del motor), el rango de IA_JOVEN
del paquete y propiedades (la carta muestra la empresa que después vive la persona).
"""

import csv
import math
from collections import defaultdict
from pathlib import Path

import pytest
from _motor_util import pq

from app.sim.motor import empresas, partida
from app.sim.motor.azar import Dados
from app.sim.motor.gemelos import comparar
from app.sim.motor.motor import Vida
from app.sim.motor.perfil import Perfil, estado_inicial

TABLAS = Path(__file__).resolve().parents[1] / "simulador" / "tablas"
LOGOS = Path(__file__).resolve().parents[2] / "frontend" / "public" / "logos"


def _csv(nombre: str) -> list[dict]:
    with open(TABLAS / nombre, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


EMPRESAS = _csv("empresas_catalogo.csv")
CARGOS = _csv("cargos_catalogo.csv")
UNIVERSIDADES = _csv("universidades.csv")
DOMINIO_RUBRO = [r for r in pq().variables["rubro"]["dominio"] if r]


# ---------------------------------------------------------------------- catálogo
def test_ids_unicos_y_consecutivos():
    assert [int(f["empresa_id"]) for f in EMPRESAS] == list(range(len(EMPRESAS)))
    assert len({int(f["cargo_id"]) for f in CARGOS}) == len(CARGOS)
    assert len({f["universidad_id"] for f in UNIVERSIDADES}) == len(UNIVERSIDADES)


def test_cubre_los_16_rubros_y_los_5_tipos():
    assert {f["rubro"] for f in EMPRESAS} == set(DOMINIO_RUBRO)
    assert {f["tipo"] for f in EMPRESAS} == {"grande", "pyme", "startup", "publico", "extranjero"}
    assert 120 <= len(EMPRESAS) <= 200


def test_multiplicadores_promedian_uno_en_cada_tipo_y_rubro():
    """Probabilidades: media aritmética 1. Sueldo: media geométrica 1, para no mover las medianas."""
    celdas = defaultdict(list)
    for f in EMPRESAS:
        celdas[(f["tipo"], f["rubro"])].append(f)
    for clave, filas in celdas.items():
        total = sum(float(f["peso"]) for f in filas)
        if total <= 0:
            continue
        for col in ("mult_despido", "mult_cierre", "mult_ascenso"):
            media = sum(float(f["peso"]) * float(f[col]) for f in filas) / total
            assert media == pytest.approx(1, abs=1e-6), (clave, col)
        geometrica = math.exp(sum(float(f["peso"]) * math.log(float(f["mult_sueldo"])) for f in filas) / total)
        assert geometrica == pytest.approx(1, abs=1e-6), clave


def test_cada_cifra_dice_su_calidad():
    for f in EMPRESAS:
        for col in ("calidad_sueldo", "calidad_despido", "calidad_ascenso", "calidad_ia", "calidad_horas"):
            assert f[col] in ("dato", "derivado", "sintetico"), (f["nombre"], col)


def test_logo_marcado_implica_archivo():
    for f in EMPRESAS:
        assert (f["logo"] == "1") == (LOGOS / "empresas" / f"{f['empresa_id']}.png").exists(), f["nombre"]
    for f in UNIVERSIDADES:
        assert (f["logo"] == "1") == (LOGOS / "universidades" / f"{f['universidad_id']}.png").exists(), f["nombre"]


def test_los_cargos_apuntan_a_ocupaciones_de_la_tabla_de_ia():
    ocupaciones = {f["ocupacion_eeuu"] for f in _csv("ia_aplicabilidad_ocupaciones.csv")}
    for c in CARGOS:
        assert c["ocupacion_ia"] in ocupaciones, c["nombre"]
        assert 1 <= int(c["ciuo08_1d"]) <= 9 and 0 <= int(c["nivel_min"]) <= int(c["nivel_max"]) <= 4


def test_toda_empresa_tiene_cargo_para_cada_educacion_y_nivel():
    for emp in empresas._catalogo(pq())["empresas"]:
        for edu in ("media", "tecnica", "universitaria", "postgrado"):
            for nivel in range(5):
                e = {"edu": edu, "nivel": nivel, "area": "", "ocupacion": -1}
                assert empresas.compatibles(pq(), emp, e), (emp["nombre"], edu, nivel)


def test_universidades_chilenas_y_extranjeras():
    tipos = {f["tipo_institucion"] for f in UNIVERSIDADES}
    assert {"U", "IP", "CFT", "EXT"} <= tipos
    sies = {f["universidad_id"] for f in _csv("sies_magister_2026.csv")}
    chilenas_u = {f["universidad_id"] for f in UNIVERSIDADES if f["tipo_institucion"] == "U"}
    assert len(sies & chilenas_u) >= 40  # mismos códigos SIES que el magíster
    assert all(float(f["matricula"] or 0) == 0 for f in UNIVERSIDADES if f["tipo_institucion"] == "EXT")


# ---------------------------------------------------------------------- motor
def _vida(perfil: Perfil, semilla: int = 0, gemelo: int | str = 0) -> Vida:
    return Vida(estado_inicial(perfil, pq()), Dados(semilla, gemelo), pq())


def test_sin_empresa_del_catalogo_los_multiplicadores_son_neutros():
    e = estado_inicial(Perfil(), pq())
    assert e["empresa_id"] == -1 and e["cargo_id"] == -1
    for c in ("mult_despido", "mult_ascenso", "mult_cierre"):
        assert pq().evaluar(f"tabla_o(1, 'empresas_catalogo', '{c}', 'empresa_id', empresa_id)", e) == 1


def test_el_despido_y_el_ascenso_leen_la_empresa():
    e = dict(_vida(Perfil()).e)
    sep, asc = pq().eventos["separacion_empleo"]["prob_anual"], pq().eventos["ascenso"]["prob_anual"]
    base_sep = pq().evaluar(sep, e)
    alta = max(empresas._catalogo(pq())["empresas"], key=lambda x: x["mult_despido"])
    assert pq().evaluar(sep, {**e, "empresa_id": alta["empresa_id"]}) == pytest.approx(base_sep * alta["mult_despido"])
    rapida = max(empresas._catalogo(pq())["empresas"], key=lambda x: x["mult_ascenso"])
    assert pq().evaluar(asc, {**e, "empresa_id": rapida["empresa_id"]}) >= pq().evaluar(asc, e)


def test_el_escenario_de_ia_es_igual_entre_opciones_y_distinto_entre_gemelos():
    bajo, alto = pq().parametros["IA_JOVEN"]["rango"]
    vida = _vida(Perfil(), 3, "tu")
    gemelos = [vida.clonar(Dados(3, g)) for g in range(40)]
    valores = [g.e["ia_adopcion"] for g in gemelos]
    assert len(set(valores)) == 40 and min(valores) < 0.2 and max(valores) > 0.8
    assert all(bajo <= g.e["ia_castigo_joven"] <= alto for g in gemelos)
    otra = vida.clonar(Dados(3, 7))
    assert otra.e["ia_adopcion"] == gemelos[7].e["ia_adopcion"]  # el mismo gemelo en otra opción


@pytest.mark.parametrize("semilla", range(12))
def test_la_empresa_de_la_carta_es_la_que_vive_la_persona(semilla):
    perfil = Perfil(edad=28, rubro="Información y comunicaciones", tipo_empleador="grande", nivel=1, skill=60)
    for duda, opcion in (("unirse_a_startup", "ir"), ("remoto_para_afuera", "postular")):
        antes = partida.vista(perfil, semilla, duda, [], 0)
        carta = next(o for o in antes["pendiente"]["opciones"] if o["opcion"] == opcion)["empresa"]
        despues = partida.jugar(perfil, semilla, [{"decision": duda, "opcion": opcion}], duda)
        registro = (despues.vida.historia[0] if despues.vida.historia else despues.vida.registro)
        tomada = next(d for d in registro["decisiones"] if d["decision"] == duda)
        if tomada["resultado"] in ("crece", "cierra", "sigue", "queda"):
            # puede haber pasado más de un año: se busca la empresa al cerrar el primero
            fin = registro.get("fin") or despues.vida.resumen()
            if fin["estado"] == "empleado" and fin["tipo_empleador"] in ("startup", "extranjero"):
                assert fin["empresa_id"] == carta["empresa_id"], (duda, semilla)


def test_la_oferta_externa_trae_la_misma_empresa_al_cambiarse_o_pedir_contraoferta():
    perfil = Perfil(edad=32, rubro="Comercio", tipo_empleador="pyme", nivel=2)
    v = partida.vista(perfil, 5, "oferta_externa", [], 0)
    ofertas = {o["opcion"]: o["empresa"] for o in v["pendiente"]["opciones"]}
    assert ofertas["quedarse"] is None
    if ofertas["cambiar"] and ofertas["contraoferta"]:
        assert ofertas["cambiar"]["empresa_id"] == ofertas["contraoferta"]["empresa_id"]


def test_al_quedar_sin_trabajo_se_suelta_la_empresa_y_se_recuerda_el_cargo():
    vida = _vida(Perfil(edad=40, rubro="Construcción", tipo_empleador="pyme"), 11)
    vida.e.update(empresa_id=0, cargo_id=0)
    vida._aplicar([{"var": "estado", "op": "fija", "valor": "'buscando'"}], "prueba")
    # la empresa se suelta; el cargo queda como su última línea de trabajo, pero ya no se muestra
    assert vida.e["empresa_id"] == -1 and vida.e["cargo_id"] == 0 and vida.resumen()["rol"] is None


def test_quien_trabaja_en_una_empresa_toma_la_exposicion_de_su_cargo():
    vida = _vida(Perfil(edad=30, rubro="Finanzas y seguros", tipo_empleador="grande"))
    car = empresas._catalogo(pq())["cargos"][0]
    vida.e.update(empresa_id=0, cargo_id=car["cargo_id"])
    vida._derivar()
    assert vida.e["exposicion_ia"] == pytest.approx(car["exposicion_ia"])


def test_primera_pega_asigna_empresa_y_rubro_coherentes():
    vistos = 0
    for semilla in range(30):
        p = partida.jugar(Perfil.a_los_18(), semilla, [{"opcion": "trabajar"}, {"opcion": "pyme"}])
        e = p.vida.e
        if e["estado"] == "empleado" and e["empresa_id"] >= 0:
            emp = empresas.empresa(pq(), e["empresa_id"])
            assert emp["rubro"] == e["rubro"] and emp["tipo"] == e["tipo_empleador"]
            vistos += 1
    assert vistos > 0


def test_las_extranjeras_del_magister_corren_sin_error():
    ext = next(f["universidad_id"] for f in UNIVERSIDADES if f["tipo_institucion"] == "EXT")
    v = partida.vista(Perfil(edad=30), 2, "magister", [], 30, {"vespertino": {"universidad_destino": ext}})
    opcion = next(o for o in v["pendiente"]["comparacion"]["opciones"] if o["opcion"] == "vespertino")
    assert opcion["parametros"]["universidad_destino"] == ext and opcion["sueldo"]["p50"] > 0


def test_salir_del_colegio_pregunta_la_institucion_del_tipo_elegido():
    v = partida.vista(Perfil.a_los_18(), 0, None, [], 0)
    opciones = {o["opcion"]: o for o in v["pendiente"]["opciones"]}
    internas = {i["variable"]: i for i in opciones["instituto"]["elecciones_internas"]}
    tipos = {f["universidad_id"]: f["tipo_institucion"] for f in UNIVERSIDADES}
    assert internas["institucion_destino"]["alternativas"]
    assert {tipos[a["valor"]] for a in internas["institucion_destino"]["alternativas"]} == {"IP"}


def test_comparar_con_parametros_parciales_conserva_los_por_defecto():
    vida = _vida(Perfil.a_los_18(), 1)
    vida.iniciar_anio(con_cartas=False)
    r = comparar(vida, "salir_del_colegio", n=4, anios=2, parametros={"universidad": {}})
    uni = next(o for o in r["opciones"] if o["opcion"] == "universidad")
    assert "institucion_destino" in uni["parametros"]


def test_api_perfil_rechaza_una_universidad_desconocida(client):
    r = client.post("/api/juego/partida", json={"perfil": {"universidad_id": "no_existe"}, "gemelos": 0})
    assert r.status_code == 422
    ok = UNIVERSIDADES[0]["universidad_id"]
    assert client.post("/api/juego/partida", json={"perfil": {"universidad_id": ok}, "gemelos": 0}).status_code == 200
    assert any(u["universidad_id"] == ok for u in client.get("/api/juego/catalogo").json()["universidades"])


def test_api_narrar_sin_credenciales_devuelve_plantillas(client, monkeypatch):
    monkeypatch.setenv("NARRADOR_IA", "0")
    r = client.post("/api/juego/narrar", json={"duda": "unirse_a_startup", "que": "pendiente"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items and all(i["via"] == "plantilla" and i["texto"] for i in items)
    assert any(i["id"] == "oferta:ir" for i in items)
    r = client.post("/api/juego/narrar", json={"duda": "unirse_a_startup", "que": "mundo", "mundo": 3})
    assert r.status_code == 200 and {i["id"] for i in r.json()["items"]} == {"mundo:ir", "mundo:quedarse"}
    assert client.post("/api/juego/narrar", json={"duda": "unirse_a_startup", "que": "mundo"}).status_code == 422


# ---------------------------------------------------------------------- escalera y familias
TRANSICIONES = _csv("transiciones_tipo.csv")


def test_las_transiciones_suman_uno_por_origen():
    por_origen = defaultdict(float)
    for f in TRANSICIONES:
        por_origen[f["origen"]] += float(f["prob"])
    assert set(por_origen) >= {"grande", "pyme", "startup", "publico", "ninguno"}
    for origen, total in por_origen.items():
        assert total == pytest.approx(1, abs=1e-6), origen


@pytest.mark.parametrize("origen", ["grande", "pyme", "startup", "publico"])
def test_el_tipo_nuevo_depende_de_donde_vienes(origen):
    """La decisión interna tipo_de_empleador lee la fila de su tipo de origen (oráculo: el CSV)."""
    tabla = {f["destino"]: float(f["prob"]) for f in TRANSICIONES if f["origen"] == origen}
    e = {**_vida(Perfil(tipo_empleador=origen if origen != "publico" else "pyme")).e, "tipo_empleador": origen}
    for o in pq().decisiones["tipo_de_empleador"]["opciones"]:
        for r in o["resultados"]:
            if r["prob"] != "resto":
                assert pq().evaluar(r["prob"], e) == pytest.approx(tabla[r["id"]]), (origen, r["id"])


def test_la_oferta_sigue_tu_linea_de_trabajo():
    """Con carrera de tecnología, el cargo que te ofrecen es de una familia afín a tecnología casi siempre."""
    carrera = next(int(f["carrera_id"]) for f in _csv("mifuturo_carreras.csv")
                   if f["area"] == "Tecnología" and f["tipo_institucion"] == "U")
    afines = set(empresas.familias_de(pq(), {"area": "Tecnología", "cargo_id": -1}))
    assert afines
    perfil = Perfil(edad=29, carrera_id=carrera, rubro="Información y comunicaciones", tipo_empleador="grande",
                    nivel=1, skill=60)
    dentro = total = 0
    for semilla in range(40):
        v = partida.vista(perfil, semilla, "oferta_externa", [], 0)
        emp = next((o["empresa"] for o in v["pendiente"]["opciones"] if o["empresa"]), None)
        if emp and emp["cargo_id"] >= 0:
            total += 1
            dentro += empresas.cargo(pq(), emp["cargo_id"])["familia"] in afines
    assert total >= 30 and dentro / total >= 0.8


def test_quien_trabaja_en_salud_publica_recibe_ofertas_del_estado_de_su_sector():
    """El rubro de un empleo público sigue siendo Administración pública, pero el empleador sale de su sector."""
    carrera = next(int(f["carrera_id"]) for f in _csv("mifuturo_carreras.csv")
                   if f["area"] == "Salud" and f["tipo_institucion"] == "U")
    perfil = Perfil(edad=40, carrera_id=carrera, rubro="Salud", tipo_empleador="publico", nivel=2)
    publicas = []
    for semilla in range(30):
        v = partida.vista(perfil, semilla, "oferta_externa", [], 0)
        emp = next((o["empresa"] for o in v["pendiente"]["opciones"] if o["empresa"]), None)
        if emp and emp["tipo"] == "publico":
            publicas.append(emp["rubro"])
    assert publicas and sum(r == "Salud" for r in publicas) / len(publicas) >= 0.8
