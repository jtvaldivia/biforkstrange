"""Arma derivados/modelo_paneles.json con las claves de backend/app/sim/params.py.

Uso: paneles_final.py <eps_out.json de paneles_eps.py> <elsoc_out.json de paneles_elsoc.py> <salida.json>
Todos los números se leen de las salidas de los dos scripts; aquí solo se convierten unidades
(1 punto de s01 o s03 en escala 1-5 = 25 puntos de 0-100) y se elige qué estimación va a cada clave.
"""

import sys, json, math

E = json.load(open(sys.argv[1])); L = json.load(open(sys.argv[2])); OUT = sys.argv[3]
FE, FL = 'EPS 2024 módulo B', 'ELSOC 2016-2022'
SE, SL = 'scripts/modelo/paneles_eps.py', 'scripts/modelo/paneles_elsoc.py'
LT = ['18-29', '30-44', '45-59']


def k(valor, unidad, fuente, script, n, ee, estado, nota):
    return {'valor': valor, 'unidad': unidad, 'fuente': fuente, 'script': script, 'n': n, 'ee_o_ic': ee, 'estado': estado, 'nota': nota}


def x25(c):
    return round(c['coef'] * 25, 2), round((c.get('ee') or c.get('se')) * 25, 2)


J = {}
# ---------------- 1. Mercado laboral ----------------
an = E['antiguedad']['inv']
J['ANTIG_NUEVO'] = k(an['razon_<1_vs_1_4']['valor'], 'multiplicador del riesgo de despido el primer año, sobre el de 1 a 4 años', FE, SE,
                     {'personas': an['n_personas'], 'anios_persona': an['anios_persona'], 'despidos': an['eventos']}, {'ic95': an['razon_<1_vs_1_4']['ic95']}, 'dato',
                     'Asalariados, episodios con inicio observado 2016-2024, Poisson ponderado (factor_XS) con tramo de edad. Contra el promedio de todas las antigüedades: '
                     f"{an['tasas_brutas']['<1']['razon_vs_promedio']}. Chequeo ELSOC (pasar a desocupado al año): {L['chequeo_antiguedad_ELSOC']['razon_<1_vs_1_4']}.")
J['ANTIG_VIEJO'] = k(an['razon_5+_vs_1_4']['valor'], 'multiplicador del riesgo de despido con 5 o más años, sobre el de 1 a 4 años', FE, SE,
                     {'anios_persona_5mas': an['tasas_brutas']['5+']['anios_persona'], 'despidos_5mas': an['tasas_brutas']['5+']['eventos']},
                     {'ic95': an['razon_5+_vs_1_4']['ic95']}, 'dato',
                     'Solo 27 despidos con 5 o más años: la EPS 2024 solo observa el inicio de empleos que partieron desde la entrevista anterior. '
                     f"Chequeo ELSOC con antigüedad completa (m09): {L['chequeo_antiguedad_ELSOC']['razon_5+_vs_1_4']} (IC95 {L['chequeo_antiguedad_ELSOC']['ic95_5+']}).")
sc = E['sector']['inv']
J['MULT_TAM.estado'] = k(sc['mult_publico_vs_media'], 'multiplicador del despido en el sector público sobre la tasa media de asalariados', FE, SE,
                         {'anios_persona_publico': sc['anios_persona_publico'], 'despidos_publico': sc['eventos_publico']}, {'ic95': sc['mult_publico_ic95']}, 'dato',
                         f"Estandarizado por edad. Público contra privado: {sc['razon_publico_vs_privado']['valor']} (IC95 {sc['razon_publico_vs_privado']['ic95']}). "
                         f"Si se cuenta además el fin de contrato (no renovación de contrata o plazo fijo): {E['sector']['invfc']['mult_publico_vs_media']} "
                         f"(IC95 {E['sector']['invfc']['mult_publico_ic95']}).")
