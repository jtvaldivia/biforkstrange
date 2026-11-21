import sys, json
E=json.load(open(sys.argv[1])); P=json.load(open(sys.argv[2])); OUT=sys.argv[3]
J={
 "meta":{
  "generado":"2026-11-21",
  "descripcion":"Parametros de calibracion para Gemelo Laboral calculados con microdatos de panel chilenos (ELSOC 2016-2022 y EPS VIII ronda 2023-2024). Todo calculado desde los archivos locales; nada copiado de publicaciones.",
  "scripts":"scratchpad/calib_scripts/elsoc_main.py y eps_main.py (temporales de la sesion)",
  "fuentes":{
   "ELSOC":"ELSOC_Long_2016_2022_v1.00.RData (COES, CC0). 18.035 obs, 4.447 personas, olas 2016, 2017, 2018, 2019, 2021, 2022.",
   "EPS":"Bases_de_datos_EPS_VIII_Ronda_2024.7z: BBDD_VIVOS/MODULO_B_HISTORIA_LABORAL.dta (44.494 episodios, 15.788 personas), MODULO_A_ENTREVISTADO.dta (a8 sexo, a9 edad), MODULO_I_HIJOS.dta (i21_anio, i21_mes), FACT_EXP/Factor_XS_EPS_2023.dta (factor_XS)."},
  "variables_ELSOC":{
   "s01":"Satisfaccion con la vida, 1 Totalmente insatisfecho a 5 Totalmente satisfecho",
   "phq9":"Suma de s11_01..s11_09 (PHQ-9, 'Frecuencia: ...'), cada item recodificado 1-5 -> 0-4; rango 0-36. dep_mod = phq9>=10",
   "s03":"Salud subjetiva, 1 Mala a 5 Excelente",
   "m02":"Actividad principal: 1-3 ocupado (completa, parcial, estudia y trabaja); 6 desempleado buscando; 4,5,7,8,9 inactivo",
   "m36":"Estado civil: 1 casado, 2 conviviente sin AUC, 3 con AUC = con pareja; 4 soltero, 5 viudo, 6 anulado, 7 divorciado, 8 separado, 9 otro = sin pareja. No preguntado en 2017",
   "m12":"Horas semanales de trabajo (2016, 2018, 2021)",
   "s12":"Frecuencia hablar problemas con familia o amigos, 1 Nunca a 5 Siempre (2016, 2018, 2021)",
   "t06_08":"Satisfaccion con proximidad a familiares y/o amigos cercanos, 1-5",
   "s13_06":"Estresores: Despidos del trabajo (si/no), 2016, 2018, 2022",
   "ponderador02":"Ponderador corte transversal ajustado por poblacion y sexo"},
  "variables_EPS":{
   "b2a_so":"Situacion ocupacional final del episodio: 1 Trabajando, 2 Cesante, 3 Buscando trabajo por 1a vez, 4 Inactivo",
   "b2_a_inicio_anio/mes, b2_a_termino_anio/mes":"Fechas del episodio (mes faltante -> junio)",
   "b22":"Motivo del termino de la relacion laboral (si b22=12 'Otra' se usa b22_e_cod recodificada)",
   "a8, a9":"Sexo y edad del entrevistado; nacimiento aprox. = fecha de entrevista (ultimo mes del historial) - edad",
   "i21_anio, i21_mes":"Fecha de nacimiento de hijos nacidos despues de la ultima entrevista",
   "factor_XS":"Factor de expansion cross-section EPS 2023, usado para ponderar exposicion y eventos"}
 },
 "1_bienestar_ELSOC":{
  "escala_referencia":E["sd"],
  "efecto_within_estado":E["fe_estado"],
  "nota_within":"MCO con efectos fijos de persona y de ola (within), sin ponderar, SE agrupados por persona. Edades 18-65. 'desocupado' e 'inactivo' contra ocupado; 'pareja' contra sin pareja (sin ola 2017). personas_con_cambio = personas cuyo estado cambia en el panel (identifican el efecto).",
  "event_study":E["event_study"],
  "hijo":E["hijo"]},
 "2_transiciones_ELSOC":E["transiciones"],
 "2b_estresor_despido_ELSOC":E["estresor_despido"],
 "3_historia_laboral_EPS":P,
 "4_horas_y_familia_ELSOC":dict(E["horas_familia"],nota="Ocupados 18-65 con horas 1-100. Efecto fijo de persona y ola; coeficiente por +10 horas semanales. No hay en ELSOC ni en la EPS una pregunta de frecuencia de contacto o visitas a los padres; s12 es el mejor sustituto disponible."),
 "parametros_sugeridos_juego":{
  "DESPIDO_por_edad_anual":{"fuente":"EPS 2016-2024, tasa_involuntario (despido + cierre + fuerza mayor)","18-29":P["empleo_2016_2024"]["18-29"]["tasa_involuntario"],"30-44":P["empleo_2016_2024"]["30-44"]["tasa_involuntario"],"45-59":P["empleo_2016_2024"]["45-59"]["tasa_involuntario"],
     "mas_fin_de_contrato":{k:round(P["empleo_2016_2024"][k]["tasa_involuntario"]+P["empleo_2016_2024"][k]["tasa_fin_contrato"],4) for k in ["18-29","30-44","45-59"]}},
  "RENUNCIA_por_edad_anual":{k:P["empleo_2016_2024"][k]["tasa_voluntario"] for k in ["18-29","30-44","45-59"]},
  "CAMBIO_EMPLEADOR_por_edad_anual":{k:P["empleo_2016_2024"][k]["tasa_cambio_empleador_j2j"] for k in ["18-29","30-44","45-59"]},
  "MESES_CESANTIA":{"mediana_KM_meses":{k:P["cesantia"][k]["mediana_KM_meses"] for k in ["18-29","30-44","45-59","todos"]},
     "media_exponencial_equivalente_meses":{"18-29":9.9,"30-44":10.5,"45-59":13.2,"todos":11.0},
     "nota":"media exponencial que reproduce la sobrevida KM a 12 meses: -12/ln(S12). pEncontrar anual = 1 - S12 = 0,70 / 0,68 / 0,60."},
  "ANIMO_cesantia":{"s01_coef":E["fe_estado"]["s01"]["cesante_vs_ocupado"]["desocupado"],"en_puntos_0_100":-3.7,"conversion":"1 punto de s01 (1-5) = 25 puntos de animo (0-100)"},
  "ANIMO_reempleo":{"s01_k0":E["event_study"]["volver_a_trabajar"]["s01"]["ev_0"],"en_puntos_0_100":6.0},
  "ANIMO_pareja":{"s01_coef":E["fe_estado"]["s01"]["con_pareja"]["pareja"],"en_puntos_0_100":2.4},
  "HIJO_SALE_MUJER":P["hijo"]["mujeres"]["prop_no_ocupado_12m_despues"],
  "HIJO_SALE_HOMBRE":P["hijo"]["hombres"]["prop_no_ocupado_12m_despues"]}
}
json.dump(J,open(OUT,'w'),ensure_ascii=False,indent=1)
print('ok', list(J))
