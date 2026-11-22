"""Del perfil que llena la persona (9 campos) al estado completo del gemelo.

El paquete describe a una persona con 90 variables. La persona declara 9; el
resto parte de los valores por defecto de `estado.json` o de los de este archivo,
que son supuestos del equipo y están marcados como tales.
"""

from dataclasses import asdict, dataclass

from app.sim.motor.paquete import K_PROPIOS, Paquete

NIVELES = ("Junior", "Semi senior", "Senior", "Jefatura", "Gerencia")
EDAD_TITULO = {"media": 18, "tecnica": 21, "universitaria": 24, "postgrado": 26}  # supuesto
OCUPACION_POR_EDU = {"media": 5, "tecnica": 3, "universitaria": 2, "postgrado": 2}  # supuesto
RUBROS_DESTINO = "Comercio"
TRABAJA = ("empleado", "independiente", "fundador")
EDAD_INGRESO_CARRERA = 18  # supuesto: sin dato del CV, entró a la carrera al salir del colegio
# Rasgos de su historia que pasan tal cual al estado, solo si el CV los trae. No son del paquete: los leen
# `politicas.pesos_personales` (cómo deciden sus gemelos), `motor.p_independiente_busca_empleo` y
# `politicas.elecciones_internas` (rubro_sonado: a qué rubro iría si se cambia).
HISTORIA = ("anos_por_empleo", "volvio_a_su_nivel", "freelance_entre_pegas", "emprendio_antes", "anos_independiente",
            "empresas_cerradas", "rubro_sonado")


def skill_por_experiencia(anios: int) -> int:
    """Supuesto del equipo: habilidad 35 al empezar y +2,5 por año, entre 20 y 90 (50 a los 6 años)."""
    return max(20, min(90, 35 + round(2.5 * anios)))


@dataclass(frozen=True)
class Perfil:
    edad: int = 30
    sexo: str = "m"                       # h | m
    edu: str = "universitaria"            # media | tecnica | universitaria | postgrado
    carrera_id: int = -1                  # fila de mifuturo_carreras; -1 sin carrera
    rubro: str = "Servicios profesionales"
    tipo_empleador: str = "pyme"          # grande | pyme | startup | publico | extranjero
    nivel: int = 1                        # 0 junior ... 4 gerencia
    sueldo: float = 1_400_000             # líquido mensual
    riesgo: int = 5                       # tolerancia al riesgo, 0 a 10
    # Opcionales: si no vienen, se suponen
    estado: str = "empleado"
    ocupacion: int | None = None
    antiguedad: int = 2
    region: str = "rm"
    ahorro: float | None = None
    # Del CV, si se sabe (ver perfil_ia.completar); si no, los supuestos neutros de siempre
    ingles: int = 0                       # 1 si trabaja en inglés (intermedio o más)
    skill: int | None = None              # 0 a 100; sin dato, 50
    red: int | None = None                # 0 a 100; sin dato, 30
    # Su situación de hoy, del CV: decide qué cartas le aparecen
    meses_cesante: int = 0                # si está buscando; 8 o más es un "hueco" en el CV
    parcial: int = 0                      # 1 si trabaja media jornada
    remoto: int = 0                       # 1 si ya trabaja remoto
    usa_ia: int = 0                       # 1 si ya trabaja con herramientas de IA
    empresa_anos: int = 0                 # si es fundador: años de su empresa
    empresa_fondos: int = 0               # si es fundador: 1 si levantó inversión
    # Su historia: cada cuántos años se ha cambiado de pega (calibra cómo deciden sus gemelos)
    anos_por_empleo: float | None = None
    # Lo que contó su Claude: el rubro al que se cambiaría ("¿a qué rubro?" parte ahí)
    rubro_sonado: str | None = None
    # Si estudia: cuánto le falta ("egreso esperado 2028") y cuántos años lleva ("cursando 3er año").
    # Sin dato, se suponen por su edad y la duración real de la carrera (ver `avance_en_carrera`).
    semestres_restantes: int | None = None
    anos_en_carrera: int | None = None
    # Cómo salió de sus cesantías, según el CV (1 = sí): sus gemelos responden igual (politicas.pesos_personales)
    volvio_a_su_nivel: int = 0            # tras un hueco de más de 6 meses, volvió a un cargo igual o mayor
    freelance_entre_pegas: int = 0        # trabajó por su cuenta entre una pega y otra
    emprendio_antes: int = 0              # ya tuvo una empresa propia antes de la de hoy
    anos_independiente: int | None = None  # si hoy trabaja por su cuenta: hace cuántos años
    practica: str = ""                    # tipo de empleador de su práctica (grande | pyme | startup | publico)
    primer_empleo: int = 0                # 1 si busca su primer empleo: nunca ha trabajado después de titularse
    toda_su_carrera_en: str = ""          # publico | startup, si todos sus empleos (dos o más) fueron ahí
    ascensos_por_ano: float | None = None  # ascensos dentro de una misma empresa por año de experiencia
    empresas_cerradas: int = 0            # empresas propias que ya cerró
    # Dónde estudió (universidades.universidad_id); vacío si no lo dice
    universidad_id: str = ""
    # Su empresa y su cargo de hoy, con el nombre que dio. Solo para contar la historia: no mueven ningún
    # número. Valen mientras siga en ese empleo (ver `Vida._nombre_empresa`).
    empresa_nombre: str = ""
    cargo_nombre: str = ""

    @classmethod
    def a_los_18(cls, sexo: str = "m", riesgo: int = 5) -> "Perfil":
        """Alguien que sale del colegio: punto de partida de la cohorte de validación."""
        return cls(edad=18, sexo=sexo, edu="media", rubro="", tipo_empleador="", nivel=0, sueldo=0,
                   riesgo=riesgo, estado="estudiando", antiguedad=0)