da = E['despido_asalariados_por_edad']
J['DESPIDO'] = k({t: da[t]['tasa_inv'] for t in LT}, 'tasa anual de despido (imputable, necesidades de la empresa, cierre, fuerza mayor) entre asalariados', FE, SE,
                 {t: da[t]['anios_persona'] for t in LT}, {'ee': {t: da[t]['ee_inv'] for t in LT}}, 'dato',
                 'El valor actual del motor (0,0529 / 0,0333 / 0,0274) divide por todos los ocupados, incluidos independientes que no pueden ser despedidos. '
                 f"Con fin de contrato: {({t: da[t]['tasa_inv_mas_fin_contrato'] for t in LT})}.")
en = E['encontrar_12m']
J['ENCONTRAR'] = k({t: en[t]['prob_12m'] for t in LT}, 'probabilidad de pasar a un trabajo en los primeros 12 meses de búsqueda', FE, SE,
                   {t: en[t]['n_episodios'] for t in LT}, {t: en[t]['ic95'] for t in LT}, 'dato',
                   'Episodios de búsqueda con inicio observado desde 2016; los episodios de cesantía consecutivos se juntan. Las salidas a inactividad '
                   f"({en['destino_de_las_salidas'].get('inactividad')}) se tratan como censura. El 0,70 / 0,68 / 0,60 del motor contaba como 'encontrar' cualquier término "
                   'del episodio, incluidos el paso a inactividad y el cambio de un episodio de cesantía a otro.')
dc = E['duracion_cesantia']
J['DURACION_DEP'] = k(dc['razon_anio2_vs_anio1']['valor'], 'multiplicador del riesgo de encontrar empleo en el segundo año de búsqueda sobre el primero', FE, SE,
                      {'episodios': dc['n_episodios'], 'salidas_a_empleo': dc['n_salidas_a_empleo']}, {'ic95': dc['razon_anio2_vs_anio1']['ic95']}, 'dato',
                      f"Tasa mensual de encontrar: {dc['tasa_mensual']}. Por edad: {dc['por_edad']}. Mezcla dependencia real de la duración con selección "
                      '(los que encuentran rápido salen primero); el motor no tiene otra fuente de heterogeneidad que la reproduzca, así que el multiplicador observado es el que corresponde.')
bo = E['busqueda_por_origen']
J['HUECO_VOLUNTARIO'] = k(bo['tras_inactividad']['razon_vs_despido'], 'multiplicador del riesgo de encontrar empleo cuando la búsqueda viene de un período de inactividad, sobre la que viene de un despido', FE, SE,
                          {'episodios_tras_inactividad': bo['tras_inactividad']['n_episodios'], 'episodios_tras_despido': bo['despido']['n_episodios']},
                          {'ic95': bo['tras_inactividad']['ic95']}, 'dato',
                          'Inactividad = estudio, cuidado, quehaceres u otra, sin jubilación. Solo 36 búsquedas vienen de una inactividad que siguió a una renuncia '
                          f"(pausa elegida en sentido estricto): {bo['tras_pausa_voluntaria']['razon_vs_despido']} (IC95 {bo['tras_pausa_voluntaria']['ic95']}), sin precisión para usarse. "
                          f"Tras renuncia directa a cesantía: {bo['renuncia']['razon_vs_despido']}; tras fin de contrato: {bo['fin_contrato']['razon_vs_despido']}.")
ie = E['independiente_entrada']
J['EMP_ENTRADA_BASE'] = k(ie['a_indep']['todos'], 'tasa anual de pasar de asalariado a independiente (cuenta propia o empleador)', FE, SE,
                          {'anios_persona_asalariado': ie['anios_persona_asalariado'], 'entradas': ie['a_indep']['n']}, {'ee': ie['a_indep']['ee_todos']}, 'dato',
                          f"Por edad: {({t: ie['a_indep'][t] for t in LT})}. Solo empleador: {ie['a_empleador']['todos']}; independiente con boleta o factura: "
                          f"{ie['a_indep_formal']['todos']}. Además, {ie['desde_cesantia_share_salidas_a_independiente']} de quienes salen de la cesantía a un trabajo entran como independientes.")
