"""Prompts del narrador. Funciones puras: reciben datos, devuelven texto."""

from app.sim.decisions import all_decisions
from app.twin.context import REGLAS_GEMELO

ESTILO = """Estilo:
- Segunda persona, español de Chile, tuteando. Cálido, concreto, sin cursilería ni moraleja.
- Breve: ve al grano, cada frase tiene que aportar. Mejor una escena precisa que tres generales.
- Escenas y detalles concretos (un lugar, una hora, una conversación), no resúmenes abstractos.
- Nunca cifras: ni montos, ni porcentajes, ni puntajes. Lo cualitativo se cuenta, no se mide.
- Género: dedúcelo de cómo la persona habla de sí misma (por ejemplo "soy ingeniero" o "estoy cansada"). Si no queda claro, escribe en neutro, sin marcar género. Nunca lo asumas por estereotipo. Lo mismo con su pareja: di "tu pareja" salvo que la persona haya dicho cómo es.
- La gente que aparece es genérica y verosímil (tu mamá, una amiga del colegio, tu jefa). No inventes datos sensibles ni de salud.
- Respeta los HECHOS del año: si quedaste sin pega o terminaste quemado, la historia lo cuenta. No los contradigas ni los suavices.
- """ + REGLAS_GEMELO


def catalog() -> str:
    return "\n".join(f"- {d.key}: {d.label}. {getattr(d, 'why', '')}" for d in all_decisions())


def opening(perfil: str, situacion: str, edad: int, anio: int, anios: int) -> str:
    return f"""Eres el narrador de una historia de vida interactiva. El protagonista es una persona real que quiere ver cómo podrían ser sus próximos {anios} años, decisión por decisión.

QUIÉN ES (su gemelo digital)
{perfil}

DÓNDE ESTÁ HOY, EN SUS PALABRAS ({edad} años, {anio - 1})
{situacion}

Escribe:
1. "titulo": un título para su historia (3–6 palabras).
2. "prologo": 1 párrafo (50–80 palabras) que la sitúe hoy, a partir de lo que contó. Que se reconozca.
3. "hilo": dónde está parada hoy, en frases cortas: "donde" (ciudad o lugar), "trabajo", "vinculos" (pareja, familia, amigos) y "en_curso" (lo que tiene abierto: un plan, una idea, una oferta).
4. "dilema": la primera decisión de {anio}, que nazca de lo que contó (su pega, su ciudad, su gente, lo que tiene pendiente). "situacion" (1–2 frases cortas: qué está pasando que obliga a decidir), "pregunta" corta, y 3 o 4 "opciones" concretas y distintas para ESTA persona, con títulos propios de su historia: con lugares, personas o cosas concretas de lo que contó, nunca genéricos como "Pedir un año sabático" o "Buscar otra pega" (título de 3–8 palabras + "detalle" de máximo 12 palabras). Cada opción debe mapear a una de estas claves en "decision", sin repetir clave si se puede:
{catalog()}

{ESTILO}"""


REGLAS_DILEMA = """Reglas del dilema (lo más importante: que cada año dependa del anterior):
- Nace de lo que ACABA de pasar y de "Tu situación ahora". Si vive afuera, las opciones son de esa vida (quedarse, volver, echar raíces); si no tiene pega, no le ofrezcas "quedarte en tu pega"; si empezó algo (un estudio, una pega nueva, un plan), las opciones lo continúan, lo profundizan o lo abandonan.
- Al menos una opción sigue el camino que eligió y al menos una lo cambia de rumbo.
- Retoma algo de "Lo que quedó abierto" o de una persona que apareció.
- Coherente con el "hilo" que acabas de escribir: no ofrezcas mudarse a donde ya vive ni volver a una pega que ya tiene.
- No repitas ni parafrasees ninguna de las opciones que ya se ofrecieron (lista abajo). El paisaje de opciones tiene que ir cambiando año a año.
- "situacion" en 1–2 frases cortas que nombren lo que pasó; cada "detalle" de máximo 12 palabras."""


