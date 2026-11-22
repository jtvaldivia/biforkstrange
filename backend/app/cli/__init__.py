"""La trayectoria laboral desde el terminal, sin levantar el servidor.

    python -m app.cli ocupaciones
    python -m app.cli perfil --ocupacion 2 --edad 30
    python -m app.cli simular --ocupacion 4 --edad 24 --decisiones seguir,cambiar_pega,seguir

`perfil` y `simular` aceptan `--json` para ver el dict crudo del motor.

El juego (motor del paquete, `app/sim/motor/`):

    python -m app.cli dudas
    python -m app.cli comparar --duda unirse_a_startup
    python -m app.cli jugar --duda unirse_a_startup --semilla 7
    python -m app.cli jugar --duda unirse_a_startup --semilla 7 --auto
    python -m app.cli jugar --duda cambiar_de_rubro --elecciones 1:3,2,1 --auto
    python -m app.cli validar
    python -m app.cli supuestos
"""

from app.cli.app import main
from app.cli.juego_formato import _frase_mundos, _plata, _tabla_gemelos

__all__ = ["_frase_mundos", "_plata", "_tabla_gemelos", "main"]
