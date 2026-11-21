"""Bienestar al tomar una pausa (año sabático) y al cambiar de jornada, ELSOC 2016-2022 (COES), archivo ancho.

Uso:
  uv run --with pandas --with numpy --with statsmodels python -I beneficios_elsoc.py <ELSOC_Wide_2016_2022_v1.00.tab> <salida.json>

Olas: w01=2016, w02=2017, w03=2018, w04=2019, w05=2021, w06=2022. m12 (horas semanales) solo en 2016, 2018 y 2021.
m02 actividad principal: 1 jornada completa, 2 jornada parcial, 3 estudia y trabaja, 4 solo estudia, 5 jubilado o pensionado,
6 desempleado buscando, 7 quehaceres del hogar, 8 enfermo crónico o con discapacidad, 9 otra. El código 5 = jubilado se
verifica abajo con la edad media por código (se reporta en el JSON).
Escalas: s01 satisfacción con la vida y s03 salud autorreportada, 1-5, pasadas a 0-100 con (x-1)*25.
PHQ-9: suma de s11_01..09 (cada uno 1-4 -> 0-3), dep_mod = PHQ-9 >= 10.
Efectos fijos de persona y de ola (within), sin ponderar, EE agrupados por persona, 18-60 años. Además se reportan diferencias
simples de cambios individuales (ponderadas con ponderador02 de la ola de origen) con sus percentiles para sortear.
"""
import json
import sys

import numpy as np
import pandas as pd

F, OUT = sys.argv[1], sys.argv[2]
W = {"w01": 1, "w02": 2, "w03": 3, "w04": 4, "w05": 5, "w06": 6}
ANIO = {1: 2016, 2: 2017, 3: 2018, 4: 2019, 5: 2021, 6: 2022}
V = ["s01", "s03", "m02", "m12", "m0_edad", "m0_sexo", "ponderador02"] + [f"s11_0{i}" for i in range(1, 10)]
cols = pd.read_csv(F, sep="\t", nrows=0).columns
usar = ["idencuesta"] + [c for c in cols if any(c == f"{v}_{w}" for v in V for w in W)]
wide = pd.read_csv(F, sep="\t", usecols=usar, low_memory=False)
filas = []
for w, o in W.items():
    x = pd.DataFrame({"id": wide.idencuesta.astype(str), "ola": o})
    for v in V:
        c = f"{v}_{w}"
        x[v] = pd.to_numeric(wide[c], errors="coerce") if c in wide else np.nan
    filas.append(x)
d = pd.concat(filas, ignore_index=True)
for v in V:
    d[v] = d[v].where(d[v] >= 0)
d = d[d.m0_edad.notna()]
d["s01"] = ((d.s01.where(d.s01.between(1, 5))) - 1) * 25
d["s03"] = ((d.s03.where(d.s03.between(1, 5))) - 1) * 25
phq = pd.concat([d[f"s11_0{i}"].where(d[f"s11_0{i}"].between(1, 4)) - 1 for i in range(1, 10)], axis=1)
d["phq9"] = phq.sum(axis=1, min_count=9)
d["dep_mod"] = (d.phq9 >= 10).astype(float).where(d.phq9.notna())
d["m12"] = d.m12.where(d.m12.between(1, 100))
d["emp"] = np.select([d.m02.isin([1, 2, 3]), d.m02.eq(6), d.m02.eq(5), d.m02.isin([4, 7, 9]), d.m02.eq(8)],
                     ["O", "D", "J", "P", "E"], default="")
d = d.sort_values(["id", "ola"]).reset_index(drop=True)
R = {"fuente": "ELSOC 2016-2022 (COES), ELSOC_Wide_2016_2022_v1.00.tab", "script": "scripts/modelo/beneficios_elsoc.py"}
R["chequeo_m02_edad_media"] = {int(k): [round(float(v), 1), int(n)] for (k, v), n in
                               zip(d.groupby("m02").m0_edad.mean().items(), d.groupby("m02").size().values)}
R["chequeo_correlaciones"] = {"s01_phq9": round(float(d[["s01", "phq9"]].corr().iloc[0, 1]), 3),
                              "s03_edad": round(float(d[["s03", "m0_edad"]].corr().iloc[0, 1]), 3)}


