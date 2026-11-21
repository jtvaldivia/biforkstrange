"""Ofertas de trabajo, búsqueda y aceptación con la SCE Labor Market Survey (Fed de Nueva York).

EE.UU., 2014-2024 (microdatos) y 2014-2026 (series publicadas por edad).
Uso:
  uv run --with pandas --with numpy --with openpyxl --with statsmodels python -I ofertas_sce.py <datos_laborales> <salida.json>

Población principal: asalariados (lmtype no vacío: trabajan para otro), con sueldo anual l3 entre
US$15.000 y US$1.000.000 (filtra jornadas muy parciales y errores de tipeo). Ponderador lm_weights.
Errores estándar por bootstrap agrupado por persona (userid), 400 réplicas.

Variables (cuestionario SCE Labor):
  js6  búsqueda en las últimas 4 semanas: 1 para dejar el empleo, 2 para un empleo adicional, 3 no
  nl1  ofertas recibidas en los últimos 4 meses (10 = 10 o más)
  nl2a_k / nl2b_k  sueldo anual de la oferta k (hasta 3, las mejores) y si es jornada completa (1)
  nl3_k  1 aceptó y trabaja ahí, 2 aceptó y ya no, 3 rechazó, 4 decidiendo
  rw2a   salario de reserva anual (desde marzo 2017 siempre anual)
  l1m/l1y  inicio del empleo actual; l3 sueldo anual actual
"""
import json
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

D, OUT = sys.argv[1], sys.argv[2]
XL = f"{D}/sce_nyfed/sce-labor-microdata-public.xlsx"
CH = f"{D}/sce_nyfed/sce-labor-chart-data-public.xlsx"
RNG = np.random.default_rng(20261121)
B = 400

