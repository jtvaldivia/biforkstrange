"""La historia de cada carta: quién te escribe, qué empresa, por qué ahora.

El paquete trae la decisión ("Otra empresa te ofrece trabajo"); aquí se cuenta como algo que le
pasa a esta persona ("Te escribe por LinkedIn la jefa de producto de Pagosur, una fintech de 80
personas"). Reglas:

- Solo texto. Ningún número del juego sale de aquí, y el texto no promete cifras: las cifras
  las pone el motor y se muestran aparte.
- Si la persona trabaja en una empresa del catálogo, o la oferta trae una (`contexto["empresa"]`,
  `contexto["oferta"]`), se usa su nombre real: es la misma que muestra la carta. Lo que le pasa a la
  empresa en la historia es de este mundo simulado, no un hecho sobre la empresa real. Sin empresa del
  catálogo, quedan las ficticias de abajo.
- Determinista: la misma partida (semilla) cuenta la misma historia. Usa dados propios, que no
  tocan los de la simulación.
"""

from app.sim.motor.azar import Dados

# Empresas ficticias por rubro: (nombre, a qué se dedica)
EMPRESAS: dict[str, list[tuple[str, str]]] = {
    "Minería": [("Minera Altiplano", "una minera de cobre en el norte"), ("Andes Servicios Mineros", "una contratista minera"),
                ("Cobretec", "una empresa de tecnología para faenas mineras")],
    "Finanzas y seguros": [("Pagosur", "una fintech de pagos"), ("Banco Pacífico", "un banco"),
                           ("Seguros Cordillera", "una aseguradora"), ("Inversiones Laguna", "una administradora de fondos")],
    "Información y comunicaciones": [("Nodo Software", "una empresa de software"), ("Austral Cloud", "una empresa de servicios en la nube"),
                                     ("Telemar", "una empresa de telecomunicaciones"), ("Datacentro", "una consultora de datos")],
    "Comercio": [("Supermercados Ñandú", "una cadena de supermercados"), ("Tiendas Arauco", "una tienda por departamento"),
                 ("Mercado Austral", "un e-commerce"), ("Distribuidora del Valle", "una distribuidora mayorista")],
    "Salud": [("Clínica Los Aromos", "una clínica privada"), ("Red Salud Sur", "una red de centros médicos"),
              ("Laboratorio Andino", "un laboratorio clínico"), ("Farmacias Copihue", "una cadena de farmacias")],
    "Enseñanza": [("Colegio Pumahue", "un colegio particular"), ("Universidad del Pacífico", "una universidad"),
                  ("Instituto Técnico Valle", "un instituto profesional"), ("Aprende+", "una plataforma de cursos en línea")],
    "Servicios profesionales": [("Ossandón Consultores", "una consultora de gestión"), ("Larraín & Pérez", "un estudio de abogados"),
                                ("Auditores Asociados", "una auditora"), ("Arquitectura Norte", "una oficina de arquitectura")],
    "Construcción": [("Constructora Maule", "una constructora"), ("Inmobiliaria Los Robles", "una inmobiliaria"),
                     ("Obras Andinas", "una constructora de obras viales")],
    "Industria manufacturera": [("Alimentos Lautaro", "una fábrica de alimentos"), ("Plásticos del Sur", "una fábrica de envases"),
                                ("Viña Santa Lucía", "una viña exportadora")],
    "Transporte": [("Logística Express", "una empresa de logística"), ("Buses Cordillera", "una empresa de buses"),
                   ("Puerto Central", "un operador portuario")],
    "Agricultura y pesca": [("Frutícola Aconcagua", "una exportadora de fruta"), ("Salmones Chiloé", "una salmonera"),
                            ("Agrícola Los Andes", "una agrícola")],
    "Hoteles y restaurantes": [("Hotel Bahía", "un hotel"), ("Grupo Fogón", "una cadena de restoranes"),
                               ("Patagonia Lodges", "una empresa de turismo")],
    "Artes y entretención": [("Productora Lumbre", "una productora audiovisual"), ("Teatro Mapocho", "un centro cultural"),
                             ("Estudio Pixel", "un estudio de videojuegos")],
    "Servicios administrativos": [("Outsourcing Andes", "una empresa de outsourcing"), ("Contact Sur", "un call center"),
                                  ("Seguridad Integral", "una empresa de seguridad")],
    "Administración pública": [("el Ministerio de Hacienda", "un ministerio"), ("la Municipalidad de Providencia", "una municipalidad"),
                               ("el Servicio de Impuestos Internos", "un servicio público")],
    "Otros servicios": [("Lavanderías Clean", "una cadena de servicios"), ("Fundación Puente", "una fundación"),
                        ("Gimnasios Activa", "una cadena de gimnasios")],
}
TAMANO = {"grande": "de más de mil personas", "pyme": "de unas 40 personas", "startup": "de 30 personas que acaba de levantar capital",
          "publico": "", "extranjero": "con oficinas en varios países"}