# Al volver a trabajar, de qué tipo de empleador viene la pega (decisión interna tipo_de_empleador).
# Supuesto del equipo, sin dato detrás: quien hizo toda su carrera en el Estado vuelve a entrar al Estado
# 40% de las veces (la población, P_REEMPLEO_PUBLICO = 12%); quien la hizo en startups encuentra una
# startup en 20% de sus ofertas privadas (la población, MIX_EMPLEADOR['startup'] = 1%).
REEMPLEO_PUBLICO_SI_SIEMPRE_ESTADO = 0.40
STARTUP_SI_SIEMPRE_STARTUP = 0.20


def parametros_propios(perfil: "Perfil", pq: Paquete) -> dict:
    """Parámetros del paquete que esta vida tiene distintos por su historia (ver paquete.K_PROPIOS)."""
    # pisos sobre la escalera de transiciones_tipo (EPS): el resto se reparte entre grande y pyme como en su fila
    if perfil.toda_su_carrera_en == "publico":
        return {"PISO_REEMPLEO_PUBLICO": REEMPLEO_PUBLICO_SI_SIEMPRE_ESTADO}
    if perfil.toda_su_carrera_en == "startup":
        return {"PISO_STARTUP": STARTUP_SI_SIEMPRE_STARTUP * (1 - pq.k("P_REEMPLEO_PUBLICO"))}
    return {}


# Ascenso extra por su ritmo de ascensos (supuesto del equipo): la mitad de lo que su ritmo supera al del
# paquete, hasta 4 puntos al año. Ver `ascenso_extra`.
ASCENSO_EXTRA_FACTOR, ASCENSO_EXTRA_MAX = 0.5, 0.04


def ascenso_extra(ascensos_por_ano: float, nivel: int, pq: Paquete) -> float:
    """Cuánto más asciende al año que lo que el paquete supone, según su CV (va a prob_ascenso_extra).

    Para no contar dos veces lo que ya dice su cargo, se compara su ritmo con el que el paquete le habría
    dado en los cargos que ya subió (ASCENSO de junior a su nivel de hoy; supuesto: partió junior), y solo
    cuenta lo que lo supera. Un ritmo más lento no resta: prob_ascenso_extra no baja de 0 en el paquete.
    La mitad del exceso (regresión a la media) y el tope son supuestos del equipo.
    """
    pasados = range(max(1, nivel))
    esperado = sum(pq.k("ASCENSO", n) for n in pasados) / len(pasados)
    return round(max(0.0, min(ASCENSO_EXTRA_MAX, ASCENSO_EXTRA_FACTOR * (ascensos_por_ano - esperado))), 4)


