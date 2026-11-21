"""Probabilidad de quedar seleccionado al postular a un empleo del Estado (empleospublicos.cl, Servicio Civil).

Uso:
  uv run --with pandas --with numpy python -I ofertas_eepp.py <datos_laborales> <salida.json>

Une convocatorias_eepp_historicas.csv (2009-2024) y eepp_convocatorias.csv (2025-2026), sin duplicar IDs.
Solo convocatorias con postulación en línea (las otras no traen el conteo de postulaciones) y con proceso
cerrado (Aprobado o Empleo Desierto). Probabilidad por postulación = seleccionados / postulaciones.
Intervalo: bootstrap por convocatoria (500 réplicas).
"""
import json
import sys

import numpy as np
import pandas as pd

D, OUT = sys.argv[1], sys.argv[2]
RNG = np.random.default_rng(20261121)
h = pd.read_csv(f"{D}/empleos_publicos/convocatorias_eepp_historicas.csv", encoding="utf-8-sig", low_memory=False)
n = pd.read_csv(f"{D}/empleos_publicos/eepp_convocatorias.csv", encoding="utf-8-sig", low_memory=False)
x = pd.concat([n, h[~h["ID Convocatoria"].isin(n["ID Convocatoria"])]], ignore_index=True)
x = x[(x["Tipo Convocatoria"] == "Con postulación en línea") & x.Estado.isin(["Aprobado", "Empleo Desierto"])]
x["post"] = pd.to_numeric(x["Número Postulaciones"], errors="coerce")
x["sel"] = pd.to_numeric(x["Seleccionados"], errors="coerce")
x["vac"] = pd.to_numeric(x["Cantidad Vacantes"], errors="coerce")
x = x[(x.post > 0) & x.sel.notna() & x.vac.between(1, 50)]
x["Año"] = pd.to_numeric(x["Año"], errors="coerce")
R = {"n_convocatorias": int(len(x)), "anios": [int(x["Año"].min()), int(x["Año"].max())]}


def est(d):
    p = d.sel.sum() / d.post.sum()
    b = []
    for _ in range(500):
        s = d.sample(len(d), replace=True, random_state=int(RNG.integers(1e9)))
        b.append(s.sel.sum() / s.post.sum())
    return {"p_por_postulacion": float(p), "ic95": [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))],
            "postulaciones_por_seleccionado": float(d.post.sum() / max(d.sel.sum(), 1)),
            "mediana_postulaciones_por_convocatoria": float(d.post.median()),
            "share_desierto": float((d.Estado == "Empleo Desierto").mean()),
            "n_convocatorias": int(len(d)), "postulaciones": int(d.post.sum()), "seleccionados": int(d.sel.sum())}


R["por_estamento"] = {e: est(g) for e, g in x.groupby("Estamento") if len(g) >= 50}
R["total"] = est(x)
R["por_estamento_2023_2026"] = {e: est(g) for e, g in x[x["Año"] >= 2023].groupby("Estamento") if len(g) >= 50}
R["por_tipo_vacante"] = {e: est(g) for e, g in x.groupby("Tipo de Vacante") if len(g) >= 200}
json.dump(R, open(OUT, "w"), indent=1, ensure_ascii=False)
print(json.dumps(R, indent=1, ensure_ascii=False))
