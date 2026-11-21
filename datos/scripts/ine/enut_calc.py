# ENUT 2023 (INE). Uso: enut_calc.py <dta> <salida.json>
import sys, json, numpy as np, pandas as pd, pyreadstat
T = ["t_to_dt","t_tdnr_dt","t_tcnr_dt","t_tnr_dt","t_vsyo_dt","t_vsyo_csar_dt","t_vsyomcm_dt","t_mcm_dt","t_cgt_dt",
     "vs1_t_ds","vs1_t_fds"]
cols = ["id_hog","n_linea_p","edad","sexo","cae","o22c","tiempo","fe_cut","c9b","c10b","cd11","cd24","vs1_p_ds","vs1_p_fds"] + T
df, m = pyreadstat.read_dta(sys.argv[1], usecols=cols)
# hijos propios: personas del hogar cuya madre (c9b) o padre (c10b) es la persona
kids = df[df.edad < 15]
def cuenta(maxe):
    k = kids[kids.edad < maxe]
    a = pd.concat([k[["id_hog","c9b"]].rename(columns={"c9b":"n_linea_p"}), k[["id_hog","c10b"]].rename(columns={"c10b":"n_linea_p"})]).dropna()
    return a.groupby(["id_hog","n_linea_p"]).size()
for maxe, nm in [(15,"hijos15"),(5,"hijos5")]:
    c = cuenta(maxe).rename(nm)
    df = df.merge(c, left_on=["id_hog","n_linea_p"], right_index=True, how="left")
    df[nm] = df[nm].fillna(0)
df["nna_hogar"] = df.groupby("id_hog")["edad"].transform(lambda e: (e < 15).sum())
r = df[(df.tiempo == 1)].copy()
for t in T:
    r.loc[r[t] >= 96, t] = np.nan          # 96 = valor perdido
    # NaN para quien respondió el CUT y no hizo la actividad = 0 horas
for t in T:
    r[t + "_0"] = r[t].fillna(0)
# quitar valores perdidos reales en las variables de ocupación y sociales
r = r[~r.sexo.isin([96])]
def wm(d, v):
    w = d.fe_cut; x = d[v]; ok = x.notna()
    return float((x[ok] * w[ok]).sum() / w[ok].sum()) if ok.any() else None
def wp(d, v):  # proporción de "Sí" (1) sobre 1/2
    d = d[d[v].isin([1, 2])]
    return float(((d[v] == 1) * d.fe_cut).sum() / d.fe_cut.sum()) if len(d) else None
out = {"fuente": "INE, II Encuesta Nacional de Uso del Tiempo 2023 (II ENUT), base Stata v2 (250403). Solo zonas urbanas.",
       "unidades": "horas por día tipo ((5·lunes-viernes + 2·fin de semana)/7), promedio poblacional: quien no hizo la actividad cuenta 0",
       "ponderador": "fe_cut (respondientes del cuestionario de uso del tiempo)"}
# (a) trabajo no remunerado por sexo y presencia de hijos propios < 15 y < 5, 18-50 años
a = r[(r.edad >= 18) & (r.edad <= 50)].copy()
a["grupo_hijos"] = np.where(a.hijos5 > 0, "con_hijo_0_4", np.where(a.hijos15 > 0, "con_hijos_5_14_sin_0_4", "sin_hijos_menores_15"))
tab = []
for (sx, g), d in a.groupby(["sexo", "grupo_hijos"]):
    tab.append({"sexo": {1:"hombre",2:"mujer"}[int(sx)], "hijos": g, "n": int(len(d)),
                "domestico_h": round(wm(d,"t_tdnr_dt_0"),2), "cuidados_h": round(wm(d,"t_tcnr_dt_0"),2),
                "no_remunerado_total_h": round(wm(d,"t_tnr_dt_0"),2), "remunerado_h": round(wm(d,"t_to_dt_0"),2),
                "carga_global_h": round(wm(d,"t_cgt_dt_0"),2), "vida_social_ocio_h": round(wm(d,"t_vsyo_dt_0"),2)})
for sx, d in a.groupby("sexo"):
    tab.append({"sexo": {1:"hombre",2:"mujer"}[int(sx)], "hijos": "todos", "n": int(len(d)),
                "domestico_h": round(wm(d,"t_tdnr_dt_0"),2), "cuidados_h": round(wm(d,"t_tcnr_dt_0"),2),
                "no_remunerado_total_h": round(wm(d,"t_tnr_dt_0"),2), "remunerado_h": round(wm(d,"t_to_dt_0"),2),
                "carga_global_h": round(wm(d,"t_cgt_dt_0"),2), "vida_social_ocio_h": round(wm(d,"t_vsyo_dt_0"),2)})