def avance_en_carrera(perfil: Perfil, pq: Paquete) -> tuple[int, int]:
    """(semestres que le faltan, años que lleva) de quien estudia una carrera del catálogo.

    Lo que diga el CV manda. Sin dato, supuesto del equipo: entró a los 18 y va al día, según la duración
    real de su carrera (mifuturo_carreras); siempre le queda al menos un año, porque sigue estudiando.
    """
    duracion = round(float(pq.tabla("mifuturo_carreras", "duracion_real_semestres", "carrera_id", perfil.carrera_id)))
    return _avance(perfil, duracion)


# Quien estudia una carrera que no está en el catálogo (el CV no la nombra). Supuesto del equipo: si su
# institución es un IP o un CFT, una carrera técnica de 5 semestres; si no, según lo que ya terminó: con media
# o técnica, una universitaria de 8 (la mayor parte de la matrícula de pregrado es universitaria); con un
# título universitario o un postgrado, un postgrado de 4. Al terminar se titula de eso.
SEMESTRES_SIN_CARRERA = {"universitaria": 8, "tecnica": 5, "postgrado": 4}


def tipo_institucion_de(pq: Paquete, universidad_id: str) -> str:
    """U, IP, CFT o EXT según el catálogo de instituciones; vacío si no se sabe."""
    if not universidad_id:
        return ""
    try:
        return str(pq.tabla("universidades", "tipo_institucion", "universidad_id", universidad_id))
    except Exception:  # noqa: BLE001 - sin catálogo o sin fila
        return ""


def estudio_sin_carrera(edu: str, tipo_institucion: str) -> tuple[str, int]:
    """(título al terminar, semestres que dura) de quien estudia sin carrera del catálogo. Ver SEMESTRES_SIN_CARRERA."""
    if edu in ("universitaria", "postgrado"):
        titulo = "postgrado"
    elif tipo_institucion in ("IP", "CFT"):
        titulo = "tecnica"
    else:
        titulo = "universitaria"
    return titulo, SEMESTRES_SIN_CARRERA[titulo]


