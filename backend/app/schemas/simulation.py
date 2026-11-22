from pydantic import BaseModel, Field


class TwinIn(BaseModel):
    edad: int = Field(25, ge=18, le=50)
    sueldo: float = Field(900_000, gt=0)
    desgaste: float = Field(0.2, ge=0, le=1)


class SimulationIn(BaseModel):
    twin: TwinIn = TwinIn()
    decisiones: list[str] = Field(min_length=1, max_length=32)
    n_runs: int | None = Field(None, ge=100, le=20_000)
    seed: int | None = None  # misma semilla = misma "suerte": la diferencia entre escenarios es solo la decisión
    profile_id: str | None = None  # si viene, tus rasgos medidos ajustan cada decisión


class CompareIn(BaseModel):
    twin: TwinIn = TwinIn()
    a: list[str] = Field(min_length=1, max_length=32)
    b: list[str] = Field(min_length=1, max_length=32)
    n_runs: int | None = Field(None, ge=100, le=20_000)
    seed: int = 7
    profile_id: str | None = None


class Factor(BaseModel):
    fuente: str  # decision | rasgo | estado
    texto: str
    efecto: str


class Explicacion(BaseModel):
    titular: str
    cambio_sueldo: float
    cambio_desgaste: float
    parametros: dict[str, float] | None = None
    factores: list[Factor]


class Step(BaseModel):
    decision: str
    edad: int
    sueldo_p10: float
    sueldo_p50: float
    sueldo_p90: float
    desgaste_p50: float
    prob_desempleo: float
    explicacion: Explicacion | None = None


class Resumen(BaseModel):
    titular: str
    puntos: list[str]


class RasgoUsado(BaseModel):
    key: str
    nombre: str
    m: float
    sd: float
    peso: float  # 0–1: cuánto confía el gemelo en este rasgo


class SimulationOut(BaseModel):
    id: str | None = None
    edad_final: int
    trayectoria: list[Step]
    resumen: Resumen | None = None
    rasgos_usados: list[RasgoUsado] = []


class Comparacion(BaseModel):
    titular: str
    puntos: list[str]
    diferencia_sueldo: float
    diferencia_desgaste: float


class CompareOut(BaseModel):
    a: SimulationOut
    b: SimulationOut
    comparacion: Comparacion


class DecisionOut(BaseModel):
    key: str
    label: str
    description: str = ""
    why: str = ""
    growth: float | None = None
    risk: float | None = None
    wear: float | None = None
