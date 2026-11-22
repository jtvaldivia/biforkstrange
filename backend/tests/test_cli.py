import json

import pytest

from app.cli import main
from app.sim import labor
from app.sim.tables import tablas


def _run(capsys, *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_ocupaciones_lista_los_diez_grupos(capsys):
    code, out, _ = _run(capsys, "ocupaciones")
    assert code == 0
    for g, nombre in enumerate(tablas().nombres):
        assert f"{g}  {nombre}" in out


def test_perfil_responde_las_tres_preguntas(capsys):
    code, out, _ = _run(capsys, "perfil", "--ocupacion", "2", "--edad", "30")
    assert code == 0
    assert "Profesionales científicos e intelectuales" in out
    assert "¿Qué tan probable es que tu trabajo termine este año?" in out
    assert "¿Cuánto suele durar un trabajo de este tipo?" in out
    assert "¿A qué tipo de trabajo pasas después?" in out
    assert "EPS 2024" in out and "Flandes" in out

    p = labor.perfil(2, 30)
    total = round(p["termino_anual"]["total"] * 100)
    assert f"a {total} se les termina" in out
    assert f"Las otras {100 - total} siguen" in out
    # los 10 destinos, en el orden del motor (de más a menos probable)
    posiciones = [out.index("  " + s["nombre"]) for s in p["siguiente"]]
    assert posiciones == sorted(posiciones)
    assert "█" in out


@pytest.mark.parametrize("grupo", range(10))
@pytest.mark.parametrize("edad", [20, 35, 50])
def test_perfil_legible_para_todos(capsys, grupo, edad):
    code, out, _ = _run(capsys, "perfil", "--ocupacion", str(grupo), "--edad", str(edad))
    assert code == 0
    assert max(len(linea) for linea in out.splitlines()) <= 100
    # el desglose suma lo mismo que el total que se anuncia
    lineas = out.splitlines()
    i = next(k for k, linea in enumerate(lineas) if "se les termina" in linea)
    total = int(lineas[i].split(" a ")[1].split()[0])
    assert sum(int(linea.split()[0]) for linea in lineas[i + 1 : i + 4]) == total
    for jerga in ("p25", "p50", "p75", "hazard", "ISCO", "percentil"):
        assert jerga not in out


def test_perfil_json_es_el_dict_del_motor(capsys):
    code, out, _ = _run(capsys, "perfil", "--ocupacion", "7", "--edad", "45", "--json")
    assert code == 0
    assert json.loads(out) == labor.perfil(7, 45)


def test_simular_muestra_una_fila_por_anio(capsys):
    code, out, _ = _run(
        capsys, "simular", "--ocupacion", "4", "--edad", "24", "--sueldo", "800000",
        "--decisiones", "seguir,cambiar_pega,estudiar", "--runs", "500", "--seed", "3",
    )  # fmt: skip
    assert code == 0
    assert "$800.000" in out
    assert "Personal de apoyo administrativo" in out
    for etiqueta in ("Seguir igual", "Cambiar de trabajo", "Estudiar"):
        assert etiqueta in out
    lineas = out.splitlines()
    filas = lineas[lineas.index("-" * 100) + 1 :]
    assert [f.split()[0] for f in filas[:3]] == ["25", "26", "27"]
    assert "terminan tus gemelos a los 27 años" in out
    assert "EPS 2024" in out and "Flandes" in out
    assert max(len(linea) for linea in lineas) <= 100
    for jerga in ("p10", "p50", "p90", "ISCO"):
        assert jerga not in out


def test_simular_sin_decisiones_usa_seguir(capsys):
    code, out, _ = _run(capsys, "simular", "--ocupacion", "2", "--edad", "30", "--anios", "4", "--runs", "200", "--json")
    assert code == 0
    data = json.loads(out)
    assert [a["decision"] for a in data["trayectoria"]] == ["seguir"] * 4
    assert data["edad_final"] == 34
    assert "ocupaciones" in data["trayectoria"][-1]


def test_simular_semilla_reproduce(capsys):
    argv = ["simular", "--ocupacion", "5", "--edad", "40", "--anios", "3", "--runs", "300"]
    _, a, _ = _run(capsys, *argv, "--seed", "7")
    _, b, _ = _run(capsys, *argv, "--seed", "7")
    _, c, _ = _run(capsys, *argv, "--seed", "8")
    assert a == b
    assert a != c


@pytest.mark.parametrize(
    "argv,pista",
    [
        (["perfil", "--ocupacion", "10", "--edad", "30"], "tipo de trabajo 10"),
        (["perfil", "--ocupacion", "-1", "--edad", "30"], "tipo de trabajo -1"),
        (["perfil", "--ocupacion", "2", "--edad", "12"], "edad"),
        (["simular", "--ocupacion", "12", "--edad", "30"], "tipo de trabajo 12"),
        (["simular", "--ocupacion", "2", "--edad", "30", "--decisiones", "seguir,volar"], "volar"),
        (["simular", "--ocupacion", "2", "--edad", "30", "--decisiones", "seguir", "--anios", "3"], "--anios"),
        (["simular", "--ocupacion", "2", "--edad", "30", "--anios", "0"], "--anios"),
        (["perfil", "--ocupacion", "dos", "--edad", "30"], "ocupacion"),
        (["perfil"], "ocupacion"),
        ([], "comando"),
    ],
)
def test_errores_de_entrada(capsys, argv, pista):
    code, out, err = _run(capsys, *argv)
    assert code != 0
    assert out == ""
    assert pista in err
    assert "Traceback" not in err