def _avance(perfil: Perfil, duracion: int) -> tuple[int, int]:
    anos, restantes = perfil.anos_en_carrera, perfil.semestres_restantes
    if anos is None and restantes is not None:
        anos = (duracion - restantes) // 2
    if anos is None:
        anos = perfil.edad - EDAD_INGRESO_CARRERA
        anos = min(anos, duracion // 2 - 1)  # supuesto: le queda al menos un año
    anos = max(0, min(10, anos))
    if restantes is None:
        restantes = max(2, duracion - 2 * anos)
    return max(1, min(16, restantes)), anos


def busca_primer_empleo(perfil: Perfil) -> bool:
    """Quien estudia (su primera pega viene al titularse) o busca sin haber trabajado: lo dice el flag
    `primer_empleo` del CV, o una práctica declarada (solo se declara si nunca tuvo empleo tras titularse).
    No se mira el sueldo: la API lo exige mayor que 0 y `perfil_ia.completar` siempre lo llena, así que
    "sueldo 0" dejaba en cesantía a todos los que buscaban su primera pega. El sueldo 0 sigue valiendo
    para los perfiles armados a mano (la cohorte de validación parte con sueldo 0)."""
    if perfil.estado == "estudiando":
        return True
    return perfil.estado == "buscando" and bool(perfil.primer_empleo or perfil.practica or perfil.sueldo == 0)


def _literal(inicio: str):
    """Valor inicial de estado.json cuando es un literal ('0', '44', "''", 'chile')."""
    if inicio == "''":
        return ""
    try:
        return int(inicio)
    except ValueError:
        try:
            return float(inicio)
        except ValueError:
            return inicio if inicio in ("chile", "bien") else None


def _institucion_por_defecto(pq: Paquete) -> str:
    """La institución chilena con más matrícula; vacío si el paquete no trae el catálogo."""
    try:
        filas = [f for f in pq.filas("universidades") if f["tipo_institucion"] != "EXT"]
    except (KeyError, OSError):
        return ""
    return max(filas, key=lambda f: float(f.get("matricula") or 0))["universidad_id"] if filas else ""


def prima_universidad(pq: Paquete, universidad_id: str) -> float:
    """Prima de sueldo de la institución (universidades.prima_pregrado); 1 si no hay dato."""
    if not universidad_id:
        return 1.0
    try:
        return float(pq.tabla("universidades", "prima_pregrado", "universidad_id", universidad_id))
    except Exception:  # noqa: BLE001 - sin fila o celda vacía (extranjeras): neutra
        return 1.0


def estado_inicial(perfil: Perfil, pq: Paquete) -> dict:
    p = asdict(perfil)
    e: dict = {}
    for nombre, v in pq.variables.items():
        if v["inicio"] == "deriva" or v["tipo"] == "eleccion":
            continue
        valor = _literal(str(v["inicio"]))
        if valor is not None:
            e[nombre] = valor
    trabaja = perfil.estado in TRABAJA
    e.update(
        edad=perfil.edad, sexo=perfil.sexo, edu=perfil.edu, estado=perfil.estado,
        carrera_id=perfil.carrera_id, rubro=perfil.rubro if trabaja else "",
        tipo_empleador=perfil.tipo_empleador if perfil.estado == "empleado" else "",
        nivel=perfil.nivel, sueldo=float(perfil.sueldo) if trabaja else 0.0,
        sueldo_ref=float(perfil.sueldo), antiguedad=perfil.antiguedad if trabaja else 0,
        region=perfil.region, riesgo=perfil.riesgo * 10,
        meses_cesante=perfil.meses_cesante if perfil.estado == "buscando" else 0,
        hueco=1 if perfil.estado == "buscando" and perfil.meses_cesante >= 8 else 0,  # PENAL_HUECO: 8 meses
        parcial=perfil.parcial if trabaja else 0, horas=22 if trabaja and perfil.parcial else 44,
        remoto=perfil.remoto if trabaja else 0, usa_ia=perfil.usa_ia,
        empresa_anos=perfil.empresa_anos if perfil.estado == "fundador" else 0,
        empresa_fondos=perfil.empresa_fondos if perfil.estado == "fundador" else 0,
        primer_empleo=1 if busca_primer_empleo(perfil) else 0,
        anos_titulado=max(0, min(40, perfil.edad - EDAD_TITULO[perfil.edu])),
        ocupacion=perfil.ocupacion if perfil.ocupacion is not None
        else (1 if perfil.nivel >= 3 else OCUPACION_POR_EDU[perfil.edu]),
        # supuestos neutros: las fórmulas del paquete están centradas en estos valores
        red=30 if perfil.red is None else perfil.red,
        # sin dato del CV: la experiencia se estima como los años desde que se tituló (supuesto)
        skill=perfil.skill if perfil.skill is not None
        else skill_por_experiencia(max(0, perfil.edad - EDAD_TITULO[perfil.edu])) if trabaja else 50,
        ambicion=50, ingles=perfil.ingles,
        pareja="no", hijos=0, edad_hijo_menor=-1, isapre=0, propietario=0,
        madre_edad=perfil.edad + round(pq.k("EDAD_MADRE")),
        padre_edad=perfil.edad + round(pq.k("EDAD_MADRE")) + 2,
        area="", tipo_institucion="", semestres_restantes=0,
        # variables que elige el jugador dentro de una opción
        rubro_destino=perfil.rubro or RUBROS_DESTINO, region_destino="Valparaíso",
        ocupacion_destino=2, quien_enferma="madre",
        universidad_destino=pq.filas("sies_magister_2026")[0]["universidad_id"],  # la con más programas
        institucion_destino=_institucion_por_defecto(pq), universidad_id=perfil.universidad_id or "",
        # nombres de su empleo de hoy (no son variables del paquete: el motor los borra al dejar ese empleo)
        empresa_inicial=perfil.empresa_nombre.strip() if perfil.estado == "empleado" else "",
        cargo_inicial=perfil.cargo_nombre.strip() if perfil.estado == "empleado" else "",
    )
    # su línea de trabajo según el cargo que escribió: queda aunque se borre el nombre, para que las ofertas sigan
    # en lo suyo mientras no tenga un cargo del catálogo (ver empresas.familias_de)
    from app.sim.motor.empresas import familia_por_nombre

    familia = familia_por_nombre(pq, perfil.cargo_nombre) if perfil.cargo_nombre.strip() else None
    if familia:
        e["familia_inicial"] = familia
    # su historia no es del paquete: la lee la política de los gemelos, y solo si el CV la trae
    for rasgo in HISTORIA:
        if getattr(perfil, rasgo):
            e[rasgo] = getattr(perfil, rasgo)
    if perfil.estado != "independiente":
        e.pop("anos_independiente", None)  # solo describe a quien hoy trabaja por su cuenta
    if perfil.practica and (perfil.estado == "estudiando" or e["primer_empleo"]):
        e["practica"] = perfil.practica  # solo pesa en su primera pega
    if perfil.estado == "fundador" and perfil.sueldo > 0:
        # ya tiene empresa: su ganancia parte de lo que declaró (el primer año gana eso en la mediana) y crece
        # con los años como la de cualquier empresa; MICRO_MEDIANA queda para quien recién emprende
        e["base_empresa"] = float(perfil.sueldo) / (1 + e["empresa_anos"] / 4)
    if perfil.ascensos_por_ano is not None:
        e["prob_ascenso_extra"] = ascenso_extra(perfil.ascensos_por_ano, perfil.nivel, pq)  # sin dato, 0 (estado.json)
    propios = parametros_propios(perfil, pq)
    if propios:
        e[K_PROPIOS] = propios
    if perfil.carrera_id >= 0:
        e["area"] = pq.tabla("mifuturo_carreras", "area", "carrera_id", perfil.carrera_id)
        e["tipo_institucion"] = pq.tabla("mifuturo_carreras", "tipo_institucion", "carrera_id", perfil.carrera_id)
        if perfil.estado == "estudiando":
            # antes quedaba en 0 semestres: todo estudiante se titulaba al cerrar su primer año
            e["semestres_restantes"], e["anos_en_carrera"] = avance_en_carrera(perfil, pq)
    elif perfil.estado == "estudiando" and not (perfil.edu == "media" and perfil.edad <= 18):
        # sin carrera del catálogo (y no es quien sale del colegio, que elige con salir_del_colegio): antes nadie
        # le descontaba semestres y estudiaba para siempre. Se supone su duración (SEMESTRES_SIN_CARRERA)
        _, duracion = estudio_sin_carrera(perfil.edu, tipo_institucion_de(pq, perfil.universidad_id))
        e["semestres_restantes"], e["anos_en_carrera"] = _avance(perfil, duracion)
    d = pq.derivar(e)
    tramo = "p80+" if d["percentil"] >= 80 else "p50-79" if d["percentil"] >= 50 else "p0-49"
    e["tasa_ahorro"] = pq.k("TASA_AHORRO", tramo)
    e["gasto_mensual"] = pq.tabla("epf_quintiles", "gasto_hogar", "quintil", d["quintil"])
    e["ahorro"] = float(perfil.ahorro) if perfil.ahorro is not None else 2.0 * e["sueldo"]  # supuesto: dos sueldos
    faltan = [n for n, v in pq.variables.items() if v["inicio"] != "deriva" and n not in e]
    if faltan:
        raise ValueError(f"variables sin valor inicial: {faltan}")
    return e
