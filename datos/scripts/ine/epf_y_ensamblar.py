# EPF IX (tabulados) + ensamblado de calibracion_ine.json. Uso: epf_y_ensamblar.py <carpeta_ine> <salida.json>
import sys, json, re, openpyxl
D = sys.argv[1].rstrip("/") + "/"
wb = openpyxl.load_workbook(D + "epf/ix_tab.xlsx", read_only=True, data_only=True)
R = [list(r) for r in wb["CUADROS 3A - 3E"].iter_rows(max_row=13, values_only=True)]
q = {}
for r in R:
    r = [c for c in r if c is not None]  # columnas: 0 grupo, 1 hogares, 2 %, 3 personas/hogar, 4 personas, 5 %, 6 gasto hogar, 7 gasto pc, 8 %, 9 ingreso hogar, 10 ingreso pc, 11 %
    if r and r[0] in ("Total", "I", "II", "III", "IV", "V"):
        r = [r[0], r[1], r[3], r[3], r[4], r[6], r[7], None, r[9], r[10]]
        q[r[0]] = {"personas_por_hogar": round(r[2], 2), "gasto_hogar": round(r[5]), "gasto_per_capita": round(r[6]), "ingreso_disponible_hogar": round(r[8]),
                   "ingreso_disponible_per_capita": round(r[9]), "ingreso_menos_gasto_hogar": round(r[8] - r[5]), "tasa_ahorro_aparente": round((r[8] - r[5]) / r[8], 3)}
A = [list(r) for r in wb["CUADRO 7A"].iter_rows(values_only=True)]
arr = next(r for r in A if str(r[0]).startswith("04.1.1.01.01"))
arr_q = dict(zip(["Total", "I", "II", "III", "IV", "V"], [round(x) for x in arr[2:8]]))
epf = {"fuente": "INE, IX Encuesta de Presupuestos Familiares (oct 2021 - sep 2022), Tabulados principales resultados (estimaciones), cuadros 3A y 7A, total capitales regionales, excluye arriendo imputado; pesos corrientes del periodo",
       "url": "http://www.ine.gob.cl/docs/default-source/encuesta-de-presupuestos-familiares/cuadros-estadisticos/ix-epf/tabulados-principales-resultados-ix-epf-(estimaciones).xlsx",
       "quintiles_ingreso_disponible_hogar": q,
       "arriendo_vivienda_principal_promedio_todos_los_hogares": arr_q,
       "nota": "el arriendo es promedio sobre todos los hogares (incluye propietarios con 0), no el arriendo de quien arrienda. El dividendo hipotecario no es gasto de consumo en la EPF y no está en los tabulados. Gasto > ingreso en quintiles I a IV es habitual en la EPF (subdeclaración de ingresos, desahorro, crédito). Para llevar a 2026 hay que reajustar por IPC"}
J = lambda f: json.load(open(D + f))
enut, vit, ene, ir, flu = J("enut_res.json"), J("vitales_res.json"), J("ene_res.json"), J("ir_res.json"), J("flujos_res.json")
vit["fecundidad"]["tef_por_mil_2024p_publicada"] = {k: v for k, v in vit["fecundidad"]["tef_por_mil_2024p_publicada"].items() if v is not None}
reg = enut["b_regresion_wls"]["resultados"]
sec = {r["glosa"]: r["multiplicador_salida_vs_total"] for r in flu["por_sector"]}
tam = {r["glosa"]: r["multiplicador_salida_vs_total"] for r in flu["por_tamano"]}
mapa = {"Minería": "Explotación de minas y canteras", "Finanzas y seguros": "Actividades financieras y de seguros", "Información y comunicaciones": "Información y comunicaciones",
        "Comercio": "Comercio al por mayor y al por menor", "Salud": "Actividades de atención de la salud humana y de asistencia social", "Enseñanza": "Enseñanza",
        "Servicios profesionales": "Actividades profesionales, científicas y técnicas", "Construcción": "Construcción", "Industria manufacturera": "Industrias manufactureras",
        "Transporte": "Transporte y almacenamiento", "Agricultura y pesca": "Agricultura, ganadería, silvicultura y pesca", "Hoteles y restaurantes": "Actividades de alojamiento y de servicio de comidas",
        "Artes y entretención": "Actividades artísticas, de entretenimiento y recreativas", "Servicios administrativos": "Actividades de servicios administrativos y de apoyo", "Otros servicios": "Otras actividades de servicios"}
