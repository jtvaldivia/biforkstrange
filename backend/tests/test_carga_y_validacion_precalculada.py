"""La fila de cálculos pesados y la validación que deja calculada el deploy."""

import json
import threading

import pytest
from fastapi import HTTPException

from app.core import carga
from app.sim.motor import validacion


def test_en_fila_corre_de_a_uno_y_da_503_si_la_espera_se_pasa(monkeypatch):
    monkeypatch.setattr(carga, "_fila", threading.BoundedSemaphore(1))
    monkeypatch.setattr(carga, "ESPERA_MAXIMA", 0.05)
    adentro = threading.Event()
    soltar = threading.Event()

    @carga.en_fila
    def lento():
        adentro.set()
        soltar.wait(2)
        return "listo"

    @carga.en_fila
    def rapido():
        return "rápido"

    hilo = threading.Thread(target=lento)
    hilo.start()
    adentro.wait(2)
    with pytest.raises(HTTPException) as error:
        rapido()
    assert error.value.status_code == 503
    assert error.value.headers == {"Retry-After": "10"}
    soltar.set()
    hilo.join(2)
    assert rapido() == "rápido"  # al salir el primero, el turno queda libre


def test_en_fila_suelta_el_turno_aunque_el_calculo_falle(monkeypatch):
    monkeypatch.setattr(carga, "_fila", threading.BoundedSemaphore(1))
    monkeypatch.setattr(carga, "ESPERA_MAXIMA", 0.05)

    @carga.en_fila
    def falla():
        raise ValueError("no aplica")

    with pytest.raises(ValueError):
        falla()
    with pytest.raises(ValueError):
        falla()  # si el turno hubiera quedado tomado, esto sería un 503


def test_precalculada_solo_se_usa_si_es_del_mismo_motor_n_y_semilla(tmp_path, monkeypatch):
    archivo = tmp_path / "validacion.json"
    monkeypatch.setattr(validacion, "PRECALCULADA", archivo)
    assert validacion.precalculada(1000, 0) is None  # sin archivo

    resultado = {"n": 1000, "semilla": 0, "cumplen": 33, "total": 37}
    archivo.write_text(json.dumps({"huella": validacion.huella(), "resultado": resultado}))
    assert validacion.precalculada(1000, 0) == resultado
    assert validacion.precalculada(2000, 0) is None
    assert validacion.precalculada(1000, 1) is None

    archivo.write_text(json.dumps({"huella": "otro-motor", "resultado": resultado}))
    assert validacion.precalculada(1000, 0) is None

    archivo.write_text("{roto")
    assert validacion.precalculada(1000, 0) is None


def test_para_api_saca_fallas_y_decisiones():
    assert validacion.para_api({"cumplen": 1, "fallas": [], "decisiones": {}}) == {"cumplen": 1}
