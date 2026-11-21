import json
from pathlib import Path

import numpy as np

from app.sim.context import Ctx
from app.sim.counterfactual import comparar, menu
from app.sim.engine import paso, simular, simulate
from app.sim.game import Partida
from app.sim.luck import Suerte
from app.sim.modules.labor import oferta_rel, p_supera
from app.sim.params import PARAMS, P
from app.sim.profile import Perfil
from app.sim.state import CES, EMP, Estado

PERFIL = Perfil.desde_dict(json.loads((Path(__file__).parent.parent / "perfiles" / "ejemplo.json").read_text()))


class Twin:
    edad, sueldo, desgaste = 25, 900_000.0, 0.2


def test_todos_los_parametros_tienen_fuente():
    assert {p.estado for p in PARAMS.values()} <= {"dato", "derivado"}
    assert all(p.fuente for p in PARAMS.values())


def test_simulate_formato_api():
    r = simulate(Twin, ["seguir", "sabatico", "cambiar_pega"], n_runs=500, seed=1)
    assert len(r["trayectoria"]) == 3 and r["edad_final"] == 28
    t = r["trayectoria"][-1]
    assert t["sueldo_p10"] <= t["sueldo_p50"] <= t["sueldo_p90"]
    assert 0 <= t["prob_desempleo"] <= 1


def test_misma_semilla_mismo_resultado():
    a = simulate(Twin, ["seguir", "buscar_pega"], n_runs=300, seed=7)
    b = simulate(Twin, ["seguir", "buscar_pega"], n_runs=300, seed=7)
    assert a == b


def test_ofertas_reproducen_la_sce():
    us = np.linspace(0.001, 0.999, 999)
    r = oferta_rel(us)
    assert abs(np.median(r) - P.OFERTA_REL["p50"]) < 0.01
    assert 0.25 < p_supera(P.UMBRAL["no_busca"]) < 0.32   # SCE: 28% de las ofertas supera 0,10


def test_suerte_compartida_entre_decisiones():
    """Con la misma suerte, trabajar más no cambia a quién despiden: solo cambia el tiempo con tu gente."""
    a, b = (simular(PERFIL, [d], n=2000, seed=3)[0] for d in ("seguir", "trabajar_mas"))
    assert np.array_equal(a.ev["despido"], b.ev["despido"])
    assert np.allclose(a.sueldo, b.sueldo)
    assert (b.social[b.sit == EMP] < a.social[b.sit == EMP]).all()


def test_paso_no_modifica_la_entrada():
    e = Estado.desde_perfil(PERFIL, 50)
    antes = e.sueldo.copy()
    paso(e, "trabajar_mas", Ctx(PERFIL, Suerte(1, 50)))
    assert np.array_equal(e.sueldo, antes) and e.t == 0


def test_sabatico_gasta_ahorros_y_deja_buscando():
    a, b = (simular(PERFIL, [d], n=1000, seed=5)[0] for d in ("seguir", "sabatico"))
    assert np.median(b.ahorros) < np.median(a.ahorros)
    assert (b.sit == CES).all() and b.hueco_vol.all()


def test_antiguedad_protege_del_despido():
    viejo = Perfil.desde_dict({**json.loads((Path(__file__).parent.parent / "perfiles" / "ejemplo.json").read_text()), "antiguedad": 8})
    d = lambda pf: simular(pf, ["seguir"], n=20000, seed=4)[0].ev["despido"].mean()  # noqa: E731
    assert d(viejo) < d(PERFIL)


def test_menu_completo_y_frecuencias():
    ops = menu(Estado.desde_perfil(PERFIL), PERFIL, horizonte=3, n=400, seed=1, todas=True)
    claves = [o.decision for o in ops]
    assert claves[0] == "seguir" and {"sabatico", "emprender", "magister"} <= set(claves)
    assert all(o.ingreso[0] <= o.ingreso[1] <= o.ingreso[2] for o in ops)
    assert all(o.gemelos is None or 0 < o.gemelos < 1 for o in ops)


def test_mano_del_anio_tiene_dos_o_tres_cartas():
    vistas = set()
    for seed in range(15):
        ops = menu(Estado.desde_perfil(PERFIL), PERFIL, horizonte=2, n=200, seed=seed)
        assert ops[0].decision == "seguir" and 2 <= len(ops) <= 3
        assert len({o.decision for o in ops}) == len(ops)
        vistas |= {o.decision for o in ops}
    assert "aceptar_oferta" in vistas and len(vistas) >= 5


def test_aceptar_oferta_cambia_de_empresa():
    seed = next(s for s in range(80) if any(o.decision == "aceptar_oferta" for o in menu(Estado.desde_perfil(PERFIL), PERFIL, 1, 100, s)))
    g = Partida(PERFIL, seed=seed, n=200)
    t = g.decidir("aceptar_oferta")
    assert t["yo"]["empresa"] and t["yo"]["empresa"] != PERFIL.empresa
    assert g.yo.ev["oferta_aceptada"][0]
    assert t["sombra"]["empresa"] in (PERFIL.empresa, "")   # la sombra no se cambia por su cuenta


def test_comparar_planes_pareado():
    r = comparar(PERFIL, {"base": ["seguir"] * 4, "igual": ["seguir"] * 4, "pausa": ["sabatico"] + ["seguir"] * 3}, n=800, seed=9)
    assert r["igual"]["p_mas_ingreso"] == 0 and r["igual"]["delta_ingreso"] == 0
    assert r["pausa"]["delta_ingreso"] < 0


def test_partida_se_reconstruye_igual():
    a = Partida(PERFIL, seed=11, n=300)
    for d in ("buscar_pega", "magister", "seguir"):
        t = a.decidir(d)
        assert t["eventos"] and t["yo"]["edad"] == t["sombra"]["edad"]
    b = Partida.reproducir(PERFIL, ["buscar_pega", "magister", "seguir"], seed=11, n=300)
    assert a.historial == b.historial
    assert a.yo.edad == PERFIL.edad + 3 and a.yo.sit[0] in (EMP, CES)
