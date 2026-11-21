"""Ingreso de empleadores y trabajadores por cuenta propia frente a asalariados privados, ESI 2023-2025.
Mediana ponderada (fact_cal_esi) del ingreso de la ocupación principal, 25-64 años, 30-80 horas habituales,
por educación; y percentiles del cociente para la dispersión."""
import json, sys
import numpy as np, pandas as pd

CAT = {1: "empleador", 2: "cuenta_propia", 3: "asalariado_privado"}
EDU = {2: "media", 3: "tecnica", 4: "universitaria", 5: "postgrado", 6: "postgrado"}
filas = []
for f in sys.argv[1:]:
    sep = ";" if open(f, encoding="latin-1").readline().count(";") > 5 else ","
    cols = ["ocup_ref", "ing_t_p", "fact_cal_esi", "edad", "cine11_1d", "categoria_ocupacion", "habituales"]
    d = pd.read_csv(f, sep=sep, usecols=cols, encoding="latin-1", low_memory=False)
    for c in cols:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["ola"] = f
    filas.append(d)
d = pd.concat(filas)
d = d[(d.ocup_ref == 1) & (d.ing_t_p > 0) & d.edad.between(25, 64) & d.habituales.between(30, 80) & d.categoria_ocupacion.isin(CAT)]
d["cat"] = d.categoria_ocupacion.map(CAT)
d["edu"] = d.cine11_1d.map(EDU)


def wq(x, w, q):
    o = np.argsort(x.values)
    x, w = x.values[o], w.values[o]
    c = np.cumsum(w) / w.sum()
    return float(np.interp(q, c, x))


out = {"fuente": "INE, ESI 2023-2025, ocupados 25-64 años con 30-80 horas, mediana ponderada por fact_cal_esi", "script": "scripts/modelo/emprender_esi.py"}
for edu in ("media", "tecnica", "universitaria", "postgrado", None):
    s = d if edu is None else d[d.edu == edu]
    base = wq(s[s.cat == "asalariado_privado"].ing_t_p, s[s.cat == "asalariado_privado"].fact_cal_esi, 0.5)
    r = {}
    for cat in ("empleador", "cuenta_propia"):
        g = s[s.cat == cat]
        if len(g) < 60:
            continue
        r[cat] = {"mediana_sobre_asalariado": round(wq(g.ing_t_p, g.fact_cal_esi, 0.5) / base, 3),
                  "p10_p90_sobre_asalariado": [round(wq(g.ing_t_p, g.fact_cal_esi, q) / base, 3) for q in (0.1, 0.9)],
                  "sd_log": round(float(np.sqrt(np.cov(np.log(g.ing_t_p), aweights=g.fact_cal_esi))), 3), "n": int(len(g))}
    a = s[s.cat == "asalariado_privado"]
    r["asalariado_sd_log"] = round(float(np.sqrt(np.cov(np.log(a.ing_t_p), aweights=a.fact_cal_esi))), 3)
    out[edu or "todos"] = r
print(json.dumps(out, ensure_ascii=False, indent=1))
