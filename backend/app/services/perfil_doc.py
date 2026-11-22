"""Tu perfil armado por tu propio Claude.

El flujo:
1. La app te da un prompt (`prompt()`).
2. Lo pegas en tu Claude (claude.ai, la app o Claude Code). Tu Claude ya te conoce por sus memorias
   y conversaciones, así que arma tu documento sin que tengas que escribirlo; si le falta algo, te pregunta.
3. Pegas o subes ese documento en la app, que lo lee sin llamar a ningún modelo (`leer_documento()`).

El documento trae un bloque con formato fijo (```gemelo-laboral ... ```) para que leerlo sea exacto,
y una sección "Cómo lo deduje" para que la persona sepa qué revisar.
"""

import re
import unicodedata
from functools import lru_cache

from app.sim.motor.motor import DECISIONES_PERSONALES
from app.sim.motor.paquete import Paquete, paquete
from app.sim.motor.perfil import NIVELES

BLOQUE = "gemelo-laboral"
_RE_BLOQUE = re.compile(r"```\s*" + BLOQUE + r"\s*\n(.*?)```", re.S | re.I)
_RE_DEDUJE = re.compile(r"^#+\s*c[oó]mo lo deduje\s*$(.*?)(?=^#+\s|\Z)", re.S | re.I | re.M)
_VACIO = {"", "?", "-", "no se", "no sé", "desconocido", "sin dato", "null", "ninguno", "ninguna"}

ESTUDIOS = {"media": "media", "tecnica": "tecnica", "técnica": "tecnica", "universitaria": "universitaria",
            "postgrado": "postgrado", "posgrado": "postgrado", "magister": "postgrado", "magíster": "postgrado",
            "doctorado": "postgrado"}
TIPOS = {"grande": "grande", "pyme": "pyme", "startup": "startup", "publico": "publico", "público": "publico",
         "estado": "publico", "extranjero": "extranjero", "afuera": "extranjero"}
SEXOS = {"h": "h", "hombre": "h", "m": "m", "mujer": "m"}
REGIONES = {"rm": "rm", "metropolitana": "rm", "santiago": "rm", "otra": "otra", "region": "otra", "regiones": "otra"}


def _normal(texto: str) -> str:
    sin = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", sin.lower()).strip()


def _dudas_laborales(pq: Paquete) -> list[dict]:
    return [d for id_, d in pq.decisiones.items()
            if d["aparicion"]["tipo"] == "carta" and id_ not in DECISIONES_PERSONALES]


SITUACIONES = {"empleado": "empleado", "empleada": "empleado", "independiente": "independiente", "freelance": "independiente",
               "fundador": "fundador", "fundadora": "fundador", "emprendedor": "fundador", "buscando": "buscando",
               "cesante": "buscando", "estudiando": "estudiando", "estudiante": "estudiando"}
USO_IA = {"no": False, "no uso": False, "nunca": False, "a veces": True, "aveces": True, "seguido": True,
          "todos los dias": True, "diario": True, "si": True}


@lru_cache(maxsize=1)
def prompt(pq: Paquete | None = None) -> str:
    """El prompt que la persona le pega a su Claude o ChatGPT. Corto: pide lo que un CV no dice."""
    pq = pq or paquete()
    rubros = [r for r in pq.variables["rubro"]["dominio"] if r]
    dudas = _dudas_laborales(pq)
    lineas = [
        "Voy a jugar Agarrar la pala, un simulador de carrera en Chile: 100 \"gemelos\" míos viven 10 años "
        "con cada decisión. Con lo que sabes de mí por nuestras conversaciones, llena este bloque.",
        "",
        "Reglas:",
        "- Solo lo que sabes o lo que yo te diga. Si no sabes algo, pon ?. No inventes.",
        "- Nada de salud, pareja, familia ni nada que yo no quiera compartir.",
        "- Si te falta mi sueldo o mi duda, pregúntamelo en un mensaje corto antes de escribir.",
        "- Responde solo con el bloque, tal cual:",
        "",
        "```" + BLOQUE,
        "sueldo_liquido: <pesos líquidos al mes, solo números>",
        "duda: <el código de la lista de dudas que más me da vueltas hoy>",
        "situacion: <empleado, independiente, fundador, buscando o estudiando>",
        "riesgo: <0 a 10: cuánto riesgo tomo en mi carrera>",
        "ingles: <si o no: ¿podría trabajar en inglés?>",
        "ia: <no uso, a veces o todos los dias: cuánto uso IA en mi trabajo>",
        "proyecto: <mi proyecto paralelo o idea de negocio, en una línea, o ?>",
        "afuera: <si o no: ¿me gustaría trabajar o vivir fuera de Chile?>",
        "rubro_sonado: <un rubro de la lista al que me cambiaría, o ?>",
        "intereses: <3 a 5 temas que me apasionan, separados por coma>",
        "retrato: <una línea sobre mí, en segunda persona, sin datos sensibles>",
        "```",
        "",
        "Si los sabes, puedes agregar en el mismo bloque: edad, estudios (media, tecnica, universitaria o "
        "postgrado), cargo (Junior, Semi senior, Senior, Jefatura o Gerencia), rubro y tipo_empresa (grande, "
        "pyme, startup, publico o extranjero).",
        "",
        "Rubros: " + "; ".join(rubros) + ".",
        "",
        "Dudas: " + "; ".join(f"{d['id']} ({d['nombre']})" for d in dudas) + ".",
    ]
    return "\n".join(lineas)