isal = E['independiente_salida']
J['EMP_SALIDA_12'] = k(isal['todos']['riesgo_anual_anios_0_2'], 'riesgo anual de cerrar el trabajo independiente en los dos primeros años (forma 1-exp(-h))', FE, SE,
                       {'episodios': isal['todos']['n_episodios']}, {'ic95': isal['ic95_riesgo_0_2']}, 'dato',
                       f"Kaplan-Meier: cierra {isal['todos']['salida_anio1']} al año, {isal['todos']['salida_2_anios']} a dos años y {isal['todos']['salida_5_anios']} a cinco. "
                       f"Empleadores: {isal['empleador']['riesgo_anual_anios_0_2']}; cuenta propia: {isal['cuenta_propia']['riesgo_anual_anios_0_2']}; con boleta o factura: "
                       f"{isal['formal_boleta_o_factura']['riesgo_anual_anios_0_2']}. Por edad al iniciar: {({t: isal['por_edad_al_iniciar'][t]['riesgo_anual_anios_0_2'] for t in LT})}.")
J['EMP_SALIDA_3'] = k(isal['todos']['riesgo_anual_anios_2_5'], 'riesgo anual de cerrar el trabajo independiente entre el año 2 y el 5', FE, SE,
                      {'episodios': isal['todos']['n_episodios']}, {'ic95': isal['ic95_riesgo_2_5']}, 'dato',
                      f"Empleadores: {isal['empleador']['riesgo_anual_anios_2_5']}; cuenta propia: {isal['cuenta_propia']['riesgo_anual_anios_2_5']}.")
sw = E['sueldo_cambio']; rg = sw['regresion_vs_j2j_voluntario']
J['BRECHA_REEMPLEO_VS_CAMBIO'] = k(rg['despido_cesantia']['coef'], 'diferencia en log sueldo: reempleo tras despido y cesantía menos cambio voluntario directo', FE, SE,
                                   {'pares': rg['n'], 'tras_despido': sw['descriptivo']['despido_cesantia']['n'], 'cambio_voluntario': sw['descriptivo']['j2j_voluntario']['n']},
                                   {'ee': rg['despido_cesantia']['ee']}, 'dato',
                                   'Clave nueva, objetivo de calibración: el motor debe reproducir esta diferencia entre CICATRIZ + (premio previo - M_REEMPLEO) y la ganancia media de las ofertas aceptadas. '
                                   'Sueldo líquido mensual promedio de cada empleo (b12), con efectos fijos del año medio de cada empleo porque b12 no dice en pesos de qué año está. '
                                   f"Contra cambios directos no voluntarios (renovaciones, fin de contrato con empleo inmediato): {sw['contraste_despido_menos_j2j_otro']['coef']} "
                                   f"(ee {sw['contraste_despido_menos_j2j_otro']['ee']}). En los cambios voluntarios directos sube el sueldo en {sw['descriptivo']['j2j_voluntario']['share_sube']} "
                                   f"de los casos y queda igual en {sw['descriptivo']['j2j_voluntario']['share_igual']} (en pesos corrientes).")
J['CICATRIZ_ANUAL'] = k(round(-rg['gap_ces_por_anio']['coef'], 4), 'pérdida adicional de log sueldo por cada año sin trabajo antes de reemplearse', FE, SE,
                        {'pares_con_cesantia': sw['descriptivo_toda_reinsercion_desde_cesantia']['n']},
                        {'ic95': [round(-rg['gap_ces_por_anio']['coef'] - 1.96 * rg['gap_ces_por_anio']['ee'], 3), round(-rg['gap_ces_por_anio']['coef'] + 1.96 * rg['gap_ces_por_anio']['ee'], 3)]},
                        'dato', 'Pendiente del cambio de log sueldo sobre los años entre empleos cuando hubo cesantía. No distinguible de cero; el 0,05 del motor queda en el borde superior del intervalo.')
