"""Arma derivados/modelo_beneficios.json a partir de los detalles de beneficios_esi.py y beneficios_elsoc.py.

Uso:
  python -I beneficios_ensamblar.py <modelo_beneficios_esi_detalle.json> <modelo_beneficios_elsoc_detalle.json> <salida.json>

"dist" es la distribución para sortear el resultado individual: percentiles del cambio de cada persona tratada menos la media
ponderada del cambio del grupo de control (así su centro es el efecto y su ancho es la dispersión entre personas, que incluye
ruido de medición).
"""
import json
import sys

E, L, OUT = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]
FE = "ESI 2023-2025 (INE), panel por rotación ENE (idrph, pares 2023-24 y 2024-25)"
FL = "ELSOC 2016-2022 (COES), ELSOC_Wide_2016_2022_v1.00.tab"
SE, SL = "scripts/modelo/beneficios_esi.py", "scripts/modelo/beneficios_elsoc.py"
PQ = ("p10", "p25", "p50", "p75", "p90")
U_ING = "cambio en log ingreso mensual de la ocupación principal en un año (relativo a la mediana de la ola)"


def r(x, k=4):
    return round(float(x), k)


def esi(v, extra_nota, n_key="reg_log_ingreso_mensual"):
    g = v[n_key]
    return {"valor": r(g["coef"]), "dist": {q: r(v["efecto_individual_dist"][q]) for q in PQ}, "unidad": U_ING, "fuente": FE, "script": SE,
            "n": g["n"], "n_tratados": v["tratados"]["n"], "ee_o_ic": {"ee": r(g["ee"]), "ic95": [r(g["ic95"][0]), r(g["ic95"][1])]},
            "estado": "dato",
            "nota": (f"Regresión ponderada (fact_cal_esi de t) del cambio en log ingreso sobre el grupo, con edad, edad², sexo, educación y ola; "
                     f"EE agrupados por conglomerado. Diferencia de medias simple {r(v['dif_medias'])}. Horas medias de los tratados "
                     f"{v['tratados']['horas_t0_media']:.1f} -> {v['tratados']['horas_t1_media']:.1f}. Distribución del cambio: tratados "
                     f"{ {q: r(v['tratados'][q], 3) for q in PQ} }, control {({q: r(v['control'][q], 3) for q in PQ})} (media control {r(v['control']['media'])}). "
                     + extra_nota)}


H = E["horas_ingreso"]
CORR = "Correlación dentro de la persona y el empleador: no separa si las horas suben por un ascenso, una crisis en la empresa o error de medición."
O = {}
O["INGRESO_SUBIR_A_50H"] = esi(H["todos"]["40a49_a_50mas_vs_sigue_40a49"],
                               "Asalariados público y privado con el mismo empleador, de 40-49 horas en t a 50+ en t+1 contra quienes siguen en 40-49. "
                               "Con cualquier jornada inicial bajo 50: " + str(r(H["todos"]["bajo50_a_50mas_vs_sigue_bajo50"]["reg_log_ingreso_mensual"]["coef"])) +
                               " (ee " + str(r(H["todos"]["bajo50_a_50mas_vs_sigue_bajo50"]["reg_log_ingreso_mensual"]["ee"])) + "). " + CORR)
O["INGRESO_SUBIR_A_55H"] = esi(H["todos"]["40a49_a_55mas_vs_sigue_40a49"],
                               "De 40-49 horas a 55+ contra quienes siguen en 40-49. Con cualquier jornada inicial bajo 55: " +
                               str(r(H["todos"]["bajo55_a_55mas_vs_sigue_bajo55"]["reg_log_ingreso_mensual"]["coef"])) + " (ee " +
                               str(r(H["todos"]["bajo55_a_55mas_vs_sigue_bajo55"]["reg_log_ingreso_mensual"]["ee"])) + "). " + CORR)
