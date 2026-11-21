"""Beneficio en ingreso de trabajar más horas (y costo de bajar el ritmo) con el panel corto de la ESI 2023-2025 (INE).

Uso:
  uv run --with pandas --with numpy --with statsmodels python -I beneficios_esi.py <datos_laborales> <salida.json>

Panel: misma lógica de enlace que scripts/modelo/ofertas_esi.py (idrph en oct-dic de un año y del siguiente por la rotación
de la ENE; mismo sexo y edad que avanza 0-2 años). Pares 2023-2024 y 2024-2025.

Muestra principal: asalariados (categoria_ocupacion 3 o 4) ocupados en ambas olas, con el mismo empleador (el empleo actual
en t+1 empezó antes de la entrevista de t: b17 <= fecha de t), ocup_ref == 1 e ingreso positivo en ambas olas, 18-64 años en t.
Resultado: cambio en log ingreso mensual de la ocupación principal, relativo a la mediana de la ola (igual que ofertas_esi.py),
recortado a |d| <= 2. También el cambio en log ingreso por hora (ing_t_p / (habituales * 4,33)).
Ponderador: fact_cal_esi de la ola t. EE agrupados por conglomerado de la ola t.
Todo es correlación dentro de la misma persona y el mismo empleador: no separa si las horas suben por un ascenso o al revés.
"""
import json
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

D, OUT = sys.argv[1], sys.argv[2]
COLS = ["ano_encuesta", "mes_encuesta", "conglomerado", "idrph", "sexo", "edad", "b1", "b17_mes", "b17_ano", "cine11_1d",
        "categoria_ocupacion", "habituales", "ing_t_p", "ocup_ref", "fact_cal_esi", "fact_cal", "activ"]
ARCH = {2023: "esi_2023.csv", 2024: "esi_2024.csv", 2025: "esi_2025_personas.csv"}

olas = []
for a, f in ARCH.items():
    x = pd.read_csv(f"{D}/esi_ine/{f}", sep=",", encoding="latin-1", usecols=lambda c: c in COLS, low_memory=False)
    x["ola"] = a
    olas.append(x)
E = pd.concat(olas, ignore_index=True)
for c in COLS:
    E[c] = pd.to_numeric(E[c], errors="coerce")
E["edu"] = pd.cut(E.cine11_1d.where(E.cine11_1d <= 6), [-1, 2, 3, 4, 6], labels=["media", "tecnica", "universitaria", "postgrado"]).astype(str)
E["ym"] = E.ano_encuesta * 12 + E.mes_encuesta
E["inicio"] = np.where(E.b17_ano.between(1940, 2026) & E.b17_mes.between(1, 12), E.b17_ano * 12 + E.b17_mes, np.nan)
E["ing_ok"] = (E.ocup_ref == 1) & (E.ing_t_p > 0) & (E.fact_cal_esi > 0)
E["lny"] = np.log(E.ing_t_p.where(E.ing_ok))
E["clu"] = E.ola.astype(str) + "_" + E.conglomerado.astype(str)


def wmed(x, w):
    o = np.argsort(x)
    x, w = np.asarray(x)[o], np.asarray(w)[o]
    c = (np.cumsum(w) - w / 2) / w.sum()
    return float(np.interp(0.5, c, x))


MED = {a: wmed(g.ing_t_p, g.fact_cal_esi) for a, g in E[E.ing_ok].groupby("ola")}
E["lrel"] = E.lny - np.log(E.ola.map(MED))
E["lwh"] = np.log(E.ing_t_p.where(E.ing_ok & E.habituales.between(1, 120)) / (E.habituales * 4.33)) - np.log(E.ola.map(MED))

K = ["idrph", "ola", "sexo", "edad", "categoria_ocupacion", "b1", "inicio", "ym", "lrel", "lwh", "ing_ok", "habituales",
     "activ", "fact_cal_esi", "fact_cal", "clu", "edu"]
P = []
for a in (2023, 2024):
    x, y = E[E.ola == a][K], E[E.ola == a + 1][K]
    j = x.merge(y, on="idrph", suffixes=("0", "1"))
    j = j[(j.sexo0 == j.sexo1) & (j.edad1 - j.edad0).between(0, 2)]
    P.append(j)
P = pd.concat(P, ignore_index=True)
R = {"panel_enlazados": int(len(P)), "mediana_ola": MED}

# muestra principal: asalariados con el mismo empleador e ingreso en ambas olas
S = P[(P.activ0 == 1) & (P.activ1 == 1) & P.categoria_ocupacion0.isin([3, 4]) & P.categoria_ocupacion1.isin([3, 4])
      & (P.categoria_ocupacion0 == P.categoria_ocupacion1) & P.inicio1.notna() & (P.inicio1 <= P.ym0)
      & P.ing_ok0 & P.ing_ok1 & P.edad0.between(18, 64) & P.habituales0.between(1, 120) & P.habituales1.between(1, 120)
      & (P.edu0 != "nan")].copy()