out["a_no_remunerado_18_50"] = {"definicion_hijos": "hijos propios en el hogar (el niño declara a la persona como madre o padre, c9b/c10b)", "tabla": tab}
# (b) ocupados 18-50 por tramo de horas habituales semanales (o22c)
b = r[(r.edad >= 18) & (r.edad <= 50) & (r.cae == 2) & r.o22c.between(1, 120)].copy()
b["tramo"] = pd.cut(b.o22c, [0, 29.99, 44.99, 54.99, 200], labels=["<30","30-44","45-54","55+"])
tb = []
for (tr), d in b.groupby("tramo", observed=True):
    tb.append({"tramo_horas_semana": str(tr), "n": int(len(d)), "horas_semana_media": round(wm(d,"o22c"),1),
       "vida_social_ocio_h": round(wm(d,"t_vsyo_dt_0"),2), "convivencia_social_recreacion_h": round(wm(d,"t_vsyo_csar_dt_0"),2),
       "conversar_compartir_familia_amigos_lunes_viernes_h": round(wm(d,"vs1_t_ds_0"),2),
       "conversar_compartir_familia_amigos_fin_semana_h": round(wm(d,"vs1_t_fds_0"),2),
       "medios_comunicacion_h": round(wm(d,"t_mcm_dt_0"),2), "no_remunerado_h": round(wm(d,"t_tnr_dt_0"),2),
       "p_se_junto_con_amigos_o_familia_no_conviviente_lunes_viernes": round(wp(d,"cd11"),3),
       "p_se_junto_con_amigos_o_familia_no_conviviente_fin_semana": round(wp(d,"cd24"),3),
       "p_compartio_con_familia_amigos_fin_semana": round(wp(d,"vs1_p_fds"),3)})
out["b_ocio_segun_horas_ocupados_18_50"] = tb
# regresión WLS: y = a + b·horas + controles (sexo, edad, edad², hijos<15, hijos<5)
def wls(d, y):
    d = d.dropna(subset=[y])
    X = np.column_stack([np.ones(len(d)), d.o22c, d.sexo == 2, d.edad, d.edad**2, d.hijos15 > 0, d.hijos5 > 0]).astype(float)
    w = np.sqrt(d.fe_cut.values); Y = d[y].values
    beta, *_ = np.linalg.lstsq(X * w[:, None], Y * w, rcond=None)
    res = Y - X @ beta; W = d.fe_cut.values
    # error estándar robusto (HC1) con pesos, sin diseño complejo
    XtWX = np.linalg.inv((X * W[:, None]).T @ X); meat = (X * (W * res)[:, None]).T @ (X * (W * res)[:, None])
    V = XtWX @ meat @ XtWX * len(d) / (len(d) - X.shape[1])
    return float(beta[1]), float(np.sqrt(V[1, 1])), int(len(d))
bb = b[b.o22c.between(10, 90)]
reg = {}
for y in ["t_vsyo_dt_0","t_vsyo_csar_dt_0","vs1_t_ds_0","vs1_t_fds_0","t_tnr_dt_0"]:
    be, se, n = wls(bb, y); mean45 = wm(bb[bb.o22c.between(40, 50)], y)
    reg[y.replace("_0","")] = {"min_dia_por_hora_semanal_extra": round(be*60,2), "ee_min": round(se*60,2), "n": n,
        "media_h_ocupados_40_50h": round(mean45,2), "cambio_pct_por_hora_extra": round(100*be/mean45,2)}
bin_ = bb.copy(); bin_["y"] = (bin_.cd24 == 1).astype(float); bin_ = bin_[bin_.cd24.isin([1,2])]
be, se, n = wls(bin_, "y"); p45 = wm(bin_[bin_.o22c.between(40,50)], "y")
reg["p_juntarse_fin_semana"] = {"puntos_por_hora_semanal_extra": round(be*100,3), "ee": round(se*100,3), "n": n,
    "p_ocupados_40_50h": round(p45,3), "cambio_pct_por_hora_extra": round(100*be/p45,2)}
out["b_regresion_wls"] = {"muestra": "ocupados 18-50 con 10-90 horas habituales", "controles": "sexo, edad, edad², hijos<15, hijos<5", "resultados": reg,
    "nota": "error estándar HC1 con pesos, ignora estratos y conglomerados (subestima algo el error)"}
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