O["INGRESO_SUBIR_A_50H_PRIVADO"] = esi(H["privado"]["40a49_a_50mas_vs_sigue_40a49"], "Solo asalariados privados en ambas olas. " + CORR)
O["INGRESO_SUBIR_A_55H_PRIVADO"] = esi(H["privado"]["40a49_a_55mas_vs_sigue_40a49"], "Solo asalariados privados en ambas olas. " + CORR)
O["INGRESO_SUBIR_A_50H_PUBLICO"] = esi(H["publico"]["40a49_a_50mas_vs_sigue_40a49"], "Solo asalariados públicos en ambas olas. " + CORR)
v = H["todos"]["40a49_a_50mas_vs_sigue_40a49"]
O["INGRESO_POR_HORA_SUBIR_A_50H"] = {"valor": r(v["reg_log_ingreso_por_hora"]["coef"]), "dist": {q: r(v["tratados_por_hora"][q] - v["control_por_hora"]["media"]) for q in PQ},
                                     "unidad": "cambio en log ingreso por hora (ing_t_p / (habituales*4,33)) en un año", "fuente": FE, "script": SE,
                                     "n": v["reg_log_ingreso_por_hora"]["n"], "n_tratados": v["tratados"]["n"],
                                     "ee_o_ic": {"ee": r(v["reg_log_ingreso_por_hora"]["ee"]), "ic95": [r(x) for x in v["reg_log_ingreso_por_hora"]["ic95"]]},
                                     "estado": "derivado",
                                     "nota": "Mismo grupo que INGRESO_SUBIR_A_50H. El sueldo mensual no se mueve, así que el pago por hora cae casi en proporción a las horas extra (log de horas sube ~0,30). " + CORR}
el = E["elasticidad_ingreso_horas_mismo_empleador"]
O["ELASTICIDAD_INGRESO_HORAS_SUBIDAS"] = {"valor": r(el["todos"]["elasticidad_subidas"][0]), "dist": None,
                                          "unidad": "cambio en log ingreso mensual por cada punto de log de horas habituales que suben", "fuente": FE, "script": SE,
                                          "n": el["todos"]["n"], "ee_o_ic": {"ee": r(el["todos"]["elasticidad_subidas"][1])}, "estado": "derivado",
                                          "nota": (f"Todos los asalariados con el mismo empleador (10-90 horas en ambas olas), {el['todos']['n_cambia_horas']} cambian sus horas. "
                                                   f"Pendiente por tramos (subidas y bajadas por separado), mismos controles. Bajadas: {r(el['todos']['elasticidad_bajadas'][0])} "
                                                   f"(ee {r(el['todos']['elasticidad_bajadas'][1])}); simétrica: {r(el['todos']['elasticidad'][0])} (ee {r(el['todos']['elasticidad'][1])}). "
                                                   "Incluye cambios chicos y jornadas parciales; para 45->55 horas (+0,20 log) implicaría +6%, dentro del IC del contraste discreto, "
                                                   "que da cerca de 0. Úsese como cota alta. " + CORR)}
O["INGRESO_BAJAR_DE_45_A_MENOS_40H"] = esi(H["todos"]["45mas_a_bajo40_vs_sigue_45mas"],
                                           "Asalariados con el mismo empleador, de 45+ horas a menos de 40 contra quienes siguen en 45+. Casi todos privados (56 de 59). "
                                           "Subconjunto que baja a 30-39 horas (n 35): " + str(r(H["todos"]["45mas_a_30a39_vs_sigue_45mas"]["reg_log_ingreso_mensual"]["coef"])) +
                                           " (ee " + str(r(H["todos"]["45mas_a_30a39_vs_sigue_45mas"]["reg_log_ingreso_mensual"]["ee"])) +
                                           "), positivo y con n muy chico; no usar. Control de reversión a la media: quienes vuelven de 50+ a 40-49 tienen " +
                                           str(r(E["placebo_50mas_a_40a49_vs_sigue_50mas"]["reg_log_ingreso_mensual"]["coef"])) + " (ee " +
                                           str(r(E["placebo_50mas_a_40a49_vs_sigue_50mas"]["reg_log_ingreso_mensual"]["ee"])) + "). " + CORR)
th = E["transicion_horas_mismo_empleador"]
O["PROB_PASAR_DE_40_49_A_50H_MISMO_EMPLEADOR"] = {"valor": r(th["pasa_de_40a49_a_50mas"]), "dist": None, "unidad": "probabilidad anual", "fuente": FE, "script": SE,
                                                  "n": th["n_40a49"], "ee_o_ic": None, "estado": "dato",
                                                  "nota": f"Frecuencia de la transición entre asalariados del panel (ponderada). A 55+: {r(th['pasa_de_40a49_a_55mas'])}. De 45+ a menos de 40: {r(th['pasa_de_45mas_a_bajo40'])} (n {th['n_45mas']})."}