QUIENES = ["la gerenta de personas", "un headhunter", "una excompañera tuya", "el jefe del área", "una reclutadora",
           "un amigo de la universidad que ahora trabaja ahí"]
CERCANOS = ["una excompañera", "un amigo de la universidad", "tu hermana", "un excolega"]
CANALES = ["Por LinkedIn", "Por correo", "Por WhatsApp", "En un evento de la industria"]
# Startups ficticias por rubro: la que te escribe es de tu mundo
STARTUPS_RUBRO: dict[str, list[tuple[str, str]]] = {
    "Finanzas y seguros": [("Kuota", "una fintech de créditos para independientes"), ("Cuentaclara", "una fintech de pagos para pymes")],
    "Información y comunicaciones": [("Nubecita", "una startup de software para restoranes"), ("Datalab", "una startup de inteligencia artificial")],
    "Salud": [("Medibox", "una startup de telemedicina"), ("Turnito", "una startup de agendamiento médico")],
    "Agricultura y pesca": [("Agrosense", "una startup de sensores para el agro")],
    "Transporte": [("Rutea", "una startup de logística para pymes")],
    "Comercio": [("Carrito", "una startup de compras por WhatsApp")],
    "Servicios profesionales": [("Contabot", "una startup de contabilidad automática"), ("Legalito", "una startup de trámites legales en línea")],
    "Construcción": [("Casa Clara", "una startup inmobiliaria")],
    "Enseñanza": [("Profe.app", "una startup de clases particulares")],
    "Minería": [("Minesight", "una startup de monitoreo de faenas")],
}
STARTUPS = [x for lista in STARTUPS_RUBRO.values() for x in lista]
EXTRANJERAS = [("Northwind Labs", "una empresa de software de Estados Unidos"), ("Bluefin Data", "una empresa de datos de Canadá"),
               ("Helio Systems", "una empresa de tecnología de Alemania")]
CARGOS = ["un cargo de entrada", "un cargo parecido al tuyo", "un cargo senior", "una jefatura", "una gerencia"]


class _Sorteo:
    def __init__(self, semilla: int, anio: int, decision: str, ocurrencia: int):
        self.dados = Dados(semilla, "narrativa")
        self.base = f"{decision}:{ocurrencia}"
        self.anio = anio

    def uno(self, que: str, lista: list):
        return lista[int(self.dados.u(self.anio, f"{self.base}:{que}") * len(lista))]


def _empresa(s: _Sorteo, rubro: str, tipo: str, que: str = "empresa") -> str:
    if tipo == "startup":
        nombre, desc = s.uno(que, STARTUPS_RUBRO.get(rubro) or STARTUPS)
    elif tipo == "extranjero":
        nombre, desc = s.uno(que, EXTRANJERAS)
    else:
        nombre, desc = s.uno(que, EMPRESAS.get(rubro) or EMPRESAS["Servicios profesionales"])
    tam = TAMANO.get(tipo, "")
    return f"{nombre}, {desc}{' ' + tam if tam else ''}"


def _otro_tipo(s: _Sorteo, tipo: str) -> str:
    return s.uno("tipo", [t for t in ("grande", "pyme", "startup") if t != tipo] or ["pyme"])