S["d"] = S.lrel1 - S.lrel0
S["dh"] = S.lwh1 - S.lwh0
S = S[S.d.between(-2, 2)]
S["cat"] = S.categoria_ocupacion0.map({3: "privado", 4: "publico"})
R["muestra_mismo_empleador"] = {"n": int(len(S)), "privado": int((S.cat == "privado").sum()), "publico": int((S.cat == "publico").sum())}
Q = (0.1, 0.25, 0.5, 0.75, 0.9)


def wq(x, w):
    x, w = np.asarray(x, float), np.asarray(w, float)
    o = np.argsort(x)
    c = np.cumsum(w[o]) / w.sum()
    return [float(x[o][min(np.searchsorted(c, q), len(x) - 1)]) for q in Q]


def resumen(g, col="d"):
    x, w = g[col].values, g.fact_cal_esi0.values
    mu = float(np.average(x, weights=w))
    neff = w.sum() ** 2 / (w ** 2).sum()
    sd = float(np.sqrt(np.average((x - mu) ** 2, weights=w)))
    q = wq(x, w)
    return {"media": mu, "ee_simple": sd / np.sqrt(neff), "sd": sd, "p10": q[0], "p25": q[1], "p50": q[2], "p75": q[3], "p90": q[4],
            "share_sube": float(np.average(x > 0, weights=w)), "n": int(len(g)),
            "horas_t0_media": float(np.average(g.habituales0, weights=w)), "horas_t1_media": float(np.average(g.habituales1, weights=w))}


CTRL = "edad0 + I(edad0**2) + C(sexo0) + C(edu0) + C(ola0)"


def efecto(trat, ctrl, nombre, extra=""):
    """trat, ctrl: subconjuntos de S. Diferencia de medias, regresión con controles y distribuciones."""
    d = pd.concat([trat.assign(T=1), ctrl.assign(T=0)])
    out = {"tratados": resumen(trat), "control": resumen(ctrl)}
    if len(trat) < 30:
        out["nota"] = "menos de 30 tratados: no se estima"
        return out
    out["dif_medias"] = out["tratados"]["media"] - out["control"]["media"]
    for col, k in (("d", "log_ingreso_mensual"), ("dh", "log_ingreso_por_hora")):
        dd = d[d[col].notna() & d[col].between(-3, 3)].dropna(subset=["edad0", "sexo0", "edu0", "ola0", "fact_cal_esi0", "cat"]).reset_index(drop=True)
        m = smf.wls(f"{col} ~ T + {CTRL}{extra}", dd, weights=dd.fact_cal_esi0).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(dd.clu0)[0]})
        out[f"reg_{k}"] = {"coef": float(m.params["T"]), "ee": float(m.bse["T"]),
                           "ic95": [float(m.conf_int().loc["T", 0]), float(m.conf_int().loc["T", 1])], "n": int(m.nobs)}
    out["tratados_por_hora"] = resumen(trat[trat.dh.notna()], "dh")
    out["control_por_hora"] = resumen(ctrl[ctrl.dh.notna()], "dh")
    # efecto individual para sortear: cambio de cada tratado menos la media ponderada del control
    mc = out["control"]["media"]
    q = wq(trat.d - mc, trat.fact_cal_esi0)
    out["efecto_individual_dist"] = dict(zip(("p10", "p25", "p50", "p75", "p90"), q))
    return out


res = {}
for cat, g in (("todos", S), ("privado", S[S.cat == "privado"]), ("publico", S[S.cat == "publico"])):
    ex = " + C(cat)" if cat == "todos" else ""
    b40 = g[g.habituales0.between(40, 49)]
    r = {
        # principal: parte en 40-49 horas
        "40a49_a_50mas_vs_sigue_40a49": efecto(b40[b40.habituales1 >= 50], b40[b40.habituales1.between(40, 49)], "50", ex),
        "40a49_a_55mas_vs_sigue_40a49": efecto(b40[b40.habituales1 >= 55], b40[b40.habituales1.between(40, 49)], "55", ex),
        # versión literal: cualquier jornada bajo el umbral
        "bajo50_a_50mas_vs_sigue_bajo50": efecto(g[(g.habituales0 < 50) & (g.habituales1 >= 50)], g[(g.habituales0 < 50) & (g.habituales1 < 50)], "50b", ex),
        "bajo55_a_55mas_vs_sigue_bajo55": efecto(g[(g.habituales0 < 55) & (g.habituales1 >= 55)], g[(g.habituales0 < 55) & (g.habituales1 < 55)], "55b", ex),
        # a la inversa: bajar el ritmo
        "45mas_a_bajo40_vs_sigue_45mas": efecto(g[(g.habituales0 >= 45) & (g.habituales1 < 40)], g[(g.habituales0 >= 45) & (g.habituales1 >= 45)], "baja", ex),
        "45mas_a_30a39_vs_sigue_45mas": efecto(g[(g.habituales0 >= 45) & g.habituales1.between(30, 39)], g[(g.habituales0 >= 45) & (g.habituales1 >= 45)], "baja30", ex),
    }
    res[cat] = r
R["horas_ingreso"] = res

