"""El juego desde el terminal: `jugar`, `comparar`, `dudas` y `validar`.

Los pesos del motor se están calibrando: aquí no se fija ningún número de resultado,
solo la forma de la salida, su consistencia con el motor y que se repita con la misma semilla.
"""

import json
import re
import sys

import pytest

from app.cli import _frase_mundos, _plata, _tabla_gemelos, main
from app.sim.motor.partida import dudas_posibles, vista
from app.sim.motor.perfil import Perfil

N = "20"  # gemelos por opción: pocos, para que los tests sean rápidos
JERGA = ("p10", "p50", "p90", "percentil", "Monte Carlo", "montecarlo", "cuantil", "mediana de los gemelos",
         "mediana de las copias")
PERFILES = [
    ["--duda", "unirse_a_startup", "--semilla", "7"],
    ["--duda", "emprender", "--semilla", "11", "--edad", "45", "--sexo", "h", "--edu", "postgrado", "--rubro",
     "finanzas", "--tipo-empleador", "grande", "--nivel", "3", "--sueldo", "4500000"],
    ["--duda", "renunciar", "--semilla", "3", "--edad", "22", "--edu", "media", "--rubro", "Comercio", "--nivel", "0",
     "--sueldo", "550000", "--riesgo", "9"],
    ["--duda", "magister", "--semilla", "8", "--tipo-empleador", "publico", "--rubro", "Administración pública"],
]


