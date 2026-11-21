"""Junta las salidas de ofertas_sce.py, ofertas_esi.py, ofertas_esi_postgrado.py, ofertas_getonbrd.py y
ofertas_eepp.py en derivados/modelo_ofertas.json, con las claves del motor (backend/app/sim/params.py).

Uso:
  python3 -I ofertas_ensamblar.py <carpeta_con_salidas_parciales> <datos_laborales>
Las salidas parciales se llaman sce_out.json, esi_out.json, pg_out.json, gob_out.json y eepp_out.json.
"""
import json
import math
import sys

P, D = sys.argv[1], sys.argv[2]
L = lambda f: json.load(open(f"{P}/{f}"))  # noqa: E731
sce, esi, pg, gob, ep = L("sce_out.json"), L("esi_out.json"), L("pg_out.json"), L("gob_out.json"), L("eepp_out.json")
S = "scripts/modelo/"
SCE_F = "Fed de Nueva York, SCE Labor Market Survey, microdatos públicos nov-2014 a nov-2024 (sce-labor-microdata-public.xlsx)"
ESI_F = "INE, Encuesta Suplementaria de Ingresos 2023, 2024 y 2025 (microdatos de personas)"
ESI_P = "INE, ESI 2023-2024 y 2024-2025 enlazadas por idrph (rotación de viviendas de la ENE), sexo igual y edad +0 a +2"
r3 = lambda x: round(x, 3)  # noqa: E731
r4 = lambda x: round(x, 4)  # noqa: E731
J = {}
bse = lambda p, n: r4(math.sqrt(p * (1 - p) / n))  # noqa: E731  error binomial aproximado, sin efecto de diseño


def k(clave, valor, unidad, fuente, script, n, ee, pais, estado, nota):
    J[clave] = {"valor": valor, "unidad": unidad, "fuente": fuente, "script": S + script, "n": n, "ee_o_ic": ee,
                "pais": pais, "estado": estado, "nota": nota}


t, tn = sce["tasas"], sce["tasas_n"]
j2j = sce["j2j"]
# ---------------------------------------------------------------- SCE: llegada de ofertas
lam_nb, se_nb = 3 * t["ofertas_4m_no_busca"][0], 3 * t["ofertas_4m_no_busca"][1]
lam_b, se_b = 3 * t["ofertas_4m_busca"][0], 3 * t["ofertas_4m_busca"][1]
jj, sjj = j2j["j2j_anual"]
fac = lam_nb / jj
se_fac = fac * math.sqrt((se_nb / lam_nb) ** 2 + (sjj / jj) ** 2)
fac4 = 3 * t["ofertas_4m_tope4_no_busca"][0] / jj
k("OFERTAS_ANUAL_NO_BUSCA", r3(lam_nb), "ofertas por año (tasa de llegada)", SCE_F, "ofertas_sce.py", tn["no_busca"], r3(se_nb), "EE.UU.", "dato",
  "Asalariados que no buscaron trabajo en las últimas 4 semanas (js6=3). nl1 son ofertas de los últimos 4 meses, por 3. El tope de la encuesta es '10 o más'; con tope en 4 da "
  f"{r3(3 * t['ofertas_4m_tope4_no_busca'][0])}. EE bootstrap por persona (8.662 personas en total).")
k("OFERTAS_ANUAL_BUSCA", r3(lam_b), "ofertas por año (tasa de llegada)", SCE_F, "ofertas_sce.py", tn["busca"], r3(se_b), "EE.UU.", "dato",
  "Asalariados que buscaron en las últimas 4 semanas para dejar su empleo (js6=1). Quien busca un empleo adicional (js6=2) recibe "
  f"{r3(3 * t['ofertas_4m_adicional'][0])} al año y no entra aquí.")
k("P_ALGUNA_OFERTA_ANUAL", {"no_busca": r3(t["p_alguna_anual_no_busca"][0]), "busca": r3(t["p_alguna_anual_busca"][0]), "todos": r3(t["p_alguna_anual_todos"][0])},
  "probabilidad anual (0-1)", SCE_F, "ofertas_sce.py", tn["no_busca"] + tn["busca"] + tn["adicional"],
  {"no_busca": r3(t["p_alguna_anual_no_busca"][1]), "busca": r3(t["p_alguna_anual_busca"][1])}, "EE.UU.", "derivado",
  "1-(1-p4)^3 con p4 = probabilidad de al menos una oferta en 4 meses (no busca 0,157; busca 0,283). Supone independencia entre cuatrimestres. Es el análogo de CARTAS['oferta'] = 0,38.")
k("CAMBIO_EMPLEADOR_SCE", r3(jj), "probabilidad anual (0-1)", SCE_F, "ofertas_sce.py", sce["j2j_n"], r3(sjj), "EE.UU.", "derivado",
  f"Panel de 4 meses: asalariado en dos olas seguidas cuyo empleo actual empezó después de la entrevista anterior ({sce['j2j_cambios']} cambios). "
  f"4 meses: {r4(j2j['j2j_4m'][0])}; anualizado 1-(1-p)^3. Excluye mar-2023 a mar-2024 por el error de l1y que informa la Fed. Solo sirve como denominador de OFERTA_FACTOR.")
