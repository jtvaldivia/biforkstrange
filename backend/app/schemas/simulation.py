from pydantic import BaseModel, ConfigDict, Field


class TwinIn(BaseModel):
    edad: int = Field(25, ge=18, le=50)
    sueldo: float = Field(900_000, gt=0)
    desgaste: float = Field(0.2, ge=0, le=1)


class SimulationIn(BaseModel):
    twin: TwinIn = TwinIn()
    perfil: dict | None = Field(None, description="Perfil completo en formato bifurca.perfil; si viene, reemplaza a `twin`")
    decisiones: list[str] = Field(min_length=1, max_length=32)
    n_runs: int | None = Field(None, ge=100, le=20_000)
    seed: int | None = None


class Step(BaseModel):
    model_config = ConfigDict(extra="allow")   # el motor agrega métricas (ánimo, ahorros, etc.)

    decision: str
    edad: int
    sueldo_p10: float
    sueldo_p50: float
    sueldo_p90: float
    desgaste_p50: float
    prob_desempleo: float


class SimulationOut(BaseModel):
    id: str | None = None
    edad_final: int
    trayectoria: list[Step]


class DecisionOut(BaseModel):
    key: str
    label: str
    description: str = ""


class TurnoIn(BaseModel):
    """Partida sin estado en el servidor: se reconstruye desde el perfil, la semilla y las decisiones."""

    perfil: dict
    decisiones: list[str] = Field(default_factory=list, max_length=40)
    seed: int = 7
    escenario_ia: str = Field("base", pattern="^(lenta|base|rapida)$")
    horizonte: int = Field(5, ge=1, le=15)
    n_runs: int = Field(1000, ge=100, le=5000)
