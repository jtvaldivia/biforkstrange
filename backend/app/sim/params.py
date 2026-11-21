"""Parámetros del motor. Cada uno declara si es DATO (sale de una fuente) o SUPUESTO
(decisión del equipo, sin número defendible). `python -m app.cli supuestos` los lista."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Par:
    valor: object
    estado: str   # "dato" | "derivado" | "supuesto"
    fuente: str


D, R, S = "dato", "derivado", "supuesto"

PARAMS: dict[str, Par] = {
    # --- mercado laboral
    "DESPIDO": Par({"18-29": 0.0529, "30-44": 0.0333, "45-59": 0.0274}, D, "EPS 2016-2024: despido, cierre o fuerza mayor al año"),
    "ENCONTRAR": Par({"18-29": 0.70, "30-44": 0.68, "45-59": 0.60}, D, "EPS 2024, Kaplan-Meier: cesantes que encuentran empleo en 12 meses"),
    "CAMBIO_EMPLEADOR": Par({"18-29": 0.2178, "30-44": 0.1377, "45-59": 0.1019}, D, "EPS 2024: cambio de empleador sin pasar por cesantía"),
    "OFERTA_FACTOR": Par(2.0, S, "Ofertas pasivas por año = cambio de empleador x 2 (calibración: no todas se aceptan)"),
    "BUSCA_MULT": Par(2.5, S, "Buscar activamente multiplica las ofertas"),
    "UMBRAL_PASIVO": Par(0.08, S, "Mejora mínima (log) para aceptar una oferta que no buscaste"),
    "UMBRAL_ACTIVO": Par(0.03, S, "Mejora mínima (log) para aceptar una oferta si estás buscando"),
    "M_SD": Par(0.15, S, "Dispersión del premio salarial entre empleadores (log)"),
    "M_REEMPLEO": Par(-0.03, S, "Premio medio del empleo que se toma desde la cesantía"),
    "MULT_TAM": Par({"startup": 1.5, "pyme": 1.14, "grande": 0.89, "estado": 0.5}, R, "INE flujos laborales por tamaño; startup y Estado son supuestos"),
    "ANTIG_NUEVO": Par(1.3, S, "Riesgo de despido el primer año en un empleo"),
    "ANTIG_VIEJO": Par(0.8, S, "Riesgo de despido con 5 o más años de antigüedad"),
    "ASCENSO": Par([0.10, 0.08, 0.05, 0.03, 0.0], R, "ADP 2019 y Baker-Gibbs-Holmstrom: 10% bajando a 2,5% anual según nivel"),
    "ASC_ALZA": Par(0.08, R, "Alza al ascender: 5 a 10 puntos (ADP 2019)"),
    "ASC_HORAS": Par(1.3, S, "Trabajar 55 horas sube la probabilidad de ascenso (correlación, no causa)"),
    "ASC_POSTGRADO": Par(1.2, S, "Un magíster sube la probabilidad de ascenso"),
    "ASC_A_JEFATURA": Par(0.5, S, "Al llegar a jefatura, probabilidad de pasar a una ocupación directiva"),
    "AUMENTO_OK": Par({"h": 0.27, "m": 0.20}, R, "Artz, Goodall y Oswald 2018 (Australia): éxito entre quienes piden"),
    "AUMENTO_ALZA": Par(0.06, S, "Tamaño del aumento cuando resulta (sin número defendible)"),
    "CICATRIZ": Par(0.12, R, "Pérdida de sueldo al reemplearse tras un despido; anclada en Couch y Placzek 2010 (15% a 6 años)"),
    "CICATRIZ_ANUAL": Par(0.05, S, "Pérdida extra por cada año adicional sin trabajo"),
    "CICATRIZ_DECAE": Par(0.7, S, "Fracción de la cicatriz que queda cada año"),
    "DURACION_DEP": Par(0.75, R, "Encontrar empleo tras un año cesante; Kroft et al. 2013: respuesta baja de 7% a 4%"),
    "HUECO_VOLUNTARIO": Par(0.7, R, "Encontrar empleo tras una pausa elegida; Weisshaar 2018: 5% contra 9% tras despido"),
    "BAJA_PRETENSION": Par((1.3, 0.90), S, "Bajar pretensiones: encuentras 30% más rápido, con 10% menos sueldo"),
    "SEGURO": Par(0.126, D, "CEP 2026: el seguro de cesantía compensa 12,6% del ingreso perdido"),
    "CAMBIA_OCUP_DESC": Par(0.5, S, "Descuento al cambio de ocupación de JobHop (el calce de títulos mete ruido)"),
    "OCUP_REL": Par(0.3, S, "Cuánto del sueldo relativo del grupo ocupacional de destino se traspasa al cambiar"),
    "TAM_MEZCLA": Par({"estado": 0.12, "grande": 0.35, "pyme": 0.52, "startup": 0.01}, R, "ESI 2025: empleador de quien cambia de trabajo"),
    "TAM_SE_QUEDA": Par(0.3, S, "Probabilidad de quedarse en el mismo tipo de empleador al cambiar"),
    # --- ingresos
    "REAJUSTE": Par((0.0173, 0.0136), D, "INE, índice de remuneraciones real: media y desviación de 10 años"),
    "DRIFT_DESCUENTO": Par(0.012, S, "Se descuenta del perfil ESI lo que ya aportan ascensos y cambios"),
    "SHOCK_P": Par(0.08, S, "Probabilidad anual de un golpe persistente al sueldo"),
    "SHOCK_SD": Par(0.10, S, "Tamaño del golpe persistente (log)"),
    "RUIDO": Par(0.04, S, "Variación transitoria del ingreso del año (log)"),
    # --- IA por ocupación
    "IA_BRECHA": Par(0.19, D, "Brynjolfsson, Chandar y Chen: empleo de 22 a 25 años 19% menor en ocupaciones expuestas"),
    "IA_PESO_OFERTA": Par([1.0, 0.5, 0.2, 0.1, 0.1], S, "Cuánto de la brecha afecta las ofertas según nivel (junior a gerencia)"),
    "IA_PESO_DESPIDO": Par([1.0, 0.6, 0.35, 0.2, 0.2], S, "Cuánto de la brecha afecta el despido según nivel"),
    "IA_ESCENARIOS": Par({"lenta": (2036, 1.5), "base": (2032, 2.5), "rapida": (2029, 4.0)}, S, "Año medio de adopción y cuántas veces crece la brecha de hoy"),
    # --- habilidades transferibles
    "RECONV_BASE": Par(0.25, S, "Probabilidad de lograr el cambio de ocupación con afinidad cero"),
    "RECONV_AFIN": Par(0.60, S, "Cuánto sube esa probabilidad con afinidad máxima"),
    "RECONV_DIRECTIVO": Par([0.15, 0.4, 0.8, 1.0, 1.0], S, "Si el destino es un cargo directivo, la probabilidad se multiplica según tu nivel (junior a gerencia)"),
    "RECONV_PEN": Par(0.20, S, "Castigo de sueldo (log) por llegar a una ocupación sin afinidad"),
    "RECONV_REL": Par(0.5, S, "Cuánto del sueldo relativo del destino se traspasa al reconvertirse"),
    "RECONV_COSTO": Par(2_500_000, S, "Costo de formación para reconvertirse (cursos, bootcamp)"),
    # --- estudios
    "MAG_PREMIO": Par(0.07, R, "DIPRES 2026: prima de USD 150 mensuales al séptimo año entre becarios; convertida a 7%"),
    "MAG_PREMIO_SD": Par(0.07, S, "El premio del magíster varía entre personas; una evaluación DIPRES de 2024 no halló retornos consistentes"),
    "MAG_ARANCEL": Par(4_500_000, S, "Arancel anual de un magíster (2 años)"),
    # --- emprender
    "EMP_MEDIANA": Par(0.65, D, "Hamilton 2000: la ganancia mediana es 35% menor que la de un empleado comparable"),
    "EMP_SD_Q": Par(0.7, S, "Dispersión persistente entre emprendimientos (cola larga)"),
    "EMP_SD_T": Par(0.4, S, "Variación de un año a otro del mismo emprendimiento"),
    "EMP_RAMPA": Par(0.5, S, "El primer año se gana la mitad"),
    "EMP_SALIDA_12": Par(0.31, R, "Manso 2016: 52% de los episodios termina en 2 años"),
    "EMP_SALIDA_3": Par(0.15, R, "Supervivencia de empresas: 80% al año y 43% a cinco años (fuente secundaria)"),
    "EMP_CAPITAL": Par(3_000_000, S, "Capital inicial para emprender"),
    "EMP_ENTRADA_BASE": Par(0.0113, D, "Caliendo, Fossen y Kritikos 2014 (Alemania): entrada anual a ser independiente"),
    # --- finanzas
    "INTERES_AHORRO": Par(0.02, S, "Retorno real anual de los ahorros"),
    "INTERES_DEUDA": Par(0.18, S, "Costo real anual de la deuda de consumo"),
    "HABITO": Par(0.6, S, "Cuánto del gasto del año pasado se mantiene"),
    "AJUSTE_CRISIS": Par(0.85, S, "Recorte del gasto en un año sin trabajo"),
    "COSTO_HIJO": Par(300_000, S, "Gasto mensual adicional por hijo"),
    "AHORRO_INICIAL_MESES": Par(3, S, "Si el perfil no trae ahorros: meses de sueldo que se asumen"),
    # --- familia
    "UNION": Par((0.08, 0.04), R, "Formar pareja: 8% anual entre 20 y 35 años, 4% después (CASEN, CEP; por confirmar)"),
    "SEPARACION": Par(0.03, S, "Separación anual entre quienes tienen pareja (divorcio 1,6% entre casados)"),
    "HIJO_PAREJA": Par((1.6, 0.3), S, "Reparto de la fecundidad INE entre quienes tienen pareja y quienes no"),
    "HIJO_BUSCADO": Par((0.75, 0.45), S, "Probabilidad de tener un hijo en el año si se busca (hasta 37 años, después)"),
    "HIJO_SALE": Par({"m": 0.173, "h": 0.05}, D, "EPS 2024: deja de trabajar en los 12 meses siguientes"),
    "HIJO_PENAL_MUJER": Par(0.21, R, "COES 2024: ingreso de las madres -35% a 20 meses; descontando las que salen"),
    # --- bienestar
    "ENERGIA_HORA": Par(0.9, S, "Energía que cuesta cada hora semanal sobre 44"),
    "ENERGIA_REVERSION": Par(0.25, S, "Velocidad con que la energía vuelve a su base de 70"),
    "CUIDADO": Par({"m": 10.0, "h": 3.6}, R, "ENUT 2023: 5,0 y 1,8 horas diarias extra por hijo de 0 a 4; la escala es supuesto"),
    "BURNOUT": Par((35.0, 0.25), S, "Bajo 35 de energía, 25% anual de licencia por agotamiento"),
    "LICENCIA_RECHAZO": Par(0.20, R, "SUSESO 2024: rechazo de licencias de salud mental, 11,5% Fonasa y 27,9% isapres"),
    "ANIMO_CESANTIA": Par(-3.7, D, "ELSOC 2016-2022, efectos fijos: satisfacción con la vida al quedar cesante"),
    "ANIMO_REEMPLEO": Par(6.0, D, "ELSOC: al volver a trabajar"),
    "ANIMO_PAREJA": Par(2.4, D, "ELSOC: al formar pareja"),
    "ANIMO_SEPARACION": Par(-4.0, D, "ELSOC: al separarse (-0,09 a -0,16 en escala 1 a 5)"),
    "ANIMO_OTROS": Par({"ascenso": 3.0, "aumento": 2.0, "aumento_no": -1.5, "burnout": -10.0, "despido": -3.0,
                        "sabatico": 6.0, "titulo": 3.0, "hijo": 3.0, "hijo_chico": -1.5, "deuda": -5.0, "cierre": -4.0}, S,
                       "Efectos en el ánimo sin magnitud medida en Chile; el signo sigue a Clark y Georgellis"),
    "ANIMO_INGRESO": Par(4.0, S, "Puntos de ánimo por cada 100% de aumento del ingreso"),
    "SOCIAL_HORA": Par(0.994, D, "ENUT 2023: -0,6% de tiempo con tu gente por hora semanal sobre 45"),
    # --- red de contactos
    "RED_ELAST": Par(0.25, S, "Efecto de los contactos en ofertas y búsqueda (Rajkumar et al. 2022 solo da la dirección)"),
    "RED_REF": Par(30, S, "Contactos de una persona promedio"),
    "RED_GANA": Par({"anual": 2, "cambio": 8, "titulo": 12, "emprende": 6}, S, "Contactos nuevos por año, por cambio de trabajo, por magíster y por año emprendiendo"),
    "RED_PIERDE": Par(0.10, S, "Contactos que se enfrían por año sin trabajar"),
    # --- personalidad (multiplicadores exp(beta * z))
    "B_DESP_C": Par(-0.19, S, "Responsabilidad y despido"),
    "B_ASC_AMB": Par(0.15, S, "Ambición y ascenso"),
    "B_AUM_A": Par(-0.25, S, "Amabilidad y éxito al pedir aumento (Mueller y Plug 2006 da la dirección)"),
    "B_EMP_SALIDA_A": Par(0.105, D, "Caliendo et al. 2014: amabilidad y salida del emprendimiento, +11% por DE"),
    "B_BURNOUT_N": Par(0.5, S, "Neuroticismo y desgaste (Swider y Zimmerman 2010 da el orden)"),
    # --- atributos del gemelo (habilidades, reputación, salud) y acciones livianas
    "ATRIBUTOS": Par({
        "hab_trabajo": 2.0, "hab_curso": 8.0, "hab_estudio": 6.0, "hab_cambio": 3.0, "hab_olvido": 2.0,
        "hab_oferta": 0.006, "hab_ascenso": 0.006, "hab_ia": 0.4,
        "rep_cambio": 0.7, "rep_anual": 2.0, "rep_horas": 5.0, "rep_ascenso": 8.0, "rep_aumento": 3.0, "rep_red": 2.0,
        "rep_despido": 8.0, "rep_burnout": 4.0, "rep_riesgo": 0.005, "rep_aumento_p": 0.008,
        "salud_edad": 0.6, "salud_horas": 4.0, "salud_agotada": 2.0, "salud_cuidarte": 6.0, "salud_descanso": 2.0, "salud_burnout": 5.0,
        "salud_umbral": 45.0, "salud_p": 0.15, "energia_salud": 0.3,
    }, S, "Cómo suben y bajan habilidades, reputación y salud, y cuánto pesan en ofertas, ascensos, despido y energía. Solo la dirección tiene respaldo (OMS/OIT 2021 para jornadas largas y salud)"),
    "ACCIONES": Par({
        "curso_costo": 600_000.0, "curso_energia": 5.0, "red_contactos": 12.0, "red_energia": 3.0,
        "cuidarte_costo": 400_000.0, "cuidarte_energia": 8.0, "gente_social": 12.0, "gente_energia": 4.0, "gente_animo": 3.0, "gente_ascenso": 0.85,
        "pituto_ingreso": 0.12, "pituto_cesante": 0.25, "pituto_energia": 9.0, "pituto_contactos": 4.0, "pituto_social": 8.0,
    }, S, "Costo y efecto de las acciones livianas: capacitarte, hacer redes, cuidarte, priorizar a tu gente y tomar trabajos extra"),
    "CARTAS": Par({"oferta": 0.38, "oferta_alza": (0.06, 0.22), "oferta_startup": 0.05, "oferta_mezcla": {"startup": 0.30, "pyme": 0.15, "grande": 0.45, "estado": 0.10}, "cupo": 0.30, "postular": (0.30, 0.004, 0.05), "postular_nivel": [1.0, 0.9, 0.65, 0.4, 0.0]}, S,
                  "Oportunidades del año: probabilidad de que llegue una oferta con nombre y de que se abra un cupo de ascenso, y cómo se resuelven"),
    "RUBRO_CAMBIA": Par(0.2, S, "Probabilidad de cambiar de rubro al cambiar de empleador"),
    # --- decisiones de los gemelos (logit)
    "GEMELOS_BASE": Par({"buscar_pega": {"18-29": 0.25, "30-44": 0.16, "45-59": 0.12}, "pedir_aumento": 0.15, "trabajar_mas": 0.08,
                         "bajar_ritmo": 0.03, "magister": 0.02, "reconvertir": 0.03, "sabatico": 0.01, "emprender": 0.0113,
                         "volver_empleo": 0.31, "bajar_pretensiones": 0.25,
                         "capacitarte": 0.12, "networking": 0.08, "cuidarte": 0.10, "tu_gente": 0.10, "pituto": 0.06,
                         "aceptar_oferta": 0.45, "postular_ascenso": 0.5}, S,
                        "Frecuencia anual con que la gente toma cada decisión. Dato: buscar pega (EPS), emprender (Caliendo), trabajar más (ESI, 7,8% sobre 50 horas), tener hijo (INE); el resto es supuesto"),
    "GEMELOS_BETA": Par({"ingreso": 2.0, "riesgo": 3.0, "animo": 0.05}, S, "Cuánto pesan en la elección el ingreso esperado, el riesgo de cesantía o deuda y el ánimo"),
    "GEMELOS_RASGOS": Par({"riesgo": {"emprender": 0.6, "sabatico": 0.5, "reconvertir": 0.4, "buscar_pega": 0.2},
                           "ambicion": {"trabajar_mas": 0.5, "magister": 0.5, "pedir_aumento": 0.4, "buscar_pega": 0.3, "emprender": 0.3, "bajar_ritmo": -0.4},
                           "O": {"emprender": 0.117}, "E": {"emprender": 0.052}}, R,
                          "Cómo la personalidad mueve cada decisión. Apertura y extraversión en emprender: Caliendo et al. 2014; el resto es supuesto"),
}


class _P:
    def __getattr__(self, k):
        return PARAMS[k].valor


P = _P()