k("OFERTA_FACTOR", round(fac, 2), "cociente: ofertas anuales de quien no busca / tasa anual de cambio de empleador", SCE_F, "ofertas_sce.py",
  tn["no_busca"], round(se_fac, 2), "EE.UU.", "derivado",
  f"{r3(lam_nb)} ofertas al año de quien no busca, dividido por {r3(jj)} cambios de empleador al año, ambos en la SCE. Con ofertas topadas en 4: {round(fac4, 2)}. "
  "El motor usa 2,0. Si se adopta, la aceptación tiene que bajar a lo que mide la SCE (P_ACEPTA_OFERTA), si no los gemelos cambiarían de empleo cuatro veces más que en Chile.")
k("BUSCA_MULT", r3(t["busca_mult"][0]), "multiplicador de la tasa de ofertas", SCE_F, "ofertas_sce.py", tn["busca"] + tn["no_busca"], r3(t["busca_mult"][1]), "EE.UU.", "dato",
  f"Ofertas de quien busca para irse / de quien no busca. Con tope en 4 ofertas: {r3(t['busca_mult_tope4'][0])}. Es asociación: quien busca puede ser distinto. El motor usa 2,5.")
k("FRAC_OFERTAS_SIN_BUSCAR", r3(t["frac_ofertas_sin_buscar"][0]), "fracción de todas las ofertas a asalariados (0-1)", SCE_F, "ofertas_sce.py",
  tn["busca"] + tn["no_busca"] + tn["adicional"], r3(t["frac_ofertas_sin_buscar"][1]), "EE.UU.", "dato",
  "Ofertas recibidas por quien no buscó en las últimas 4 semanas sobre el total de ofertas. La SCE no pregunta si la oferta fue espontánea, y la búsqueda se mide en 4 semanas mientras las ofertas en 4 meses: es una cota.")
k("SHARE_BUSCA_ASALARIADOS", r3(t["share_busca"][0]), "fracción de asalariados (0-1)", SCE_F, "ofertas_sce.py", tn["busca"] + tn["no_busca"] + tn["adicional"],
  r3(t["share_busca"][1]), "EE.UU.", "dato", "Buscó en las últimas 4 semanas para dejar su empleo. Para contrastar con GEMELOS_BASE['buscar_pega'] (EPS: 0,25 / 0,16 / 0,12).")

# ---------------------------------------------------------------- SCE: sueldo de la oferta
o, on, cola = sce["oferta_rel"], sce["oferta_rel_n"], sce["oferta_cola"]
k("OFERTA_REL_DIST", {q: r3(o[q][0]) for q in ("media", "sd", "sd_robusta", "p10", "p25", "p50", "p75", "p90", "share_mejora")},
  "log(sueldo anual de la oferta / sueldo anual actual)", SCE_F, "ofertas_sce.py", on["ofertas"], {q: r3(o[q][1]) for q in ("media", "sd", "p50")}, "EE.UU.", "dato",
  f"Ofertas de jornada completa a asalariados, rechazadas o aceptadas ({on['personas']} personas). Base: sueldo actual si la rechazó; sueldo de la ola anterior si la aceptó "
  f"(solo {on['aceptadas_con_base']} de {on['aceptadas_total_en_datos']} aceptadas tienen ola anterior, y se reponderan). Se descartan cocientes fuera de 0,2-5. "
  "Colas más gruesas que una normal: la desviación robusta (rango intercuartil/1,349) es 0,22 y la estándar 0,32.")
k("M_SD", r3(o["sd"][0] / math.sqrt(2)), "desviación del premio salarial entre empleadores (log)", SCE_F, "ofertas_sce.py", on["ofertas"], r3(o["sd"][1] / math.sqrt(2)), "EE.UU.", "derivado",
  "Si el premio actual m y el de la oferta m' son independientes con la misma desviación, sd(m'-m) = M_SD·√2; sd observada 0,317. Con la desviación robusta da 0,157, y si se ajusta para reproducir "
  "que 27,7% de las ofertas supera al sueldo actual en más de 10% (lo relevante para el umbral) da 0,15. Chequeo chileno: en la ESI la desviación del cambio de ingreso de quien cambia de empleador "
  "excede la de quien se queda en sqrt(0,494²-0,361²) = 0,34, que da 0,24. El motor usa 0,15.")
k("OFERTA_SUPERA_UMBRAL", {f">{x}": r3(cola[f'p_mayor_{x}'][0]) for x in ("0.0", "0.03", "0.05", "0.08", "0.1", "0.15", "0.2")},
  "fracción de ofertas cuyo log(oferta/actual) supera el umbral", SCE_F, "ofertas_sce.py", on["ofertas"], {">0.1": r3(cola["p_mayor_0.1"][1])}, "EE.UU.", "dato",
  "Momento para calibrar M_SD junto con UMBRAL_*: con los umbrales del motor (0,03 y 0,08) la SCE da 37% y 30%.")