def fe(data, y, xs):
    t = data[["id", "ola", y] + xs].dropna()
    t = t[t.groupby("id").id.transform("size") >= 2]
    Wd = pd.get_dummies(t.ola, prefix="o", drop_first=True).astype(float)
    X = pd.concat([t[xs].astype(float), Wd], axis=1)
    cl = list(X.columns)
    Z = pd.concat([t[["id", y]], X], axis=1)
    Zd = Z[[y] + cl] - Z.groupby("id")[[y] + cl].transform("mean")
    keep = [c for c in cl if Zd[c].abs().sum() > 1e-9]
    Xm, yv = Zd[keep].values, Zd[y].values
    XtX = np.linalg.pinv(Xm.T @ Xm)
    b = XtX @ Xm.T @ yv
    u = yv - Xm @ b
    G, N, K = t.id.nunique(), len(t), len(keep) + t.id.nunique()
    S = np.zeros((len(keep), len(keep)))
    for _, idx in t.groupby("id").indices.items():
        s = Xm[idx].T @ u[idx]
        S += np.outer(s, s)
    V_ = XtX @ S @ XtX * (G / (G - 1)) * ((N - 1) / max(N - K, 1))
    se = np.sqrt(np.diag(V_))
    out = {"n_obs": N, "n_personas": G}
    for i, c in enumerate(keep):
        if c in xs:
            out[c] = {"coef": round(float(b[i]), 4), "ee": round(float(se[i]), 4),
                      "ic95": [round(float(b[i] - 1.96 * se[i]), 4), round(float(b[i] + 1.96 * se[i]), 4)],
                      "obs_con_1": int(t[c].sum())}
    return out


Q = (0.1, 0.25, 0.5, 0.75, 0.9)


def wq(x, w):
    x, w = np.asarray(x, float), np.asarray(w, float)
    o = np.argsort(x)
    c = np.cumsum(w[o]) / w.sum()
    return {f"p{int(q * 100)}": float(x[o][min(np.searchsorted(c, q), len(x) - 1)]) for q in Q}


def resumen(x, w):
    x, w = np.asarray(x, float), np.asarray(w, float)
    ok = ~np.isnan(x) & ~np.isnan(w)
    x, w = x[ok], w[ok]
    if len(x) == 0:
        return {"n": 0}
    mu = np.average(x, weights=w)
    neff = w.sum() ** 2 / (w ** 2).sum()
    sd = np.sqrt(np.average((x - mu) ** 2, weights=w))
    return {"media": round(float(mu), 3), "ee": round(float(sd / np.sqrt(neff)), 3), "sd": round(float(sd), 3), "n": int(len(x))} | wq(x, w)


# ------------------------------------------------------------------ A. pausa: ocupado -> inactivo no jubilado
d["p_emp"] = d.groupby("id").emp.shift(1)
d["p_ola"] = d.groupby("id").ola.shift(1)
d["n_emp"] = d.groupby("id").emp.shift(-1)
a = d[d.m0_edad.between(18, 60)].copy()
pausa = {}
for nom, dest in (("principal_estudio_hogar_otra", ["P"]), ("incluye_enfermedad", ["P", "E"])):
    t = a.copy()
    t["ev"] = (t.p_emp == "O") & t.emp.isin(dest)
    first = t[t.ev].groupby("id").ola.min()
    t["ev_ola"] = t.id.map(first)
    t = t[t.groupby("id").emp.transform(lambda s: (s == "O").any())]          # en riesgo: alguna vez ocupado
    # el control (nunca tratado) se limita a quienes trabajan en todas sus olas, para que no entren otras salidas
    nunca = t.ev_ola.isna()
    t = t[~nunca | t.groupby("id").emp.transform(lambda s: (s == "O").all())]
    k = t.ola - t.ev_ola
    t["ev_pre2"] = (k <= -2).astype(float)
    t["ev_0"] = (k == 0).astype(float)
    t["ev_1_vuelve"] = ((k == 1) & (t.emp == "O")).astype(float)
    t["ev_1_sigue_fuera"] = ((k == 1) & (t.emp != "O")).astype(float)
    t["ev_2mas"] = (k >= 2).astype(float)
    xs = ["ev_pre2", "ev_0", "ev_1_vuelve", "ev_1_sigue_fuera", "ev_2mas"]
    res = {"n_eventos": int(first.reindex(t.id.unique()).notna().sum()),
           "destinos_m02_en_evento": {int(kk): int(v) for kk, v in t[k == 0].m02.value_counts().items()}}
    for y in ("s01", "s03", "dep_mod", "phq9"):
        res[y] = fe(t, y, xs)
    pausa[nom] = res

# cambios simples (diferencias individuales ponderadas) para sortear: ola del evento menos ola anterior
prev = d.groupby("id")[["s01", "s03", "dep_mod"]].shift(1)
for y in ("s01", "s03", "dep_mod"):
    a["d_" + y] = a[y] - prev.loc[a.index, y]
a["w0"] = d.groupby("id").ponderador02.shift(1).loc[a.index]
trat = a[(a.p_emp == "O") & (a.emp == "P")]
ctrl = a[(a.p_emp == "O") & (a.emp == "O")]
pausa["cambio_simple_ola_evento"] = {y: {"pausa": resumen(trat["d_" + y], trat.w0), "sigue_ocupado": resumen(ctrl["d_" + y], ctrl.w0)}
                                     for y in ("s01", "s03", "dep_mod")}
