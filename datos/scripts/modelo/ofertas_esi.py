"""Sueldos por ocupación, tamaño, sector, antigüedad, horas y cuenta propia con la ESI 2023, 2024 y 2025 (INE).
Además, el panel corto que deja la rotación de la ENE: la misma persona (idrph) aparece en oct-dic de un
año y del siguiente (2023-2024 y 2024-2025).

Uso:
  uv run --with pandas --with numpy --with statsmodels python -I ofertas_esi.py <datos_laborales> <salida.json>

Convenciones:
- Ingreso = ing_t_p (ingreso mensual neto de la ocupación principal), solo ocup_ref == 1 e ing_t_p > 0,
  ponderado con fact_cal_esi. Horas y shares de ocupados con fact_cal.
- Los pesos de cada ola son nominales. Para comparar olas se usa el ingreso relativo a la mediana de los
  ocupados de esa misma ola (no se usa un IPC externo).
- cine11_1d: 0-2 media o menos, 3 técnica superior, 4 universitaria, 5-6 postgrado.
- categoria_ocupacion: 1 empleador, 2 cuenta propia, 3 asalariado privado, 4 asalariado público.
- b1: gran grupo CIUO-08 (1-9, 10 FF.AA.). La ESI pública no trae más dígitos.
- b15_1: personas en la empresa (1 <5, 2 5-10, 3 11-49, 4 50-199, 5 200+).
- b17_mes/b17_ano: mes y año en que empezó a trabajar en el empleo actual.
- Errores estándar agrupados por conglomerado (y ola) en las regresiones; ponderadas con fact_cal_esi.
"""
import json
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

D, OUT = sys.argv[1], sys.argv[2]
COLS = ["ano_encuesta", "mes_encuesta", "conglomerado", "idrph", "sexo", "edad", "b1", "b15_1", "b17_mes",
        "b17_ano", "cine11_1d", "categoria_ocupacion", "habituales", "ing_t_p", "ocup_ref", "fact_cal_esi",
        "fact_cal", "activ", "region", "r_p_rev4cl_caenes", "ocup_form"]
ARCH = {2023: "esi_2023.csv", 2024: "esi_2024.csv", 2025: "esi_2025_personas.csv"}
RNG = np.random.default_rng(20261121)

olas = []
for a, f in ARCH.items():
    x = pd.read_csv(f"{D}/esi_ine/{f}", sep=None, engine="python", encoding="latin-1", usecols=lambda c: c in COLS)
    x["ola"] = a
    olas.append(x)
E = pd.concat(olas, ignore_index=True)
E["edu"] = pd.cut(E.cine11_1d.where(E.cine11_1d <= 6), [-1, 2, 3, 4, 6], labels=["media", "tecnica", "universitaria", "postgrado"])
E["superior"] = E.cine11_1d.between(3, 6)
E["ym"] = E.ano_encuesta * 12 + E.mes_encuesta
E["inicio"] = np.where(E.b17_ano.between(1940, 2026) & E.b17_mes.between(1, 12), E.b17_ano * 12 + E.b17_mes, np.nan)
E["antig"] = (E.ym - E.inicio) / 12
E["ing_ok"] = (E.ocup_ref == 1) & (E.ing_t_p > 0) & (E.fact_cal_esi > 0)
E["lny"] = np.log(E.ing_t_p.where(E.ing_ok))
E["clu"] = E.ola.astype(str) + "_" + E.conglomerado.astype(str)
E["tipo"] = np.select(
    [E.categoria_ocupacion == 4, (E.categoria_ocupacion == 3) & E.b15_1.between(1, 4), (E.categoria_ocupacion == 3) & (E.b15_1 == 5)],
    ["estado", "pyme", "grande"], default="")
R = {}


def wmed(x, w):
    o = np.argsort(x)
    x, w = np.asarray(x)[o], np.asarray(w)[o]
    c = (np.cumsum(w) - w / 2) / w.sum()          # regla de interpolación del manual INE
    return float(np.interp(0.5, c, x))