def _campos(bloque: str) -> dict[str, str]:
    salida = {}
    for linea in bloque.splitlines():
        linea = linea.split("#", 1)[0].strip()
        if ":" not in linea:
            continue
        clave, valor = (x.strip() for x in linea.split(":", 1))
        valor = valor.strip("<>\"' ")
        if _normal(valor) not in _VACIO:
            salida[_normal(clave).replace(" ", "_")] = valor
    return salida


def _entero(valor: str) -> int | None:
    numeros = re.sub(r"[^\d]", "", valor.split(",")[0])
    return int(numeros) if numeros else None


def _carrera(nombre: str, institucion: str | None, pq: Paquete) -> tuple[int | None, str | None]:
    """Busca el título en el catálogo de mifuturo. Devuelve (carrera_id, nota)."""
    buscado = _normal(nombre)
    filas = pq.filas("mifuturo_carreras")
    if institucion:
        mismas = [f for f in filas if f["tipo_institucion"].upper() == institucion.upper()]
        filas = mismas or filas
    exactas = [f for f in filas if _normal(f["carrera"]) == buscado]
    if exactas:
        return int(exactas[0]["carrera_id"]), None
    palabras = set(buscado.split()) - {"de", "en", "y", "la", "el"}
    mejor, puntaje = None, 0.0
    for f in filas:
        otras = set(_normal(f["carrera"]).split()) - {"de", "en", "y", "la", "el"}
        if not palabras or not otras:
            continue
        p = len(palabras & otras) / len(palabras | otras)
        if p > puntaje:
            mejor, puntaje = f, p
    if mejor and puntaje >= 0.5:
        return int(mejor["carrera_id"]), f"carrera: «{nombre}» se tomó como «{mejor['carrera']}» ({mejor['tipo_institucion']})."
    return None, f"carrera: «{nombre}» no está en el catálogo de carreras; se simula sin carrera."


