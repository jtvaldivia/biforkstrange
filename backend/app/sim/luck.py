"""Suerte compartida (números aleatorios comunes). Cada sorteo depende solo de
(semilla, año, nombre del sorteo), no de la decisión tomada. Así dos caminos del mismo
gemelo viven la misma suerte y su diferencia se debe a la decisión, no al azar."""

import zlib

import numpy as np


class Suerte:
    def __init__(self, seed: int, n: int):
        self.seed, self.n = int(seed), int(n)

    def _rng(self, t: int, nombre: str) -> np.random.Generator:
        return np.random.default_rng([self.seed, int(t), zlib.crc32(nombre.encode())])

    def u(self, t: int, nombre: str) -> np.ndarray:
        return self._rng(t, nombre).random(self.n)

    def z(self, t: int, nombre: str) -> np.ndarray:
        return self._rng(t, nombre).standard_normal(self.n)

    def escalar(self, t: int, nombre: str) -> float:
        """Un solo número para todos los universos: lo que el mundo te ofrece ese año (cartas de oportunidad)."""
        return float(self._rng(t, "escalar_" + nombre).random())

    def indice(self, t: int) -> int:
        """Cuál de los universos es el que 'te tocó' este año."""
        return int(self._rng(t, "realizado").integers(self.n))