# med de cada ola (ocupados con ingreso), para pasar todo a ingreso relativo
MED = {a: wmed(g.ing_t_p, g.fact_cal_esi) for a, g in E[E.ing_ok].groupby("ola")}
R["mediana_ola"] = MED
E["lrel"] = E.lny - np.log(E.ola.map(MED))

# ------------------------------------------------------------------ 1. sueldo relativo por gran grupo CIUO
occ = {}
base = E[E.ing_ok & E.edad.between(25, 54) & E.superior & E.b1.between(1, 10)]
univ = E[E.ing_ok & E.edad.between(25, 54) & E.cine11_1d.between(4, 6) & E.b1.between(1, 10)]
tot = E[E.ing_ok & E.edad.between(25, 54) & E.b1.between(1, 10)]
for g in range(1, 11):
    fila = {"rel_superior_por_ola": {}, "rel_todos_por_ola": {}, "rel_univ_por_ola": {}, "n_superior": 0, "n_todos": 0, "n_univ": 0}
    for a in ARCH:
        bu = univ[univ.ola == a]
        u_ = bu[bu.b1 == g]
        if len(u_) >= 30:
            fila["rel_univ_por_ola"][a] = wmed(u_.ing_t_p, u_.fact_cal_esi) / wmed(bu.ing_t_p, bu.fact_cal_esi)
        fila["n_univ"] += len(u_)
        bs, ba = base[base.ola == a], tot[tot.ola == a]
        ms, ma = wmed(bs.ing_t_p, bs.fact_cal_esi), wmed(ba.ing_t_p, ba.fact_cal_esi)
        s, t = bs[bs.b1 == g], ba[ba.b1 == g]
        if len(s) >= 30:
            fila["rel_superior_por_ola"][a] = wmed(s.ing_t_p, s.fact_cal_esi) / ms
            fila["mediana_superior_por_ola"] = fila.get("mediana_superior_por_ola", {}) | {a: wmed(s.ing_t_p, s.fact_cal_esi)}
        if len(t) >= 30:
            fila["rel_todos_por_ola"][a] = wmed(t.ing_t_p, t.fact_cal_esi) / ma
        fila["n_superior"] += len(s)
        fila["n_todos"] += len(t)
    for k in ("superior", "todos", "univ"):
        v = list(fila[f"rel_{k}_por_ola"].values())
        fila[f"rel_{k}"] = float(np.mean(v)) if v else None
        fila[f"rel_{k}_rango"] = [float(min(v)), float(max(v))] if v else None
    occ[g] = fila
R["ocupacion_gran_grupo"] = occ

# ------------------------------------------------------------------ 2. premio por tipo de empleador y tamaño
A = E[E.ing_ok & E.edad.between(18, 64) & E.categoria_ocupacion.isin([3, 4]) & E.habituales.between(30, 60)
      & E.b1.between(1, 10) & E.edu.notna()].copy()
A["lnh"] = np.log(A.habituales)
A["tam"] = np.where(A.categoria_ocupacion == 4, "publico", A.b15_1.map({1: "t1_<5", 2: "t2_5-10", 3: "t3_11-49", 4: "t4_50-199", 5: "t5_200+"}))
A = A[A.tam.notna()]
CTRL = "edad + I(edad**2) + C(sexo) + C(edu) + C(b1) + lnh + C(ola) + C(region)"


def wls(f, d):
    return smf.wls(f, d, weights=d.fact_cal_esi).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.clu)[0]})


m = wls(f"lny ~ C(tam, Treatment('t5_200+')) + {CTRL}", A)
R["premio_tamano_vs_200mas"] = {k.split("[T.")[1].rstrip("]"): [float(m.params[k]), float(m.bse[k])]
                                for k in m.params.index if k.startswith("C(tam")}