J['CICATRIZ_PAUSA_VS_DESPIDO'] = k(sw['contraste_pausa_menos_despido']['coef'], 'diferencia en log sueldo al volver: tras pausa voluntaria menos tras despido', FE, SE,
                                   {'pausas': sw['descriptivo']['pausa_voluntaria']['n'], 'despidos': sw['descriptivo']['despido_cesantia']['n']},
                                   {'ee': sw['contraste_pausa_menos_despido']['ee']}, 'dato',
                                   'Clave nueva. El motor da a quien vuelve de una pausa la mitad de la cicatriz de un despido (0,5 x CICATRIZ). En la EPS la caída es la misma '
                                   '(diferencia cercana a cero), aunque el intervalo es ancho y no descarta la mitad.')
dr = sw['descriptivo_toda_reinsercion_desde_cesantia']
J['M_SD'] = k(round(dr['de_robusta_iqr'] / math.sqrt(2), 3), 'desviación del premio salarial entre empleadores (log)', FE, SE, {'pares': dr['n']},
              {'de_robusta_del_cambio': dr['de_robusta_iqr'], 'de_simple_del_cambio': dr['de']}, 'derivado',
              'Si el premio del empleo nuevo y el del anterior son independientes con la misma dispersión, el cambio al reemplearse desde la cesantía tiene desviación M_SD x raíz de 2. '
              'Se usa la desviación robusta (rango intercuartil / 1,349) del cambio de log sueldo; el error de recuerdo del sueldo la infla, así que es cota superior.')
pz = E['pausas']
J['GEMELOS_BASE.sabatico'] = k({t: pz['pausa_voluntaria_sin_estudio_ni_cuidado'][t] for t in LT}, 'fracción anual de ocupados que deja su empleo por voluntad propia y pasa a inactividad sin estudiar, cuidar ni por salud', FE, SE,
                               {t: pz['anios_persona_ocupado'][t] for t in LT}, {t: pz['pausa_voluntaria_sin_estudio_ni_cuidado']['ee_' + t] for t in LT}, 'dato',
                               f"Incluye quehaceres del hogar. Todas las pausas tras renuncia o mutuo acuerdo: {({t: pz['pausa_voluntaria'][t] for t in LT})}, de las cuales "
                               f"{pz['tipo_de_inactividad_en_pausas_voluntarias'].get('estudiar')} son para estudiar. "
                               f"Duración: siguen inactivos a los 12 meses {pz['duracion_pausa_voluntaria_KM']['sigue_inactivo_a_meses']['12']} y a los 24 meses "
                               f"{pz['duracion_pausa_voluntaria_KM']['sigue_inactivo_a_meses']['24']}; el motor supone un año.")
cv = E['cambio_voluntario']
J['GEMELOS_BASE.buscar_pega'] = k({t: cv['tasa'][t] for t in LT}, 'fracción anual de ocupados que se cambia de empleador por renuncia o por un mejor trabajo, sin pasar por cesantía', FE, SE,
                                  {'cambios': cv['n']}, {t: cv['tasa']['ee_' + t] for t in LT}, 'dato',
                                  f"Es el resultado (cambio logrado), no la decisión de buscar. El valor actual del motor (0,25 / 0,16 / 0,12) es el total de cambios directos de "
                                  f"cualquier motivo: {({t: cv['tasa_j2j_cualquier_motivo'][t] for t in LT})}.")
J['GEMELOS_BASE.emprender'] = k({t: ie['a_indep'][t] for t in LT}, 'fracción anual de asalariados que pasa a independiente', FE, SE,
                                {'entradas': ie['a_indep']['n']}, {t: ie['a_indep']['ee_' + t] for t in LT}, 'dato', 'Misma estimación que EMP_ENTRADA_BASE, por edad.')
