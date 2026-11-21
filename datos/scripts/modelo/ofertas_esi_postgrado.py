"""Premio de sueldo del magíster sobre el título universitario en la ESI 2023-2025 (corte transversal).

Uso:
  uv run --with pandas --with numpy --with statsmodels python -I ofertas_esi_postgrado.py <datos_laborales> <salida.json>

Asalariados y por cuenta propia de 25 a 64 años, ocupación principal con ingreso (ocup_ref == 1), 30 a 60 horas.
cine11_1d: 4 universitaria, 5 magíster, 6 doctorado. Regresión ponderada (fact_cal_esi) de log ingreso en
el nivel, con edad, edad², sexo, horas, ola y región; luego se agrega gran grupo CIUO y categoría.
Es una correlación: quien hace un magíster ya ganaba distinto. Errores agrupados por conglomerado y ola.
"""
import json
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

D, OUT = sys.argv[1], sys.argv[2]
COLS = ["conglomerado", "sexo", "edad", "b1", "cine11_1d", "categoria_ocupacion", "habituales", "ing_t_p", "ocup_ref",
        "fact_cal_esi", "region"]
xs = []
for a, f in {2023: "esi_2023.csv", 2024: "esi_2024.csv", 2025: "esi_2025_personas.csv"}.items():
    x = pd.read_csv(f"{D}/esi_ine/{f}", sep=None, engine="python", encoding="latin-1", usecols=lambda c: c in COLS)
    x["ola"] = a
    xs.append(x)
E = pd.concat(xs, ignore_index=True)
E = E[(E.ocup_ref == 1) & (E.ing_t_p > 0) & (E.fact_cal_esi > 0) & E.edad.between(25, 64) & E.cine11_1d.between(4, 6)
      & E.habituales.between(30, 60) & E.categoria_ocupacion.isin([1, 2, 3, 4]) & E.b1.between(1, 10)]
E["lny"], E["lnh"] = np.log(E.ing_t_p), np.log(E.habituales)
E["niv"] = E.cine11_1d.map({4: "a_universitaria", 5: "magister", 6: "doctorado"})
E["clu"] = E.ola.astype(str) + "_" + E.conglomerado.astype(str)
R = {"n_por_nivel": E.niv.value_counts().to_dict()}
for nom, f in (("sin_ocupacion", "lny ~ C(niv) + edad + I(edad**2) + C(sexo) + lnh + C(ola) + C(region)"),
               ("con_ocupacion", "lny ~ C(niv) + edad + I(edad**2) + C(sexo) + lnh + C(ola) + C(region) + C(b1) + C(categoria_ocupacion)")):
    m = smf.wls(f, E, weights=E.fact_cal_esi).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(E.clu)[0]})
    R[nom] = {k.split("[T.")[1].rstrip("]"): [float(m.params[k]), float(m.bse[k])] for k in m.params.index if k.startswith("C(niv)")}
    R[nom]["n"] = int(m.nobs)
json.dump(R, open(OUT, "w"), indent=1)
print(json.dumps(R, indent=1))