for h, lab in (("h50", "50"), ("h55", "55")):
    x = E["paso_a_directivo"]["todos_asalariados"][h]
    me = E["paso_a_directivo"]["mismo_empleador"][h]
    O[f"PROB_PASAR_A_DIRECTIVO_CON_{lab}H"] = {
        "valor": r(x["mpl_dif_con_controles"]), "dist": None, "unidad": "diferencia en probabilidad anual de pasar a CIUO gran grupo 1 (directivo)",
        "fuente": FE, "script": SE, "n": x["n"], "ee_o_ic": {"ee": r(x["ee"])}, "estado": "dato",
        "nota": (f"Correlación, no efecto. Asalariados en CIUO 2-9 en t. Tasa con {lab}+ horas: {r(x['tasa_horas_largas'])} ({x['pasan_horas_largas']} de {x['n_horas_largas']}); "
                 f"resto: {r(x['tasa_resto'])} ({x['pasan_resto']} de {x['n_resto']}). MPL con edad, sexo, educación, ola y gran grupo de origen. "
                 f"Mismo empleador: {r(me['mpl_dif_con_controles'])} (ee {r(me['ee'])}). Muy pocos eventos; el código CIUO a 1 dígito también cambia por error de codificación.")}

# ------------------------------------------------------------------ ELSOC
P = L["pausa"]["principal_estudio_hogar_otra"]
CS = L["pausa"]["cambio_simple_ola_evento"]
CV = L["pausa"]["cambio_simple_vuelve_a_trabajar_vs_dos_olas_antes"]
UN = {"s01": "puntos de satisfacción con la vida (0-100)", "s03": "puntos de salud autorreportada (0-100)", "dep_mod": "cambio en probabilidad de PHQ-9 >= 10"}
NP = ("Efectos fijos de persona y de ola, 18-60 años, EE agrupados por persona, sin ponderar. Pausa = ocupado en la ola anterior e inactivo no jubilado "
      "(m02 4 solo estudia, 7 quehaceres, 9 otra; m02=5 jubilado, edad media 69, excluido). " + str(P["n_eventos"]) + " pausas, " +
      str(P["destinos_m02_en_evento"].get("7", 0)) + " de ellas a quehaceres del hogar: ELSOC no dice si la salida fue voluntaria, así que esto es 'dejar de trabajar', no un sabático elegido. "
      "Control: personas ocupadas en todas sus olas. Referencia: ola anterior a la pausa.")
for y in ("s01", "s03", "dep_mod"):
    k = 2 if y != "dep_mod" else 4
    c0 = P[y]["ev_0"]
    T, C = CS[y]["pausa"], CS[y]["sigue_ocupado"]
    alt = L["pausa"]["incluye_enfermedad"][y]["ev_0"]
    O[f"PAUSA_{y.upper()}_ANIO_PAUSA"] = {
        "valor": r(c0["coef"], k), "dist": {q: r(T[q] - C["media"], 3) for q in PQ}, "unidad": UN[y], "fuente": FL, "script": SL,
        "n": P[y]["n_obs"], "n_tratados": c0["obs_con_1"], "ee_o_ic": {"ee": c0["ee"], "ic95": c0["ic95"]}, "estado": "dato",
        "nota": (NP + f" Pre-tendencia (2+ olas antes): {P[y]['ev_pre2']['coef']} (ee {P[y]['ev_pre2']['ee']}). Diferencia simple de cambios individuales "
                 f"(ponderada): pausa {T['media']} (n {T['n']}) contra sigue ocupado {C['media']} (n {C['n']}). Incluyendo m02=8 (enfermo): {alt['coef']} (ee {alt['ee']}). "
                 "dist: percentiles del cambio individual de quien pausa menos la media del control; la escala 1-5 hace que los saltos sean de 25 puntos.")}
    c1 = P[y]["ev_1_vuelve"]
    T2, C2 = CV[y]["pausa_y_vuelve"], CV[y]["siempre_ocupado"]
    O[f"PAUSA_{y.upper()}_ANIO_SIGUIENTE_SI_VUELVE"] = {
        "valor": r(c1["coef"], k), "dist": {q: r(T2[q] - C2["media"], 3) for q in PQ}, "unidad": UN[y], "fuente": FL, "script": SL,
        "n": P[y]["n_obs"], "n_tratados": c1["obs_con_1"], "ee_o_ic": {"ee": c1["ee"], "ic95": c1["ic95"]}, "estado": "dato",
        "nota": (NP + f" Ola siguiente a la pausa y de nuevo ocupado, contra la ola anterior a la pausa. Si sigue sin trabajar: {P[y]['ev_1_sigue_fuera']['coef']} "
                 f"(ee {P[y]['ev_1_sigue_fuera']['ee']}). Diferencia simple (vuelve menos dos olas antes): {T2['media']} (n {T2['n']}) contra siempre ocupado {C2['media']} (n {C2['n']}).")}