def narrar(decision: str, contexto: dict, semilla: int, anio: int, ocurrencia: int = 0) -> dict | None:
    """Devuelve {"situacion": texto} para la carta, o None si no hay historia para esa decisión.

    `contexto` es el estado de la persona cuando le llegó la carta (rubro, tipo_empleador, nivel, edad...).
    """
    s = _Sorteo(semilla, anio, decision, ocurrencia)
    rubro = contexto.get("rubro") or "Servicios profesionales"
    tipo = contexto.get("tipo_empleador") or "pyme"
    nivel = int(contexto.get("nivel") or 0)
    quien, canal, cercano = s.uno("quien", QUIENES), s.uno("canal", CANALES), s.uno("cercano", CERCANOS)
    # tu propia empresa no cambia mientras sigas ahí: se sortea por el año en que entraste, no por el año de la carta
    entrada = int(contexto.get("edad", 0)) - int(contexto.get("antiguedad") or 0)
    propia = _Sorteo(semilla, 0, f"propia:{rubro}:{tipo}:{entrada}", 0)
    aqui = contexto.get("empresa") or _empresa(propia, rubro, tipo, "propia")
    oferta = contexto.get("oferta") or {}
    puesto = f"ser {oferta['cargo']}" if oferta.get("cargo") else CARGOS[min(nivel, 4)]

    if decision == "oferta_externa" and oferta:
        texto = (f"{canal}, te contacta {quien} de {oferta['nombre']}. Buscan a alguien con tu experiencia "
                 f"en {rubro.lower()} y te ofrecen {puesto}. Quieren una respuesta esta semana.")
    elif decision == "oferta_externa":
        destino = _otro_tipo(s, tipo) if s.dados.u(anio, f"{s.base}:cambia_tipo") < 0.4 else tipo
        otra = _empresa(s, rubro, destino)
        for intento in range(1, 6):  # que no te ofrezca trabajo tu propia empresa
            if otra.split(",")[0] != aqui.split(",")[0]:
                break
            otra = _empresa(s, rubro, destino, f"empresa{intento}")
        texto = (f"{canal}, te contacta {quien} de {otra}. Buscan a alguien con tu experiencia "
                 f"en {rubro.lower()} para {CARGOS[min(nivel, 4)]}. Quieren una respuesta esta semana.")
    elif decision == "unirse_a_startup" and oferta:
        texto = (f"{oferta['nombre']} te ofrece {puesto} en su equipo. Pagan menos que tu pega actual, "
                 f"pero te dan acciones. {canal}, te lo propone {quien}.")
    elif decision == "unirse_a_startup":
        nombre, desc = s.uno("startup", STARTUPS_RUBRO.get(rubro) or STARTUPS)
        texto = (f"{nombre}, {desc}, te ofrece entrar al equipo fundador. Pagan menos que tu pega actual, "
                 f"pero te dan acciones. {canal}, te lo propone {quien}.")
    elif decision == "buscar_estando_empleado":
        texto = (f"Llevas un tiempo en {aqui.split(',')[0]} y te preguntas si afuera te valorarían más. "
                 f"¿Actualizas el CV y empiezas a postular, sin que se entere nadie?")
    elif decision == "pedir_aumento":
        texto = (f"Se viene la evaluación de desempeño en {aqui.split(',')[0]}. Cerraste un buen año y {s.uno('par', ['un compañero', 'una compañera'])} "
                 f"que entró después que tú te contó cuánto gana. ¿Pides aumento?")
    elif decision == "trabajar_mas_horas":
        texto = (f"En {aqui.split(',')[0]} viene un cierre {s.uno('cierre', ['de año', 'de proyecto', 'de licitación'])} y tu equipo "
                 f"se está quedando hasta tarde. Tu jefatura no lo pide, pero lo nota.")
    elif decision == "jefatura":
        texto = (f"Se va {s.uno('sale', ['tu jefa', 'tu jefe'])} y en {aqui.split(',')[0]} te ofrecen quedarte con el equipo. "
                 f"Más responsabilidad, gente a cargo y menos tiempo para lo que te gusta hacer.")
    elif decision == "cambiar_de_rubro":
        texto = (f"Después de años en {rubro.lower()}, {cercano} te dice que en otros rubros pagan más por lo que tú sabes hacer. "
                 f"Partirías con menos antigüedad y tendrías que aprender el negocio.")
    elif decision == "cambiar_de_ocupacion":
        texto = ("Te das cuenta de que lo que haces todos los días ya no te entusiasma. "
                 f"{cercano.capitalize()} te cuenta cómo se cambió de oficio. ¿Pruebas tú?")
    elif decision == "aprender_ia":
        texto = (f"En {aqui.split(',')[0]} empezaron a usar herramientas de IA y hay tareas que antes te tomaban una tarde "
                 f"y ahora salen en minutos. ¿Le dedicas tiempo a aprenderlas de verdad?")
    elif decision == "invertir_en_red":
        texto = (f"Te invitan a {s.uno('evento', ['un meetup de la industria', 'un after de exalumnos', 'una conferencia del rubro'])} "
                 f"este jueves. Podrías ir, o quedarte en la casa como siempre.")
    elif decision == "emprender":
        texto = (f"Tienes una idea dándote vueltas hace meses: {s.uno('idea', ['un servicio para pymes de tu rubro', 'una app que resuelve algo que ves todos los días en la pega', 'una consultora propia'])}. "
                 f"{cercano.capitalize()} te anima a lanzarte.")
    elif decision == "independizarse":
        texto = (f"Un cliente de {aqui.split(',')[0]} te dice que te contrataría directo, a honorarios. "
                 f"Serías independiente: sin jefatura, pero sin contrato.")
    elif decision == "renunciar":
        texto = (f"Llevas semanas llegando sin ganas a {aqui.split(',')[0]} y el ambiente no mejora. "
                 f"Un domingo en la noche, escribes la carta de renuncia en el celular.")
    elif decision == "magister":
        texto = (f"Te llega la convocatoria de {s.uno('mg', ['un magíster en la Chile', 'un MBA en la Católica', 'un magíster en la Adolfo Ibáñez'])}. "
                 f"Varios de tu generación ya lo hicieron.")
    elif decision == "emigrar" and oferta:
        texto = (f"{oferta['nombre']} está contratando gente de Latinoamérica con visa de trabajo y te ofrece {puesto}. "
                 f"{canal}, te escribe {quien}.")
    elif decision == "emigrar":
        nombre, desc = s.uno("afuera", EXTRANJERAS)
        texto = f"{nombre}, {desc}, está contratando gente de Latinoamérica con visa de trabajo. {canal}, te escribe {quien}."
    elif decision == "remoto_para_afuera" and oferta:
        texto = f"{oferta['nombre']} busca gente remota desde Chile, pagando en dólares: te ofrece {puesto}. {canal}, te llega la oferta."
    elif decision == "remoto_para_afuera":
        nombre, desc = s.uno("remoto", EXTRANJERAS)
        texto = f"{nombre}, {desc}, busca gente remota desde Chile, pagando en dólares. {canal}, te llega la oferta."
    elif decision == "mudarse_de_region":
        destino = "Santiago" if contexto.get("region") == "otra" else s.uno("region", ["Antofagasta", "Concepción", "Puerto Montt", "La Serena"])
        texto = f"{cercano.capitalize()} te cuenta de una vacante en {destino} en tu mismo rubro. Implicaría mudarte."
    elif decision == "pedir_hibrido":
        texto = f"En {aqui.split(',')[0]} algunos equipos ya trabajan dos días desde la casa. El tuyo no. ¿Lo pides?"
    elif decision == "media_jornada":
        texto = f"Quieres más tiempo para lo tuyo. En {aqui.split(',')[0]} existe la media jornada, pero casi nadie la pide."
    elif decision == "sabatico":
        texto = "Llevas años sin parar y {}. ¿Te tomas un año para ti?".format(
            s.uno("sab", ["un amigo se fue a recorrer Sudamérica", "te ofrecen un voluntariado afuera", "te sientes al límite"]))
    elif decision == "bootcamp":
        texto = (f"Ves un aviso de {s.uno('bc', ['un bootcamp de programación', 'un bootcamp de análisis de datos', 'un bootcamp de diseño UX'])}: "
                 f"cuatro meses intensivos para cambiarte al mundo tech.")
    elif decision == "cesantia":
        texto = (f"Llevas meses mandando currículums. {s.uno('ces', ['Te llamaron de dos lados y en ninguno quedaste', 'Te ofrecieron algo, pero pagan menos que antes', 'Un conocido te ofrece trabajar con él sin contrato'])}. "
                 f"Los ahorros se van achicando.")
    elif decision == "ahorro":
        texto = f"Te llega el sueldo y {s.uno('ah', ['te dan ganas de cambiar el auto', 'tus amigos arman un viaje', 'ves que no has ahorrado nada este año'])}. ¿Cómo manejas tu plata?"
    else:
        return None
    return {"situacion": texto}