def leer_documento(texto: str, pq: Paquete | None = None) -> dict | None:
    """Lee el documento que armó el Claude de la persona. None si el texto no trae el bloque.

    Devuelve lo mismo que `perfil_ia.completar` más `duda` (la duda inicial, si es válida) y `avisos`
    (valores del documento que no se pudieron usar).
    """
    from app.services.perfil_ia import PerfilLeido, completar

    pq = pq or paquete()
    encontrado = _RE_BLOQUE.search(texto)
    if not encontrado:
        return None
    c = _campos(encontrado.group(1))
    avisos: list[str] = []
    leido: dict = {}

    def opcion(campo: str, destino: str, tabla: dict[str, str], nombre: str) -> None:
        if campo in c:
            valor = tabla.get(_normal(c[campo]))
            if valor is None:
                avisos.append(f"{nombre}: «{c[campo]}» no es una opción válida.")
            leido[destino] = valor

    def numero(campo: str, destino: str, nombre: str) -> None:
        if campo in c:
            valor = _entero(c[campo])
            if valor is None:
                avisos.append(f"{nombre}: «{c[campo]}» no es un número.")
            leido[destino] = valor

    numero("edad", "edad", "edad")
    opcion("sexo", "sexo", SEXOS, "sexo")
    opcion("estudios", "edu", ESTUDIOS, "estudios")
    opcion("tipo_empresa", "tipo_empleador", TIPOS, "tipo de empresa")
    opcion("region", "region", REGIONES, "región")
    opcion("ingles", "ingles", {"si": True, "no": False}, "inglés")
    opcion("situacion", "situacion", SITUACIONES, "situación")
    if "ia" in c:
        leido["usa_ia"] = USO_IA.get(_normal(c["ia"]))
    numero("experiencia", "anios_experiencia", "experiencia")
    numero("empleadores", "empleadores", "empleadores")
    if c.get("empresa") and _normal(c["empresa"]) not in _VACIO:
        leido["empresa_actual"] = c["empresa"]
    for campo, destino, nombre in (("cargo", "nivel", "cargo"), ("sueldo_liquido", "sueldo", "sueldo"),
                                   ("riesgo", "riesgo", "riesgo"), ("ocupacion", "ocupacion", "tipo de trabajo"),
                                   ("antiguedad", "antiguedad", "antigüedad")):
        numero(campo, destino, nombre)
    if "cargo" in c and leido.get("nivel") is None:  # también acepta el nombre del cargo
        por_nombre = {_normal(n): i for i, n in enumerate(NIVELES)}
        leido["nivel"] = por_nombre.get(_normal(c["cargo"]))
        if leido["nivel"] is not None:  # el aviso de "no es un número" ya no aplica
            avisos[:] = [a for a in avisos if not a.startswith("cargo:")]
    if "rubro" in c:
        rubros = {_normal(r): r for r in pq.variables["rubro"]["dominio"] if r}
        leido["rubro"] = rubros.get(_normal(c["rubro"])) or next(
            (r for n, r in rubros.items() if _normal(c["rubro"]) in n), None)
        if leido["rubro"] is None:
            avisos.append(f"rubro: «{c['rubro']}» no está en la lista de rubros.")
    notas = [linea.strip()[1:].strip() for linea in
             (_RE_DEDUJE.search(texto).group(1).splitlines() if _RE_DEDUJE.search(texto) else [])
             if linea.strip().startswith(("-", "*"))]
    if "carrera" in c:
        leido["carrera_id"], nota = _carrera(c["carrera"], c.get("institucion"), pq)
        if nota:
            notas.append(nota)

    resultado = completar(PerfilLeido(**leido, inferido=notas), pq)
    # completar descarta en silencio lo que está fuera de rango: se avisa
    for campo in ("edad", "nivel", "riesgo", "ocupacion", "antiguedad", "sueldo"):
        if leido.get(campo) is not None and resultado["perfil"].get(campo) != leido[campo]:
            avisos.append(f"{campo}: {leido[campo]} está fuera de rango; se usó un valor por defecto.")

    rubros_validos = {_normal(r): r for r in pq.variables["rubro"]["dominio"] if r}
    sonado = rubros_validos.get(_normal(c.get("rubro_sonado", ""))) or next(
        (r for k, r in rubros_validos.items() if c.get("rubro_sonado") and _normal(c["rubro_sonado"]) in k), None)
    if sonado and sonado != resultado["perfil"]["rubro"]:
        resultado["perfil"]["rubro_sonado"] = sonado

    from app.sim.motor.partida import dudas_posibles
    from app.sim.motor.perfil import Perfil

    posibles = {d["decision"]: d for d in dudas_posibles(Perfil(**resultado["perfil"]), pq)}
    # La duda que trajo, y las que se desprenden de lo que contó (plantillas, sin modelo)
    candidatas: list[tuple[str, str]] = []
    if "duda" in c:
        codigo = _normal(c["duda"]).replace(" ", "_")
        if codigo in posibles:
            candidatas.append((codigo, "Es la que te da vueltas, según tu Claude."))
        else:
            avisos.append(f"duda: «{c['duda']}» no es una duda posible para este perfil; elígela en la lista.")
    if c.get("proyecto"):
        candidatas += [("emprender", f"Tienes un proyecto: {c['proyecto'][:90]}."),
                       ("independizarse", f"Tienes un proyecto: {c['proyecto'][:90]}.")]
    if _normal(c.get("afuera", "")) in ("si", "s"):
        candidatas += [("remoto_para_afuera", "Te gustaría trabajar para afuera."),
                       ("emigrar", "Te gustaría vivir fuera de Chile.")]
    if sonado and sonado != resultado["perfil"]["rubro"]:
        candidatas.append(("cambiar_de_rubro", f"Te atrae {sonado}."))
    if leido.get("usa_ia") is False:
        candidatas.append(("aprender_ia", "Todavía no usas IA en tu trabajo."))
    vistas, sugeridas = set(), []
    for decision, por_que in candidatas:
        if decision in posibles and decision not in vistas:
            vistas.add(decision)
            sugeridas.append({"decision": decision, "nombre": posibles[decision]["nombre"], "por_que": por_que})
    intereses = [x.strip() for x in re.split(r"[,;]", c.get("intereses", "")) if x.strip()][:5]
    # Qué campos del perfil dijo de verdad (para sumarlos a lo del CV sin pisarlo con valores por defecto)
    a_perfil = {"situacion": ["estado"], "anios_experiencia": ["skill"], "empleadores": ["red"],
                "empresa_actual": ["tipo_empleador", "rubro"] if resultado.get("empresa") else []}
    dados = sorted({k for campo, v in leido.items() if v is not None for k in a_perfil.get(campo, [campo])
                    if k in resultado["perfil"]} | ({"rubro_sonado"} if "rubro_sonado" in resultado["perfil"] else set())
                   | ({"anos_por_empleo"} if resultado["perfil"].get("anos_por_empleo") else set()))
    return {**resultado, "duda": sugeridas[0]["decision"] if sugeridas else None, "dudas_sugeridas": sugeridas[:3],
            "retrato": c.get("retrato") or resultado.get("retrato"), "intereses": intereses,
            "proyecto": c.get("proyecto"), "dados": dados, "avisos": avisos}