def _run(capsys, *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def _jugar(capsys, *argv: str) -> tuple[int, str, str]:
    return _run(capsys, "jugar", "--gemelos", N, *argv)


def _elecciones_de(out: str) -> str:
    """Las elecciones que el propio juego dice que hay que pasar para repetir la partida."""
    comando = " ".join(linea.strip() for linea in out.split("Para repetir esta partida:")[1].splitlines())
    return re.search(r"--elecciones (\S+)", comando).group(1)


# ── jugar ────────────────────────────────────────────────────────────────────


def test_auto_juega_la_partida_completa(capsys):
    code, out, err = _jugar(capsys, "--duda", "unirse_a_startup", "--semilla", "7", "--auto")
    assert code == 0 and err == ""
    assert "Una startup te ofrece entrar con acciones." in out
    for anio in range(1, 11):
        assert f"AÑO {anio} DE 10" in out
    assert out.index("AÑO 1 DE 10") < out.index("AÑO 10 DE 10") < out.index("EL CIERRE")
    assert "Tu primera decisión: Una startup te ofrece entrar con acciones." in out
    assert "Semilla de esta partida: 7" in out
    # la partida se muestra entera: una elección y un cierre de año por cada paso
    assert out.count("Elegiste: ") >= 10
    assert out.count("→ Cierras el año con") == 10
    assert "EL CIERRE · 10 años después, tienes 40 años" in out


def test_auto_muestra_lo_que_entrega_el_motor(capsys):
    """La primera carta y el cierre son los de `vista`: ningún número sale del terminal."""
    _, out, _ = _jugar(capsys, "--duda", "unirse_a_startup", "--semilla", "7", "--auto")
    elecciones = [{"opcion": o} for o in ()]
    inicio = vista(Perfil(), 7, "unirse_a_startup", elecciones, int(N))
    comp = inicio["pendiente"]["comparacion"]
    primera = out.split("AÑO 2 DE 10")[0]
    for o in comp["opciones"]:
        assert o["nombre"] in primera
        for q in ("p10", "p50", "p90"):
            assert _plata(o["sueldo"][q]) in primera
        assert "Terminan en un cargo más alto" in primera
    assert f"a {N} copias tuyas" in primera
    assert "Calidad de estos números: mixto" in primera
    base = next(o for o in comp["opciones"] if o["es_base"])
    for o in comp["opciones"]:
        if not o["es_base"]:
            assert _frase_mundos(o, base) in " ".join(primera.split())


def test_misma_semilla_misma_salida(capsys):
    args = ["--duda", "unirse_a_startup", "--semilla", "5", "--auto"]
    _, primera, _ = _jugar(capsys, *args)
    _, segunda, _ = _jugar(capsys, *args)
    assert primera == segunda
    otras = {_jugar(capsys, "--duda", "unirse_a_startup", "--semilla", str(s), "--auto")[1] for s in (1, 2, 3)}
    assert len(otras | {primera}) > 1  # otra semilla, otra suerte


def test_elecciones_repiten_la_partida_de_auto(capsys):
    """La línea "para repetir esta partida" de verdad la repite, ahora sin --auto."""
    _, auto, _ = _jugar(capsys, "--duda", "cambiar_de_rubro", "--semilla", "4", "--auto")
    code, repetida, err = _jugar(capsys, "--duda", "cambiar_de_rubro", "--semilla", "4", "--elecciones", _elecciones_de(auto))
    assert code == 0 and err == ""
    assert repetida == auto


def test_elecciones_y_despues_auto(capsys):
    code, out, _ = _jugar(capsys, "--duda", "unirse_a_startup", "--semilla", "7", "--elecciones", "1", "--auto")
    assert code == 0
    assert "Elegiste: Irte." in out.split("AÑO 2 DE 10")[0]
    assert "EL CIERRE" in out and "Elegiste «Irte»" in out
    assert _elecciones_de(out).split(",")[0] == "1"


def test_eleccion_interna_va_al_motor(capsys):
    """`1:2` es opción 1 y, dentro de ella, la segunda alternativa (a qué rubro)."""
    interna = vista(Perfil(), 0, "cambiar_de_rubro", [], 0)["pendiente"]["opciones"][0]["elecciones_internas"][0]
    assert interna["variable"] == "rubro_destino"
    destino = interna["alternativas"][1]["nombre"]
    code, out, _ = _jugar(capsys, "--duda", "cambiar_de_rubro", "--semilla", "0", "--elecciones", "1:2", "--auto")
    assert code == 0
    assert f"¿A qué rubro? {destino}." in out
    assert _elecciones_de(out).split(",")[0] == "1:2"
    historia = vista(Perfil(), 0, "cambiar_de_rubro", [{"opcion": "cambiar", "parametros": {"rubro_destino": destino}}], 0)
    registro = (historia["historia"] or [historia["anio_en_curso"]])[0]
    assert registro["decisiones"][0]["texto"] in out


@pytest.mark.parametrize("perfil", PERFILES, ids=lambda p: p[1])
def test_partida_legible(capsys, perfil):
    code, out, err = _jugar(capsys, *perfil, "--auto")
    assert code == 0 and err == ""
    assert "EL CIERRE" in out
    largas = [linea for linea in out.splitlines() if len(linea) > 100]
    assert largas == []
    for jerga in JERGA:
        assert jerga not in out
    # los montos se escriben de una sola forma: pesos con puntos, redondeados a miles
    # (los textos del paquete traen sus propias cifras, como "$9 millones" o "$667 mil": esas no son nuestras)
    montos = [m.group() for m in re.finditer(r"\$[\d.,]*\d", out) if not out[m.end():].startswith(" mil")]
    assert montos
    for monto in montos:
        assert re.fullmatch(r"\$(0|\d{1,3}(\.\d{3})+)", monto), monto
    assert not re.search(r"\d[,.]\d ?M\b", out)  # nada de "$1,4M" mezclado con "$1.400.000"
    assert "$-" not in out
    assert not re.search(r"\b(None|nan|inf)\b", out)


def test_jugar_con_teclado(capsys, monkeypatch):
    """Sin --duda ni --elecciones se pregunta todo: la duda, cada opción y lo que se elige dentro de ella."""
    preguntas = []

    def responder(texto: str = "") -> str:
        preguntas.append(texto)
        return "" if "Enter" in texto else "1"

    monkeypatch.setattr("builtins.input", responder)
    code, out, err = _jugar(capsys, "--semilla", "2")
    assert code == 0 and err == ""
    assert "¿Qué duda te trae?" in out
    assert preguntas[0].startswith("Tu duda (1 a ")
    assert sum(1 for p in preguntas if p.startswith("¿Qué eliges?")) >= 10
    primera = dudas_posibles(Perfil())[0]
    assert primera["pregunta"] in out
    assert f"--duda {primera['decision']} --semilla 2" in " ".join(out.split())
    assert "EL CIERRE" in out


def test_teclado_repite_la_pregunta_si_la_respuesta_no_sirve(capsys, monkeypatch):
    respuestas = iter(["", "x", "99", "2"])
    monkeypatch.setattr("builtins.input", lambda texto="": next(respuestas, "1"))
    code, out, _ = _jugar(capsys, "--duda", "unirse_a_startup", "--semilla", "7")
    assert code == 0
    assert out.count("Escribe un número entre 1 y 2.") == 3
    assert "Elegiste: Quedarte." in out.split("AÑO 2 DE 10")[0]


def test_sin_gemelos_no_compara(capsys):
    code, out, _ = _run(capsys, "jugar", "--gemelos", "0", "--duda", "unirse_a_startup", "--semilla", "7", "--auto")
    assert code == 0
    assert "copias tuyas" not in out
    assert "(Para esta decisión no se simulan copias.)" in out
    assert "EL CIERRE" in out


def test_un_doctorado_ocupa_varios_anios_y_el_juego_dura_diez(capsys):
    """El año se cuenta por edad: tras un doctorado el encabezado salta, y la partida termina a los 40."""
    code, out, _ = _jugar(capsys, "--duda", "doctorado", "--semilla", "8", "--elecciones", "1", "--auto")
    assert code == 0
    cabeceras = [(int(n), int(edad)) for n, edad in re.findall(r"AÑO (\d+) DE 10 · tienes (\d+) años", out)]
    assert cabeceras[0] == (1, 30)
    assert all(n == edad - 29 and 1 <= n <= 10 for n, edad in cabeceras)
    assert cabeceras[1][0] >= 4  # el doctorado no dura un año
    assert re.search(r"→ Pasan \d años y quedas con 3\d años", out)
    assert "EL CIERRE · 10 años después, tienes 40 años" in out


def _opcion(mas: float, igual: float, menos: float, diferencia: int) -> dict:
    return {"nombre": "Sí", "gana_mas_que_base": mas, "igual_que_base": igual, "gana_menos_que_base": menos,
            "diferencia_tipica": diferencia}


@pytest.mark.parametrize(
    "opcion, frase",
    [
        (_opcion(0, 1, 0, 0), "«Sí» frente a «No»: no cambia tu sueldo en ningún mundo."),
        (_opcion(0.03, 0.96, 0.01, 0), "«Sí» frente a «No»: no cambia tu sueldo en casi ningún mundo."),
        (_opcion(0.09, 0.89, 0.02, 0),
         "«Sí» frente a «No»: en 1 de cada 10 mundos ganas más y en 9 de cada 10 da lo mismo. "
         "Diferencia típica: $0 al mes."),
        (_opcion(0.02, 0.26, 0.72, -12_300),
         "«Sí» frente a «No»: en 3 de cada 10 mundos da lo mismo y en 7 de cada 10 ganas menos. "
         "Diferencia típica: −$12.000 al mes."),
        (_opcion(0.55, 0.14, 0.31, 169_363),
         "«Sí» frente a «No»: en 6 de cada 10 mundos ganas más, en 1 de cada 10 da lo mismo y en 3 de cada 10 "
         "ganas menos. Diferencia típica: +$169.000 al mes."),
        (_opcion(1, 0, 0, 250_000),
         "«Sí» frente a «No»: en todos los mundos ganas más. Diferencia típica: +$250.000 al mes."),
        (_opcion(0.02, 0.0, 0.98, -400_000),
         "«Sí» frente a «No»: en casi todos los mundos ganas menos. Diferencia típica: −$400.000 al mes."),
    ],
)
def test_frase_de_mundos(opcion, frase):
    """Los tres casos (más, igual, menos) y la magnitud: un empate no se cuenta como derrota."""
    assert _frase_mundos(opcion, {"nombre": "No"}) == frase


def test_cesantia_con_cinco_opciones_cabe_en_la_pantalla():
    cesante = Perfil(estado="buscando")
    comp = vista(cesante, 3, "cesantia", [], int(N))["pendiente"]["comparacion"]
    assert len(comp["opciones"]) == 5
    tabla = _tabla_gemelos(comp)
    assert max(len(linea) for linea in tabla) <= 100
    texto = "\n".join(tabla)
    for i, o in enumerate(comp["opciones"], 1):
        assert f"{i}. {o['nombre'][:12]}" in texto
        assert _plata(o["sueldo"]["p50"]) in texto
    assert "…" not in "\n".join(linea for linea in tabla if "de cada 100" in linea)  # ninguna celda cortada


def test_auto_toma_la_base_del_motor_con_y_sin_gemelos(capsys):
    """`--auto` elige lo mismo se simulen gemelos o no: la base la define el motor, no la comparación."""
    _, con, _ = _jugar(capsys, "--duda", "oferta_externa", "--semilla", "9", "--auto")
    _, sin, _ = _run(capsys, "jugar", "--gemelos", "0", "--duda", "oferta_externa", "--semilla", "9", "--auto")
    assert _elecciones_de(con) == _elecciones_de(sin)
    base = vista(Perfil(), 9, "oferta_externa", [], int(N))["pendiente"]["comparacion"]["base"]
    assert base == "quedarse" and "Elegiste: Quedarte." in con.split("AÑO 2 DE 10")[0]


# ── comparar y dudas ─────────────────────────────────────────────────────────


def test_comparar_json_es_el_dict_del_motor(capsys):
    code, out, _ = _run(capsys, "comparar", "--duda", "oferta_externa", "--semilla", "3", "--gemelos", N, "--json")
    assert code == 0
    comp = json.loads(out)
    assert comp == vista(Perfil(), 3, "oferta_externa", [], int(N))["pendiente"]["comparacion"]
    assert comp["gemelos"] == int(N) and comp["decision"] == "oferta_externa"
    assert [o["es_base"] for o in comp["opciones"]].count(True) == 1
    for o in comp["opciones"]:
        assert o["sueldo"]["p10"] <= o["sueldo"]["p50"] <= o["sueldo"]["p90"]
        assert 0 <= o["paso_por_cesantia"] <= 1
        assert sum(r["gemelos"] for r in o["por_resultado"]) == int(N)
        assert (o["gana_mas_que_base"] is None) == o["es_base"]


def test_comparar_muestra_la_tabla_sin_jugar(capsys):
    code, out, err = _run(capsys, "comparar", "--duda", "oferta_externa", "--semilla", "3", "--gemelos", N)
    assert code == 0 and err == ""
    comp = vista(Perfil(), 3, "oferta_externa", [], int(N))["pendiente"]["comparacion"]
    assert comp["pregunta"] in out
    for i, o in enumerate(comp["opciones"], 1):
        assert f"{i}. {o['nombre']}" in out
        assert _plata(o["sueldo"]["p50"]) in out
        if not o["es_base"]:
            assert f"«{o['nombre']}» frente a «" in " ".join(out.split())
    assert comp["creencia_vs_dato"] in " ".join(out.split())
    assert "AÑO 1" not in out and "Elegiste" not in out
    assert max(len(linea) for linea in out.splitlines()) <= 100
    for jerga in JERGA:
        assert jerga not in out


def test_comparar_dice_que_eligen_los_gemelos_dentro_de_la_opcion(capsys):
    _, out, _ = _run(capsys, "comparar", "--duda", "cambiar_de_rubro", "--gemelos", N)
    assert "Las copias de «Cambiarte» responden «¿A qué rubro?» con «" in out


def test_dudas_lista_las_del_motor(capsys):
    code, out, _ = _run(capsys, "dudas")
    assert code == 0
    dudas = dudas_posibles(Perfil())
    assert dudas
    for d in dudas:
        assert d["decision"] in out and d["pregunta"] in out
    assert max(len(linea) for linea in out.splitlines()) <= 100
    code, crudo, _ = _run(capsys, "dudas", "--json")
    assert code == 0 and json.loads(crudo) == dudas


def test_dudas_dependen_del_perfil(capsys):
    """Quien ya trabaja en una startup no recibe la carta de irse a una."""
    _, out, _ = _run(capsys, "dudas", "--tipo-empleador", "startup", "--json")
    ids = [d["decision"] for d in json.loads(out)]
    assert ids == [d["decision"] for d in dudas_posibles(Perfil(tipo_empleador="startup"))]
    assert "unirse_a_startup" not in ids


# ── errores ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "argv, pista",
    [
        (["jugar", "--duda", "no_existe", "--auto"], "no existe o no aplica"),
        (["jugar", "--duda", "cesantia", "--auto"], "no existe o no aplica"),  # está empleada: no aplica
        (["jugar", "--auto"], "--duda"),
        (["jugar", "--duda", "unirse_a_startup", "--elecciones", "1,dos"], "no entiendo 'dos'"),
        (["jugar", "--duda", "unirse_a_startup", "--elecciones", "0"], "no entiendo '0'"),
        (["jugar", "--duda", "unirse_a_startup", "--elecciones", "9"], "opción 9"),
        (["jugar", "--duda", "unirse_a_startup", "--elecciones", "1:4"], "dentro de «Irte»"),
        (["jugar", "--duda", "cambiar_de_rubro", "--elecciones", "1:99"], "alternativa 99"),
        (["jugar", "--duda", "unirse_a_startup", "--gemelos", "5000", "--auto"], "--gemelos"),
        (["jugar", "--duda", "unirse_a_startup", "--edad", "17", "--auto"], "--edad"),
        (["jugar", "--duda", "unirse_a_startup", "--sexo", "x", "--auto"], "--sexo"),
        (["jugar", "--duda", "unirse_a_startup", "--edu", "kinder", "--auto"], "--edu"),
        (["jugar", "--duda", "unirse_a_startup", "--rubro", "Astrología", "--auto"], "No conozco el rubro"),
        (["jugar", "--duda", "unirse_a_startup", "--tipo-empleador", "ong", "--auto"], "--tipo-empleador"),
        (["jugar", "--duda", "unirse_a_startup", "--nivel", "9", "--auto"], "--nivel"),
        (["jugar", "--duda", "unirse_a_startup", "--sueldo", "0", "--auto"], "--sueldo"),
        (["jugar", "--duda", "unirse_a_startup", "--riesgo", "11", "--auto"], "--riesgo"),
        (["comparar", "--duda", "no_existe"], "no existe o no aplica"),
        (["comparar", "--duda", "unirse_a_startup", "--gemelos", "0"], "--gemelos"),
        (["dudas", "--edad", "80"], "--edad"),
        (["validar", "--n", "0"], "--n"),
    ],
)
def test_entrada_invalida(capsys, argv, pista):
    if argv[0] == "jugar" and "--gemelos" not in argv:
        argv = [*argv, "--gemelos", N]
    code, out, err = _run(capsys, *argv)
    assert code != 0
    assert err.startswith("Error: ") and pista in err
    assert "Traceback" not in err and "Traceback" not in out