fr = L['frecuencias']['empieza_a_estudiar_y_trabajar_con_titulo']
J['GEMELOS_BASE.magister'] = k(fr['tasa'], 'fracción anual de ocupados con título universitario (25-45 años) que pasa a estudiar y trabajar', FL, SL,
                               {'personas_anio': fr['n'], 'eventos': fr['eventos']}, {'ee': fr['ee']}, 'dato',
                               'ELSOC no pregunta qué se estudia; con título universitario lo más probable es un posgrado o diplomado. 17 eventos.')

# ---------------- 2. Familia ----------------
fa = L['familia']
u, s_ = fa['union']['tramos_motor'], fa['separacion']['tramos_motor']
pe = E['pareja_entre_entrevistas']['eng']
J['UNION'] = k((u['20-35']['anual_persistente']['tasa'], u['36-59']['anual_persistente']['tasa']), 'tasa anual de formar pareja entre quienes no tienen (20-35 años, 36-59)', FL, SL,
               {'20-35': u['20-35']['anual_persistente']['n'], '36-59': u['36-59']['anual_persistente']['n']},
               {'ee': (u['20-35']['anual_persistente']['ee'], u['36-59']['anual_persistente']['ee'])}, 'dato',
               'Pares de olas a un año (2018-19, 2021-22), exigiendo que la nueva pareja siga en la ola siguiente. Sin esa exigencia sale 0,18-0,19, inflado por idas y vueltas '
               f"conviviente-soltero. Versión estricta (mismo estado también la ola anterior): {u['20-35']['anual_estricto']['tasa']} / {u['36-59']['anual_estricto']['tasa']}. "
               f"La EPS (uniones declaradas desde la entrevista anterior) da {pe['20-35']['union_tasa_anual']} / {pe['36-59']['union_tasa_anual']}, demasiado bajo para explicar que "
               f"la fracción con pareja suba de {fa['share_con_pareja_2018']['(17, 24]']} (18-24) a {fa['share_con_pareja_2018']['(29, 34]']} (30-34) en ELSOC 2018; la versión persistente sí lo explica.")
J['SEPARACION'] = k({'20-35': s_['20-35']['anual_persistente']['tasa'], '36-59': s_['36-59']['anual_persistente']['tasa']}, 'tasa anual de quedar sin pareja entre quienes tienen (sin viudez)', FL, SL,
                    {'20-35': s_['20-35']['anual_persistente']['n'], '36-59': s_['36-59']['anual_persistente']['n']},
                    {'ee': {'20-35': s_['20-35']['anual_persistente']['ee'], '36-59': s_['36-59']['anual_persistente']['ee']}}, 'dato',
                    'Incluye el fin de convivencias, no solo divorcios. El motor usa un solo valor; los datos piden dos tramos. '
                    f"Estricta: {s_['20-35']['anual_estricto']['tasa']} / {s_['36-59']['anual_estricto']['tasa']}. EPS (cota inferior, no ve a quien se separó y volvió a emparejarse): "
                    f"{pe['20-35']['separacion_riesgo_anual']} / {pe['36-59']['separacion_riesgo_anual']}.")
hp = E['hijo_segun_pareja']
J['HIJO_PAREJA'] = k((hp['mujeres']['mult_estandarizado_18_39']['con_pareja'], hp['mujeres']['mult_estandarizado_18_39']['sin_pareja']),
                     'multiplicador de la fecundidad por edad del INE según tenga pareja o no (mujeres 18-39)', FE, SE,
                     {'nacimientos_con_pareja': hp['mujeres']['mult_estandarizado_18_39']['nacimientos_con_pareja'], 'nacimientos_sin_pareja': hp['mujeres']['mult_estandarizado_18_39']['nacimientos_sin_pareja']},
                     {'ic95': (hp['mujeres']['ic95_con_pareja'], hp['mujeres']['ic95_sin_pareja'])}, 'dato',
                     'Razón estandarizada por edad: nacimientos observados sobre esperados con la tasa de todas las mujeres de su edad. Pareja medida en la entrevista anterior '
                     '(unos 4-5 años antes de algunos nacimientos), lo que acerca ambos grupos: el primero es cota inferior y el segundo cota superior. '
                     f"Hombres: {hp['hombres']['mult_estandarizado_18_39']['con_pareja']} / {hp['hombres']['mult_estandarizado_18_39']['sin_pareja']}.")

