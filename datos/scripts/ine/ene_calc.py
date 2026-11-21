# Indicadores ENE desde la base ESI 2025 (ENE trimestre oct-dic 2025). Uso: ene_calc.py <esi_2025_personas.csv> <salida.json>
import sys, json, numpy as np, pandas as pd
d = pd.read_csv(sys.argv[1], usecols=["ano_encuesta","mes_encuesta","edad","sexo","activ","tpi","ocup_form","habituales","e6_mes","e6_ano","fact_cal"], low_memory=False)
d = d[d.edad >= 15]
d["tramo"] = pd.cut(d.edad, [14, 17, 24, 29, 34, 44, 54, 64, 200], labels=["15-17","18-24","25-29","30-34","35-44","45-54","55-64","65+"])
d["sx"] = d.sexo.map({1: "hombre", 2: "mujer"})
oc = d[d.activ == 1].copy()
oc["parcial"] = (oc.habituales <= 30).astype(float)       # definición INE: hasta 30 horas habituales
oc.loc[oc.habituales.isna() | (oc.habituales > 168), "parcial"] = np.nan
oc["inf"] = (oc.ocup_form == 2).astype(float)
def wmean(g, v):
    g = g[g[v].notna()]; return round(float((g[v] * g.fact_cal).sum() / g.fact_cal.sum()), 4) if len(g) else None
res = {"fuente": "INE, Encuesta Nacional de Empleo, trimestre octubre-diciembre 2025, tomada de la base de la ESI 2025 (misma muestra, variables ENE: activ, tpi, ocup_form, habituales, e6_mes, e6_ano)",
       "ponderador": "fact_cal (factor de expansión ENE)", "n_personas_15_mas": int(len(d))}
tab = []
for (sx, tr), g in oc.groupby(["sx", "tramo"], observed=True):
    tab.append({"sexo": sx, "tramo": str(tr), "n_ocupados": int(len(g)), "p_tiempo_parcial": wmean(g, "parcial"),
                "p_parcial_involuntario_sobre_ocupados": wmean(g, "tpi"),
                "p_parcial_involuntario_sobre_parciales": wmean(g[g.parcial == 1], "tpi"), "tasa_informalidad": wmean(g, "inf")})
for tr, g in oc.groupby("tramo", observed=True):
    tab.append({"sexo": "ambos", "tramo": str(tr), "n_ocupados": int(len(g)), "p_tiempo_parcial": wmean(g, "parcial"),
                "p_parcial_involuntario_sobre_ocupados": wmean(g, "tpi"),
                "p_parcial_involuntario_sobre_parciales": wmean(g[g.parcial == 1], "tpi"), "tasa_informalidad": wmean(g, "inf")})
for sx, g in oc.groupby("sx"):
    tab.append({"sexo": sx, "tramo": "total", "n_ocupados": int(len(g)), "p_tiempo_parcial": wmean(g, "parcial"),
                "p_parcial_involuntario_sobre_ocupados": wmean(g, "tpi"), "p_parcial_involuntario_sobre_parciales": wmean(g[g.parcial == 1], "tpi"), "tasa_informalidad": wmean(g, "inf")})
g = oc; tab.append({"sexo": "ambos", "tramo": "total", "n_ocupados": int(len(g)), "p_tiempo_parcial": wmean(g, "parcial"),
                "p_parcial_involuntario_sobre_ocupados": wmean(g, "tpi"), "p_parcial_involuntario_sobre_parciales": wmean(g[g.parcial == 1], "tpi"), "tasa_informalidad": wmean(g, "inf")})
res["ocupados_por_sexo_y_edad"] = tab
ft = d[d.activ.isin([1, 2])].copy(); ft["des"] = (ft.activ == 2).astype(float)
des = []
for keys, g in list(ft.groupby(["sx", "tramo"], observed=True)) + [(("ambos", t), g) for t, g in ft.groupby("tramo", observed=True)] + [(("ambos", "total"), ft)]:
    des.append({"sexo": keys[0], "tramo": str(keys[1]), "n_fuerza_trabajo": int(len(g)), "n_desocupados": int((g.activ == 2).sum()), "tasa_desocupacion": wmean(g, "des")})
res["desocupacion_por_sexo_y_edad"] = des
# duración de la búsqueda: desde el mes y año en que empezó a buscar (e6_mes/e6_ano, pregunta '¿desde cuándo ha estado buscando trabajo?') hasta el mes de la encuesta
u = d[(d.activ == 2) & d.e6_ano.between(1950, 2026) & d.e6_mes.between(1, 12)].copy()
print("desocupados con fecha valida", len(u), "de", int((d.activ == 2).sum()))
u["meses"] = (u.ano_encuesta - u.e6_ano) * 12 + (u.mes_encuesta - u.e6_mes) + 0.5
u["meses"] = u.meses.clip(lower=0.25)
def wq(g, q):
    g = g.sort_values("meses"); c = g.fact_cal.cumsum() / g.fact_cal.sum(); return round(float(g.meses[c >= q].iloc[0]), 2)
dur = []
for tr, g in list(u.groupby("tramo", observed=True)) + [("total", u)]:
    if len(g) < 30: continue
    dur.append({"tramo": str(tr), "n_desocupados": int(len(g)), "media_meses": round(float((g.meses * g.fact_cal).sum() / g.fact_cal.sum()), 2),
                "p25_meses": wq(g, .25), "mediana_meses": wq(g, .5), "p75_meses": wq(g, .75), "p_mas_de_6_meses": round(float(((g.meses > 6) * g.fact_cal).sum() / g.fact_cal.sum()), 3),
                "p_mas_de_12_meses": round(float(((g.meses > 12) * g.fact_cal).sum() / g.fact_cal.sum()), 3)})
res["duracion_busqueda_desocupados"] = {"nota": "duración en curso (incompleta) al momento de la encuesta, no la duración total del episodio; la duración completa esperada es mayor", "tabla": dur}
json.dump(res, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
