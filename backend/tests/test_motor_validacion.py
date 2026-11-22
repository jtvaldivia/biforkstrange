"""El motor frente a Chile, con una cohorte chica (600 personas, unos 6 segundos).

La corrida de verdad es `python -m app.sim.motor.validacion` (5.000 personas) y su resultado
está en `docs/motor/VALIDACION.md`. Aquí se fija lo que no debe romperse:

- cuántas metas cuadran como mínimo;
- las metas clave una por una, con un margen extra por el tamaño de la cohorte.

Metas que quedan al borde de la tolerancia y cambian con la semilla no se fijan en ningún
sentido: `ingreso_p50_18-24`, `ingreso_p50_25-29`, `ingreso_p75_35-39`, `ingreso_p25_25-29`,
`ingreso_p25_35-39`, `ingreso_p25_45-49`, `publico_45-49`, `cambio_45_59`.
"""

import pytest

from app.sim.motor import validacion
from app.sim.motor.azar import Dados
from app.sim.motor.motor import Vida
from app.sim.motor.paquete import paquete
from app.sim.motor.perfil import Perfil, estado_inicial
from app.sim.motor.politicas import Poblacion

N, SEMILLA = 600, 0
MINIMO_CUADRAN = 22        # con 600 personas cuadran 26; con 5.000, 25 o 26
MARGEN = 0.015             # puntos extra por ruido de una cohorte chica
MARGEN_RELATIVO = 0.05

CUADRAN = [
    "desocupacion_18-24", "desocupacion_25-29", "desocupacion_30-34",
    "desocupacion_35-39", "desocupacion_40-44", "desocupacion_45-49",
    "edu_media_30_34", "edu_universitaria_30_34", "edu_tecnica_30_34", "edu_postgrado_30_34",
    "independientes_25-29", "independientes_35-39", "independientes_45-49",
    "publico_25-29", "empresa_grande", "startup_anos",
    "separacion_18_29", "separacion_30_44", "separacion_45_59",
    "cambio_18_29", "cambio_30_44", "sigue_cesante_12m",
    "ingreso_p75_25-29",
    # desde que el alza anual no baja el sueldo de quien sigue en su pega, los sueldos medianos cuadran
    "ingreso_p50_30-34", "ingreso_p50_35-39", "ingreso_p50_40-44", "ingreso_p50_45-49", "ingreso_p75_45-49",
]


@pytest.fixture(scope="module")
def resultado() -> dict:
    return validacion.validar(N, SEMILLA, procesos=1)


@pytest.fixture(scope="module")
def metas(resultado) -> dict:
    return {m["id"]: m for m in resultado["metas"]}


def test_ninguna_vida_revienta(resultado):
    assert resultado["fallas"] == []
    assert resultado["personas"] == N


def test_son_las_37_metas_laborales_y_todas_se_miden(resultado):
    assert resultado["total"] == 37
    assert resultado["no_medibles"] == []
    grupos = {m["grupo"] for m in resultado["metas"]}
    assert "Vida" not in grupos
    assert {o["id"] for o in paquete().objetivos if o["grupo"] != "Vida"} == {m["id"] for m in resultado["metas"]}


def test_cuantas_metas_cuadran(resultado):
    assert resultado["cumplen"] >= MINIMO_CUADRAN, [m["id"] for m in resultado["metas"] if not m["cumple"]]
    assert resultado["cumplen"] == sum(1 for m in resultado["metas"] if m["cumple"])


@pytest.mark.parametrize("id_", CUADRAN)
def test_meta_clave_cuadra(metas, id_):
    m = metas[id_]
    margen = MARGEN_RELATIVO if m["tolerancia_relativa"] else MARGEN
    assert abs(m["error"]) <= m["tolerancia"] + margen, (m["meta"], m["simulado"])


def test_los_insumos_estan_marcados(metas):
    """Reproducir un insumo no es validar: esas metas no cuentan como validación."""
    for id_ in ("separacion_18_29", "cambio_30_44", "sigue_cesante_12m", "empresa_grande", "startup_anos"):
        assert metas[id_]["calidad"] == "insumo" and metas[id_]["es_insumo"]
    assert metas["desocupacion_25-29"]["calidad"] == "validacion"
    assert metas["edu_media_30_34"]["calidad"] == "calibrada"
    assert metas["ingreso_p50_30-34"]["calidad"] == "parcial"


def test_resumen_sin_insumos(resultado):
    por = resultado["por_calidad"]
    assert sum(v["total"] for v in por.values()) == 37
    assert resultado["total_sin_insumos"] == por["validacion"]["total"] + por["parcial"]["total"] == 18
    assert por["validacion"] == {"cumplen": 6, "total": 6}  # la desocupación por edad, que el motor no usa


def test_elsoc(resultado):
    filas = {x["id"]: x for x in resultado["elsoc"]}
    assert len(filas) == 9 and resultado["elsoc_total"] == 6
    for banda in ("18-29", "30-44", "45-59"):
        entrada = filas[f"elsoc_ocupado_a_cesante_{banda}"]
        assert abs(entrada["error"]) <= entrada["tolerancia"] + MARGEN, entrada
        # falta la salida a la inactividad: se mide, se muestra y no cuenta
        sin_empleo = filas[f"elsoc_ocupado_a_no_ocupado_{banda}"]
        assert sin_empleo["comparable"] is False and sin_empleo["cumple"] is None
        assert sin_empleo["error"] < -0.03


def test_el_ascenso_que_descuenta_el_alza_anual_es_el_promedio_de_la_cohorte():
    """ASCENSO_POBLACION se midió con esta cohorte: si cambia la regla de ascenso o los pesos, hay que medirla
    de nuevo; si no, el alza anual vuelve a contar los ascensos dos veces (o a no contarlos)."""
    pq = paquete()

    class Espia(Vida):
        diferencias: list[float] = []

        def _evento(self, id_, directo=False):
            if id_ == "alza_anual" and self.e["estado"] == "empleado":
                Espia.diferencias.append(self.e["prob_ascenso"] - pq.k("ASCENSO_POBLACION", self.e["banda7"]))
            super()._evento(id_, directo)

    for g in range(300):
        v = Espia(estado_inicial(Perfil.a_los_18(sexo="hm"[g % 2]), pq), Dados(SEMILLA, g), pq)
        while v.e["edad"] < validacion.EDAD_FIN:
            v.vivir_anio(Poblacion())
    assert len(Espia.diferencias) > 5000
    assert abs(sum(Espia.diferencias) / len(Espia.diferencias)) < 0.005


def test_misma_semilla_mismo_resultado_en_serie_y_en_paralelo():
    serie, _ = validacion.simular(24, semilla=3, procesos=1)
    paralelo, _ = validacion.simular(24, semilla=3, procesos=2)
    assert serie == paralelo
    otra, _ = validacion.simular(24, semilla=4, procesos=1)
    assert serie != otra


def test_la_tabla_se_imprime(resultado):
    texto = validacion.tabla(resultado)
    assert f"{resultado['cumplen']} de 37 metas cuadran" in texto
    assert "ELSOC" in texto
