import numpy as np
import pytest

from app.sim.ocupacional import labor
from app.sim.ocupacional.engine import simulate
from app.sim.ocupacional.state import State, Twin
from app.sim.ocupacional.tables import N_GRUPOS, banda_idx, tablas

N = 40_000


def _state(**twin) -> State:
    return State.from_twin(Twin(**twin), N)


def test_tablas_consistentes():
    t = tablas()
    assert t.transicion.shape == (N_GRUPOS, N_GRUPOS)
    assert np.allclose(t.transicion.sum(axis=1), 1)
    assert all(t.nombres)
    # la matriz y la tabla de cambio de grupo salen de los mismos pares de empleos
    assert np.allclose(1 - np.diag(t.transicion), t.p_cambia_grupo, atol=1e-3)
    assert (t.p_cambia_ocupacion >= t.p_cambia_grupo).all()
    assert (t.dur_p25 <= t.dur_p50).all() and (t.dur_p50 <= t.dur_p75).all()


@pytest.mark.parametrize("edad,banda", [(18, 0), (29, 0), (30, 1), (44, 1), (45, 2), (70, 2)])
def test_banda(edad, banda):
    assert banda_idx(edad) == banda


@pytest.mark.parametrize("edad", [25, 35, 50])
def test_un_anio_reproduce_la_eps(edad):
    """Con empleo, un año del motor da las tasas de la EPS ajustadas por la rotación del grupo."""
    t, b, g = tablas(), banda_idx(edad), 2
    state = _state(edad=edad, ocupacion=g)
    year = labor.advance(state, np.random.default_rng(1))
    mult = t.mult_rotacion[g]
    assert year.perdio_empleo.mean() == pytest.approx((t.p_cesantia[b] + t.p_inactividad[b]) * mult, abs=0.006)
    assert year.nuevo_empleo.mean() == pytest.approx(t.p_cambio_directo[b] * mult, abs=0.008)
    assert (state.desempleado == year.perdio_empleo).all()


def test_los_jovenes_rotan_mas():
    joven, mayor = (labor.advance(_state(edad=e), np.random.default_rng(2)) for e in (22, 50))
    assert joven.nuevo_empleo.mean() > mayor.nuevo_empleo.mean()
    assert joven.perdio_empleo.mean() > mayor.perdio_empleo.mean()


@pytest.mark.parametrize("grupo", [2, 4, 9])
def test_siguiente_trabajo_sigue_la_matriz(grupo):
    """Al cambiar de empleo, el grupo de destino se reparte como la fila de JobHop del origen."""
    state = _state(ocupacion=grupo)
    year = labor.advance(state, np.random.default_rng(3), cambio_forzado=True)
    cambio = year.nuevo_empleo
    assert cambio.sum() > N * 0.8
    reparto = np.bincount(state.ocupacion[cambio], minlength=N_GRUPOS) / cambio.sum()
    assert np.allclose(reparto, tablas().transicion[grupo], atol=0.01)
    t = tablas()
    assert year.cambio_grupo[cambio].mean() == pytest.approx(t.p_cambia_grupo[grupo], abs=0.01)
    assert year.cambio_ocupacion[cambio].mean() == pytest.approx(t.p_cambia_ocupacion[grupo], abs=0.01)
    # quien no cambió de empleo conserva su grupo
    assert (state.ocupacion[~cambio] == grupo).all()


def test_reempleo_y_antiguedad():
    edad = 35
    state = _state(edad=edad, antiguedad=4)
    state.desempleado[: N // 2] = True
    year = labor.advance(state, np.random.default_rng(4))
    sin_empleo = slice(0, N // 2)
    esperado = 1 - tablas().p_sigue_cesante_12m[banda_idx(edad)]
    assert year.nuevo_empleo[sin_empleo].mean() == pytest.approx(esperado, abs=0.01)
    assert not year.perdio_empleo[sin_empleo].any()
    sigue = ~year.nuevo_empleo & ~state.desempleado
    assert (state.antiguedad[sigue] == 5).all()
    assert (state.antiguedad[year.nuevo_empleo | state.desempleado] == 0).all()
    assert (state.n_empleos == year.nuevo_empleo).all()


def test_la_cesantia_persiste_entre_anios():
    """Antes el desempleo se sorteaba de cero cada año; ahora quien cae puede seguir cesante."""
    r = simulate(Twin(edad=22), ["seguir"] * 6, n_runs=5000, seed=5)
    probs = [s["prob_desempleo"] for s in r["trayectoria"]]
    assert probs[-1] > probs[0]
    assert all(0 < p < 0.5 for p in probs)


def test_metricas_de_trayectoria():
    r = simulate(Twin(ocupacion=4), ["seguir", "cambiar_pega"], n_runs=5000, seed=6)
    primero, segundo = r["trayectoria"]
    assert sum(o["prob"] for o in segundo["ocupaciones"]) == pytest.approx(1)
    assert primero["ocupaciones"][0]["grupo"] == 4
    assert segundo["prob_nuevo_empleo"] > 0.75 > primero["prob_nuevo_empleo"]
    assert 0 < segundo["prob_cambio_grupo"] <= segundo["prob_cambio_ocupacion"] <= segundo["prob_nuevo_empleo"]


def test_perfil():
    p = labor.perfil(2, 30)
    assert p["nombre"].startswith("Profesionales")
    assert sum(s["prob"] for s in p["siguiente"]) == pytest.approx(1)
    assert p["siguiente"][0]["prob"] >= p["siguiente"][1]["prob"]
    ta = p["termino_anual"]
    assert ta["total"] == pytest.approx(ta["cambio_directo"] + ta["cesantia"] + ta["inactividad"])
    assert labor.perfil(2, 22)["termino_anual"]["total"] > ta["total"]