k("OFERTA_ALZA_SI_MEJORA", {q: r3(cola[f"mejora_{q}"][0]) for q in ("p10", "p25", "p50", "p75", "p90")}, "log(oferta/actual) entre ofertas que mejoran el sueldo",
  SCE_F, "ofertas_sce.py", on["ofertas"], {"p50": r3(cola["mejora_p50"][1])}, "EE.UU.", "dato",
  "Para CARTAS['oferta_alza'] = (0,06; 0,22), que sortea entre 6% y 28% con mediana 11,5%. La mediana de la SCE es 0,178 (19,5%) y el p90 0,58.")
ne = sce["oferta_rel_desempleo"]
k("M_REEMPLEO", r3(ne["media"][0]), "log(sueldo de la oferta / sueldo del último empleo)", SCE_F, "ofertas_sce.py", sce["oferta_rel_desempleo_n"]["ofertas"], r3(ne["media"][1]),
  "EE.UU.", "dato",
  f"No ocupados que buscan, con a lo más 24 meses sin trabajo, ofertas de jornada completa ({sce['oferta_rel_desempleo_n']['personas']} personas). Mediana {r3(ne['p50'][0])}; "
  f"entre las {sce['oferta_rel_desempleo_n']['aceptadas']} aceptadas la mediana es 0. Este número ya contiene la pérdida por haber perdido el empleo: el motor suma además CICATRIZ (0,12), "
  "así que usar ambos cuenta la pérdida dos veces. El motor usa -0,03.")

# ---------------------------------------------------------------- SCE: aceptación y umbrales
a, an = sce["acepta_panel"], sce["acepta_panel_n"]
a2 = sce["acepta"]
k("P_ACEPTA_OFERTA", {"todos": r3(a["p_acepta"][0]), "busca": r3(a["p_acepta_busca"][0]), "no_busca": r3(a["p_acepta_no_busca"][0])},
  "fracción de ofertas aceptadas (0-1)", SCE_F, "ofertas_sce.py", an["ofertas"],
  {"todos": r3(a["p_acepta"][1]), "busca": r3(a["p_acepta_busca"][1]), "no_busca": r3(a["p_acepta_no_busca"][1])}, "EE.UU.", "dato",
  f"Ofertas ya decididas de quien era asalariado 4 meses antes, según si buscaba en esa ola anterior (n busca {an['busca']}, no busca {an['no_busca']}). "
  f"Sin el panel (búsqueda medida después del cambio, aceptadas reponderadas) da {r3(a2['p_acepta'][0])}, {r3(a2['p_acepta_busca'][0])} y {r3(a2['p_acepta_no_busca'][0])}.")
rs, rn = sce["reserva"], sce["reserva_n"]
k("UMBRAL_PASIVO", r3(rs["p50_no_busca"][0]), "log(salario de reserva / sueldo actual), mediana", SCE_F, "ofertas_sce.py", rn["no_busca"], r3(rs["p50_no_busca"][1]),
  "EE.UU.", "dato",
  f"Asalariados que no buscan: mínimo que aceptarían por un trabajo nuevo (rw2a, anual desde mar-2017) sobre su sueldo. Media {r3(rs['media_no_busca'][0])}, p25 0, p75 {r3(rs['p75_no_busca'][0])}. "
  f"La versión revelada (logit de aceptar sobre la mejora, punto de 50%) da {r3(sce['umbral_logit']['no_busca']['umbral_log'])} (ee {r3(sce['umbral_logit']['no_busca']['ee'])}): quien no busca rechaza casi todo. El motor usa 0,08.")
k("UMBRAL_ACTIVO", r3(rs["p50_busca"][0]), "log(salario de reserva / sueldo actual), mediana", SCE_F, "ofertas_sce.py", rn["busca"], r3(rs["p50_busca"][1]),
  "EE.UU.", "dato",
  f"Asalariados que buscan para irse. Media {r3(rs['media_busca'][0])}, p25 0, p75 {r3(rs['p75_busca'][0])}. Revelada por logit: {r3(sce['umbral_logit']['busca']['umbral_log'])} "
  f"(ee {r3(sce['umbral_logit']['busca']['ee'])}), es decir, quien busca acepta ofertas que igualan su sueldo. El motor usa 0,03.")

# ---------------------------------------------------------------- SCE: edad (series publicadas)
ed = sce["edad_series"]
y, v = ed["<=45 years"], ed[">45 years"]
k("OFERTAS_EDAD_MAYOR45", {"ofertas_media": r3(v["ofertas_media_cota_inf"] / y["ofertas_media_cota_inf"]),
                           "alguna_oferta": r3(v["p_alguna_oferta_pct"] / y["p_alguna_oferta_pct"]),
                           "nuevo_empleador": r3(v["nuevo_empleador_4m_pct"][0] / y["nuevo_empleador_4m_pct"][0]),
                           "busca": r3(v["busca_pct"][0] / y["busca_pct"][0])},
  "cociente mayores de 45 / 45 o menos", "Fed de Nueva York, SCE Labor Market Survey, series publicadas por edad (sce-labor-chart-data-public.xlsx), promedio de nov-2014 a jul-2026",
  "ofertas_sce.py", y["nuevo_empleador_4m_pct"][2], {"nuevo_empleador_pct_4m_ee_entre_olas": [r3(y["nuevo_empleador_4m_pct"][1]), r3(v["nuevo_empleador_4m_pct"][1])]}, "EE.UU.", "derivado",
  f"Ofertas en 4 meses: {r3(y['ofertas_media_cota_inf'])} (≤45) y {r3(v['ofertas_media_cota_inf'])} (>45), contando '4 o más' como 4. Con alguna oferta: {round(y['p_alguna_oferta_pct'], 1)}% y {round(v['p_alguna_oferta_pct'], 1)}%. "
  "Población de las series según la Fed, no solo asalariados. Para CARTAS por edad (1,0 / 0,8 / 0,6): el 0,6 de 45-59 calza. Los microdatos públicos no traen edad, así que no hay corte 18-29 contra 30-44.")