df = pd.read_excel(XL, sheet_name="Data", header=1, engine="openpyxl")
df = df.sort_values(["userid", "date"]).reset_index(drop=True)
df["ym"] = (df.date // 100) * 12 + (df.date % 100)          # mes absoluto
df["w"] = df.lm_weights.fillna(0)

asal = df[df.lmtype.notna() & df.l1y.notna() & df.l3.between(15_000, 1_000_000)].copy()
asal = asal[asal.date >= 201411]                              # nl1 existe desde nov-2014
asal["busca"] = asal.js6.map({1: "busca", 2: "adicional", 3: "no_busca"})
asal["nl1c"] = asal.nl1.clip(upper=10)


def wmean(x, w):
    m = np.isfinite(x) & np.isfinite(w)
    return float(np.sum(x[m] * w[m]) / np.sum(w[m]))


def boot(data, f, b=B):
    """Bootstrap agrupado por userid. f(data) -> escalar o dict de escalares."""
    ids = data.userid.unique()
    grp = {u: ix for u, ix in data.groupby("userid").indices.items()}
    est = f(data)
    reps = []
    for _ in range(b):
        s = RNG.choice(ids, len(ids), replace=True)
        ix = np.concatenate([grp[u] for u in s])
        reps.append(f(data.iloc[ix]))
    if isinstance(est, dict):
        return {k: (est[k], float(np.nanstd([r[k] for r in reps]))) for k in est}
    return est, float(np.nanstd(reps))


R = {}

# ------------------------------------------------------------------ 1. tasa de ofertas
def tasas(d):
    out = {}
    for g in ("busca", "no_busca", "adicional"):
        s = d[d.busca == g]
        out[f"ofertas_4m_{g}"] = wmean(s.nl1c.values, s.w.values)
        out[f"p_alguna_4m_{g}"] = wmean((s.nl1c > 0).astype(float).values, s.w.values)
        out[f"ofertas_4m_tope4_{g}"] = wmean(s.nl1c.clip(upper=4).values, s.w.values)
    s = d[d.busca.notna()]
    out["ofertas_4m_todos"] = wmean(s.nl1c.values, s.w.values)
    out["ofertas_4m_tope4_todos"] = wmean(s.nl1c.clip(upper=4).values, s.w.values)
    out["share_busca"] = wmean((s.busca == "busca").astype(float).values, s.w.values)
    out["share_adicional"] = wmean((s.busca == "adicional").astype(float).values, s.w.values)
    for g in ("busca", "no_busca"):
        out[f"p_alguna_anual_{g}"] = 1 - (1 - out[f"p_alguna_4m_{g}"]) ** 3
    out["p_alguna_anual_todos"] = 1 - (1 - wmean((s.nl1c > 0).astype(float).values, s.w.values)) ** 3
    out["busca_mult"] = out["ofertas_4m_busca"] / out["ofertas_4m_no_busca"]
    out["busca_mult_tope4"] = out["ofertas_4m_tope4_busca"] / out["ofertas_4m_tope4_no_busca"]
    # fracción de las ofertas que recibe quien no buscó en las últimas 4 semanas
    tot = (s.nl1c * s.w).sum()
    out["frac_ofertas_sin_buscar"] = float((s.nl1c * s.w)[s.busca == "no_busca"].sum() / tot)
    out["frac_ofertas_sin_buscar_tope4"] = float((s.nl1c.clip(upper=4) * s.w)[s.busca == "no_busca"].sum()
                                                 / (s.nl1c.clip(upper=4) * s.w).sum())
    return out


d1 = asal[asal.nl1c.notna() & asal.busca.notna()]
R["tasas"] = boot(d1, tasas)
R["tasas_n"] = {g: int((d1.busca == g).sum()) for g in ("busca", "no_busca", "adicional")}
R["tasas_n_personas"] = int(d1.userid.nunique())

# ------------------------------------------------------------------ 2. cambio de empleador (panel 4 meses)
# Pares de olas consecutivas (4 meses) de la misma persona, asalariada en ambas. Cambio = el empleo
# actual empezó después del mes de la entrevista anterior. Se excluyen 2023-03 a 2024-03: l1y no
# permitía elegir 2023-2024 (nota del archivo).
p = df.copy()
p["prev_ym"] = p.groupby("userid").ym.shift()
p["es_asal"] = (p.lmtype.notna() & p.l1y.notna()).astype(float)
p["l1"] = p.l1y * 12 + p.l1m
p["prev_asal"] = p.groupby("userid").es_asal.shift().eq(1)
p["prev_l3"] = p.groupby("userid").l3.shift()
p["prev_js6"] = p.groupby("userid").js6.shift()
par = p[(p.ym - p.prev_ym == 4) & p.prev_asal & p.lmtype.notna() & p.l1y.notna()
        & ~p.date.between(202303, 202407) & (p.date >= 201407)].copy()
par["cambio"] = (par.l1 > par.prev_ym).astype(float)          # empezó después de la entrevista anterior
par = par[par.l1.notna()]


def j2j(d):
    out = {"j2j_4m": wmean(d.cambio.values, d.w.values)}
    out["j2j_anual"] = 1 - (1 - out["j2j_4m"]) ** 3
    for g, v in (("busca", 1), ("no_busca", 3)):
        s = d[d.prev_js6 == v]
        out[f"j2j_4m_{g}"] = wmean(s.cambio.values, s.w.values)
    return out


R["j2j"] = boot(par, j2j)
R["j2j_n"] = int(len(par))
R["j2j_cambios"] = int(par.cambio.sum())

# ------------------------------------------------------------------ 3. sueldo de la oferta / sueldo actual
# Base del sueldo: si rechazó o está decidiendo, el l3 actual. Si aceptó y trabaja ahí (nl3=1), el l3 de la
# ola anterior, solo si 4 meses antes era asalariado y su empleo actual empezó después de esa entrevista.
p["nl1c"] = p.nl1.clip(upper=10)
filas = []
for k in (1, 2, 3):
    s = p[p.lmtype.notna() & p.l1y.notna() & (p[f"nl2a_{k}"] > 0) & (p[f"nl2b_{k}"] == 1) & (p.date >= 201411)]
    for _, r in s.iterrows():
        st = r[f"nl3_{k}"]
        if st in (3, 4):
            base, js = r.l3, r.js6
        elif st == 1 and (r.ym - r.prev_ym == 4) and bool(r.prev_asal) and r.l1 > r.prev_ym:
            base, js = r.prev_l3, r.prev_js6
        else:
            continue
        if not (15_000 <= (base or 0) <= 1_000_000):
            continue
        filas.append({"userid": r.userid, "w": r.w, "k": k, "estado": st, "js6": js, "js6_prev": r.prev_js6,
                      "lr": float(np.log(r[f"nl2a_{k}"] / base))})
of = pd.DataFrame(filas)
of = of[of.lr.between(np.log(0.2), np.log(5))]                  # descarta errores de unidad (x10, mensual)
of["acepta"] = (of.estado == 1).astype(float)

# las aceptadas solo se ven si hay ola anterior; se reponderan por la inversa de esa probabilidad
acept_tot = p[(p.date >= 201411) & p.lmtype.notna()][[f"nl3_{k}" for k in (1, 2, 3)]].eq(1).sum().sum()
acept_obs = (of.estado == 1).sum()
of["w2"] = of.w * np.where(of.estado == 1, acept_tot / max(acept_obs, 1), 1.0)


def wq(x, w, q):
    o = np.argsort(x)
    x, w = np.asarray(x)[o], np.asarray(w)[o]
    c = np.cumsum(w) / w.sum()
    return [float(x[np.searchsorted(c, qq)]) for qq in q]


def dist(d, col="w2"):
    x, w = d.lr.values, d[col].values
    m = wmean(x, w)
    sd = float(np.sqrt(np.sum(w * (x - m) ** 2) / w.sum()))
    q = wq(x, w, [0.1, 0.25, 0.5, 0.75, 0.9])
    return {"media": m, "sd": sd, "p10": q[0], "p25": q[1], "p50": q[2], "p75": q[3], "p90": q[4],
            "sd_robusta": (q[3] - q[1]) / 1.349, "share_mejora": wmean((x > 0).astype(float), w)}


dec = of[of.estado.isin([1, 3])]
R["oferta_rel"] = boot(dec, dist)
R["oferta_rel_n"] = {"ofertas": int(len(dec)), "aceptadas_con_base": int(acept_obs),
                     "aceptadas_total_en_datos": int(acept_tot), "personas": int(dec.userid.nunique())}
R["oferta_rel_rechazadas"] = boot(of[of.estado == 3], lambda d: dist(d, "w"))
R["oferta_rel_aceptadas"] = boot(of[of.estado == 1], lambda d: dist(d, "w"))

# ------------------------------------------------------------------ 4. aceptación
def acept(d):
    out = {"p_acepta": wmean(d.acepta.values, d.w2.values)}
    for g, v in (("busca", 1), ("no_busca", 3)):
        s = d[d.js6 == v]
        out[f"p_acepta_{g}"] = wmean(s.acepta.values, s.w2.values)
    return out


R["acepta"] = boot(dec, acept)

# aceptación sin necesitar sueldo base: todas las ofertas de quien era asalariado 4 meses antes,
# clasificadas por su búsqueda en esa ola anterior (así la búsqueda no es posterior al cambio)
fil2 = []
pp = p[p.lmtype.notna() & p.l1y.notna() & (p.date >= 201411) & (p.ym - p.prev_ym == 4) & p.prev_asal]
for k in (1, 2, 3):
    s = pp[pp[f"nl3_{k}"].isin([1, 2, 3])]
    fil2.append(pd.DataFrame({"userid": s.userid, "w": s.w, "js6_prev": s.prev_js6,
                              "acepta": s[f"nl3_{k}"].isin([1, 2]).astype(float), "ft": (s[f"nl2b_{k}"] == 1)}))
ac2 = pd.concat(fil2)


def acept2(d):
    out = {"p_acepta": wmean(d.acepta.values, d.w.values)}
    for g, v in (("busca", 1), ("no_busca", 3)):
        s = d[d.js6_prev == v]
        out[f"p_acepta_{g}"] = wmean(s.acepta.values, s.w.values)
    return out


R["acepta_panel"] = boot(ac2, acept2)
R["acepta_panel_n"] = {"ofertas": int(len(ac2)), "busca": int((ac2.js6_prev == 1).sum()),
                       "no_busca": int((ac2.js6_prev == 3).sum()), "personas": int(ac2.userid.nunique())}


# cola de mejoras: qué fracción de ofertas supera cada umbral y cuánto mejora la oferta que mejora
def cola(d):
    x, w = d.lr.values, d.w2.values
    out = {f"p_mayor_{t}": wmean((x > t).astype(float), w) for t in (0.0, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20)}
    pos = x > 0
    q = wq(x[pos], w[pos], [0.1, 0.25, 0.5, 0.75, 0.9])
    out.update({f"mejora_p{int(qq * 100)}": v for qq, v in zip([0.1, 0.25, 0.5, 0.75, 0.9], q)})
    return out


R["oferta_cola"] = boot(dec, cola)

# desde la no-ocupación: oferta / sueldo del último empleo (l9), jornada completa
ne = p[p.l7y.notna() & (p.js5 == 1) & p.l9.between(15_000, 1_000_000) & (p.date >= 201411)]
fil3 = []
for k in (1, 2, 3):
    s = ne[(ne[f"nl2a_{k}"] > 0) & (ne[f"nl2b_{k}"] == 1)]
    fil3.append(pd.DataFrame({"userid": s.userid, "w": s.w, "lr": np.log(s[f"nl2a_{k}"] / s.l9),
                              "estado": s[f"nl3_{k}"], "meses_sin": s.ym - (s.l7y * 12 + s.l7m)}))
ne_of = pd.concat(fil3)
ne_of = ne_of[ne_of.lr.between(np.log(0.2), np.log(5)) & (ne_of.meses_sin <= 24)]
ne_of["w2"] = ne_of.w
R["oferta_rel_desempleo"] = boot(ne_of, dist)
R["oferta_rel_desempleo_aceptadas"] = boot(ne_of[ne_of.estado.isin([1, 2])], lambda d: dist(d, "w"))
R["oferta_rel_desempleo_n"] = {"ofertas": int(len(ne_of)), "aceptadas": int(ne_of.estado.isin([1, 2]).sum()),
                               "personas": int(ne_of.userid.nunique())}
R["acepta_n"] = {"busca": int((dec.js6 == 1).sum()), "no_busca": int((dec.js6 == 3).sum())}

# umbral: logit de aceptar sobre log(oferta/actual); umbral = -b0/b1 (prob. 50%)
umb = {}
for g, v in (("todos", None), ("busca", 1), ("no_busca", 3)):
    s = dec if v is None else dec[dec.js6 == v]
    X = sm.add_constant(s.lr.values)
    m = sm.GLM(s.acepta.values, X, family=sm.families.Binomial(), freq_weights=s.w2.values).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(s.userid)[0]})
    b0, b1 = m.params
    V = m.cov_params()
    g0, g1 = -1 / b1, b0 / b1 ** 2
    se = float(np.sqrt(g0 ** 2 * V[0, 0] + g1 ** 2 * V[1, 1] + 2 * g0 * g1 * V[0, 1]))
    umb[g] = {"umbral_log": float(-b0 / b1), "ee": se, "b1": float(b1), "n": int(len(s))}