ns = L["pausa"]["estado_ola_siguiente"]
O["PAUSA_ESTADO_OLA_SIGUIENTE"] = {"valor": {k: ns[k] for k in ("O", "D", "P", "J", "E")}, "dist": None, "unidad": "proporción en la ola siguiente (O ocupado, D desocupado, P sigue inactivo, J jubilado, E enfermo)",
                                   "fuente": FL, "script": SL, "n": ns["n"], "ee_o_ic": None, "estado": "dato", "nota": "Ponderado con ponderador02. Entre olas hay 1 año, salvo 2019-2021."}

JF, JC = L["jornada_fe"], L["jornada_cambios"]
for y in ("s01", "s03", "dep_mod"):
    k = 2 if y != "dep_mod" else 4
    f = JF[y]["h_55mas"]
    c = JC["40a45_a_55mas_vs_sigue_40a45"][y]
    O[f"HORAS_55_{y.upper()}"] = {
        "valor": r(f["coef"], k), "dist": {q: r(c["tratados"][q] - c["control"]["media"], 3) for q in PQ}, "unidad": UN[y], "fuente": FL, "script": SL,
        "n": JF[y]["n_obs"], "n_tratados": f["obs_con_1"], "ee_o_ic": {"ee": f["ee"], "ic95": f["ic95"]}, "estado": "dato",
        "nota": (f"55+ horas (m12) contra 40-45 (n_tratados = observaciones en 55+), efectos fijos de persona y ola, ocupados 18-60 con horas en 2016, 2018, 2021. Diferencia simple de quienes pasan "
                 f"de 40-45 a 55+ contra quienes siguen en 40-45: {c['dif']} (IC95 {c['ic95']}, n {c['tratados']['n']} contra {c['control']['n']}). dist: cambio individual de quien pasa a 55+ menos la media del control.")}
    c2 = JC["45mas_a_bajo40_vs_sigue_45mas"][y]
    f3 = JF[y]["h_30_39"]
    O[f"BAJAR_DE_45_A_MENOS_40H_{y.upper()}"] = {
        "valor": c2["dif"], "dist": {q: r(c2["tratados"][q] - c2["control"]["media"], 3) for q in PQ}, "unidad": UN[y], "fuente": FL, "script": SL,
        "n": c2["tratados"]["n"] + c2["control"]["n"], "n_tratados": c2["tratados"]["n"], "ee_o_ic": {"ee": c2["ee_dif"], "ic95": c2["ic95"]}, "estado": "dato",
        "nota": (f"Diferencia simple ponderada del cambio individual: de 45+ horas a menos de 40 contra quienes siguen en 45+ (pares 2016-18 y 2018-21). "
                 f"En efectos fijos, 30-39 horas contra 40-45: {f3['coef']} (ee {f3['ee']}); menos de 30: {JF[y]['h_lt30']['coef']} (ee {JF[y]['h_lt30']['ee']}).")}

O["sin_dato"] = {
    "INGRESO_55H_PUBLICO": "Solo 25 asalariados públicos pasan de 40-49 a 55+ horas con el mismo empleador (mínimo usado: 30).",
    "INGRESO_BAJAR_RITMO_PUBLICO": "Solo 3 asalariados públicos bajan de 45+ a menos de 40 horas con el mismo empleador.",
    "INGRESO_HORAS_LARGAS_MAS_DE_UN_ANIO": "El panel ESI enlaza a cada persona solo dos olas seguidas; no hay forma de ver si las horas largas pagan a los 2-3 años.",
    "INGRESO_HORAS_INDEPENDIENTES": "No se estimó para cuenta propia: el pedido es sobre asalariados con el mismo empleador.",
    "PAUSA_VOLUNTARIA_VS_INVOLUNTARIA": "ELSOC no pregunta por qué se dejó de trabajar. 294 de 415 pausas son a quehaceres del hogar; solo 70 a estudiar y 51 a 'otra', muy pocas para estimar un sabático elegido por separado.",
    "PAUSA_SUELDO_AL_VOLVER": "Ni la ESI (dos olas) ni ELSOC (m13 ingreso con muchos faltantes; no se intentó) permiten medirlo aquí. El valor de EPS ya está en modelo_paneles.md (CICATRIZ_PAUSA_VS_DESPIDO).",
    "PAUSA_EN_ESI": "La ESI enlaza solo dos olas: no se puede ver ocupado -> inactivo -> ocupado.",
}
json.dump(O, open(OUT, "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: (v["valor"], v.get("ee_o_ic"), v.get("n_tratados")) for k, v in O.items() if k != "sin_dato"}, ensure_ascii=False, indent=0))
