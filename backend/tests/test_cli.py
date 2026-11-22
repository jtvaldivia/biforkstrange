import pytest

from app.cli import main
from app.sim.motor.paquete import paquete


def _run(capsys, *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_ocupaciones_lista_los_diez_grupos(capsys):
    code, out, _ = _run(capsys, "ocupaciones")
    assert code == 0
    grupos = {int(f["origen"]): f["origen_nombre"] for f in paquete().filas("jobhop_transiciones")}
    assert len(grupos) == 10
    for g, nombre in grupos.items():
        assert f"{g}  {nombre}" in out


@pytest.mark.parametrize(
    "argv,pista",
    [
        (["simular"], "invalid choice"),  # el motor viejo ya no existe
        (["perfil"], "invalid choice"),
        ([], "comando"),
    ],
)
def test_errores_de_entrada(capsys, argv, pista):
    code, out, err = _run(capsys, *argv)
    assert code != 0
    assert out == ""
    assert pista in err
    assert "Traceback" not in err