# ---------------------------------------------------------------- ESI: ocupación
occ = esi["ocupacion_gran_grupo"]
NOM = {"1": "Directores y gerentes", "2": "Profesionales científicos e intelectuales", "3": "Técnicos y profesionales de nivel medio",
       "4": "Personal de apoyo administrativo", "5": "Trabajadores de servicios y vendedores", "6": "Agricultores calificados",
       "7": "Oficiales, operarios y artesanos", "8": "Operadores de instalaciones y máquinas", "9": "Ocupaciones elementales", "10": "Fuerzas Armadas"}
tabla = {}
for g, f in occ.items():
    tabla[g] = {"nombre": NOM[g], "rel_universitaria_o_mas": r3(f["rel_univ"]) if f["rel_univ"] else None,
                "rango_olas_universitaria": [r3(x) for x in f["rel_univ_rango"]] if f["rel_univ_rango"] else None, "n_universitaria": f["n_univ"],
                "rel_superior_con_tecnica": r3(f["rel_superior"]) if f["rel_superior"] else None, "n_superior": f["n_superior"],
                "rel_todos": r3(f["rel_todos"]) if f["rel_todos"] else None, "n_todos": f["n_todos"]}
J["sueldo_relativo_ocupacion"] = {
    "nivel": "CIUO-08 gran grupo (1 dígito, variable b1). La ESI pública no trae 2 dígitos.",
    "definicion": "mediana ponderada del ingreso de la ocupación principal del grupo / mediana del mismo universo, ocupados de 25 a 54 años; promedio de las olas 2023, 2024 y 2025",
    "universos": "rel_universitaria_o_mas: cine11_1d 4-6 (mismo universo que tablas.json); rel_superior_con_tecnica: 3-6; rel_todos: cualquier educación",
    "fuente": ESI_F, "script": S + "ofertas_esi.py", "pais": "Chile", "estado": "dato", "por_grupo": tabla,
    "nota": "El motor tiene hoy la versión 2025 (1,851 para directores). Con tres olas el rango entre años es de ±0,05 en la mayoría de los grupos."}

tr = esi["panel_traspaso_ocupacion"]
k("OCUP_REL", r3(tr["cambia_empleador"]["traspaso"]), "fracción del log del sueldo relativo del grupo de destino que se traspasa", ESI_P, "ofertas_esi.py",
  tr["cambia_empleador"]["n"], r3(tr["cambia_empleador"]["ee"]), "Chile", "dato",
  f"Regresión del cambio de log ingreso (relativo a la mediana de la ola) sobre el cambio de log del sueldo relativo del gran grupo, entre quienes cambiaron de empleador "
  f"({tr['cambia_empleador']['n_cambia_gran_grupo']} cambiaron de gran grupo). Errores de codificación de b1 entre olas sesgan el coeficiente hacia cero. El motor usa 0,3.")
k("RECONV_REL", r3(tr["todos"]["traspaso"]), "fracción del log del sueldo relativo del grupo de destino que se traspasa", ESI_P, "ofertas_esi.py",
  tr["todos"]["n"], r3(tr["todos"]["ee"]), "Chile", "dato",
  f"Igual que OCUP_REL, con todos los asalariados que siguen ocupados ({tr['todos']['n_cambia_gran_grupo']} cambiaron de gran grupo); sin cambiar de empleador da {r3(tr['mismo_empleador']['traspaso'])}. "
  "La ESI no distingue una reconversión buscada de otro cambio de ocupación. Mismo sesgo hacia cero. El motor usa 0,5.")

# ---------------------------------------------------------------- ESI: tipo de empleador
pt = esi["premio_tipo_vs_pyme"]
dm = esi["panel_tipo_al_cambiar"]
mix = dm["destino"]
avg = mix["pyme"] + mix["grande"] * math.exp(pt["grande"][0]) + mix["estado"] * math.exp(pt["estado"][0])
k("PREMIO_TIPO_EMPLEADOR", {"pyme": 0.0, "grande": r3(pt["grande"][0]), "estado": r3(pt["estado"][0])}, "log de sueldo respecto de pyme (1 a 199 personas)", ESI_F, "ofertas_esi.py",
  esi["premio_tipo_n"], {"grande": r3(pt["grande"][1]), "estado": r3(pt["estado"][1])}, "Chile", "dato",
  "Asalariados 18-64 con 30-60 horas; controla edad, edad², sexo, educación, gran grupo CIUO, log horas, ola y región. Sin controlar ocupación: grande "
  f"{r3(esi['premio_tipo_vs_pyme_sin_ocupacion']['grande'][0])}, Estado {r3(esi['premio_tipo_vs_pyme_sin_ocupacion']['estado'][0])}. Solo educación superior: grande "
  f"{r3(esi['premio_tipo_vs_pyme_superior']['grande'][0])}, Estado {r3(esi['premio_tipo_vs_pyme_superior']['estado'][0])}. En el motor no existe este premio; MULT_TAM es un multiplicador de despido, no de sueldo. Startup no se puede identificar.")