def chapter(perfil: str, historia: str, edad: int, anio: int, eleccion: str, hechos: str, ultimo: bool,
            hilo: str, previas: list[str]) -> str:
    ya = "\n".join(f"- {t}" for t in previas) or "(ninguna)"
    siguiente = (
        "Este es el último capítulo: en \"dilema\" deja una situación abierta breve igual, pero no importa mucho."
        if ultimo
        else f"""En "dilema", plantea la decisión de {anio + 1}. 3 o 4 opciones concretas y distintas, con títulos propios de esta historia (ej. "Aceptar el traslado a Concepción", nunca el nombre genérico de la clave como "Seguir igual"), cada una mapeada a una clave:
{catalog()}

{REGLAS_DILEMA}

OPCIONES QUE YA SE OFRECIERON (no las repitas)
{ya}"""
    )
    return f"""Eres el narrador de una historia de vida interactiva, en segunda persona.

QUIÉN ES (su gemelo digital)
{perfil}

LA HISTORIA HASTA AHORA
{historia}

SU SITUACIÓN AL EMPEZAR ESTE AÑO
{hilo}

ESTE AÑO: {anio}, cumple {edad}. Eligió: "{eleccion}".

HECHOS DEL AÑO (vienen de la simulación; respétalos)
{hechos}

LA ELECCIÓN SE CUMPLE: si eligió mudarse, cambiarse, estudiar o parar, eso pasó (los HECHOS dicen cómo le fue). El relato y el "hilo" tienen que reflejarlo: si se mudó a otra ciudad, "donde" es la nueva ciudad; si se cambió de pega, "trabajo" es la pega nueva.

Escribe el capítulo:
- "titulo": 2–6 palabras, evocador.
- "relato": 2 párrafos cortos (70–110 palabras en total), separados por una línea en blanco. Qué pasó, cómo se sintió, qué cambió. Que se note la continuidad con el año anterior. Si "Por cómo eres" o "Lo que arrastras" traen algo, muéstralo en la historia, sin nombrar rasgos ni puntajes.
- "momentos": 1–2 mensajes de personas de su vida (quién + texto de máximo 12 palabras + hora tipo "21:40"). Que digan algo de lo que ganó o perdió este año.
- "ganaste": una frase, lo que este año le dio (sin empezar con "Ganaste").
- "dejaste": una frase, lo que quedó atrás o se perdió, puede ser pequeño (sin empezar con "Dejaste").
- "vida": 1–3 palabras sobre su vida personal este año (ej. "más presente", "a la distancia").
- "hilo": su situación AL CERRAR este año: "donde", "trabajo", "vinculos" y "en_curso" (lo que queda abierto para el año que viene). Frases cortas, coherentes con lo que pasó.
{siguiente}

{ESTILO}"""


def classify(texto: str, situacion: str) -> str:
    return f"""Una persona, ante esta situación:
{situacion}

respondió con sus palabras lo que haría: "{texto}"

Elige la clave cuyo EFECTO se parece más a esa elección (más o menos horas, más o menos sueldo, cambiar o quedarse, parar, estudiar). Fíjate en la dirección: reducir jornada o recuperar tiempo nunca es "trabajar_mas".
Elige la clave que mejor representa esa elección y resume la elección en un título de 3–8 palabras, en segunda persona implícita (ej. "Pedir el traslado a Valparaíso").
{catalog()}"""


def epilogue(perfil: str, historia: str, edad: int) -> str:
    return f"""Eres el narrador de una historia de vida interactiva. Terminó: la persona llegó a los {edad} años.

QUIÉN ES
{perfil}

SU HISTORIA COMPLETA
{historia}

Escribe el cierre:
- "titulo": 2–6 palabras.
- "relato": 2 párrafos (100–150 palabras): quién es ahora, qué decisiones la definieron y por qué, mirando hacia atrás con honestidad. Sin moraleja ni juicio.
- "lo_que_ganaste": 3–4 cosas concretas que estos años le dieron, de máximo 10 palabras cada una.
- "lo_que_no_vuelve": 2–3 cosas concretas que se quedaron en el camino, de máximo 10 palabras cada una (momentos, personas, versiones de sí misma).

{ESTILO}"""
