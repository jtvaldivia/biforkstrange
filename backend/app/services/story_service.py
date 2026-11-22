"""Tu historia: orquesta el motor (qué te pasa), el gemelo (quién eres) y el narrador (cómo se cuenta)."""

import random
from datetime import date

from app.repositories.stories import StoryRepository
from app.repositories.twin_profiles import TwinProfileRepository
from app.sim.personality import Trait
from app.sim.state import Twin
from app.story import qualitative as q
from app.story.engine import replay
from app.story.model import Chapter, Story, StoryStart
from app.story.teller import Teller, epilogue_model, hilo_dict, hilo_text, moments, to_dilemma
from app.twin.context import build_context
from app.twin.dims import DIMS

PERFIL_CHARS = 5000


class NotFoundError(Exception):
    pass


class StaleChapterError(Exception):
    """El cliente eligió sobre un capítulo que ya no es el actual (doble clic, otra pestaña)."""

    def __init__(self, story: Story):
        super().__init__("La historia ya avanzó")
        self.story = story


class StoryService:
    def __init__(self, repo: StoryRepository, teller: Teller, twins: TwinProfileRepository | None = None):
        self.repo = repo
        self.teller = teller
        self.twins = twins

    # ---- gemelo ----

    def _twin(self, profile_id: str | None) -> tuple[str, dict[str, Trait] | None]:
        p = self.twins.get(profile_id) if (profile_id and self.twins) else None
        if p is None:
            return "(Todavía no hay gemelo: usa solo lo que contó de su presente.)", None
        rasgos = {k: Trait(d.m, d.sd) for k, d in p.dims.items() if k in DIMS}
        return build_context(p, PERFIL_CHARS), rasgos

    # ---- historia ----

    def get(self, story_id: str) -> Story:
        s = self.repo.get(story_id)
        if s is None:
            raise NotFoundError(story_id)
        return s

    def start(self, situacion: str, edad: int, sueldo: float, desgaste: float, anios: int,
              profile_id: str | None) -> Story:
        perfil, _ = self._twin(profile_id)
        anio = date.today().year + 1
        story = Story(
            profile_id=profile_id,
            inicio=StoryStart(edad=edad, anio=anio, situacion=situacion.strip(), sueldo=sueldo, desgaste=desgaste),
            seed=random.randrange(1_000_000),
            anios=anios,
        )
        o = self.teller.opening(perfil, story.inicio.situacion, edad, anio, anios)
        story.titulo, story.prologo, story.dilema = o.titulo, o.prologo, to_dilemma(o.dilema)
        story.hilo = hilo_dict(o.hilo)
        return self.repo.save(story)

    def choose(self, story_id: str, capitulo: int, option_id: str | None, texto: str | None) -> Story:
        story = self.get(story_id)
        if capitulo != len(story.capitulos) or story.dilema is None or story.terminada:
            raise StaleChapterError(story)

        if option_id:
            opt = next((o for o in story.dilema.opciones if o.id == option_id), None)
            if opt is None:
                raise ValueError("Esa opción no está en el dilema actual")
            key, eleccion = opt.decision, opt.titulo
        elif texto and texto.strip():
            c = self.teller.classify(texto.strip(), story.dilema.situacion)
            key, eleccion = c.decision, c.titulo
        else:
            raise ValueError("Elige una opción o escribe lo que harías")

        perfil, rasgos = self._twin(story.profile_id)
        ini = story.inicio
        facts = replay(Twin(edad=ini.edad, sueldo=ini.sueldo, desgaste=ini.desgaste),
                       story.decisiones + [key], story.seed, rasgos)[-1]
        n = len(story.capitulos) + 1
        edad, anio = ini.edad + n, ini.anio + n - 1
        ultimo = n >= story.anios

        ofrecidas = [o.titulo for o in story.dilema.opciones]
        o = self.teller.chapter(perfil, self._so_far(story), edad, anio, eleccion, q.facts_for_prompt(facts), ultimo,
                                hilo_text(story.hilo_actual), story.opciones_previas + ofrecidas)
        story.capitulos.append(Chapter(
            n=n, edad=edad, anio=anio, eleccion=eleccion, decision=key,
            titulo=o.titulo, relato=o.relato.strip(), momentos=moments(o),
            ganaste=o.ganaste, dejaste=o.dejaste,
            estado={"trabajo": q.trabajo(facts), "plata": q.plata(facts), "energia": q.energia(facts), "vida": o.vida},
            tono=q.tone(facts), hechos=facts.as_dict(), hilo=hilo_dict(o.hilo), ofrecidas=ofrecidas,
        ))
        story.dilema = None if ultimo else to_dilemma(o.dilema)
        return self.repo.save(story)

    def close(self, story_id: str) -> Story:
        story = self.get(story_id)
        if not story.capitulos:
            raise ValueError("Vive al menos un año antes de cerrar la historia")
        perfil, _ = self._twin(story.profile_id)
        edad = story.inicio.edad + len(story.capitulos)
        story.epilogo = epilogue_model(self.teller.epilogue(perfil, self._so_far(story, full=True), edad))
        story.dilema = None
        story.anios = len(story.capitulos)  # cerrar antes de tiempo también termina la partida
        return self.repo.save(story)

    @staticmethod
    def _so_far(story: Story, full: bool = False) -> str:
        """Prólogo + capítulos resumidos; el último (o todos, si full) va completo para dar continuidad."""
        parts = [f"Prólogo ({story.inicio.edad} años): {story.prologo}"]
        for i, c in enumerate(story.capitulos):
            head = f"{c.anio}, {c.edad} años — eligió \"{c.eleccion}\" — «{c.titulo}». Estado: " + ", ".join(
                f"{k} {v}" for k, v in c.estado.items())
            if full or i == len(story.capitulos) - 1:
                parts.append(f"{head}\n{c.relato}\nGanó: {c.ganaste} Dejó: {c.dejaste}")
            else:
                parts.append(f"{head}. Ganó: {c.ganaste} Dejó: {c.dejaste}")
        return "\n\n".join(parts)


def public_story(s: Story) -> dict:
    doc = s.model_dump()
    for c in doc["capitulos"]:
        c.pop("hechos", None)  # los números del motor no salen al cliente
    doc["terminada"] = s.terminada
    return doc
