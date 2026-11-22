"""Lo que el cierre y la comparación dicen con números: la decisión medida mundo a mundo (como la carta), el
sueldo con y sin los mundos que terminan sin trabajo, y el año en que solo hubo reajuste por inflación."""

from statistics import median

from app.sim.motor import gemelos, partida
from app.sim.motor.motor import SOLO_IPC
from app.sim.motor.perfil import Perfil

N = 20


def _jugar(semilla: int, elegir) -> tuple[list[dict], dict]:
    elecciones: list[dict] = []
    for _ in range(80):
        v = partida.vista(Perfil(), semilla, None, elecciones, n_gemelos=N)
        if v["terminada"]:
            return elecciones, v
        p = v["pendiente"]
        o = elegir(p["opciones"])
        elecciones.append({"decision": p["decision"], "opcion": o["opcion"],
                           "parametros": {e["variable"]: e["alternativas"][0]["valor"] for e in o["elecciones_internas"]}})
    raise AssertionError("la partida no terminó")


def test_la_decision_del_cierre_es_la_diferencia_mundo_a_mundo():
    elecciones, v = _jugar(1, lambda ops: ops[-1])
    primera = v["cierre"]["primera_decision"]
    assert primera is not None
    contra, comp = primera["contra"], primera["comparacion"]
    assert contra["opcion"] != primera["elegida"]
    assert all("sueldos_por_mundo" not in o and "sueldos" not in o for o in comp["opciones"])
    # la otra: la de mejor sueldo típico entre las que no elegiste
    otras = [o for o in comp["opciones"] if o["opcion"] != primera["elegida"]]
    assert contra["opcion"] == max(otras, key=lambda o: o["sueldo"]["p50"])["opcion"]
    # oráculo: rehacer la comparación en el punto de la decisión, con la misma semilla, y parear por mundo
    k = next(i for i, e in enumerate(elecciones) if e["decision"] == primera["decision"])
    hasta = partida.jugar(Perfil(), 1, elecciones[:k], None)
    cruda = partida.comparar_pendiente(hasta, 1, N, crudo=True)
    por = {o["opcion"]: o["sueldos_por_mundo"] for o in cruda["opciones"]}
    esperada = round(median(a - b for a, b in zip(por[primera["elegida"]], por[contra["opcion"]])))
    assert contra["diferencia_tipica"] == esperada


def test_sueldo_con_trabajo_deja_fuera_los_ceros():
    p = partida.jugar(Perfil(), 1, [], None)
    comp = gemelos.comparar(p.vida, p.pendiente.decision["id"], n=N, semilla=1, crudo=True)
    for o in comp["opciones"]:
        positivos = [s for s in o["sueldos"] if s > 0]
        assert o["sueldo_con_trabajo"]["p10"] >= o["sueldo"]["p10"]
        if positivos:
            assert o["sueldo_con_trabajo"]["p10"] >= min(positivos)


def test_el_anio_con_solo_reajuste_queda_marcado():
    marcados = []
    for semilla in range(6):
        _, v = _jugar(semilla, lambda ops: ops[0])
        marcados += [e for a in v["historia"] for e in a["eventos"] if e.get("solo_ipc")]
    assert marcados, "en 6 vidas de 10 años debería haber algún año con solo reajuste"
    assert all(e["texto"] == SOLO_IPC and e["evento"] == "alza_anual" and not e["rutina"] for e in marcados)