m25 = vit["mortalidad"]["2025"]
par = {
 "TIEMPO_SOCIAL_POR_HORA_TRABAJO": {"valor": round(1 + reg["t_vsyo_csar_dt"]["cambio_pct_por_hora_extra"] / 100, 4), "uso": "multiplicar el tiempo de convivencia social por este factor por cada hora semanal sobre 45; ENUT 2023 da -0,6% por hora (-0,8 min/día)"},
 "JUNTARSE_FIN_DE_SEMANA_POR_HORA": {"valor": round(1 + reg["p_juntarse_fin_semana"]["cambio_pct_por_hora_extra"] / 100, 4), "uso": "alternativa chilena a VISITAS_POR_HORA (0,935 del motor, Corea): la probabilidad de juntarse con familia o amigos no convivientes el fin de semana cae 0,48% por hora semanal extra"},
 "OCIO_POR_TRAMO_HORAS_h_dia": {r["tramo_horas_semana"]: r["vida_social_ocio_h"] for r in enut["b_ocio_segun_horas_ocupados_18_50"]},
 "CUIDADOS_EXTRA_POR_HIJO_0_4_h_dia": {"mujer": round([t for t in enut["a_no_remunerado_18_50"]["tabla"] if t["sexo"] == "mujer" and t["hijos"] == "con_hijo_0_4"][0]["no_remunerado_total_h"] - [t for t in enut["a_no_remunerado_18_50"]["tabla"] if t["sexo"] == "mujer" and t["hijos"] == "sin_hijos_menores_15"][0]["no_remunerado_total_h"], 2),
                                       "hombre": round([t for t in enut["a_no_remunerado_18_50"]["tabla"] if t["sexo"] == "hombre" and t["hijos"] == "con_hijo_0_4"][0]["no_remunerado_total_h"] - [t for t in enut["a_no_remunerado_18_50"]["tabla"] if t["sexo"] == "hombre" and t["hijos"] == "sin_hijos_menores_15"][0]["no_remunerado_total_h"], 2)},
 "MORT_por_sexo_2025": {"hombre": [m25["Hombre"]["gompertz_50_95"]["a"], m25["Hombre"]["gompertz_50_95"]["b"]], "mujer": [m25["Mujer"]["gompertz_50_95"]["a"], m25["Mujer"]["gompertz_50_95"]["b"]],
                        "promedio": [m25["promedio_simple_hombre_mujer"]["gompertz_50_95"]["a"], m25["promedio_simple_hombre_mujer"]["gompertz_50_95"]["b"]],
                        "uso": "reemplaza K.MORT = [-10.2, 0.094], que sobreestima la mortalidad entre 1,5 y 1,7 veces a los 60-90 años"},
 "EDAD_MADRE": {"media_al_nacer_cualquier_hijo": vit["fecundidad"]["edad_media_de_la_madre_2023"], "media_primer_hijo": vit["fecundidad"]["edad_media_al_primer_hijo_2023_cruda"], "uso": "la diferencia de edad mamá-jugador puede sortearse centrada en 30 (rango 24-34 del motor queda bien centrado)"},
 "P_HIJO_ANUAL_MUJER_por_edad": {k.replace(" años", ""): round(v / 1000, 4) for k, v in vit["fecundidad"]["tef_por_mil_2024p_publicada"].items()},
 "P_PRIMER_HIJO_ANUAL_MUJER_por_edad_2023": {k: round(v / 1000, 4) for k, v in vit["fecundidad"]["tasa_primeros_hijos_por_mil_mujeres_2023"].items()},
 "P_CASARSE_ANUAL_por_edad": {sx: {k: round(v["por_mil"] / 1000, 4) for k, v in d.items() if isinstance(v, dict)} for sx, d in vit["nupcialidad"]["matrimonios_por_mil_personas_por_edad"].items()},
 "P_AUC_ANUAL_por_edad": {k: round(v / 1000, 4) for k, v in vit["nupcialidad"]["auc_por_mil_personas_por_edad_ambos_sexos"].items()},
 "REAJUSTE_REAL_ANUAL": {"valor": round(ir["tasa_compuesta_10_anios_pct"] / 100, 4), "desv": round(ir["desv_estandar_10_anios_pct"] / 100, 4), "uso": "crecimiento real del sueldo de toda la economía, aparte del ascenso y la experiencia"},
 "MULT_SALIDA_POR_RUBRO": {k: sec.get(v) for k, v in mapa.items()},
 "MULT_SALIDA_POR_TAMANO": tam,
 "DESOCUPACION_por_edad": {r["tramo"]: r["tasa_desocupacion"] for r in ene["desocupacion_por_sexo_y_edad"] if r["sexo"] == "ambos"},
 "INFORMALIDAD_por_edad": {r["tramo"]: r["tasa_informalidad"] for r in ene["ocupados_por_sexo_y_edad"] if r["sexo"] == "ambos"},
 "MESES_BUSQUEDA_EN_CURSO": {"mediana": ene["duracion_busqueda_desocupados"]["tabla"][-1]["mediana_meses"], "media": ene["duracion_busqueda_desocupados"]["tabla"][-1]["media_meses"]},
 "TASA_AHORRO_por_quintil": {k: v["tasa_ahorro_aparente"] for k, v in q.items()},
}
out = {"meta": {"generado": "2026-11-21", "autor": "agente de datos INE", "scripts": "datos_laborales/scripts/ine/", "descargas_en": "scratchpad/ine (no versionadas)"},
       "1_uso_del_tiempo_ENUT_2023": enut, "2_fecundidad_2023_2024": vit["fecundidad"], "2b_nupcialidad_2023": vit["nupcialidad"], "fuente_poblacion": vit["fuente_poblacion"],
       "3_mortalidad": vit["mortalidad"], "4_ENE_OND_2025": ene, "5_EPF_IX": epf, "7_IR_real": ir, "8_flujos_laborales": flu,
       "6_demografia_empresas": {"estado": "no calculado", "motivo": "no encontré en el sitio del INE tabulados de nacimiento, cierre y supervivencia de empresas por cohorte; los flujos por continuidad de empresa (sección 8) solo separan empresas continuas y no continuas"},
       "parametros_sugeridos_juego": par}
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print(json.dumps(par, ensure_ascii=False))
