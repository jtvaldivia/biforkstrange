from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.sim.motor.empresas import universidades
from app.sim.motor.paquete import paquete
from app.sim.motor.perfil import Perfil


@lru_cache(maxsize=1)
def _ids_universidades() -> frozenset[str]:
    return frozenset(u["universidad_id"] for u in universidades(paquete()))


class PerfilIn(BaseModel):
    """Los 9 campos que declara la persona (más opcionales)."""

    edad: int = Field(30, ge=18, le=50)
    sexo: Literal["h", "m"] = "m"
    edu: Literal["media", "tecnica", "universitaria", "postgrado"] = "universitaria"
    carrera_id: int = Field(-1, ge=-1, le=251)
    rubro: str = "Servicios profesionales"
    tipo_empleador: Literal["grande", "pyme", "startup", "publico", "extranjero"] = "pyme"
    nivel: int = Field(1, ge=0, le=4)
    sueldo: float = Field(1_400_000, gt=0, le=30_000_000)
    riesgo: int = Field(5, ge=0, le=10)
    ocupacion: int | None = Field(None, ge=0, le=9)
    antiguedad: int = Field(2, ge=0, le=40)
    region: Literal["rm", "otra"] = "rm"
    ahorro: float | None = None
    ingles: int = Field(0, ge=0, le=1)
    skill: int | None = Field(None, ge=0, le=100)
    red: int | None = Field(None, ge=0, le=100)
    estado: Literal["empleado", "independiente", "fundador", "buscando", "estudiando"] = "empleado"
    meses_cesante: int = Field(0, ge=0, le=120)
    parcial: int = Field(0, ge=0, le=1)
    remoto: int = Field(0, ge=0, le=1)
    usa_ia: int = Field(0, ge=0, le=1)
    empresa_anos: int = Field(0, ge=0, le=30)
    empresa_fondos: int = Field(0, ge=0, le=1)
    anos_por_empleo: float | None = Field(None, gt=0, le=40)
    rubro_sonado: str | None = None
    semestres_restantes: int | None = Field(None, ge=0, le=16)
    anos_en_carrera: int | None = Field(None, ge=0, le=10)
    volvio_a_su_nivel: int = Field(0, ge=0, le=1)
    freelance_entre_pegas: int = Field(0, ge=0, le=1)
    emprendio_antes: int = Field(0, ge=0, le=1)
    anos_independiente: int | None = Field(None, ge=0, le=40)
    practica: Literal["", "grande", "pyme", "startup", "publico"] = ""
    toda_su_carrera_en: Literal["", "publico", "startup"] = ""
    ascensos_por_ano: float | None = Field(None, ge=0, le=2)
    empresas_cerradas: int = Field(0, ge=0, le=10)
    universidad_id: str = Field("", max_length=40)

    @field_validator("universidad_id")
    @classmethod
    def _universidad_del_catalogo(cls, v: str) -> str:
        if v and v not in _ids_universidades():
            raise ValueError(f"universidad desconocida: {v!r}")
        return v

    def a_perfil(self) -> Perfil:
        return Perfil(**self.model_dump())


class EleccionIn(BaseModel):
    decision: str | None = None
    opcion: str
    parametros: dict[str, str | int] = {}


class PartidaIn(BaseModel):
    perfil: PerfilIn = PerfilIn()
    semilla: int = 0
    duda: str | None = None
    elecciones: list[EleccionIn] = Field(default_factory=list, max_length=200)
    gemelos: int = Field(100, ge=0, le=2000)
    # lo que se elige dentro de cada opción de la decisión pendiente, para comparar: {opción: {variable: valor}}
    parametros: dict[str, dict[str, str | int]] = {}


class NarrarIn(PartidaIn):
    """Qué textos narrar de la partida: la carta pendiente, la historia o un mundo."""

    que: Literal["pendiente", "historia", "mundo"] = "pendiente"
    mundo: int | None = Field(None, ge=0, le=1999)


class MundoIn(PartidaIn):
    """La partida y cuál de sus mundos se quiere ver (0 a `gemelos` - 1)."""

    mundo: int = Field(ge=0, le=1999)


class DudasIn(BaseModel):
    perfil: PerfilIn = PerfilIn()


class TextoPerfilIn(BaseModel):
    """Lo que la persona escribe o sube sobre sí misma (markdown, currículum pegado, un párrafo)."""

    texto: str = Field("", max_length=60_000)
    # un PDF (el CV o el "Guardar como PDF" de LinkedIn) en base64; ~10 MB como máximo
    pdf: str | None = Field(None, max_length=14_000_000)


class PesoCvIn(BaseModel):
    """El perfil y la duda: se repite la comparación sin cada dato del CV, con la misma semilla."""

    perfil: PerfilIn = PerfilIn()
    duda: str
    semilla: int = 0
    gemelos: int = Field(100, ge=20, le=300)


class EnJuegoIn(BaseModel):
    """El perfil y las dudas que sugiere su CV: cuál tiene más en juego para esta persona."""

    perfil: PerfilIn = PerfilIn()
    dudas: list[str] = Field(min_length=1, max_length=5)
    semilla: int = 0
    gemelos: int = Field(100, ge=20, le=300)