R["premio_tamano_n"] = int(m.nobs)
R["premio_tamano_n_por_categoria"] = A.tam.value_counts().to_dict()
A2 = A[A.tipo != ""]
m2 = wls(f"lny ~ C(tipo, Treatment('pyme')) + {CTRL}", A2)
R["premio_tipo_vs_pyme"] = {k.split("[T.")[1].rstrip("]"): [float(m2.params[k]), float(m2.bse[k])]
                            for k in m2.params.index if k.startswith("C(tipo")}
m2b = wls("lny ~ C(tipo, Treatment('pyme')) + edad + I(edad**2) + C(sexo) + C(edu) + lnh + C(ola) + C(region)", A2)
R["premio_tipo_vs_pyme_sin_ocupacion"] = {k.split("[T.")[1].rstrip("]"): [float(m2b.params[k]), float(m2b.bse[k])]
                                          for k in m2b.params.index if k.startswith("C(tipo")}
R["premio_tipo_n"] = int(m2.nobs)
# solo educación superior
A3 = A2[A2.edu.isin(["tecnica", "universitaria", "postgrado"])]
m3 = wls(f"lny ~ C(tipo, Treatment('pyme')) + {CTRL}", A3)
R["premio_tipo_vs_pyme_superior"] = {k.split("[T.")[1].rstrip("]"): [float(m3.params[k]), float(m3.bse[k])]
                                     for k in m3.params.index if k.startswith("C(tipo")}
R["premio_tipo_superior_n"] = int(m3.nobs)

# mezcla de empleadores entre quienes llevan menos de un año (asalariados, 18-64)
nu = E[(E.activ == 1) & E.edad.between(18, 64) & (E.tipo != "") & (E.antig < 1) & (E.antig >= 0)]
R["mezcla_recien_llegados"] = {t: float(nu.fact_cal[nu.tipo == t].sum() / nu.fact_cal.sum()) for t in ("estado", "pyme", "grande")}
R["mezcla_recien_llegados_n"] = int(len(nu))

# ------------------------------------------------------------------ 3. retorno a la antigüedad (corte transversal)
T = A[A.antig.notna() & (A.antig >= 0)].copy()
T["tr_antig"] = pd.cut(T.antig, [-0.01, 1, 2, 5, 10, 100], labels=["a0_<1", "a1_1-2", "a2_2-5", "a3_5-10", "a4_10+"], right=False)
m4 = wls(f"lny ~ C(tr_antig) + C(tipo) + {CTRL}", T[T.tipo != ""])
R["antiguedad_vs_menos_1"] = {k.split("[T.")[1].rstrip("]"): [float(m4.params[k]), float(m4.bse[k])]
                              for k in m4.params.index if k.startswith("C(tr_antig")}
m5 = wls(f"lny ~ antig + I(antig**2) + C(tipo) + {CTRL}", T[(T.tipo != "") & (T.antig <= 40)])
R["antiguedad_lineal"] = {k: [float(m5.params[k]), float(m5.bse[k])] for k in ("antig", "I(antig ** 2)")}
R["antiguedad_n"] = int(m4.nobs)

# ------------------------------------------------------------------ 4. horas largas por edad (ocupados)
H = E[(E.activ == 1) & E.edad.between(18, 64) & E.habituales.between(1, 120) & (E.fact_cal > 0)]
H = H.assign(banda=pd.cut(H.edad, [17, 24, 29, 34, 39, 44, 49, 54, 64], labels=["18-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-64"]))
horas = {}
for b, g in H.groupby("banda", observed=True):
    horas[b] = {"pct_50_o_mas": float(100 * g.fact_cal[g.habituales >= 50].sum() / g.fact_cal.sum()),
                "pct_55_o_mas": float(100 * g.fact_cal[g.habituales >= 55].sum() / g.fact_cal.sum()), "n": int(len(g))}