k("PREMIO_TIPO_MULT", {"pyme": r3(1 / avg), "grande": r3(math.exp(pt["grande"][0]) / avg), "estado": r3(math.exp(pt["estado"][0]) / avg)},
  "multiplicador sobre el promedio de quienes cambian de empleador", ESI_F, "ofertas_esi.py", esi["premio_tipo_n"], None, "Chile", "derivado",
  "exp(premio) normalizado con la mezcla de destinos de TAM_MEZCLA (pyme 0,62, grande 0,30, Estado 0,08).")
k("PREMIO_TAMANO", {kk: r3(vv[0]) for kk, vv in esi["premio_tamano_vs_200mas"].items()}, "log de sueldo respecto de empresas de 200 o más", ESI_F, "ofertas_esi.py",
  esi["premio_tamano_n"], {kk: r3(vv[1]) for kk, vv in esi["premio_tamano_vs_200mas"].items()}, "Chile", "dato", "Mismos controles que PREMIO_TIPO_EMPLEADOR; 'publico' es asalariado público.")
k("TAM_MEZCLA", {kk: r3(vv) for kk, vv in mix.items()} | {"startup": None}, "fracción de quienes cambian de empleador (0-1)", ESI_P, "ofertas_esi.py", dm["n"], None, "Chile", "dato",
  f"Tipo del nuevo empleador entre asalariados que cambiaron de empleador entre olas. Entre todos los asalariados con menos de un año en su empleo (corte transversal, n={esi['mezcla_recien_llegados_n']}): "
  f"pyme {r3(esi['mezcla_recien_llegados']['pyme'])}, grande {r3(esi['mezcla_recien_llegados']['grande'])}, Estado {r3(esi['mezcla_recien_llegados']['estado'])}. El motor usa Estado 0,12, grande 0,35, pyme 0,52, startup 0,01.")
po, pd_ = dm["origen"], dm["destino"]
base_same = sum(po[x] * pd_[x] for x in po)
s_q = (dm["mismo_tipo"] - base_same) / (1 - base_same)
se_same = math.sqrt(dm["mismo_tipo"] * (1 - dm["mismo_tipo"]) / dm["n"])
k("TAM_SE_QUEDA", r3(s_q), "probabilidad (0-1) de conservar el tipo antes de sortear uno nuevo", ESI_P, "ofertas_esi.py", dm["n"], r3(se_same / (1 - base_same)), "Chile", "derivado",
  f"En el panel {r3(dm['mismo_tipo'])} de quienes cambian de empleador queda en el mismo tipo (pyme, grande, Estado). El motor primero conserva el tipo con probabilidad s y si no sortea de TAM_MEZCLA, "
  f"así que s = (P(mismo) - Σ origen·destino)/(1 - Σ origen·destino) con Σ = {r3(base_same)}. El motor usa 0,3. Error aproximado binomial sin efecto de diseño.")

# ---------------------------------------------------------------- ESI: antigüedad, horas, cambio de empleo
an_ = esi["antiguedad_vs_menos_1"]
k("RETORNO_ANTIGUEDAD", {"1-2": r3(an_["a1_1-2"][0]), "2-5": r3(an_["a2_2-5"][0]), "5-10": r3(an_["a3_5-10"][0]), "10+": r3(an_["a4_10+"][0]),
                         "lineal_por_anio": r4(esi["antiguedad_lineal"]["antig"][0]), "cuadratico": round(esi["antiguedad_lineal"]["I(antig ** 2)"][0], 5)},
  "log de sueldo respecto de menos de 1 año en el empleo", ESI_F, "ofertas_esi.py", esi["antiguedad_n"],
  {"1-2": r3(an_["a1_1-2"][1]), "10+": r3(an_["a4_10+"][1]), "lineal_por_anio": r4(esi["antiguedad_lineal"]["antig"][1])}, "Chile", "dato",
  "Asalariados 18-64, 30-60 horas; controla edad, edad², sexo, educación, gran grupo, tipo de empleador, horas, ola y región. Corte transversal: incluye que los buenos calces duran más, "
  "así que es cota alta del retorno causal. El motor no tiene un retorno a la antigüedad aparte del perfil por edad.")
hl = esi["horas_largas"]
k("HORAS_50_O_MAS", {b: r3(hl[b]["pct_50_o_mas"] / 100) for b in ("18-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-64", "18-54")},
  "fracción de ocupados (0-1)", ESI_F, "ofertas_esi.py", hl["18-64"]["n"], {"18-54": bse(hl["18-54"]["pct_50_o_mas"] / 100, hl["18-54"]["n"])}, "Chile", "dato",
  f"Horas habituales ≥50, ponderado con fact_cal, tres olas. 18-54 por ola: 2023 {round(hl['18-54']['por_ola_50']['2023'], 1)}%, 2024 {round(hl['18-54']['por_ola_50']['2024'], 1)}%, 2025 {round(hl['18-54']['por_ola_50']['2025'], 1)}% (baja con la ley de 40 horas).")
