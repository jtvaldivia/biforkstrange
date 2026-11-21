"""Estado vectorizado: cada atributo es un arreglo con un valor por universo."""

from dataclasses import dataclass, field, fields

import numpy as np

from app.sim.companies import RUBRO_DEFECTO, RUBROS
from app.sim.params import P
from app.sim.profile import TAMANOS, Perfil
from app.sim.tables import por_tramo, tablas

EMP, CES, SAB, EMPR = 0, 1, 2, 3          # situación laboral
SITUACIONES = ["con empleo", "sin trabajo", "en pausa", "emprendiendo"]
ANIO_INICIAL = 2026


class Eventos(dict):
    """Lo que pasó en el año, un arreglo por tipo de evento. Lo que no ocurrió vale False."""

    def __init__(self, n: int, *a, **kw):
        super().__init__(*a, **kw)
        self.n = n

    def __missing__(self, k):
        return np.zeros(self.n, bool)


@dataclass
class Estado:
    n: int
    t: int                 # años simulados
    edad: int
    anio: int
    sit: np.ndarray        # EMP | CES | SAB | EMPR
    ocup: np.ndarray       # índice de ocupación ISCO-3
    exp_ocup: np.ndarray   # años en la ocupación actual (capital humano específico)
    tam: np.ndarray        # índice en TAMANOS
    nivel: np.ndarray      # 0 junior .. 4 gerencia
    antig: np.ndarray      # años con el empleador actual
    sueldo: np.ndarray     # líquido mensual del empleo actual o del último
    cicatriz: np.ndarray   # castigo tras la cesantía (log), decae
    mult_rubro: np.ndarray
    rubro: np.ndarray      # índice en companies.RUBROS
    empresa: np.ndarray    # índice en companies.NOMBRES (0 = la empresa del perfil)
    anios_ces: np.ndarray
    hueco_vol: np.ndarray  # viene de una pausa elegida
    emp_anios: np.ndarray
    emp_q: np.ndarray      # calidad persistente del emprendimiento (z)
    postgrado: np.ndarray
    estudia: np.ndarray    # años de magíster que quedan
    penal_hijo: np.ndarray
    horas: np.ndarray
    animo: np.ndarray      # satisfacción con la vida, 0-100
    salud: np.ndarray      # salud subjetiva, 0-100
    depresion: np.ndarray  # síntomas depresivos moderados o severos este año
    social: np.ndarray     # tiempo con tu gente, 100 = jornada de 45 horas
    ahorros: np.ndarray
    gasto: np.ndarray      # gasto mensual
    pareja: np.ndarray
    hijos: np.ndarray
    edad_hijo: np.ndarray  # edad del hijo menor (99 = sin hijos)
    # resultados del último año
    ingreso: np.ndarray    # ingreso mensual promedio del año
    meses_ces: np.ndarray
    sueldo0: float = 0.0   # sueldo de partida, para referencias
    ev: dict = field(default_factory=dict)

    @classmethod
    def desde_perfil(cls, p: Perfil, n: int = 1) -> "Estado":
        tb = tablas()
        f = lambda v, dt=float: np.full(n, v, dtype=dt)  # noqa: E731
        gasto = max(tb.gasto_piso, (1 - float(tb.tasa_ahorro(np.array([p.sueldo]))[0])) * p.sueldo) + P.HIJO_COSTO * p.hijos
        trabaja = p.situacion == "trabajando"
        return cls(
            n=n, t=0, edad=p.edad, anio=ANIO_INICIAL,
            sit=f(EMP if trabaja else CES, np.int8), ocup=f(tb.idx[p.ocupacion], np.int16), exp_ocup=f(p.antiguedad),
            tam=f(TAMANOS.index(p.tipo_empleador), np.int8), nivel=f(p.nivel, np.int8), antig=f(p.antiguedad),
            sueldo=f(p.sueldo), cicatriz=f(0.0), mult_rubro=f(tb.mult_rubro.get(p.rubro, 1.0)),
            rubro=f(RUBROS.index(p.rubro if p.rubro in RUBROS else RUBRO_DEFECTO), np.int8), empresa=f(0, np.int16),
            anios_ces=f(0, np.int16), hueco_vol=f(False, bool), emp_anios=f(0, np.int16), emp_q=f(0.0),
            postgrado=f(p.edu == "postgrado", bool), estudia=f(0, np.int8), penal_hijo=f(0.0), horas=f(P.HORAS_BASE if trabaja else 0.0),
            animo=f(por_tramo(P.ANIMO_BASE, p.edad)), salud=f(por_tramo(P.SALUD_BASE, p.edad)), depresion=f(False, bool),
            social=f(100.0), ahorros=f(p.ahorros - p.deuda_estudios), gasto=f(gasto), pareja=f(p.pareja, bool),
            hijos=f(p.hijos, np.int8), edad_hijo=f(3.0 if p.hijos else 99.0),
            ingreso=f(p.sueldo if trabaja else 0.0), meses_ces=f(0.0), sueldo0=p.sueldo,
        )

    def _mapa(self, fn) -> "Estado":
        kw = {}
        for fl in fields(self):
            v = getattr(self, fl.name)
            kw[fl.name] = fn(v) if isinstance(v, np.ndarray) else v
        ev = {k: fn(v) for k, v in self.ev.items()}
        e = Estado(**kw)
        e.ev = Eventos(len(e.sit), ev)
        return e

    def copia(self) -> "Estado":
        return self._mapa(np.copy)

    def tomar(self, i: int) -> "Estado":
        """Un solo universo (el que te tocó)."""
        e = self._mapa(lambda a: a[i : i + 1].copy())
        e.n = e.ev.n = 1
        return e

    def replicar(self, n: int) -> "Estado":
        e = self._mapa(lambda a: np.repeat(a[:1], n))
        e.n = e.ev.n = n
        return e