# ---------------- 3. Bienestar ----------------
b = L['bienestar']
v, e_ = x25(b['ingreso']['s01_log_ingreso_personal']['lm13'])
J['ANIMO_INGRESO'] = k(v, 'puntos de ánimo (0-100) por cada unidad de log del ingreso propio', FL, SL,
                       {'obs': b['ingreso']['s01_log_ingreso_personal']['n_obs'], 'personas': b['ingreso']['s01_log_ingreso_personal']['n_personas']}, {'ee': e_}, 'dato',
                       'Efectos fijos de persona y ola, ocupados. Por un aumento de 100% del ingreso son 0,69 x este valor. Con ingreso del hogar: '
                       f"{x25(b['ingreso']['s01_log_ingreso_hogar']['lm29'])[0]}. El motor aplica 4,0 por unidad de log (su comentario dice 'por 100%', pero el código usa log).")
for y, key, uni in [('s01', 'ANIMO_HORAS_55', 'puntos de ánimo (0-100)'), ('s03', 'SALUD_HORAS_55', 'puntos de salud (0-100), nivel')]:
    c = b['horas'][y]['h55mas']; v, e_ = x25(c)
    J[key] = k(v, f'{uni} por trabajar 55 horas o más frente a 40-45', FL, SL, {'obs': b['horas'][y]['n_obs'], 'personas_que_cambian': c['personas_con_cambio']}, {'ee': e_}, 'dato',
               'Clave nueva. Efectos fijos de persona y ola, olas 2016, 2018 y 2021. No distinguible de cero. '
               + ('El motor resta 4 puntos de salud por cada año con 55 horas o más (ATRIBUTOS.salud_horas); ELSOC no muestra diferencia de nivel dentro de la persona.' if y == 's03' else
                  'El motor baja el ánimo con las horas por la vía de la energía (ENERGIA_HORA); ELSOC no lo muestra.'))
c = b['horas']['dep_mod']['h55mas']
dh = b['depresion_por_horas']
J['DEPRESION_INCIDENCIA'] = k({t: dh['incidencia_anual'][t]['incidencia_anual'] for t in dh['incidencia_anual']},
                              'probabilidad anual de pasar a síntomas depresivos moderados o severos (PHQ-9 >= 10) entre ocupados sin ellos, por horas semanales', FL, SL,
                              {t: dh['incidencia_anual'][t]['n'] for t in dh['incidencia_anual']}, {t: dh['incidencia_anual'][t]['ee'] for t in dh['incidencia_anual']}, 'dato',
                              'Clave nueva, propuesta como reemplazo medible de BURNOUT y de la energía. Todos los ocupados: '
                              f"{dh['incidencia_anual_todos_ocupados']['tasa']}. Prevalencia por horas: {({t: dh['prevalencia_ocupados'][t]['prevalencia'] for t in dh['prevalencia_ocupados']})}. "
                              f"Efecto fijo de 55+ horas sobre la probabilidad de PHQ-9 >= 10: {c['coef']} (ee {c['ee']}). Quedar cesante la sube en "
                              f"{b['cesantia_desde_calibracion_paneles']['dep_mod']['coef']} (ee {b['cesantia_desde_calibracion_paneles']['dep_mod']['se']}) y el PHQ-9 en "
                              f"{b['cesantia_desde_calibracion_paneles']['phq9']['coef']} puntos (ee {b['cesantia_desde_calibracion_paneles']['phq9']['se']}).")