R["umbral_logit"] = umb

# ------------------------------------------------------------------ 5. salario de reserva / sueldo actual
rw = asal[(asal.date >= 201703) & asal.rw2a.between(5_000, 2_000_000)].copy()
rw["lr"] = np.log(rw.rw2a / rw.l3)
rw = rw[rw.lr.between(np.log(0.2), np.log(5))]


def resv(d):
    out = {}
    for g in ("busca", "no_busca", "adicional"):
        s = d[d.busca == g]
        q = wq(s.lr.values, s.w.values, [0.25, 0.5, 0.75])
        out[f"p25_{g}"], out[f"p50_{g}"], out[f"p75_{g}"] = q
        out[f"media_{g}"] = wmean(s.lr.values, s.w.values)
    return out


R["reserva"] = boot(rw, resv, b=200)
R["reserva_n"] = {g: int((rw.busca == g).sum()) for g in ("busca", "no_busca", "adicional")}

# ------------------------------------------------------------------ 6. edad: series publicadas (<=45 / >45)
import openpyxl  # noqa: E402

rows = list(openpyxl.load_workbook(CH, read_only=True, data_only=True)["Data"].iter_rows(values_only=True))
hdr = rows[:6]
cols = {}
for j in range(1, len(hdr[0])):
    cols[(str(hdr[3][j]).strip(), str(hdr[4][j]).strip(), str(hdr[5][j]).strip())] = j
data = [r for r in rows[6:] if r[0]]


def serie(key):
    j = cols[key]
    v = [r[j] for r in data if isinstance(r[j], (int, float))]
    return float(np.mean(v)), float(np.std(v) / np.sqrt(len(v))), len(v)


edad = {}
for g in ("<=45 years", ">45 years"):
    ne = serie(("Job Transitions", g, "With a new employer"))
    sh = {k: serie(("Number of Job Offers", g, k))[0] for k in ("1 Offer", "2 Offers", "3 Offers", "4+ Offers")}
    sk = serie(("Job Seekers", "None", g))
    edad[g] = {"nuevo_empleador_4m_pct": ne, "ofertas_share_pct": sh,
               "ofertas_media_cota_inf": (sh["1 Offer"] + 2 * sh["2 Offers"] + 3 * sh["3 Offers"] + 4 * sh["4+ Offers"]) / 100,
               "p_alguna_oferta_pct": sum(sh.values()), "busca_pct": sk}
R["edad_series"] = edad

json.dump(R, open(OUT, "w"), indent=1, default=float)
print(json.dumps(R, indent=1, default=float))