k("HORAS_55_O_MAS", {b: r3(hl[b]["pct_55_o_mas"] / 100) for b in ("18-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-64", "18-54")},
  "fracción de ocupados (0-1)", ESI_F, "ofertas_esi.py", hl["18-64"]["n"], None, "Chile", "dato", "Horas habituales ≥55.")
ph = esi["panel_horas"]
k("TRABAJAR_MAS_FLUJO", r3(ph["pasa_a_50_o_mas"]), "probabilidad anual (0-1)", ESI_P, "ofertas_esi.py", ph["n_bajo_50"], bse(ph["pasa_a_50_o_mas"], ph["n_bajo_50"]), "Chile", "dato",
  f"Ocupados con menos de 50 horas que al año siguiente declaran 50 o más. Por edad: {', '.join(f'{b} {r3(x)}' for b, x in ph['pasa_a_50_por_edad'].items())}. "
  f"De quienes trabajan 50 o más, {r3(ph['sigue_50_o_mas'])} sigue así al año siguiente (n={ph['n_50_o_mas']}). GEMELOS_BASE['trabajar_mas'] = 0,08 usa el stock (8%), no la entrada anual.")
ce = esi["panel_cambio_empleador_asalariados"]
k("CAMBIO_EMPLEADOR_ESI", {"total": r3(ce["anual_total"]), "18-29": r3(ce["18-29"]["tasa"]), "30-44": r3(ce["30-44"]["tasa"]), "45-59": r3(ce["45-59"]["tasa"])},
  "probabilidad anual (0-1)", ESI_P, "ofertas_esi.py", ce["n"], {"total": bse(ce["anual_total"], ce["n"]), "18-29": bse(ce["18-29"]["tasa"], ce["18-29"]["n"])}, "Chile", "dato",
  "Asalariados en ambas olas cuyo empleo actual empezó después de la entrevista anterior. Incluye a quien perdió el empleo y encontró otro dentro del año, y renovaciones registradas como empleo nuevo. "
  "Más alta que CAMBIO_EMPLEADOR del motor (EPS: 0,218 / 0,138 / 0,102). Sirve como cota alta.")
pc = esi["panel_cambio_ingreso"]
k("CAMBIO_INGRESO_AL_CAMBIAR", {"se_queda": {q: r3(pc["se_queda"][q]) for q in ("media", "sd", "p25", "p50", "p75", "share_sube")},
                                "cambia_empleador": {q: r3(pc["cambia_empleador"][q]) for q in ("media", "sd", "p25", "p50", "p75", "share_sube")},
                                "premio_cambio": r3(esi["panel_premio_cambio"][0])},
  "cambio anual de log ingreso relativo a la mediana de la ola", ESI_P, "ofertas_esi.py", esi["panel_premio_cambio"][2], {"premio_cambio": r3(esi["panel_premio_cambio"][1])}, "Chile", "dato",
  f"Asalariados en ambas olas. Sube el ingreso del {round(100 * pc['cambia_empleador']['share_sube'])}% de quienes cambian de empleador y del {round(100 * pc['se_queda']['share_sube'])}% de quienes se quedan; "
  "el premio medio de cambiar no es distinto de cero. Mezcla cambios voluntarios e involuntarios. Objetivo para el motor, junto al 54% del Banco Central.")

# ---------------------------------------------------------------- ESI: cuenta propia
cp = esi["cuenta_propia"]
emp = {e: r3(math.exp(cp[e]["cuenta_propia"][0])) for e in ("media", "tecnica", "universitaria", "postgrado", "todos")}
k("EMP_MEDIANA", emp, "cociente de ingreso cuenta propia / asalariado comparable", ESI_F, "ofertas_esi.py",
  {e: cp[e]["n_cuenta_propia"] for e in emp}, {e: r3(math.exp(cp[e]["cuenta_propia"][0]) * cp[e]["cuenta_propia"][1]) for e in emp}, "Chile", "dato",
  f"exp del coeficiente de cuenta propia en log ingreso, 25-64 años con 30-80 horas, controla edad, sexo, horas, ola y región (y educación en 'todos'). Cociente de medianas en celdas edad×sexo: "
  f"{r3(math.exp(cp['todos']['log_cociente_medianas_celdas']))} en todos, {r3(math.exp(cp['universitaria']['log_cociente_medianas_celdas']))} en universitarios. "
  f"En el panel, quien pasa de asalariado a cuenta propia cambia su ingreso en mediana {r3(esi['panel_cuenta_propia']['asalariado_a_cuenta_propia']['p50'])} (cociente {r3(math.exp(esi['panel_cuenta_propia']['asalariado_a_cuenta_propia']['p50']))}, n={esi['panel_cuenta_propia']['asalariado_a_cuenta_propia']['n']}). "
  f"Empleadores ganan más que asalariados: {r3(math.exp(cp['todos']['empleador'][0]))}. Incluye cuenta propia informal y de subsistencia. El motor usa 0,65 (Hamilton 2000, EE.UU.).")
