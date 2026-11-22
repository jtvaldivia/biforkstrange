"""Robustez: vidas largas y perfiles variados, en los dos alcances, con invariantes en cada cierre.

Cualquier excepción aquí es un hallazgo. Lo que ya se sabe que falla está descrito y aislado
en `test_motor_hallazgos.py`; aquí se excluye por su firma exacta (`CONOCIDOS`), no por tipo.
"""

import itertools
import math
from collections import Counter

import pytest
from _motor_util import n, pq, vida

from app.sim.motor.azar import Dados
from app.sim.motor.motor import TRANQUILO
from app.sim.motor.perfil import Perfil
from app.sim.motor.politicas import Poblacion

ESTADOS = {"estudiando", "buscando", "empleado", "independiente", "fundador", "inactivo"}
# Fallas ya reportadas (ver test_motor_hallazgos.py). Al corregirlas, borrar la línea.
CONOCIDOS = (
    "dominio ahorro",                           # el cierre no acota el ahorro (alcance completo)
)


def _violaciones(v, registro) -> list[str]:
    """Invariantes de una vida recién cerrada el año."""
    p, e, malas = pq(), v.e, []
    for nombre, d in p.variables.items():
        x = e[nombre]
        if d["tipo"] in ("categoria", "eleccion"):
            if d["dominio"] and x not in d["dominio"]:
                malas.append(f"dominio {nombre}: {x!r}")
            continue
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            malas.append(f"tipo {nombre}: {x!r}")
        elif not math.isfinite(x):
            malas.append(f"no finito {nombre}")
        elif len(d["dominio"]) == 2 and not d["dominio"][0] - 1e-6 <= x <= d["dominio"][1] + 1e-6:
            malas.append(f"dominio {nombre}")
        elif d["tipo"] in ("entero", "bool") and x != int(x):
            malas.append(f"no entero {nombre}: {x!r}")
    if e["estado"] not in ESTADOS:
        malas.append("estado inválido")
    if e["sueldo"] < 0 or e["sueldo_ref"] < 0:
        malas.append("sueldo negativo")
    if e["estado"] == "empleado" and (e["sueldo"] <= 0 or e["tipo_empleador"] == ""):
        malas.append("empleada sin sueldo o sin tipo de empleador")
    if e["estado"] in ("buscando", "inactivo", "estudiando") and e["sueldo"] != 0:
        malas.append(f"sin trabajo con sueldo ({e['estado']})")
    if e["estado"] == "empleado" and e["tipo_empleador"] == "publico" and e["rubro"] != "Administración pública":
        malas.append("empleo público fuera de Administración pública")
    if e["estado"] == "empleado" and e["tipo_empleador"] not in ("", "publico") and e["rubro"] in ("", "Administración pública"):
        malas.append(f"empleo privado con rubro {e['rubro']!r}")
    if not math.isfinite(v.ingreso_total) or v.ingreso_total < 0:
        malas.append("ingreso total")
    fin = registro["fin"]
    if (fin["edad"], fin["estado"], fin["sueldo"]) != (e["edad"], e["estado"], round(e["sueldo"])):
        malas.append("el resumen del año no es el estado")
    if fin["edad"] <= registro["edad"] or v.cola or v.registro is not None:
        malas.append("el año no cerró bien")
    for d in registro["decisiones"]:
        if (d["decision"] not in p.decisiones and d["decision"] != TRANQUILO) or not 0 <= d["prob"] <= 1:
            malas.append(f"decisión rara {d['decision']}")
        if d["resultado"] is None and e["p_encontrar"] >= 1:
            malas.append(f"decisión sin resultado {d['decision']}/{d['opcion']}")
    for x in registro["eventos"]:
        if (x["evento"] not in p.eventos and x["evento"] != "diferido") or not 0 <= x["prob"] <= 1:
            malas.append(f"evento raro {x['evento']}")
    if any(t["quedan"] <= 0 for t in v.temporales):
        malas.append("efecto vencido sin revertir")
    return malas


def _catalogo_evaluable(v) -> list[str]:
    """Desde este estado, todo lo que el año siguiente podría evaluar da números válidos."""
    p, e, malas = pq(), v.e, []
    for id_, d in p.decisiones.items():
        try:
            aplica = d["aparicion"]["tipo"] != "interna" and p.evaluar(d["cuando"], e)
            peso = p.evaluar(d["aparicion"]["peso"], e)
            opciones = v.opciones(id_) if aplica else []
        except Exception as x:  # noqa: BLE001
            malas.append(f"{id_}: {type(x).__name__}: {x}")
            continue
        if not isinstance(peso, (int, float)) or peso < 0:
            malas.append(f"{id_}: peso {peso}")
        for o in opciones[:8]:
            suma = 0.0
            for r in o.resultados:
                try:
                    if r["prob"] != "resto":
                        pr = p.evaluar(r["prob"], {**e, **o.fila})
                        suma += pr
                        if not 0 <= pr <= 1:
                            malas.append(f"{id_}/{o.id}/{r['id']}: prob {pr}")
                except Exception as x:  # noqa: BLE001
                    malas.append(f"{id_}/{o.id}/{r['id']}: {type(x).__name__}: {x}")
            if suma > 1 + 1e-9:
                malas.append(f"{id_}/{o.id}: las probabilidades suman {suma:.3f}")
    for id_, ev in p.eventos.items():
        if not v._evento_en_alcance(id_):
            continue
        try:
            if p.evaluar(ev["cuando"], e) and not 0 <= p.evaluar(ev["prob_anual"], e) <= 1:
                malas.append(f"evento {id_}: prob_anual fuera de [0, 1]")
        except Exception as x:  # noqa: BLE001
            malas.append(f"evento {id_}: {type(x).__name__}: {x}")
    return malas