# año siguiente: de los que pausaron, los que vuelven a trabajar en la ola siguiente; cambio respecto de la ola previa a la pausa
a["pp_emp"] = d.groupby("id").emp.shift(2).loc[a.index]
prev2 = d.groupby("id")[["s01", "s03", "dep_mod"]].shift(2)
for y in ("s01", "s03", "dep_mod"):
    a["d2_" + y] = a[y] - prev2.loc[a.index, y]
v = a[(a.pp_emp == "O") & (a.p_emp == "P") & (a.emp == "O")]
cc = a[(a.pp_emp == "O") & (a.p_emp == "O") & (a.emp == "O")]
a["w00"] = d.groupby("id").ponderador02.shift(2).loc[a.index]
v, cc = a.loc[v.index], a.loc[cc.index]
pausa["cambio_simple_vuelve_a_trabajar_vs_dos_olas_antes"] = {y: {"pausa_y_vuelve": resumen(v["d2_" + y], v.w00), "siempre_ocupado": resumen(cc["d2_" + y], cc.w00)}
                                                               for y in ("s01", "s03", "dep_mod")}
# qué pasa en la ola siguiente a la pausa
s = a[(a.p_emp == "O") & (a.emp == "P") & a.n_emp.notna()]
pausa["estado_ola_siguiente"] = {kk: round(float(np.average(s.n_emp == kk, weights=s.ponderador02.fillna(s.ponderador02.mean()))), 3) for kk in ("O", "D", "P", "J", "E")} | {"n": int(len(s))}
pausa["nota"] = ("Pausa = ocupado (m02 1-3) en la ola anterior e inactivo no jubilado en la actual: solo estudia (4), quehaceres del hogar (7) u otra (9); "
                 "'incluye_enfermedad' suma m02=8. No se sabe si la salida fue voluntaria. k = olas desde la primera pausa; referencia k=-1. "
                 "ev_1_vuelve: ola siguiente a la pausa y de nuevo ocupado; ev_1_sigue_fuera: ola siguiente sin trabajar. Control: personas ocupadas en todas sus olas. "
                 "Entre olas hay 1 año, salvo 2019-2021 (2 años).")
R["pausa"] = pausa

# ------------------------------------------------------------------ B. jornada: m12 en 2016, 2018, 2021
h = a[(a.emp == "O") & a.m12.notna()].copy()
h["b"] = pd.cut(h.m12, [0, 29, 39, 45, 54, 100], labels=["lt30", "30_39", "40_45", "46_54", "55mas"])
for bb in ("lt30", "30_39", "46_54", "55mas"):
    h["h_" + bb] = (h.b == bb).astype(float)
hx = ["h_lt30", "h_30_39", "h_46_54", "h_55mas"]
R["jornada_fe"] = {y: fe(h, y, hx) for y in ("s01", "s03", "dep_mod")}
R["jornada_fe"]["nota"] = "Ocupados con m12 en 2016, 2018, 2021; referencia 40-45 horas; FE persona y ola."
# cambios individuales entre olas con horas (siguiente observación con horas de la misma persona)
h = h.sort_values(["id", "ola"])
for col in ("m12", "s01", "s03", "dep_mod", "ponderador02", "ola"):
    h["p_" + col] = h.groupby("id")[col].shift(1)
hh = h[h.p_m12.notna()]
tr = {}
for nom, tm, cm in (
        ("40a45_a_55mas_vs_sigue_40a45", hh.p_m12.between(40, 45) & (hh.m12 >= 55), hh.p_m12.between(40, 45) & hh.m12.between(40, 45)),
        ("45mas_a_bajo40_vs_sigue_45mas", (hh.p_m12 >= 45) & (hh.m12 < 40), (hh.p_m12 >= 45) & (hh.m12 >= 45))):
    out = {}
    for y in ("s01", "s03", "dep_mod"):
        dy = hh[y] - hh["p_" + y]
        T, C = resumen(dy[tm], hh.p_ponderador02[tm]), resumen(dy[cm], hh.p_ponderador02[cm])
        dif = T["media"] - C["media"]
        out[y] = {"tratados": T, "control": C, "dif": round(dif, 3), "ee_dif": round(float(np.hypot(T["ee"], C["ee"])), 3),
                  "ic95": [round(dif - 1.96 * float(np.hypot(T["ee"], C["ee"])), 3), round(dif + 1.96 * float(np.hypot(T["ee"], C["ee"])), 3)]}
    tr[nom] = out
R["jornada_cambios"] = tr
R["jornada_cambios"]["nota"] = ("Pares de olas con horas (2016-2018, 2018-2021), ocupados en ambas. Cambio individual de s01/s03 (0-100) y dep_mod. "
                                "Ponderado con ponderador02 de la ola de origen; EE con n efectivo. Diferencia simple, sin controles.")
json.dump(R, open(OUT, "w"), indent=1, ensure_ascii=False)
print(json.dumps(R, indent=1, ensure_ascii=False))