for nom, g in (("18-54", H[H.edad <= 54]), ("18-64", H)):
    horas[nom] = {"pct_50_o_mas": float(100 * g.fact_cal[g.habituales >= 50].sum() / g.fact_cal.sum()),
                  "pct_55_o_mas": float(100 * g.fact_cal[g.habituales >= 55].sum() / g.fact_cal.sum()), "n": int(len(g))}
    horas[nom]["por_ola_50"] = {int(a): float(100 * gg.fact_cal[gg.habituales >= 50].sum() / gg.fact_cal.sum()) for a, gg in g.groupby("ola")}
R["horas_largas"] = horas

# ------------------------------------------------------------------ 5. cuenta propia contra asalariado comparable
CPd = E[E.ing_ok & E.edad.between(25, 64) & E.categoria_ocupacion.isin([1, 2, 3, 4]) & E.edu.notna()
      & E.habituales.between(30, 80)].copy()
CPd["lnh"] = np.log(CPd.habituales)
CPd["cat"] = CPd.categoria_ocupacion.map({1: "empleador", 2: "cuenta_propia", 3: "asalariado", 4: "asalariado"})
cp = {}
for e in ("media", "tecnica", "universitaria", "postgrado", "todos"):
    d = CPd if e == "todos" else CPd[CPd.edu == e]
    f = "lny ~ C(cat, Treatment('asalariado')) + edad + I(edad**2) + C(sexo) + lnh + C(ola) + C(region)" + (" + C(edu)" if e == "todos" else "")
    mm = wls(f, d)
    out = {k.split("[T.")[1].rstrip("]"): [float(mm.params[k]), float(mm.bse[k])] for k in mm.params.index if k.startswith("C(cat")}
    resid = mm.resid
    for c in ("cuenta_propia", "asalariado", "empleador"):
        s = d.cat == c
        r_ = resid[s]
        w_ = d.fact_cal_esi[s]
        out[f"sd_resid_{c}"] = float(np.sqrt(np.sum(w_ * r_ ** 2) / w_.sum()))
        out[f"n_{c}"] = int(s.sum())
    # cociente de medianas dentro de celdas edad x sexo, promediado con el peso de los cuentapropistas
    d2 = d.assign(b=pd.cut(d.edad, [24, 34, 44, 54, 64]))
    rat, ws = [], []
    for _, g in d2.groupby(["b", "sexo"], observed=True):
        a_, c_ = g[g.cat == "asalariado"], g[g.cat == "cuenta_propia"]
        if len(a_) >= 30 and len(c_) >= 30:
            rat.append(np.log(wmed(c_.ing_t_p, c_.fact_cal_esi) / wmed(a_.ing_t_p, a_.fact_cal_esi)))
            ws.append(c_.fact_cal_esi.sum())
    out["log_cociente_medianas_celdas"] = float(np.average(rat, weights=ws)) if rat else None
    cp[e] = out
R["cuenta_propia"] = cp

# ------------------------------------------------------------------ 6. panel entre olas (rotación ENE)
K = ["idrph", "ola", "sexo", "edad", "categoria_ocupacion", "b1", "b15_1", "inicio", "ym", "lrel", "ing_ok",
     "habituales", "activ", "fact_cal_esi", "fact_cal", "tipo", "clu", "edu"]
P = []
for a in (2023, 2024):
    x, y = E[E.ola == a][K], E[E.ola == a + 1][K]
    j = x.merge(y, on="idrph", suffixes=("0", "1"))
    j = j[(j.sexo0 == j.sexo1) & (j.edad1 - j.edad0).between(0, 2)]
    P.append(j)
P = pd.concat(P, ignore_index=True)
R["panel_enlazados"] = int(len(P))
R["panel_coherentes_por_par"] = {f"{a}-{a + 1}": int((P.ola0 == a).sum()) for a in (2023, 2024)}

