"""Satisfacción con la vida (s01) y salud subjetiva (s03) de partida por tramo de edad, ELSOC 2016-2022.
Promedio ponderado (ponderador02) de todas las olas; escala 1-5 llevada a 0-100 con (x-1)*25."""
import json, sys
import numpy as np, pandas as pd

f = sys.argv[1]
cols = pd.read_csv(f, sep="\t", nrows=0).columns
olas = [f"w0{i}" for i in range(1, 7)]
usar = [c for c in cols if any(c == f"{v}_{w}" for v in ("s01", "s03", "m0_edad", "ponderador02", "m02") for w in olas)]
d = pd.read_csv(f, sep="\t", usecols=usar, low_memory=False)
filas = []
for w in olas:
    if f"s01_{w}" not in d or f"m0_edad_{w}" not in d:
        continue
    x = pd.DataFrame({"s01": d.get(f"s01_{w}"), "s03": d.get(f"s03_{w}"), "edad": d[f"m0_edad_{w}"], "p": d.get(f"ponderador02_{w}"), "m02": d.get(f"m02_{w}")})
    x["ola"] = w
    filas.append(x)
x = pd.concat(filas)
for c in ("s01", "s03", "edad", "p", "m02"):
    x[c] = pd.to_numeric(x[c], errors="coerce")
x = x[x.edad.between(18, 60) & x.p.gt(0)]
x["tramo"] = pd.cut(x.edad, [17, 29, 39, 49, 60], labels=["18-29", "30-39", "40-49", "50-60"])
out = {"fuente": "ELSOC 2016-2022, todas las olas, ponderador02; escala 1-5 -> 0-100 con (x-1)*25", "script": "scripts/modelo/base_bienestar.py"}
for v in ("s01", "s03"):
    y = x[x[v].between(1, 5)]
    out[v] = {t: round(float(np.average((g[v] - 1) * 25, weights=g.p)), 1) for t, g in y.groupby("tramo", observed=True)}
    out[v + "_n"] = {t: int(len(g)) for t, g in y.groupby("tramo", observed=True)}
    oc = y[y.m02.between(1, 3)]
    out[v + "_ocupados"] = {t: round(float(np.average((g[v] - 1) * 25, weights=g.p)), 1) for t, g in oc.groupby("tramo", observed=True)}
print(json.dumps(out, ensure_ascii=False, indent=1))