sdq = math.sqrt(cp["todos"]["sd_resid_cuenta_propia"] ** 2 - cp["todos"]["sd_resid_asalariado"] ** 2)
pcp = esi["panel_cuenta_propia"]
sdt = math.sqrt((pcp["sigue_cuenta_propia"]["sd"] ** 2 - pcp["sigue_asalariado"]["sd"] ** 2) / 2)
ent = math.sqrt(max(pcp["asalariado_a_cuenta_propia"]["sd"] ** 2 - pcp["sigue_asalariado"]["sd"] ** 2 - sdt ** 2, 0))
k("EMP_SD_Q", r3(sdq), "desviación (log) adicional del ingreso por cuenta propia", ESI_F, "ofertas_esi.py", cp["todos"]["n_cuenta_propia"], None, "Chile", "derivado",
  f"sqrt(sd_resid_cuenta_propia² - sd_resid_asalariado²) = sqrt({r3(cp['todos']['sd_resid_cuenta_propia'])}² - {r3(cp['todos']['sd_resid_asalariado'])}²). Con el panel (varianza del cambio al pasar a cuenta propia "
  f"menos la de asalariados que siguen y menos EMP_SD_T²) da {r3(ent)}. Sin error calculado. El motor usa 0,7.")
k("EMP_SD_T", r3(sdt), "desviación (log) del componente anual transitorio", ESI_P, "ofertas_esi.py", pcp["sigue_cuenta_propia"]["n"], None, "Chile", "derivado",
  f"sqrt((sd del cambio anual de quien sigue por cuenta propia² - sd de quien sigue asalariado²)/2) = sqrt(({r3(pcp['sigue_cuenta_propia']['sd'])}² - {r3(pcp['sigue_asalariado']['sd'])}²)/2). "
  "Supone que el exceso es transitorio e independiente entre años. Sin error calculado. El motor usa 0,4.")
k("EMP_ENTRADA_CHILE", r3(esi["panel_entrada_cuenta_propia"]["tasa"]), "probabilidad anual (0-1)", ESI_P, "ofertas_esi.py", esi["panel_entrada_cuenta_propia"]["n"], bse(esi["panel_entrada_cuenta_propia"]["tasa"], esi["panel_entrada_cuenta_propia"]["n"]), "Chile", "dato",
  "Asalariados de 25-64 ocupados en ambas olas que pasan a cuenta propia o empleador. Incluye cuenta propia informal. El motor usa 0,0113 (Alemania).")
k("EMP_SALIDA_CHILE", r3(1 - esi["panel_salida_cuenta_propia"]["sigue_cuenta_propia"]), "probabilidad anual (0-1) de dejar de ser cuenta propia", ESI_P, "ofertas_esi.py",
  esi["panel_salida_cuenta_propia"]["n"], bse(1 - esi["panel_salida_cuenta_propia"]["sigue_cuenta_propia"], esi["panel_salida_cuenta_propia"]["n"]), "Chile", "dato",
  f"Cuenta propia de 25-64 que al año siguiente no es cuenta propia ocupado; {r3(esi['panel_salida_cuenta_propia']['a_asalariado'])} pasa a asalariado. Sin duración del negocio, así que no separa los primeros años. "
  "El motor usa 0,31 en los dos primeros años y 0,15 después.")

# ---------------------------------------------------------------- postgrado
k("MAG_PREMIO_ESI", {"con_ocupacion": r3(pg["con_ocupacion"]["magister"][0]), "sin_ocupacion": r3(pg["sin_ocupacion"]["magister"][0]),
                     "doctorado_con_ocupacion": r3(pg["con_ocupacion"]["doctorado"][0])},
  "log de sueldo respecto de título universitario", ESI_F, "ofertas_esi_postgrado.py", pg["con_ocupacion"]["n"],
  {"con_ocupacion": r3(pg["con_ocupacion"]["magister"][1]), "sin_ocupacion": r3(pg["sin_ocupacion"]["magister"][1])}, "Chile", "dato",
  f"25-64 años, 30-60 horas, universitarios ({pg['n_por_nivel']['a_universitaria']}), magíster ({pg['n_por_nivel']['magister']}) y doctorado ({pg['n_por_nivel']['doctorado']}). "
  "Corte transversal: mezcla el efecto del magíster con quién lo hace. Es cota alta; el motor usa 0,07 (DIPRES 2026, becarios, estudio de eventos), que es la mejor estimación causal disponible.")

