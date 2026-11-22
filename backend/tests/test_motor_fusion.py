"""Lo que llegó desde los PR #3 y #4: magíster con universidad real, horas largas sin premio,
empresas reales como ejemplo, la lista de supuestos y la validación por la API."""

import pytest
from _motor_util import pq

from app.sim.motor import empresas, partida, supuestos
from app.sim.motor.perfil import Perfil

MAGISTER = Perfil(edad=30, edu="universitaria", sueldo=1_400_000)


def _vespertino(universidad: str) -> dict:
    v = partida.vista(MAGISTER, 3, "magister", [], 200, {"vespertino": {"universidad_destino": universidad}})
    return next(o for o in v["pendiente"]["comparacion"]["opciones"] if o["opcion"] == "vespertino")


def test_el_magister_pregunta_la_universidad_con_las_51_de_sies_y_las_extranjeras():
    v = partida.vista(MAGISTER, 0, "magister", [], 0)
    vespertino = next(o for o in v["pendiente"]["opciones"] if o["opcion"] == "vespertino")
    (interna,) = vespertino["elecciones_internas"]
    assert interna["variable"] == "universidad_destino"
    chilenas = [a for a in interna["alternativas"] if a["pais"] == "Chile"]
    extranjeras = [a for a in interna["alternativas"] if a["pais"] != "Chile"]
    assert len(chilenas) == len(pq().filas("sies_magister_2026")) == 51
    assert sum(a["selectiva"] for a in chilenas) == 11
    ext = [f for f in pq().filas("universidades") if f["tipo_institucion"] == "EXT"]
    assert len(extranjeras) == len(ext) > 0 and all(a["calidad"] == "sintetico" for a in extranjeras)


def test_la_prima_y_el_costo_dependen_de_la_universidad():
    assert pq().k("PREMIO_MAGISTER", 1.0) > pq().k("PREMIO_MAGISTER", 0.0)
    uc, no_selectiva = _vespertino("86"), _vespertino("68")  # UC selectiva; U. Miguel de Cervantes no
    assert uc["parametros"] == {"universidad_destino": "86"}
    assert uc["sueldo"]["p50"] > no_selectiva["sueldo"]["p50"]


def test_quedarse_hasta_tarde_casi_no_cambia_el_sueldo():
    par = pq().parametros["ASCENSO_HORAS"]
    assert par["calidad"] == "dato" and par["fuente"] == "ine_esi_panel"
    v = partida.vista(MAGISTER, 3, "trabajar_mas_horas", [], 200)
    si = next(o for o in v["pendiente"]["comparacion"]["opciones"] if o["opcion"] == "si")
    assert abs(si["diferencia_tipica"]) < 0.01 * si["sueldo"]["p50"]


@pytest.mark.parametrize(("duda", "opcion", "tipo"), [
    ("unirse_a_startup", "ir", "startup"),
    ("remoto_para_afuera", "postular", "extranjero"),
])
def test_las_opciones_de_trabajo_traen_una_empresa_del_catalogo(duda, opcion, tipo):
    v = partida.vista(Perfil(), 4, duda, [], 0)
    emp = next(o for o in v["pendiente"]["opciones"] if o["opcion"] == opcion)["empresa"]
    assert emp["tipo"] == tipo and emp["nombre"] and emp["calidad"] == "sintetico"
    assert empresas.empresa(pq(), emp["empresa_id"])["nombre"] == emp["nombre"]
    assert v == partida.vista(Perfil(), 4, duda, [], 0)  # determinista


def test_las_opciones_que_no_llevan_a_un_empleador_no_traen_empresa():
    v = partida.vista(Perfil(), 0, "unirse_a_startup", [], 0)
    ofertas = {o["opcion"]: o["empresa"] for o in v["pendiente"]["opciones"]}
    assert ofertas["quedarse"] is None and ofertas["ir"]["tipo"] == "startup"


def test_supuestos_cuenta_cada_parametro_una_vez():
    r = supuestos.listar()
    assert r["total"] == len(pq().parametros) == sum(r["por_calidad"].values())
    assert [p["calidad"] for p in r["parametros"]] == sorted((p["calidad"] for p in r["parametros"]), key=supuestos.ORDEN.get)


def test_api_supuestos_y_validacion(client):
    r = client.get("/api/juego/supuestos")
    assert r.status_code == 200 and r.json()["total"] == len(pq().parametros)
    r = client.get("/api/juego/validacion", params={"n": 200})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["total"] == len(cuerpo["metas"]) and 0 <= cuerpo["cumplen"] <= cuerpo["total"]
    assert "fallas" not in cuerpo
    assert client.get("/api/juego/validacion", params={"n": 10}).status_code == 422
