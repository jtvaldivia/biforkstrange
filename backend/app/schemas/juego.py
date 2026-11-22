import ast
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.sim.motor.empresas import universidades
from app.sim.motor.paquete import paquete
from app.sim.motor.perfil import Perfil


@lru_cache(maxsize=1)
def _ids_universidades() -> frozenset[str]:
    return frozenset(u["universidad_id"] for u in universidades(paquete()))


@lru_cache(maxsize=1)
def _rubros() -> tuple[str, ...]:
    """Los rubros del paquete ("" es "sin rubro": quien estudia o busca su primera pega)."""
    return tuple(paquete().variables["rubro"]["dominio"])


@lru_cache(maxsize=1)
def _dominios_eleccion() -> dict[str, frozenset | None]:
    """Lo que se puede elegir dentro de una opción (variable: valores válidos), como lo ofrece
    politicas.elecciones_internas. None: el paquete no fija los valores."""
    pq = paquete()
    regiones = {f["region"] for f in pq.filas("esi_ingreso_region")} - {"Metropolitana", "Nacional"}
    dominios: dict[str, frozenset | None] = {
        "rubro_destino": frozenset(r for r in _rubros() if r),
        "ocupacion_destino": frozenset(range(1, 10)),
        "region_destino": frozenset(regiones),
        "universidad_destino": _ids_universidades(),
        "institucion_destino": _ids_universidades(),
    }
    for nombre, v in pq.variables.items():
        if v.get("tipo") == "eleccion" and nombre not in dominios:
            dominio = v.get("dominio")
            if isinstance(dominio, str):  # el paquete trae algunos dominios como texto: "['madre', 'padre']"
                try:
                    dominio = ast.literal_eval(dominio)
                except (ValueError, SyntaxError):
                    dominio = None
            dominios[nombre] = frozenset(dominio) if dominio else None
    return dominios


@lru_cache(maxsize=1)
def _opciones() -> frozenset[str]:
    return frozenset(o["id"] for d in paquete().decisiones.values() for o in d["opciones"])


def _validar_elecciones(parametros: dict[str, str | int]) -> dict[str, str | int]:
    """Cada variable es algo que se elige dentro de una opción, y su valor es una de sus alternativas."""
    dominios = _dominios_eleccion()
    for variable, valor in parametros.items():
        if variable not in dominios:
            raise ValueError(f"{variable!r} no es algo que se elija dentro de una opción")
        dominio = dominios[variable]
        if dominio is not None and (isinstance(valor, bool) or valor not in dominio):
            raise ValueError(f"{valor!r} no es una alternativa de {variable}")
    return parametros


class PerfilIn(BaseModel):
    """Los 9 campos que declara la persona (más opcionales)."""

    # Infinity o NaN en un número (el JSON de Python los acepta) rompían el motor con un 500
    model_config = ConfigDict(allow_inf_nan=False)

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
    ahorro: float | None = Field(None, ge=-1_000_000_000, le=100_000_000_000)  # negativo: deudas
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
    primer_empleo: int = Field(0, ge=0, le=1)  # 1 si busca su primer empleo (sin experiencia tras titularse)
    toda_su_carrera_en: Literal["", "publico", "startup"] = ""
    ascensos_por_ano: float | None = Field(None, ge=0, le=2)
    empresas_cerradas: int = Field(0, ge=0, le=10)
    universidad_id: str = Field("", max_length=40)
    empresa_nombre: str = Field("", max_length=120)
    cargo_nombre: str = Field("", max_length=120)

    @field_validator("universidad_id")
    @classmethod
    def _universidad_del_catalogo(cls, v: str) -> str:
        if v and v not in _ids_universidades():
            raise ValueError(f"universidad desconocida: {v!r}")
        return v

    @field_validator("rubro")
    @classmethod
    def _rubro_del_paquete(cls, v: str) -> str:
        if v not in _rubros():
            raise ValueError(f"rubro desconocido: {v!r}")
        return v

    @field_validator("rubro_sonado")
    @classmethod
    def _rubro_sonado_del_paquete(cls, v: str | None) -> str | None:
        if v and v not in _rubros():
            raise ValueError(f"rubro desconocido: {v!r}")
        return v

    # cómo te describes con tus palabras: el narrador lo usa como trasfondo. Fuera de model_dump: no es campo del motor
    relato: str = Field("", max_length=20000, exclude=True)

    def a_perfil(self) -> Perfil:
        return Perfil(**self.model_dump())


class EleccionIn(BaseModel):
    decision: str | None = None
    opcion: str
    parametros: dict[str, str | int] = {}

    @field_validator("parametros")
    @classmethod
    def _parametros_validos(cls, v: dict[str, str | int]) -> dict[str, str | int]:
        return _validar_elecciones(v)


class PartidaIn(BaseModel):
    perfil: PerfilIn = PerfilIn()
    semilla: int = 0
    duda: str | None = None
    elecciones: list[EleccionIn] = Field(default_factory=list, max_length=200)
    # hasta qué edad se juega; sin dato, 10 años desde la edad del perfil
    edad_final: int | None = Field(None, ge=19, le=60)
    gemelos: int = Field(100, ge=0, le=2000)
    # lo que se elige dentro de cada opción de la decisión pendiente, para comparar: {opción: {variable: valor}}
    parametros: dict[str, dict[str, str | int]] = {}

    @field_validator("parametros")
    @classmethod
    def _parametros_validos(cls, v: dict[str, dict[str, str | int]]) -> dict[str, dict[str, str | int]]:
        for opcion, elecciones in v.items():
            if opcion not in _opciones():
                raise ValueError(f"{opcion!r} no es una opción de ninguna decisión")
            _validar_elecciones(elecciones)
        return v


class NarrarIn(PartidaIn):
    """Qué textos narrar de la partida: la carta pendiente, la historia o un mundo.

    El front narra con `gemelos: 0` (solo rejuega tu vida), así que aquí `mundo` no se compara con `gemelos`.
    """

    que: Literal["pendiente", "historia", "mundo"] = "pendiente"
    mundo: int | None = Field(None, ge=0, le=1999)


class MundoIn(PartidaIn):
    """La partida y cuál de sus mundos se quiere ver (0 a `gemelos` - 1)."""

    mundo: int = Field(ge=0, le=1999)

    @model_validator(mode="after")
    def _mundo_entre_los_gemelos(self):
        if self.mundo >= self.gemelos:
            raise ValueError(f"el mundo {self.mundo} no existe: con {self.gemelos} gemelos, "
                             f"los mundos van del 0 al {self.gemelos - 1}")
        return self


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