v, e_ = x25(b['cambio_empleo']['s01']['nuevo_empleo'])
J['ANIMO_OTROS.cambio_empleo'] = k(v, 'puntos de ánimo (0-100) en el año del cambio de empleo', FL, SL,
                                   {'obs': b['cambio_empleo']['s01']['n_obs'], 'personas_que_cambian': b['cambio_empleo']['s01']['nuevo_empleo']['personas_con_cambio']}, {'ee': e_}, 'dato',
                                   'Efectos fijos; cambio = el trabajo actual empezó este año o el anterior (m09). No distinguible de cero. El motor da +2 al aceptar una oferta.')
v, e_ = x25(b['supervisa_proxy_ascenso']['s01_todos']['supervisa'])
J['ANIMO_OTROS.ascenso'] = k(v, 'puntos de ánimo (0-100) al pasar a tener personas a cargo', FL, SL,
                             {'obs': b['supervisa_proxy_ascenso']['s01_todos']['n_obs'], 'personas_que_cambian': b['supervisa_proxy_ascenso']['s01_todos']['supervisa']['personas_con_cambio']},
                             {'ee': e_}, 'derivado',
                             'ELSOC no pregunta por ascensos; tener personas a cargo (m06 > 0) es el sustituto. Dentro del mismo empleo: '
                             f"{x25(b['supervisa_proxy_ascenso']['s01_mismo_empleo']['supervisa'])[0]} (ee {x25(b['supervisa_proxy_ascenso']['s01_mismo_empleo']['supervisa'])[1]}). "
                             'No distinguible de cero; el motor suma +3 permanente.')
sp = b['salud_por_edad']['pendiente_transversal_por_anio_edad']
J['ATRIBUTOS.salud_edad'] = k(round(-sp['en_0_100'], 2), 'puntos de salud (0-100) que se pierden por año de edad', FL, SL, {'obs': sp['n_obs']}, {'ee': round(sp['ee'] * 25, 3)}, 'dato',
                              'Pendiente de salud autorreportada (s03) sobre la edad, 18-70, con efectos de ola, ponderada; compara personas de distintas edades. '
                              f"El cambio dentro de la misma persona por tramo de edad es { {t: -x['en_0_100'] for t, x in b['salud_por_edad']['cambio_dentro_persona'].items()} }, "
                              'ruidoso y mezclado con el período 2019-2021. El motor resta 0,6 desde los 30.')

# ---------------- 4. Red ----------------
rd = L['red']
J['RED_ELAST'] = k(rd['encontrar_empleo']['cloglog_coef_lred']['coef'], 'elasticidad del riesgo de encontrar empleo respecto del número de conocidos', FL, SL,
                   {'desocupados': rd['encontrar_empleo']['n_desocupados'], 'encuentran': rd['encontrar_empleo']['encuentran']},
                   {'ee': rd['encontrar_empleo']['cloglog_coef_lred']['ee']}, 'dato',
                   'Desocupados en 2016, 2018 o 2021; resultado: ocupados un año después; cloglog con edad, sexo y educación superior. Conocidos medidos con el generador de posiciones '
                   '(13 ocupaciones). No distinguible de cero; el 0,25 del motor queda fuera del intervalo de 95%. Es asociación, no efecto causal. '
                   f"En 2018, {rd['empleo_con_ayuda_de_red_2018']['share_si']} de los ocupados dice que alguien lo ayudó a conseguir su trabajo.")
J['RED_REF'] = k(rd['descriptivo']['red_vol_media'], 'conocidos de una persona promedio en el generador de posiciones de ELSOC', FL, SL,
                 {'obs': rd['fe_lred']['n_obs']}, None, 'derivado',
                 f"Mediana {rd['descriptivo']['red_vol_mediana']}. Suma de conocidos en 13 ocupaciones con el punto medio de cada tramo; mide una parte de la red, no toda. "
                 'Solo sirve como referencia si el motor adopta esta unidad para los contactos.')