# elasticidad del ingreso mensual a las horas habituales dentro del mismo empleador (todas las personas de S)
el = {}
for cat, g in (("todos", S), ("privado", S[S.cat == "privado"]), ("publico", S[S.cat == "publico"])):
    g = g[S.habituales0.between(10, 90) & S.habituales1.between(10, 90)].dropna(subset=["edad0", "sexo0", "edu0", "ola0"]).reset_index(drop=True)
    g["dlnh"] = np.log(g.habituales1) - np.log(g.habituales0)
    g["dlnh_sube"] = g.dlnh.clip(lower=0)
    g["dlnh_baja"] = g.dlnh.clip(upper=0)
    m = smf.wls(f"d ~ dlnh + {CTRL}", g, weights=g.fact_cal_esi0).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(g.clu0)[0]})
    m2 = smf.wls(f"d ~ dlnh_sube + dlnh_baja + {CTRL}", g, weights=g.fact_cal_esi0).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(g.clu0)[0]})
    el[cat] = {"elasticidad": [float(m.params["dlnh"]), float(m.bse["dlnh"])], "elasticidad_subidas": [float(m2.params["dlnh_sube"]), float(m2.bse["dlnh_sube"])],
               "elasticidad_bajadas": [float(m2.params["dlnh_baja"]), float(m2.bse["dlnh_baja"])], "n": int(m.nobs),
               "n_cambia_horas": int((g.habituales0 != g.habituales1).sum())}
R["elasticidad_ingreso_horas_mismo_empleador"] = el

# persistencia: de quienes subieron a 50+ en t+1, cuántos estaban en 50+ en t (sesgo por error de medición / reversión a la media)
b40 = S[S.habituales0.between(40, 49)]
R["transicion_horas_mismo_empleador"] = {
    "pasa_de_40a49_a_50mas": float(np.average(b40.habituales1 >= 50, weights=b40.fact_cal_esi0)),
    "pasa_de_40a49_a_55mas": float(np.average(b40.habituales1 >= 55, weights=b40.fact_cal_esi0)),
    "pasa_de_45mas_a_bajo40": float(np.average(S[S.habituales0 >= 45].habituales1 < 40, weights=S[S.habituales0 >= 45].fact_cal_esi0)),
    "n_40a49": int(len(b40)), "n_45mas": int((S.habituales0 >= 45).sum())}

# placebo de reversión a la media: quienes estaban en 50+ y vuelven a 40-49 contra quienes siguen en 50+
a50 = S[S.habituales0 >= 50]
R["placebo_50mas_a_40a49_vs_sigue_50mas"] = efecto(a50[a50.habituales1.between(40, 49)], a50[a50.habituales1 >= 50], "plac", " + C(cat)")

# ---------------------------------------------------------------- 4. horas largas y paso a directivo (CIUO gran grupo 1)
G = P[(P.activ0 == 1) & (P.activ1 == 1) & P.categoria_ocupacion0.isin([3, 4]) & P.b10.between(2, 9) & P.b11.between(1, 10)
      & P.edad0.between(18, 64) & P.habituales0.between(1, 120) & (P.edu0 != "nan")].copy()
G["dir"] = (G.b11 == 1).astype(float)
G["h50"] = (G.habituales0 >= 50).astype(float)
G["h55"] = (G.habituales0 >= 55).astype(float)
G["mismo_emp"] = G.inicio1.notna() & (G.inicio1 <= G.ym0)
dirr = {}
for nom, g in (("todos_asalariados", G), ("mismo_empleador", G[G.mismo_emp]), ("cambia_o_sin_dato_empleador", G[~G.mismo_emp])):
    fila = {}
    for h in ("h50", "h55"):
        t1, t0 = g[g[h] == 1], g[g[h] == 0]
        g = g.dropna(subset=["edad0", "sexo0", "edu0", "ola0", "fact_cal_esi0", "b10"]).reset_index(drop=True)
        t1, t0 = g[g[h] == 1], g[g[h] == 0]
        m = smf.wls(f"dir ~ {h} + {CTRL} + C(b10)", g, weights=g.fact_cal_esi0).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(g.clu0)[0]})
        fila[h] = {"tasa_horas_largas": float(np.average(t1.dir, weights=t1.fact_cal_esi0)), "n_horas_largas": int(len(t1)), "pasan_horas_largas": int(t1.dir.sum()),
                   "tasa_resto": float(np.average(t0.dir, weights=t0.fact_cal_esi0)), "n_resto": int(len(t0)), "pasan_resto": int(t0.dir.sum()),
                   "mpl_dif_con_controles": float(m.params[h]), "ee": float(m.bse[h]), "n": int(m.nobs)}
    dirr[nom] = fila
R["paso_a_directivo"] = dirr
R["paso_a_directivo_nota"] = ("Asalariados en ambas olas, CIUO gran grupo 2-9 en t; resultado: gran grupo 1 en t+1. MPL ponderado con controles de edad, "
                              "sexo, educación, ola y gran grupo de origen. Correlación, no efecto causal; el código CIUO a 1 dígito cambia también por error de codificación.")

json.dump(R, open(OUT, "w"), indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps(R, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
