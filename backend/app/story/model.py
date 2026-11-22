"""Tu historia: capítulos año a año. Lo cualitativo se muestra; los números del motor quedan escondidos."""

import time
import uuid

from pydantic import BaseModel, Field


def now() -> float:
    return time.time()


class Option(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    titulo: str  # "Aceptar la oferta de la fintech"
    detalle: str  # una frase de qué implica
    decision: str  # clave del catálogo que mueve el motor (seguir, cambiar_pega, ...)


class Dilemma(BaseModel):
    situacion: str  # dónde estás parado al empezar el año
    pregunta: str  # "¿Qué haces?"
    opciones: list[Option]


class Moment(BaseModel):
    de: str  # quién: "Mamá", "Tu jefa", "Los cabros"
    texto: str  # el mensaje o la escena breve
    hora: str = ""  # opcional, para mostrarlo como notificación


class Chapter(BaseModel):
    n: int
    edad: int
    anio: int
    eleccion: str  # lo que elegiste, en tus palabras o el título de la opción
    decision: str  # clave del catálogo
    titulo: str
    relato: str  # 2–4 párrafos separados por línea en blanco
    momentos: list[Moment] = []
    ganaste: str = ""
    dejaste: str = ""
    estado: dict[str, str] = {}  # plata, energia, trabajo, vida (palabras, no números)
    tono: str = "dia"  # dia | noche (años duros)
    hilo: dict[str, str] = {}  # tu situación al cerrar el año: donde, trabajo, vinculos, en_curso
    ofrecidas: list[str] = []  # títulos de las opciones del dilema que respondiste (para no repetirlas)
    hechos: dict = {}  # números del motor: solo servidor, nunca al cliente


class Epilogue(BaseModel):
    titulo: str
    relato: str
    lo_que_ganaste: list[str]
    lo_que_no_vuelve: list[str]


class StoryStart(BaseModel):
    edad: int
    anio: int
    situacion: str  # cómo describe la persona su presente
    sueldo: float
    desgaste: float


class Story(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    profile_id: str | None = None
    inicio: StoryStart
    seed: int
    anios: int = 8  # capítulos de la partida
    titulo: str = ""
    prologo: str = ""
    hilo: dict[str, str] = {}  # situación al empezar (la escribe el narrador en la apertura)
    capitulos: list[Chapter] = []
    dilema: Dilemma | None = None
    epilogo: Epilogue | None = None
    created_at: float = Field(default_factory=now)

    @property
    def decisiones(self) -> list[str]:
        return [c.decision for c in self.capitulos]

    @property
    def hilo_actual(self) -> dict[str, str]:
        return self.capitulos[-1].hilo if self.capitulos else self.hilo

    @property
    def opciones_previas(self) -> list[str]:
        return [t for c in self.capitulos for t in c.ofrecidas]

    @property
    def terminada(self) -> bool:
        return len(self.capitulos) >= self.anios
