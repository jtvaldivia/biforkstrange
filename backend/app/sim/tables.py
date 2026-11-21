"""Tablas agregadas que usa el motor (se generan con scripts/build_sim_data.py)."""

import json
from functools import lru_cache
from pathlib import Path

import numpy as np


def por_tramo(tabla: dict, x: float):
    """Valor de una tabla con llaves como '18-29', '<30', '55+' o '20-35' para x."""
    for k, v in tabla.items():
        if k.startswith("<") and x < float(k[1:]):
            return v
        if k.endswith("+") and x >= float(k[:-1]):
            return v
        if "-" in k:
            a, b = k.split("-")
            if float(a) <= x <= float(b):
                return v
    claves = [k for k in tabla if "-" in k]   # fuera de rango: el tramo más cercano
    return tabla[min(claves, key=lambda k: min(abs(x - float(c)) for c in k.split("-")))]


def tramo3(edad: int) -> str:
    return "18-29" if edad < 30 else "30-44" if edad < 45 else "45-59"


class Tablas:
    def __init__(self):
        t = json.loads((Path(__file__).parent / "data" / "tablas.json").read_text(encoding="utf-8"))
        self.raw = t
        jh = t["jobhop"]
        self.codigos: list[str] = jh["ocupaciones"]
        self.idx = {c: i for i, c in enumerate(self.codigos)}
        self.nombres = [t["isco3"][c] for c in self.codigos]
        k = len(self.codigos)
        n = np.array([jh["n_empleos"][c] for c in self.codigos], float)
        self.peso = n / n.sum()
        T = np.zeros((k, k))
        for a, fila in jh["transiciones"].items():
            for b, p in fila.items():
                T[self.idx[a], self.idx[b]] = p
        s = T.sum(1, keepdims=True)
        self.tiene_destinos = s[:, 0] > 0
        self.T = T / np.where(s == 0, 1, s)
        self.T_acum = np.cumsum(self.T, 1)
        # afinidad 0..1: 0,5 = se pasa de a hacia b tanto como al azar; cerca de 1 = paso muy frecuente
        self.afinidad = self.T / (self.T + self.peso[None, :])
        self.p_cambia = np.array([jh["p_cambia_de_grupo"].get(c, 0.0) for c in self.codigos])
        self.ia = np.array([t["exposicion_ia"]["percentil"][c] for c in self.codigos])
        rel = {g: v["relativo"] for g, v in t["esi_ocupacion"]["por_grupo"].items()}
        # ocupaciones de grupos sin sueldo en la ESI (fuerzas armadas, agropecuarios calificados) no son destino posible
        self.con_sueldo = np.array([c[0] in rel for c in self.codigos])
        self.rel = np.array([rel.get(c[0], np.nan) for c in self.codigos])
        T = self.T * self.con_sueldo[None, :]
        s = T.sum(1, keepdims=True)
        self.tiene_destinos = (s[:, 0] > 0) & self.con_sueldo
        self.T = T / np.where(s == 0, 1, s)
        self.T_acum = np.cumsum(self.T, 1)
        self.es_directivo = np.array([c[0] == "1" for c in self.codigos])
        # a qué ocupación directiva se asciende desde cada una (-1 si no hay)
        dirig = np.where(self.es_directivo[None, :], self.T, 0)
        self.jefatura_dest = np.where(dirig.max(1) > 0, dirig.argmax(1), -1)
        self.universidades = json.loads((Path(__file__).parent / "data" / "magister.json").read_text(encoding="utf-8"))["universidades"]
        self.uni_idx = {u["codigo"]: k for k, u in enumerate(self.universidades)}
        self.uni_defecto = max(range(len(self.universidades)), key=lambda k: self.universidades[k]["n"])   # la que más magísteres ofrece
        self.mult_rubro = t["ine"]["MULT_SALIDA_POR_RUBRO"]
        from app.sim.companies import RUBROS

        self.mult_rubro_idx = np.array([self.mult_rubro.get(r, 1.0) for r in RUBROS])
        self._hijo = t["ine"]["P_HIJO_ANUAL_MUJER_por_edad"]
        self._perfil_edu = {}
        for edu, d in t["esi_edad_educacion"].items():
            xs, ys = [], []
            for tr, v in sorted(d.items()):
                a, b = tr.split("-")
                if v.get("n", 0) >= 100:
                    xs.append((int(a) + int(b)) / 2)
                    ys.append(np.log(v["p50"]))
            self._perfil_edu[edu] = (np.array(xs), np.array(ys))
        # tasa de ahorro por ingreso per cápita (EPF IX)
        q = [t["epf_quintiles"][k] for k in ("I", "II", "III", "IV", "V")]
        self._epf_x = np.log([v["ingreso_disponible_per_capita"] for v in q])
        self._epf_s = np.array([v["tasa_ahorro_aparente"] for v in q])
        self.gasto_piso = q[0]["gasto_per_capita"]

    def crecimiento_edad(self, edu: str, edad: int) -> float:
        """Pendiente anual del log sueldo mediano según el perfil por edad de la ESI 2025."""
        xs, ys = self._perfil_edu.get(edu, self._perfil_edu["universitaria"])
        return float(np.interp(edad + 1, xs, ys) - np.interp(edad, xs, ys))

    def mediana_esi(self, edu: str, edad: int) -> float:
        xs, ys = self._perfil_edu.get(edu, self._perfil_edu["universitaria"])
        return float(np.exp(np.interp(edad, xs, ys)))

    def p_hijo(self, edad: int) -> float:
        for tr, p in self._hijo.items():
            a, b = tr.split("-")
            if int(a) <= edad <= int(b):
                return p
        return 0.0

    def tasa_ahorro(self, ingreso_mes: np.ndarray) -> np.ndarray:
        return np.interp(np.log(np.maximum(ingreso_mes, 1.0)), self._epf_x, self._epf_s)

    def buscar(self, texto: str) -> list[int]:
        q = texto.lower()
        return [i for i, (c, nom) in enumerate(zip(self.codigos, self.nombres)) if q == c or q in nom.lower()]


@lru_cache
def tablas() -> Tablas:
    return Tablas()
