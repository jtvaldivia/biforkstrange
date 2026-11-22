"""Dados con suerte compartida.

Cada sorteo se identifica por (semilla, gemelo, año, sitio) y no por el orden en
que se pide. Así un mismo gemelo que vive dos veces con decisiones distintas
recibe la misma suerte en todo lo que no depende de la decisión: la misma
recesión siempre, y el mismo ascenso o despido mientras sigue en la misma pega
(`motor.py` agrega el número de pega al sitio de esos eventos).
"""

import math
import random
from hashlib import blake2b
from statistics import NormalDist

_Z = NormalDist()
_Z90 = 1.2816  # percentil 90 de la normal estándar, igual que el evaluador de referencia


def _entero(clave: str) -> int:
    return int.from_bytes(blake2b(clave.encode(), digest_size=8).digest(), "big")


class Flujo:
    """Números al azar para una expresión (azar(), azar_uniforme()...), propios de su sitio."""

    def __init__(self, semilla: int):
        self._r = random.Random(semilla)

    def u(self) -> float:
        return self._r.random()

    def uniforme(self, a, b) -> float:
        return a + (b - a) * self._r.random()

    def normal(self) -> float:
        return _Z.inv_cdf(min(max(self._r.random(), 1e-12), 1 - 1e-12))

    def entero(self, a, b) -> int:
        return self._r.randint(int(a), int(b))

    def lognormal(self, p10, p50, p90) -> float:
        s = (math.log(p90) - math.log(p10)) / (2 * _Z90)
        return math.exp(math.log(p50) + s * self.normal())


class Dados:
    def __init__(self, semilla: int, gemelo: int | str = 0):
        self.semilla = semilla
        self.gemelo = gemelo
        self._prefijo = f"{semilla}|{gemelo}|"

    def u(self, anio: int, sitio: str) -> float:
        """Uniforme en [0, 1) para un sorteo con nombre."""
        return _entero(f"{self._prefijo}{anio}|{sitio}") / 2**64

    def flujo(self, anio: int, sitio: str) -> Flujo:
        return Flujo(_entero(f"{self._prefijo}{anio}|{sitio}|f"))

    def elegir(self, anio: int, sitio: str, pesos: list[float]) -> int:
        """Índice sorteado en proporción a los pesos."""
        total = sum(pesos)
        if total <= 0:
            raise ValueError(f"pesos sin masa en {sitio}")
        x = self.u(anio, sitio) * total
        acumulado = 0.0
        for i, p in enumerate(pesos):
            acumulado += p
            if x < acumulado:
                return i
        return len(pesos) - 1