def test_sobran_elecciones(capsys):
    _, auto, _ = _jugar(capsys, "--duda", "unirse_a_startup", "--semilla", "7", "--auto")
    code, _, err = _jugar(capsys, "--duda", "unirse_a_startup", "--semilla", "7", "--elecciones", _elecciones_de(auto) + ",1")
    assert code != 0
    assert "Sobran elecciones" in err and "Traceback" not in err


def test_sin_teclado_y_sin_elecciones_avisa(capsys, monkeypatch):
    def sin_teclado(texto: str = "") -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", sin_teclado)
    code, out, err = _jugar(capsys, "--duda", "unirse_a_startup", "--semilla", "7", "--elecciones", "2")
    assert code != 0
    assert "AÑO 1 DE 10" in out  # lo jugado hasta ahí se alcanza a ver
    assert "--auto" in err and "Traceback" not in err


def test_falta_el_subcomando_o_la_duda(capsys):
    assert main(["comparar"]) != 0
    assert "--duda" in capsys.readouterr().err


# ── validar ──────────────────────────────────────────────────────────────────


def test_validar_sin_el_modulo_avisa(capsys, monkeypatch):
    monkeypatch.setitem(sys.modules, "app.sim.motor.validacion", None)  # como si todavía no existiera
    code, out, err = _run(capsys, "validar")
    assert code != 0
    assert out == "" and "validación" in err and "Traceback" not in err


def test_validar_imprime_la_tabla_del_modulo(capsys, monkeypatch):
    """`validar` no depende de la forma del resultado: le pasa n y semilla y muestra su tabla."""
    import types

    falso = types.ModuleType("app.sim.motor.validacion")
    falso.validar = lambda n, semilla: {"n": n, "semilla": semilla}
    falso.tabla = lambda r: f"cohorte de {r['n']} con semilla {r['semilla']}"
    monkeypatch.setitem(sys.modules, "app.sim.motor.validacion", falso)
    code, out, _ = _run(capsys, "validar", "--n", "40", "--semilla", "3")
    assert code == 0 and out.strip() == "cohorte de 40 con semilla 3"
    code, out, _ = _run(capsys, "validar", "--n", "40", "--json")
    assert code == 0 and json.loads(out) == {"n": 40, "semilla": 0}


def test_validar_de_verdad_si_ya_existe(capsys):
    pytest.importorskip("app.sim.motor.validacion")
    code, out, err = _run(capsys, "validar", "--n", "40")
    assert code == 0 and err == ""
    assert out.strip()