# ---------------------------------------------------------------- Getonbrd
ga, gc = gob["todos"], gob["chile"]
k("ASC_ALZA_SENIORITY_TECH", {"junior->semi": r3(ga["saltos_log"]["junior->1_semi"][0]), "semi->senior": r3(ga["saltos_log"]["1_semi->2_senior"][0]),
                              "senior->expert": r3(ga["saltos_log"]["2_senior->3_expert"][0])},
  "log de sueldo ofrecido entre niveles consecutivos", "Get on Board, API pública v0, avisos con sueldo publicado (getonbrd_vacantes.csv)", "ofertas_getonbrd.py", ga["n"],
  {"junior->semi": r3(ga["saltos_log"]["junior->1_semi"][1]), "semi->senior": r3(ga["saltos_log"]["1_semi->2_senior"][1]), "senior->expert": r3(ga["saltos_log"]["2_senior->3_expert"][1])},
  "Chile", "dato",
  f"Avisos de jornada completa, punto medio del rango en USD, efectos fijos de categoría y país, errores por empresa ({gob['n_empresas']} empresas). Solo avisos de Chile (n={gc['n']}): "
  f"{r3(gc['saltos_log']['junior->1_semi'][0])}, {r3(gc['saltos_log']['1_semi->2_senior'][0])}, {r3(gc['saltos_log']['2_senior->3_expert'][0])}. 'Sin experiencia' se junta con junior. "
  "Son diferencias de mercado entre niveles que también reflejan años de experiencia; el alza de un ascenso dentro de la empresa (ASC_ALZA = 0,08) no se observa aquí. Mezcla avisos remotos (pago en USD) con avisos chilenos.")

# ---------------------------------------------------------------- Empleos públicos
pe = ep["por_estamento"]
k("P_GANA_POSTULACION_ESTADO", {e: r4(x["p_por_postulacion"]) for e, x in pe.items()} | {"total": r4(ep["total"]["p_por_postulacion"])},
  "probabilidad por postulación (0-1)", "Servicio Civil, empleospublicos.cl: convocatorias 2009-2026 (convocatorias_eepp_historicas.csv y eepp_convocatorias.csv)",
  "ofertas_eepp.py", ep["n_convocatorias"], {e: [r4(y) for y in x["ic95"]] for e, x in pe.items()}, "Chile", "dato",
  "Seleccionados / postulaciones en convocatorias con postulación en línea y proceso cerrado (aprobado o desierto). IC 95% bootstrap por convocatoria. "
  f"2023-2026: Profesionales {r4(ep['por_estamento_2023_2026']['Profesionales']['p_por_postulacion'])}, Técnicos {r4(ep['por_estamento_2023_2026']['Técnicos']['p_por_postulacion'])}. "
  f"Quedan desiertas {round(100 * ep['total']['share_desierto'])}% de las convocatorias. Son concursos abiertos, no el cupo interno de CARTAS['postular'] (0,30 base), que no tiene análogo en estos datos. "
  "La renta por estamento ya está en calibracion.json (empleos_publicos.por_estamento).")

# ---------------------------------------------------------------- sin dato
J["sin_dato"] = {
    "BUSCA_MULT_POR_EDAD": "Los microdatos públicos de la SCE no traen edad ni otras variables demográficas (están en el módulo principal de la SCE, no incluido). Solo hay series publicadas ≤45 / >45 sin corte por búsqueda.",
    "UMBRAL_POR_EDAD": "Mismo motivo: sin edad en los microdatos de la SCE.",
    "OFERTAS_18_29_VS_30_44": "Las series por edad de la SCE solo separan 45 o menos y más de 45.",
    "OFERTA_FACTOR_CHILE": "Ninguna fuente chilena disponible pregunta por ofertas recibidas o rechazadas; solo hay cambios realizados (EPS, ESI).",
    "ASC_ALZA": "Ninguna fuente local registra ascensos dentro de la empresa con su alza. Get on Board da diferencias de mercado entre niveles (ASC_ALZA_SENIORITY_TECH), que no son lo mismo.",
    "ASC_ALZA_FUERA_DE_TECH": "La ESI no trae nivel jerárquico ni seniority; Get on Board es casi solo tecnología.",
    "PREMIO_Y_MEZCLA_STARTUP": "La ESI no distingue startups; el tamaño (b15_1) y la categoría no bastan para identificarlas.",
    "SUELDO_RELATIVO_CIUO_2_DIGITOS": "La ESI pública solo trae b1 (gran grupo, 1 dígito); los códigos a 2 o 3 dígitos no se publican.",
    "MAG_PREMIO_MIFUTURO": "Los buscadores de mifuturo descargados (2022-2026) cubren solo carreras de pregrado y técnicas; no hay filas de magíster, postítulo ni doctorado.",
    "CARTAS_POSTULAR_INTERNO": "Ninguna fuente registra concursos internos de ascenso; empleospublicos.cl son concursos abiertos (ver P_GANA_POSTULACION_ESTADO).",
    "REEMPLEO_CHILE_SUELDO_OFERTA": "La ESI no tiene sueldo previo de quien estaba cesante en la ola anterior (ing_t_p es solo de ocupados), así que no hay versión chilena de M_REEMPLEO con este panel.",
}
J["_meta"] = {"generado": "2026-11-21", "scripts": [S + x for x in ("ofertas_sce.py", "ofertas_esi.py", "ofertas_esi_postgrado.py", "ofertas_getonbrd.py", "ofertas_eepp.py", "ofertas_ensamblar.py")],
              "nota": "Cada clave dice si viene de EE.UU. o de Chile. 'dato' = estimado directo; 'derivado' = cálculo sobre datos con un supuesto explícito en la nota."}
json.dump(J, open(f"{D}/derivados/modelo_ofertas.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(J, indent=1, ensure_ascii=False))
