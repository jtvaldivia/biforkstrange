"""Parámetros del motor. Todos salen de una fuente: "dato" si se leyó o estimó directo,
"derivado" si es un cálculo sobre datos con la operación escrita en la fuente.
No hay supuestos del equipo: lo que no tiene dato no está en el modelo.
`python -m app.cli supuestos` los lista. Los cálculos están en datos_laborales/scripts/modelo/."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Par:
    valor: object
    estado: str   # "dato" | "derivado"
    fuente: str
    pais: str = "Chile"


D, R = "dato", "derivado"
EPS = "EPS 2024, historia laboral, ponderada (scripts/modelo/paneles_eps.py)"
ELSOC = "ELSOC 2016-2022, efectos fijos de persona y ola (scripts/modelo/paneles_elsoc.py)"
SCE = "Fed de Nueva York, SCE Labor Market Survey, microdatos 2014-2025 (scripts/modelo/ofertas_sce.py)"
ESI = "INE, ESI 2023-2025, panel por rotación (scripts/modelo/ofertas_esi.py)"

PARAMS: dict[str, Par] = {
    # --- despido
    "DESPIDO": Par({"18-29": 0.0617, "30-44": 0.039, "45-59": 0.0353}, D, EPS + ": despido, cierre o fuerza mayor al año entre asalariados"),
    "ANTIG": Par({"nuevo": 1.35, "medio": 1.0, "viejo": 0.333}, D, EPS + ": riesgo de despido con menos de 1 año, 1 a 4 y 5 o más años de antigüedad, sobre el promedio"),
    "MULT_TAM": Par({"startup": 1.14, "pyme": 1.14, "grande": 0.89, "estado": 0.332}, D,
                    "Pyme y grande: INE, flujos laborales por tamaño. Estado: " + EPS + ". Startup usa el valor de pyme: ninguna fuente las distingue"),
    "MULT_RUBRO": Par("tabla", D, "INE, flujos laborales: salida por rubro sobre el promedio (tablas.json)"),
    # --- búsqueda desde la cesantía
    "ENCONTRAR": Par({"18-29": 0.612, "30-44": 0.571, "45-59": 0.492}, D, EPS + ": encuentra empleo dentro de 12 meses de cesantía"),
    "DURACION_DEP": Par(0.445, D, EPS + ": tasa de encontrar con 12 o más meses de cesantía, sobre la de los primeros 12"),
    "HUECO_VOLUNTARIO": Par(0.718, D, EPS + ": tasa de encontrar tras una inactividad, sobre la de tras un despido"),
    "SEGURO": Par(0.126, D, "CEP 2026, Puntos de Referencia 788: el seguro de cesantía compensa 12,6% del ingreso perdido"),
    "INDEMNIZACION": Par((1, 11), D, "Código del Trabajo, art. 163: un sueldo por año de servicio, con tope de 11"),
    # --- ofertas de trabajo
    "CAMBIO_VOLUNTARIO": Par({"18-29": 0.0782, "30-44": 0.0371, "45-59": 0.0195}, D, EPS + ": cambio directo de empleador por renuncia, al año"),
    "OFERTA_REL": Par({"p10": -0.348, "p25": -0.182, "p50": -0.027, "p75": 0.118, "p90": 0.363}, D,
                      SCE + ": sueldo de la oferta sobre el sueldo actual (log), cuantiles", "EE.UU."),
    "UMBRAL": Par({"no_busca": 0.105, "busca": 0.069}, D, SCE + ": sueldo mínimo que aceptarían por un trabajo nuevo sobre su sueldo (log)", "EE.UU."),
    "BUSCA_MULT": Par(1.713, D, SCE + ": ofertas al año de quien busca sobre las de quien no busca", "EE.UU."),
    "TASA_OFERTAS": Par("CAMBIO_VOLUNTARIO / P(oferta > UMBRAL no_busca)", R,
                        "Ofertas al año en Chile: cambios voluntarios de la EPS divididos por la fracción de ofertas de la SCE que supera el umbral de quien no busca"),
    "TAM_MEZCLA": Par({"startup": 0.0, "pyme": 0.621, "grande": 0.299, "estado": 0.081}, D, ESI + ": tipo del nuevo empleador entre quienes cambiaron"),
    "TAM_SE_QUEDA": Par(0.347, R, ESI + ": 66% de quienes cambian quedan en el mismo tipo de empleador; descontado lo que da el sorteo por azar"),
    # --- sueldo al reemplearse
    "CICATRIZ": Par(0.117, D, SCE + ": las ofertas a desempleados quedan 0,117 (log) bajo su último sueldo", "EE.UU."),
    "CICATRIZ_DECAE": Par(0.105, R, "Carranza, Prieto y Sehnbruch 2025 (Chile): en el decil bajo la pérdida pasa de 27% al mes 3 a 5% al mes 12; (5/27)^(12/9)"),
    "PAUSA_IGUAL_DESPIDO": Par(True, D, EPS + ": volver de una pausa voluntaria cuesta lo mismo que volver de un despido (+0,02, ee 0,09)"),
    # --- ascensos
    "ASCENSO": Par([0.263, 0.18, 0.109, 0.014, 0.0], D,
                   "Baker, Gibbs y Holmstrom 1994, tabla II: tasa anual de ascenso por nivel (una empresa de EE.UU., cargos de gestión)", "EE.UU."),
    "ASC_ALZA": Par(0.058, D, "Baker, Gibbs y Holmstrom 1994, tabla VI: alza al ascender sobre quienes no ascienden", "EE.UU."),
    # --- sueldo en el tiempo
    "PERFIL_EDAD": Par("tabla", D, "INE, ESI 2025: mediana del ingreso por edad y educación (tablas.json)"),
    "REAJUSTE": Par((0.0173, 0.0136), D, "INE, índice de remuneraciones real: media y desviación anual de 10 años"),
    "ASC_EN_PERFIL": Par("ASCENSO x ASC_ALZA", R, "El perfil por edad de la ESI ya incluye los ascensos: se descuenta el alza esperada por ascenso de cada nivel"),
    # --- ocupación (JobHop y capital humano específico)
    "OCUP_REL": Par(0.255, D, ESI + ": cuánto del sueldo relativo del nuevo gran grupo se traspasa al cambiar de empleador"),
    "OCUP_EXPERIENCIA": Par(0.024, R, "Kambourov y Manovskii 2009: 5 años en una ocupación suben el sueldo 12% a 20%; se usa la cota baja, 12%/5 por año, que se pierde al cambiar de ocupación", "EE.UU."),
    "OCUP_EXP_TOPE": Par(5, D, "Kambourov y Manovskii 2009: retorno medido hasta 5 años"),
    # --- IA
    "IA_BRECHA_JOVENES": Par(0.19, D, "Brynjolfsson, Chandar y Chen 2025: empleo de 22 a 25 años 19% menor en las ocupaciones más expuestas (EE.UU., ADP)", "EE.UU."),
    "IA_EDAD_MAX": Par(25, D, "Brynjolfsson, Chandar y Chen 2025: el efecto se mide entre 22 y 25 años; Humlum y Vestergaard (Dinamarca) no hallan efecto en sueldos ni horas"),
    "IA_QUINTIL": Par(0.8, D, "Brynjolfsson, Chandar y Chen 2025: compara el quintil más expuesto"),
    # --- capacitación
    "CURSO_SUELDO": Par(0.006, D, "Comisión revisora del sistema de capacitación 2011 (vía BCN 2019, p. 7): franquicia SENCE, +0,6% de sueldo; sin efecto en empleo"),
    # --- magíster
    "MAG_PREMIO": Par(0.07, R, "DIPRES 2026, becarios Magíster Nacional: prima de USD 150 mensuales al séptimo año; llevada a porcentaje del sueldo"),
    "MAG_ARANCEL": Par(4_210_070, D, "U. de Chile, Facultad de Filosofía y Humanidades: arancel anual 2026 de sus magísteres (un programa de referencia; falta promedio nacional)"),
    "MAG_ANIOS": Par(2, D, "U. de Chile: los magísteres pagan como mínimo dos años de arancel"),
    # --- emprender
    "EMP_INGRESO": Par({"media": 0.632, "tecnica": 0.648, "universitaria": 0.579, "postgrado": 0.657}, D,
                       ESI + ": ingreso de cuenta propia sobre asalariado comparable"),
    "EMP_SD_Q": Par(0.562, R, ESI + ": dispersión persistente entre negocios (residuo de cuenta propia menos el de asalariados)"),
    "EMP_SD_T": Par(0.468, R, ESI + ": variación de un año a otro del mismo negocio"),
    "EMP_SALIDA": Par([0.313, 0.175, 0.095], D, EPS + ": cierre en el año 1, en el año 2 y por año entre el 3 y el 5 (Kaplan-Meier: 31% al año, 43% a dos, 58% a cinco)"),
    "B_EMP_SALIDA_A": Par(0.105, D, "Caliendo, Fossen y Kritikos 2014: amabilidad y salida del emprendimiento, +11% por desviación estándar", "Alemania"),
    "B_EMP_ENTRADA": Par({"O": 0.117, "E": 0.052}, D, "Caliendo, Fossen y Kritikos 2014: entrada a independiente +12,4% por DE de apertura y +5,3% por DE de extraversión", "Alemania"),
    # --- familia
    "UNION": Par({"20-35": 0.0913, "36-59": 0.0894}, D, ELSOC + ": formar pareja al año entre quienes no tienen"),
    "SEPARACION": Par({"20-35": 0.1076, "36-59": 0.0801}, D, ELSOC + ": separarse al año, incluye fin de convivencias"),
    "FECUNDIDAD": Par("tabla", D, "INE, estadísticas vitales 2023: nacimientos por edad de la madre (tablas.json)"),
    "HIJO_PAREJA": Par((1.557, 0.624), D, ELSOC + ": nacimientos con y sin pareja sobre los esperados para su edad"),
    "DIF_EDAD_PAREJA": Par(2, D, "INE, nupcialidad 2023: edad mediana al matrimonio entre personas de distinto sexo, 36 hombres y 34 mujeres"),
    "HIJO_SALE": Par({"m": 0.173, "h": 0.05}, D, "EPS 2024: deja de trabajar en los 12 meses siguientes al nacimiento"),
    "HIJO_PENAL_MUJER": Par(0.21, R, "COES 2024: ingreso de las madres -35% a 20 meses en el sector privado, descontando las que salen"),
    "HIJO_COSTO": Par(383_267, D, "UNICEF y Ministerio de la Mujer 2025, tabla 3: gasto mensual en bienes y servicios por hijo de 0 a 17 años (pesos de marzo 2025)"),
    # --- bienestar
    "ANIMO_BASE": Par({"18-29": 68.7, "30-39": 71.8, "40-49": 71.7, "50-60": 71.8}, D,
                      "ELSOC 2016-2022: satisfacción con la vida de ocupados por edad, escala 1-5 llevada a 0-100 (scripts/modelo/base_bienestar.py)"),
    "ANIMO_INGRESO": Par(2.25, D, ELSOC + ": puntos de satisfacción (0-100) por unidad de log ingreso"),
    "ANIMO_CESANTIA": Par(-3.7, D, ELSOC + ": al quedar cesante"),
    "ANIMO_REEMPLEO": Par(6.0, D, ELSOC + ": el año en que vuelves a trabajar"),
    "ANIMO_PAREJA": Par(2.4, D, ELSOC + ": el año en que formas pareja"),
    "ANIMO_SEPARACION": Par(-4.0, D, ELSOC + ": el año en que te separas"),
    "ANIMO_HORAS_55": Par(-0.22, D, ELSOC + ": trabajar 55 horas o más (no distinguible de cero)"),
    "SALUD_BASE": Par({"18-29": 50.7, "30-39": 49.7, "40-49": 44.3, "50-60": 40.7}, D,
                      "ELSOC 2016-2022: salud subjetiva de ocupados por edad, escala 1-5 llevada a 0-100 (scripts/modelo/base_bienestar.py)"),
    "DEPRESION": Par({"<30": 0.21, "30-39": 0.1835, "40-45": 0.1349, "46-54": 0.1338, "55+": 0.1617}, D,
                     ELSOC + ": probabilidad anual de pasar a síntomas depresivos moderados o severos (PHQ-9 de 10 o más) según horas semanales"),
    "DEPRESION_OCUPADOS": Par(0.1533, D, ELSOC + ": la misma probabilidad para todos los ocupados, base de quien no trabaja"),
    "DEPRESION_CESANTE": Par(0.0345, D, ELSOC + ": quedar cesante sube esa probabilidad"),
    "SOCIAL_HORA": Par(0.994, D, "INE, ENUT 2023: -0,6% de tiempo con tu gente por hora semanal sobre 45"),
    "HORAS_BASE": Par(44.0, D, "INE, ESI 2025: mediana de horas habituales, ocupados de 18 a 54 años"),
    "HORAS_LARGAS": Par(55.0, D, "Tramo de 55 horas o más de ELSOC y del meta-análisis de Virtanen et al. 2018"),
    # --- finanzas
    "TASA_AHORRO": Par("tabla", D, "INE, IX EPF 2021-22: tasa de ahorro y gasto per cápita por quintil de ingreso (tablas.json)"),
    # --- frecuencia con que la gente toma cada decisión (lo que muestra 'gente como tú')
    "FRECUENCIA": Par({
        "buscar_pega": 0.148, "trabajar_mas": {"18-29": 0.046, "30-44": 0.042, "45-59": 0.053}, "magister": 0.0345,
        "sabatico": {"18-29": 0.0037, "30-44": 0.0017, "45-59": 0.0014}, "emprender": {"18-29": 0.0179, "30-44": 0.0134, "45-59": 0.0092},
        "aceptar_oferta": 0.162, "volver_empleo": 0.284,
    }, D, "Buscar: SCE (EE.UU.); trabajar 50+ horas: ESI; postgrado: ELSOC; pausa y emprender: EPS; aceptar oferta: SCE; cerrar negocio: EPS"),
}


class _P:
    def __getattr__(self, k):
        return PARAMS[k].valor


P = _P()