def _correr(v, anios: int, fallas: Counter, ejemplo: dict, quien: str, revisar_catalogo: bool) -> None:
    def anotar(mensaje):
        if not any(c in mensaje for c in CONOCIDOS):
            fallas[mensaje] += 1
            ejemplo.setdefault(mensaje, f"{quien}, año {v.anio}")
    try:
        for _ in range(anios):
            if v.terminada():
                break
            registro = v.vivir_anio(Poblacion())
            for m in _violaciones(v, registro):
                anotar(m)
            if revisar_catalogo and v.anio % 4 == 1:
                for m in _catalogo_evaluable(v):
                    anotar("catálogo: " + m)
    except Exception as x:  # noqa: BLE001
        anotar(f"EXCEPCIÓN {type(x).__name__}: {x}")


@pytest.mark.parametrize("alcance", ["laboral", "completo"])
def test_vidas_de_32_anios_desde_los_18(alcance):
    fallas, ejemplo, finales = Counter(), {}, Counter()
    for g in range(n(150)):
        v = vida(Perfil.a_los_18(sexo="hm"[g % 2], riesgo=g % 11), Dados(2026, g), alcance)
        _correr(v, 32, fallas, ejemplo, f"gemelo {g}", revisar_catalogo=g % 3 == 0)
        finales[v.e["estado"]] += 1
        assert v.e["edad"] >= 50 or fallas
    assert not fallas, {k: (c, ejemplo[k]) for k, c in fallas.most_common(12)}
    assert finales["empleado"] > n(150) * 0.4  # la cohorte no se queda pegada estudiando ni buscando
    assert finales["estudiando"] == 0


EDUS = ["media", "tecnica", "universitaria", "postgrado"]
TIPOS = ["grande", "pyme", "startup", "publico", "extranjero"]
EDADES = [18, 22, 26, 31, 38, 45, 50]


@pytest.mark.parametrize("alcance", ["laboral", "completo"])
def test_10_anios_desde_perfiles_variados(alcance):
    """Todas las combinaciones de educación, empleador y edad, con y sin carrera; nivel, sexo,
    sueldo, riesgo, región y rubro van rotando."""
    carreras = [-1, 11, 120, 200]
    sueldos = [350_000, 900_000, 2_500_000, 9_000_000]
    rubros = pq().variables["rubro"]["dominio"][:-1]
    fallas, ejemplo = Counter(), {}
    combos = list(itertools.product(EDUS, TIPOS, EDADES, [False, True]))
    paso = max(1, round(1 / min(1.0, n(100) / 100)))
    for i, (edu, tipo, edad, con_carrera) in enumerate(combos[::paso]):
        perfil = Perfil(edad=edad, sexo="hm"[i % 2], edu=edu, carrera_id=carreras[1 + i % 3] if con_carrera else -1,
                        rubro="Administración pública" if tipo == "publico" else rubros[i % len(rubros)],
                        tipo_empleador=tipo, nivel=i % 5, sueldo=sueldos[i % 4], riesgo=i % 11, antiguedad=i % 7,
                        region=("rm", "otra")[i % 2], ocupacion=(None, 1, 4, 9, 0)[i % 5])
        _correr(vida(perfil, Dados(7, i), alcance), 10, fallas, ejemplo, repr(perfil), revisar_catalogo=i % 4 == 0)
    assert not fallas, {k: (c, ejemplo[k]) for k, c in fallas.most_common(12)}


@pytest.mark.parametrize("alcance", ["laboral", "completo"])
def test_10_anios_desde_quien_no_esta_empleado(alcance):
    fallas, ejemplo = Counter(), {}
    estados = ["buscando", "independiente", "fundador", "estudiando", "inactivo"]
    for i, (estado, edu, edad) in enumerate(itertools.product(estados, EDUS, [18, 24, 33, 47])):
        perfil = Perfil(edad=edad, sexo="hm"[i % 2], edu=edu, carrera_id=(-1, 57)[i % 2], estado=estado,
                        sueldo=(0, 700_000, 1_800_000)[i % 3], nivel=i % 4, riesgo=i % 11)
        for semilla in range(n(3)):
            _correr(vida(perfil, Dados(semilla, i), alcance), 10, fallas, ejemplo, repr(perfil), revisar_catalogo=True)
    assert not fallas, {k: (c, ejemplo[k]) for k, c in fallas.most_common(12)}


def test_todas_las_carreras_se_pueden_estudiar_y_derivar():
    """Las 252 carreras: matricularse, titularse y cobrar el primer sueldo no revienta con ninguna."""
    p = pq()
    for fila in p.filas("mifuturo_carreras"):
        cid = int(fila["carrera_id"])
        for titulado in range(5):
            e = vida(Perfil(edad=24, carrera_id=cid, antiguedad=0), anos_titulado=titulado).e
            assert 0 <= e["crecimiento_carrera"] <= 0.2 and 0 <= e["exposicion_ia"] <= 1
        recien = vida(Perfil(edad=22, estado="buscando", sueldo=0, edu="tecnica", carrera_id=cid))
        assert recien.e["primer_empleo"] == 1
        for o in recien.opciones("primera_pega"):
            for r in o.resultados:
                if r["prob"] != "resto":
                    assert 0 <= p.evaluar(r["prob"], recien.e) <= 1
                for ef in r["efectos"]:
                    if ef["var"] == "sueldo":
                        assert p.evaluar(ef["valor"], recien.e) > 0