# a. asalariados en ambas olas: cambio de empleador (empleo actual empezó después de la entrevista anterior)
PA = P[(P.activ0 == 1) & (P.activ1 == 1) & P.categoria_ocupacion0.isin([3, 4]) & P.categoria_ocupacion1.isin([3, 4])
       & P.inicio1.notna() & P.edad0.between(18, 64)].copy()
PA["cambia"] = PA.inicio1 > PA.ym0
PA["banda"] = pd.cut(PA.edad0, [17, 29, 44, 59, 64], labels=["18-29", "30-44", "45-59", "60-64"])
cam = {"anual_total": float(np.average(PA.cambia, weights=PA.fact_cal0)), "n": int(len(PA)), "cambios": int(PA.cambia.sum())}
for b, g in PA.groupby("banda", observed=True):
    cam[str(b)] = {"tasa": float(np.average(g.cambia, weights=g.fact_cal0)), "n": int(len(g))}
R["panel_cambio_empleador_asalariados"] = cam

# b. cambio de ingreso relativo según cambio de empleador
PI = PA[PA.ing_ok0 & PA.ing_ok1].copy()
PI["d"] = PI.lrel1 - PI.lrel0
PI = PI[PI.d.between(-2, 2)]


def resumen(g, w="fact_cal_esi0"):
    x, ww = g.d.values, g[w].values
    mu = float(np.average(x, weights=ww))
    o = np.argsort(x)
    c = np.cumsum(ww[o]) / ww.sum()
    q = [float(x[o][np.searchsorted(c, qq)]) for qq in (0.1, 0.25, 0.5, 0.75, 0.9)]
    return {"media": mu, "sd": float(np.sqrt(np.average((x - mu) ** 2, weights=ww))), "p10": q[0], "p25": q[1], "p50": q[2],
            "p75": q[3], "p90": q[4], "share_sube": float(np.average(x > 0, weights=ww)),
            "share_sube_5pct": float(np.average(x > 0.05, weights=ww)), "n": int(len(g))}


R["panel_cambio_ingreso"] = {"se_queda": resumen(PI[~PI.cambia]), "cambia_empleador": resumen(PI[PI.cambia])}
mp = smf.wls("d ~ cambia + edad0 + C(ola0)", PI, weights=PI.fact_cal_esi0).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(PI.clu0)[0]})
R["panel_premio_cambio"] = [float(mp.params["cambia[T.True]"]), float(mp.bse["cambia[T.True]"]), int(mp.nobs)]

# c. traspaso del sueldo relativo del gran grupo al cambiar de ocupación
rel = {a: {g: np.log(v) for g, v in ((g, occ[g]["rel_todos_por_ola"].get(a)) for g in occ) if v} for a in ARCH}
PO = PI[PI.b10.between(1, 9) & PI.b11.between(1, 9)].copy()
PO["drel"] = [rel[a1].get(g1, np.nan) - rel[a0].get(g0, np.nan) for a0, a1, g0, g1 in zip(PO.ola0, PO.ola1, PO.b10, PO.b11)]
PO["cambia_ocup"] = PO.b10 != PO.b11
tras = {}
for nom, d in (("todos", PO), ("cambia_empleador", PO[PO.cambia]), ("mismo_empleador", PO[~PO.cambia])):
    mm = smf.wls("d ~ drel + edad0 + C(ola0)", d, weights=d.fact_cal_esi0).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.clu0)[0]})
    tras[nom] = {"traspaso": float(mm.params["drel"]), "ee": float(mm.bse["drel"]), "n": int(mm.nobs),
                 "n_cambia_gran_grupo": int(d.cambia_ocup.sum())}
R["panel_traspaso_ocupacion"] = tras

