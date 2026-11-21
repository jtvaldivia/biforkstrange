"""Replica la regla de selectividad de DIPRES (2026, Anexo p. 44-45) con datos DEMRE PAES (proceso 2024 o 2025).

Regla DIPRES: se reparte a toda la poblacion de rendidores en 10 deciles segun puntaje de ingreso;
una universidad es "competitiva" si la proporcion de sus matriculados en deciles 8-10 supera
a la proporcion en deciles 1-7 (es decir, > 50 %).
Aqui: puntaje = PROMEDIO_CM_MAX (promedio Competencia Lectora + Matematica 1, maximo entre procesos),
poblacion = inscritos con puntaje > 0 (Inscritos-Puntajes PAES 2025), matricula = D_MATRICULA PAES 2025.
Fuente: https://datosabiertos.mineduc.cl/pruebas-de-admision-a-la-educacion-superior/
Uso: python -I magister_selectividad.py <dir_csv_demre> <anio_proceso> <salida_json>
"""
import json, sys
import pandas as pd

d, an, out = sys.argv[1], sys.argv[2], sys.argv[3]

def leer(path, **kw):
    t = pd.read_csv(path, sep=";", encoding="latin-1", **kw)
    t.columns = [c.replace("\u00ef\u00bb\u00bf", "") for c in t.columns]
    return t

p = leer(f"{d}/A_INSCRITOS_PUNTAJES_PAES_{an}_PUB_MRUN.csv")[["MRUN", "PROMEDIO_CM_MAX"]]
p["PROMEDIO_CM_MAX"] = pd.to_numeric(p["PROMEDIO_CM_MAX"].astype(str).str.replace(",", "."), errors="coerce")
p = p[p["PROMEDIO_CM_MAX"] > 0].drop_duplicates("MRUN")
p["decil"] = pd.qcut(p["PROMEDIO_CM_MAX"].rank(method="first"), 10, labels=range(1, 11)).astype(int)
corte_d8 = float(p.loc[p["decil"] == 8, "PROMEDIO_CM_MAX"].min())
m = leer(f"{d}/D_MATRICULA_PAES_{an}_PUB_MRUN.csv")
m = m.merge(p[["MRUN", "decil", "PROMEDIO_CM_MAX"]], on="MRUN", how="left")
g = m.groupby("SIGLA_UNIVERSIDAD").agg(
    n_matriculados=("MRUN", "size"),
    n_con_puntaje=("decil", lambda s: int(s.notna().sum())),
    frac_top30=("decil", lambda s: float((s.dropna() >= 8).mean())),
    puntaje_mediano=("PROMEDIO_CM_MAX", "median"),
).reset_index()
g["competitiva"] = g["frac_top30"] > 0.5
g = g.sort_values("frac_top30", ascending=False)
res = {
    "n_rendidores": int(len(p)),
    "corte_decil8_promedio_cl_m1": corte_d8,
    "universidades": g.round(4).to_dict(orient="records"),
}
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
print(len(p), corte_d8)
print(g.to_string())
