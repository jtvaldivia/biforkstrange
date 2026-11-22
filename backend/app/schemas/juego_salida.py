"""Respuestas de /api/juego, para que OpenAPI las documente.

Los campos de primer nivel van tipados. Lo que arma el motor más adentro (historia, opciones,
comparaciones) va como `dict` y queda descrito en el motor: tiparlo entero duplicaría el motor.
`extra="allow"` hace que un campo nuevo del motor llegue al cliente aunque todavía no esté aquí.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class Salida(BaseModel):
    model_config = ConfigDict(extra="allow")


# ── catálogo y supuestos ──────────────────────────────────────────────────────


class NivelOut(Salida):
    nivel: int
    nombre: str


class OcupacionJuegoOut(Salida):
    grupo: int
    nombre: str


class CarreraOut(Salida):
    carrera_id: int
    carrera: str
    tipo_institucion: str
    area: str


class SueldoRefOut(Salida):
    educacion: str
    banda: str
    p25: int
    p50: int
    p75: int


class CatalogoOut(Salida):
    rubros: list[str]
    tipos_empleador: list[str]
    niveles: list[NivelOut]
    educacion: list[str]
    ocupaciones: list[OcupacionJuegoOut]
    carreras: list[CarreraOut]
    sueldos_ref: list[SueldoRefOut]
    universidades: list[dict[str, Any]]


class SupuestosOut(Salida):
    total: int
    por_calidad: dict[str, int]
    por_pais: dict[str, int]
    parametros: list[dict[str, Any]]


class ValidacionOut(Salida):
    n: int
    semilla: int
    personas: int
    cumplen: int
    total: int
    metas: list[dict[str, Any]]


class PromptOut(Salida):
    prompt: str


# ── partida ───────────────────────────────────────────────────────────────────


class DudaOut(Salida):
    decision: str
    nombre: str
    pregunta: str
    categoria: str
    calidad: str


class PartidaOut(Salida):
    terminada: bool
    anio: int
    anios: int
    edad_final: int
    semilla: int
    duda: str | None
    elecciones: list[dict[str, Any]]
    estado: dict[str, Any]
    historia: list[dict[str, Any]]
    anio_en_curso: dict[str, Any] | None = None
    pendiente: dict[str, Any] | None = None
    cierre: dict[str, Any] | None = None


class MundoOut(Salida):
    mundo: int
    decision: str
    ia: dict[str, Any]
    ganador: str | None
    opciones: list[dict[str, Any]]


class NarradoOut(Salida):
    id: str
    texto: str
    via: Literal["claude", "plantilla"]


class NarrarOut(Salida):
    items: list[NarradoOut]


class PerfilLeidoOut(Salida):
    """Lo que Claude (o el documento de perfil) dejó listo para revisar: `perfil`, `supuestos`, `inferido`…"""

    via: str


class PesoCvOut(Salida):
    decision: str
    nombre: str
    pregunta: str
    gemelos: int
    semilla: int
    base: str
    datos: list[dict[str, Any]]
    sin_efecto: list[Any]
    otros: list[Any]


class EnJuegoOut(Salida):
    gemelos: int
    semilla: int
    mas_en_juego: Any = None
    dudas: list[dict[str, Any]]
