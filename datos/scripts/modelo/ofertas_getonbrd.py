"""Salto de sueldo entre niveles de seniority en avisos de Get on Board (tecnología, sobre todo Chile).

Uso:
  uv run --with pandas --with numpy --with statsmodels python -I ofertas_getonbrd.py <datos_laborales> <salida.json>

Unidad: aviso con rango de sueldo publicado (USD mensuales). Sueldo = punto medio del rango.
Solo jornada completa. Regresión de log sueldo en nivel, con efectos fijos de categoría y de país
(Chile, remoto, otro); errores agrupados por empresa. Son sueldos ofrecidos, no pagados.
"""
import json
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

D, OUT = sys.argv[1], sys.argv[2]
g = pd.read_csv(f"{D}/getonbrd/getonbrd_vacantes.csv")
g = g[(g.modality == "Full time") & g.min_salary_usd.notna() & g.max_salary_usd.notna() & (g.min_salary_usd > 0)]
g["mid"] = (g.min_salary_usd + g.max_salary_usd) / 2
g = g[g.mid.between(300, 20000) & (g.max_salary_usd >= g.min_salary_usd)]
g["pais"] = np.where(g.countries.str.contains("Chile", na=False), "chile", np.where(g.countries == "Remote", "remoto", "otro"))
g["nivel"] = g.seniority.map({"Sin experiencia": "0_junior", "Junior": "0_junior", "Semi Senior": "1_semi",
                              "Senior": "2_senior", "Expert": "3_expert"})
g = g[g.nivel.notna()]
g["lny"] = np.log(g.mid)
R = {"n": int(len(g)), "n_por_nivel": g.nivel.value_counts().to_dict(), "n_empresas": int(g.company_id.nunique()),
     "n_chile": int((g.pais == "chile").sum())}
R["mediana_usd_por_nivel"] = g.groupby("nivel").mid.median().to_dict()

for nom, d in (("todos", g), ("chile", g[g.pais == "chile"])):
    f = "lny ~ C(nivel) + C(category)" + (" + C(pais)" if nom == "todos" else "")
    m = smf.ols(f, d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.company_id)[0]})
    b = {k.split("[T.")[1].rstrip("]"): float(m.params[k]) for k in m.params.index if k.startswith("C(nivel)")}
    V = m.cov_params()
    keys = {k.split("[T.")[1].rstrip("]"): k for k in m.params.index if k.startswith("C(nivel)")}
    out = {"vs_junior": {k: [b[k], float(m.bse[keys[k]])] for k in b}, "n": int(m.nobs)}
    # saltos entre niveles consecutivos, con su error (diferencia de coeficientes)
    sal = {}
    prev = None
    for k in ("1_semi", "2_senior", "3_expert"):
        if k not in b:
            continue
        if prev is None:
            sal[f"junior->{k}"] = [b[k], float(m.bse[keys[k]])]
        else:
            v = V.loc[keys[k], keys[k]] + V.loc[keys[prev], keys[prev]] - 2 * V.loc[keys[k], keys[prev]]
            sal[f"{prev}->{k}"] = [b[k] - b[prev], float(np.sqrt(v))]
        prev = k
    out["saltos_log"] = sal
    R[nom] = out

json.dump(R, open(OUT, "w"), indent=1, default=float)
print(json.dumps(R, indent=1, default=float))