c = rd['fe_lred']['nuevo_empleo0']
J['RED_GANA.cambio'] = k(round(c['coef'] * rd['descriptivo']['red_vol_media'], 1), 'contactos nuevos por cambiar de trabajo (unidad: conocidos del generador de posiciones)', FL, SL,
                         {'obs': rd['fe_lred']['n_obs'], 'personas_que_cambian': c['personas_con_cambio']},
                         {'ic95': [round((c['coef'] - 1.96 * c['ee']) * rd['descriptivo']['red_vol_media'], 1), round((c['coef'] + 1.96 * c['ee']) * rd['descriptivo']['red_vol_media'], 1)]},
                         'derivado', f"Efecto fijo sobre log(1+conocidos): {c['coef']} (ee {c['ee']}), multiplicado por RED_REF. No distinguible de cero; el motor suma 8.")
c = rd['fe_lred']['desocupado']
J['RED_PIERDE'] = k(round(-c['coef'], 3), 'fracción de los contactos que falta mientras se está desocupado (nivel, no por año)', FL, SL,
                    {'obs': rd['fe_lred']['n_obs'], 'personas_que_cambian': c['personas_con_cambio']},
                    {'ic95': [round(-c['coef'] - 1.96 * c['ee'], 3), round(-c['coef'] + 1.96 * c['ee'], 3)]}, 'derivado',
                    'Efecto fijo de estar desocupado sobre log(1+conocidos). El motor resta 10% por cada año de cesantía después del primero; ELSOC no permite separar por duración.')

J['sin_dato'] = {
    'CICATRIZ': 'Requiere el sueldo que habría tenido quien fue despedido si no lo despiden. La EPS trae un solo sueldo por empleo (b12, promedio, sin año de referencia) y no sigue '
                'el sueldo de quienes se quedan; en ELSOC hay 30 personas que cambian de empleo con desempleo entremedio (coeficiente -0,10, ee 0,14). Queda la brecha conjunta BRECHA_REEMPLEO_VS_CAMBIO.',
    'M_REEMPLEO': 'Mismo motivo que CICATRIZ: con un sueldo por empleo solo se identifica la suma de premio de reempleo y cicatriz.',
    'CICATRIZ_DECAE': 'Hace falta el sueldo año a año después del reempleo; b12 es un promedio por empleo.',
    'ENERGIA_HORA, ENERGIA_REVERSION, BURNOUT': 'Ninguna encuesta mide energía ni licencias por agotamiento. Se propone reemplazarlos por DEPRESION_INCIDENCIA (PHQ-9 en ELSOC).',
    'RED_GANA.anual': 'Dentro de la persona los conocidos suben 11% a 15% por año en todas las edades (2016-2021), y entre edades el promedio no cambia (30 a 35): '
                      'el aumento es del período, no de la edad. No se puede separar.',
    'RED_GANA.titulo, RED_GANA.emprende': 'No estimado. ELSOC mide la red solo en 2016, 2018 y 2021, no registra el inicio de un emprendimiento y el posgrado declarado (m01) cambia de una ola a otra con mucho ruido.',
    'UMBRAL_PASIVO, UMBRAL_ACTIVO, OFERTA_FACTOR, BUSCA_MULT': 'Ni la EPS ni ELSOC registran ofertas recibidas o rechazadas ni búsqueda mientras se trabaja.',
    'GEMELOS_BASE (pedir_aumento, trabajar_mas, bajar_ritmo, reconvertir, capacitarte, networking, cuidarte, tu_gente, pituto, aceptar_oferta, postular_ascenso, bajar_pretensiones, volver_empleo)':
        'No hay variable en la EPS 2024 ni en ELSOC que registre estas decisiones.',
    'ASCENSO, ASC_ALZA': 'ELSOC no pregunta por ascensos ni la EPS por cambios de cargo dentro del mismo empleo.',
}
json.dump(J, open(OUT, 'w'), ensure_ascii=False, indent=1)
print(len([x for x in J if x != 'sin_dato']), 'claves con dato;', len(J['sin_dato']), 'grupos sin dato')
