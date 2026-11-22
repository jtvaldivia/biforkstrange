"""El narrador: Claude con API key; uno de plantilla sin ella (para tests y modo sin IA)."""

from typing import Protocol

from pydantic import BaseModel

from app.core.llm import ClaudeJSON
from app.sim.decisions.base import _REGISTRY, get_decision
from app.story import prompts
from app.story.model import Dilemma, Epilogue, Moment, Option


class OptionOut(BaseModel):
    titulo: str
    detalle: str
    decision: str


class DilemmaOut(BaseModel):
    situacion: str
    pregunta: str
    opciones: list[OptionOut]


class HiloOut(BaseModel):
    """Dónde está parada la persona: lo que el año siguiente tiene que tomar en cuenta."""

    donde: str  # dónde vive / está
    trabajo: str  # qué hace hoy (o que no tiene pega)
    vinculos: str  # pareja, familia, amigos: cómo están
    en_curso: str  # lo que quedó abierto: una promesa, un plan, una oferta, un estudio a medias


class OpeningOut(BaseModel):
    titulo: str
    prologo: str
    hilo: HiloOut
    dilema: DilemmaOut


class MomentOut(BaseModel):
    de: str
    texto: str
    hora: str


class ChapterOut(BaseModel):
    titulo: str
    relato: str
    momentos: list[MomentOut]
    ganaste: str
    dejaste: str
    vida: str
    hilo: HiloOut
    dilema: DilemmaOut


class ClassifyOut(BaseModel):
    decision: str
    titulo: str


class EpilogueOut(BaseModel):
    titulo: str
    relato: str
    lo_que_ganaste: list[str]
    lo_que_no_vuelve: list[str]


def check_dilemma(d: DilemmaOut, previas: list[str] | None = None) -> None:
    if not 2 <= len(d.opciones) <= 4:
        raise ValueError("Se esperaban 3–4 opciones")
    bad = [o.decision for o in d.opciones if o.decision not in _REGISTRY]
    if bad:
        raise ValueError(f"Claves de decisión inválidas: {bad}")
    # ni el nombre del catálogo ni algo que lo contenga ("Pedir un año sabático" ≈ "Año sabático")
    generic = [r.label.lower() for r in _REGISTRY.values() if len(r.label.split()) >= 2]
    if any(g in o.titulo.strip().lower() for o in d.opciones for g in generic):
        raise ValueError("Las opciones deben tener títulos propios de la historia, no los nombres del catálogo")
    seen = {t.strip().lower() for t in previas or []}
    repeated = [o.titulo for o in d.opciones if o.titulo.strip().lower() in seen]
    if repeated:
        raise ValueError(f"Estas opciones ya se ofrecieron antes; propón otras que nazcan de lo que pasó: {repeated}")


def to_dilemma(d: DilemmaOut) -> Dilemma:
    return Dilemma(
        situacion=d.situacion,
        pregunta=d.pregunta,
        opciones=[Option(titulo=o.titulo, detalle=o.detalle, decision=o.decision) for o in d.opciones],
    )


class Teller(Protocol):
    def opening(self, perfil: str, situacion: str, edad: int, anio: int, anios: int) -> OpeningOut: ...
    def chapter(self, perfil: str, historia: str, edad: int, anio: int, eleccion: str, hechos: str, ultimo: bool,
                hilo: str, previas: list[str]) -> ChapterOut: ...
    def classify(self, texto: str, situacion: str) -> ClassifyOut: ...
    def epilogue(self, perfil: str, historia: str, edad: int) -> EpilogueOut: ...