# d. horas: paso de menos de 50 a 50 o más horas habituales entre un año y el siguiente (ocupados en ambas)
PH = P[(P.activ0 == 1) & (P.activ1 == 1) & P.habituales0.between(1, 120) & P.habituales1.between(1, 120) & P.edad0.between(18, 64)]
bajo = PH[PH.habituales0 < 50]
alto = PH[PH.habituales0 >= 50]
R["panel_horas"] = {"pasa_a_50_o_mas": float(np.average(bajo.habituales1 >= 50, weights=bajo.fact_cal0)), "n_bajo_50": int(len(bajo)),
                    "sigue_50_o_mas": float(np.average(alto.habituales1 >= 50, weights=alto.fact_cal0)), "n_50_o_mas": int(len(alto)),
                    "pasa_a_menos_de_40_desde_44_o_mas": float(np.average(PH[PH.habituales0 >= 44].habituales1 < 40, weights=PH[PH.habituales0 >= 44].fact_cal0))}
PHb = PH.assign(banda=pd.cut(PH.edad0, [17, 29, 44, 64], labels=["18-29", "30-44", "45-64"]))
R["panel_horas"]["pasa_a_50_por_edad"] = {str(b): float(np.average(g[g.habituales0 < 50].habituales1 >= 50, weights=g[g.habituales0 < 50].fact_cal0))
                                          for b, g in PHb.groupby("banda", observed=True)}

# e. asalariado -> cuenta propia y cuenta propia que sigue: cambio de ingreso relativo
PC = P[P.ing_ok0 & P.ing_ok1 & P.edad0.between(25, 64)].copy()
PC["d"] = PC.lrel1 - PC.lrel0
PC = PC[PC.d.between(-3, 3)]
a2c = PC[PC.categoria_ocupacion0.isin([3, 4]) & (PC.categoria_ocupacion1 == 2)]
c2c = PC[(PC.categoria_ocupacion0 == 2) & (PC.categoria_ocupacion1 == 2)]
a2a = PC[PC.categoria_ocupacion0.isin([3, 4]) & PC.categoria_ocupacion1.isin([3, 4])]
R["panel_cuenta_propia"] = {"asalariado_a_cuenta_propia": resumen(a2c), "sigue_cuenta_propia": resumen(c2c), "sigue_asalariado": resumen(a2a)}
# entrada anual a cuenta propia desde asalariado
EA = P[(P.activ0 == 1) & P.categoria_ocupacion0.isin([3, 4]) & P.edad0.between(25, 64) & (P.activ1 == 1)]
R["panel_entrada_cuenta_propia"] = {"tasa": float(np.average(EA.categoria_ocupacion1.isin([1, 2]), weights=EA.fact_cal0)), "n": int(len(EA))}
SA = P[(P.activ0 == 1) & (P.categoria_ocupacion0 == 2) & P.edad0.between(25, 64)]
R["panel_salida_cuenta_propia"] = {"a_asalariado": float(np.average(SA.categoria_ocupacion1.isin([3, 4]) & (SA.activ1 == 1), weights=SA.fact_cal0)),
                                   "sigue_cuenta_propia": float(np.average((SA.categoria_ocupacion1 == 2) & (SA.activ1 == 1), weights=SA.fact_cal0)),
                                   "n": int(len(SA))}

# f. tipo de empleador al cambiar: se queda en el mismo tipo (pyme, grande, Estado)
PT = PA[PA.cambia & (PA.tipo0 != "") & (PA.tipo1 != "")]
R["panel_tipo_al_cambiar"] = {"mismo_tipo": float(np.average(PT.tipo0 == PT.tipo1, weights=PT.fact_cal0)), "n": int(len(PT)),
                              "origen": {t: float(np.average(PT.tipo0 == t, weights=PT.fact_cal0)) for t in ("pyme", "grande", "estado")},
                              "destino": {t: float(np.average(PT.tipo1 == t, weights=PT.fact_cal0)) for t in ("pyme", "grande", "estado")},
                              "matriz": {o: {t: float(np.average(g.tipo1 == t, weights=g.fact_cal0)) for t in ("pyme", "grande", "estado")} | {"n": int(len(g))}
                                         for o, g in PT.groupby("tipo0")}}

json.dump(R, open(OUT, "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps(R, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
