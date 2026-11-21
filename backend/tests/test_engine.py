import json
from pathlib import Path

import numpy as np

from app.sim.context import Ctx
from app.sim.counterfactual import comparar, menu
from app.sim.engine import paso, simular, simulate
from app.sim.game import Partida
from app.sim.luck import Suerte
from app.sim.profile import Perfil
from app.sim.state import CES, EMP, Estado
from app.sim.tables import tablas

PERFIL = Perfil.desde_dict(json.loads((Path(__file__).parent.parent / "perfiles" / "ejemplo.json").read_text()))


class Twin:
    edad, sueldo, desgaste = 25, 900_000.0, 0.2


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


def test_suerte_compartida_entre_decisiones():
    """Con la misma suerte, bajar el ritmo no cambia a quién despiden: solo cambia la energía."""
    a, b = (simular(PERFIL, [d], n=2000, seed=3)[0] for d in ("seguir", "bajar_ritmo"))
    assert np.array_equal(a.ev["despido"], b.ev["despido"])
    assert np.allclose(a.sueldo, b.sueldo)
    assert (b.energia >= a.energia).all()


def test_paso_no_modifica_la_entrada():
    e = Estado.desde_perfil(PERFIL, 50)
    antes = e.sueldo.copy()
    paso(e, "trabajar_mas", Ctx(PERFIL, Suerte(1, 50)))
    assert np.array_equal(e.sueldo, antes) and e.t == 0


def test_sabatico_gasta_ahorros_y_deja_buscando():
    a, b = (simular(PERFIL, [d], n=1000, seed=5)[0] for d in ("seguir", "sabatico"))
    assert np.median(b.ahorros) < np.median(a.ahorros)
    assert (b.sit == CES).all() and b.hueco_vol.all()


def test_trabajar_mas_cansa_y_asciende_mas():
    a, b = (simular(PERFIL, [d] * 3, n=4000, seed=5) for d in ("seguir", "trabajar_mas"))
    assert np.median(b[-1].energia) < np.median(a[-1].energia)
    assert sum(e.ev["ascenso"].sum() for e in b) > sum(e.ev["ascenso"].sum() for e in a)


def test_reconvertir_es_mas_facil_a_ocupacion_afin():
    tb = tablas()
    o = tb.idx[PERFIL.ocupacion]
    af = tb.afinidad[o].copy()
    af[o] = af[tb.es_directivo] = 0
    cerca, lejos = tb.codigos[int(np.argmax(af))], tb.codigos[int(np.argmin(np.where(af > 0, af, 9)))]
    ok = lambda c: simular(PERFIL, [f"reconvertir:{c}"], n=3000, seed=2)[0].ev["reconv_ok"].mean()  # noqa: E731
    assert ok(cerca) > ok(lejos) + 0.1


def test_ia_rapida_sube_despidos_en_ocupacion_expuesta():
    pf = Perfil.desde_dict({"edad": 25, "sueldo": 1_500_000, "ocupacion": "251", "nivel": "junior", "ahorros": 0})
    d = lambda esc: sum(e.ev["despido"].sum() for e in simular(pf, ["seguir"] * 12, n=4000, seed=4, escenario_ia=esc))  # noqa: E731
    assert d("rapida") > d("lenta")


def test_menu_y_gemelos():
    ops = menu(Estado.desde_perfil(PERFIL), PERFIL, horizonte=3, n=400, seed=1, todas=True)
    claves = [o.decision for o in ops]
    assert claves[0] == "seguir" and "sabatico" in claves and any(c.startswith("reconvertir:") for c in claves)
    assert abs(sum(o.gemelos for o in ops) - 1) < 1e-9
    assert all(o.ingreso[0] <= o.ingreso[1] <= o.ingreso[2] for o in ops)


def test_mano_del_anio_es_corta_y_trae_oportunidades():
    vistas = set()
    for seed in range(12):
        ops = menu(Estado.desde_perfil(PERFIL), PERFIL, horizonte=2, n=200, seed=seed)
        assert ops[0].decision == "seguir" and 2 <= len(ops) <= 3
        assert len({o.decision for o in ops}) == len(ops)
        vistas |= {o.decision for o in ops}
    assert {"aceptar_oferta", "postular_ascenso"} & vistas and len(vistas) >= 8


def test_aceptar_oferta_cambia_de_empresa_y_sube_sueldo():
    seed = next(s for s in range(50) if any(o.decision == "aceptar_oferta" for o in menu(Estado.desde_perfil(PERFIL), PERFIL, 1, 100, s)))
    g = Partida(PERFIL, seed=seed, n=200)
    antes = g.yo.sueldo[0]
    t = g.decidir("aceptar_oferta")
    assert t["yo"]["empresa"] and t["yo"]["empresa"] != "tu empresa actual"
    assert g.yo.ev["oferta_aceptada"][0] and g.yo.sueldo[0] > antes
    assert t["sombra"]["empresa"] in ("un banco grande", "")   # la sombra no se cambia por su cuenta


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