class ClaudeTeller:
    def __init__(self, llm: ClaudeJSON):
        self.llm = llm

    def opening(self, perfil, situacion, edad, anio, anios):
        return self.llm.ask(prompts.opening(perfil, situacion, edad, anio, anios), OpeningOut,
                            check=lambda o: check_dilemma(o.dilema), fast=True)

    def chapter(self, perfil, historia, edad, anio, eleccion, hechos, ultimo, hilo, previas):
        def check(o: ChapterOut):
            if not o.relato.strip():
                raise ValueError("Capítulo vacío")
            if not ultimo:
                check_dilemma(o.dilema, previas)

        return self.llm.ask(prompts.chapter(perfil, historia, edad, anio, eleccion, hechos, ultimo, hilo, previas), ChapterOut,
                            check=check, max_tokens=10000, fast=True)

    def classify(self, texto, situacion):
        def check(o: ClassifyOut):
            if o.decision not in _REGISTRY:
                raise ValueError("Clave inválida")

        return self.llm.ask(prompts.classify(texto, situacion), ClassifyOut, check=check, max_tokens=4000)  # con razonamiento: equivocarse aquí tuerce la historia

    def epilogue(self, perfil, historia, edad):
        return self.llm.ask(prompts.epilogue(perfil, historia, edad), EpilogueOut, max_tokens=10000, fast=True)


# ---- Sin API key ----

_OPTS = [
    OptionOut(titulo="Quedarte donde estás", detalle="Lo conocido, sin sobresaltos.", decision="seguir"),
    OptionOut(titulo="Buscar una pega nueva", detalle="Subir de golpe, con el riesgo del cambio.", decision="cambiar_pega"),
    OptionOut(titulo="Meterle más horas", detalle="Hacerte notar, a costa de tu tiempo.", decision="trabajar_mas"),
    OptionOut(titulo="Tomarte un año para ti", detalle="Parar y recargar.", decision="sabatico"),
]


_HILO = HiloOut(donde="Santiago", trabajo="lo de siempre", vinculos="cerca", en_curso="nada todavía")


def _dilemma(anio: int) -> DilemmaOut:
    return DilemmaOut(situacion=f"[Modo sin IA] Empieza {anio} y toca decidir cómo seguir.", pregunta="¿Qué haces?",
                      opciones=_OPTS)


class OfflineTeller:
    def opening(self, perfil, situacion, edad, anio, anios):
        return OpeningOut(titulo="Tu historia", prologo=f"[Modo sin IA] Tienes {edad} años. {situacion}",
                          hilo=_HILO, dilema=_dilemma(anio))

    def chapter(self, perfil, historia, edad, anio, eleccion, hechos, ultimo, hilo, previas):
        return ChapterOut(
            titulo=f"El año de {eleccion.lower()}",
            relato=f"[Modo sin IA] En {anio} elegiste {eleccion.lower()}.\n\n{hechos}",
            momentos=[MomentOut(de="Mamá", texto="¿Cómo te fue este año?", hora="21:30")],
            ganaste="Una decisión tomada.", dejaste="Las otras opciones.", vida="igual que antes",
            hilo=HiloOut(donde="Santiago", trabajo=eleccion, vinculos="cerca", en_curso="lo que viene"),
            dilema=_dilemma(anio + 1),
        )

    def classify(self, texto, situacion):
        return ClassifyOut(decision="seguir", titulo=texto[:60])

    def epilogue(self, perfil, historia, edad):
        return EpilogueOut(titulo="Hasta aquí", relato=f"[Modo sin IA] Llegaste a los {edad}.\n\n{historia}",
                           lo_que_ganaste=["Experiencia"], lo_que_no_vuelve=["El tiempo"])


def hilo_dict(h: HiloOut) -> dict[str, str]:
    return h.model_dump()


def hilo_text(h: dict[str, str]) -> str:
    labels = {"donde": "Dónde está", "trabajo": "Trabajo", "vinculos": "Su gente", "en_curso": "Lo que quedó abierto"}
    return "\n".join(f"- {labels.get(k, k)}: {v}" for k, v in h.items() if v) or "(sin datos)"


def moments(o: ChapterOut) -> list[Moment]:
    return [Moment(de=m.de, texto=m.texto, hora=m.hora) for m in o.momentos[:3]]


def epilogue_model(o: EpilogueOut) -> Epilogue:
    return Epilogue(**o.model_dump())


def label(key: str) -> str:
    return get_decision(key).label
