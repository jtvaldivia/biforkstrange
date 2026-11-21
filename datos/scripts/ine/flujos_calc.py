# Flujos laborales con registros administrativos (INE). Uso: flujos_calc.py <general.xlsx> <sector.xlsx> <tamano.xlsx> <continuidad.xlsx> <salida.json>
import sys, json, re, pandas as pd
SH = "10-06-2026"
def load(f):
    raw = pd.read_excel(f, sheet_name=SH, header=None)
    h = raw.index[raw.iloc[:, 0].astype(str).str.strip() == "Año"][0]
    cols = [re.sub(r"\s+", " ", str(c)).strip() for c in raw.iloc[h]]
    d = raw.iloc[h + 1:].copy(); d.columns = cols
    d = d[pd.to_numeric(d["Año"], errors="coerce").notna()]
    d["Año"] = d["Año"].astype(int); d["t"] = d["Año"] * 100 + pd.to_numeric(d["id_Mes"]).astype(int)
    return d
def tasa(d, name): return [c for c in d.columns if c.startswith(name)][0]
out = {"fuente": "INE, Estadísticas de flujos laborales con registros administrativos (Seguro de Cesantía), serie publicada el 10-06-2026; asalariados privados con contrato",
       "url_base": "http://www.ine.gob.cl/docs/default-source/estadisticas-registros-administrativos/cuadro-estadisticos/tasas-de-rotación-laboral/"}
g = load(sys.argv[1]); per = sorted(g["t"].unique())[-12:]
print("periodo", g[g.t.isin(per)][["Año", "Mes"]].iloc[[0, -1]].values.tolist())
s_tot = pd.to_numeric(g[g.t.isin(per)][tasa(g, "Tasa de Salida")]).mean()
e_tot = pd.to_numeric(g[g.t.isin(per)][tasa(g, "Tasa de Entrada")]).mean()
out["periodo_12_meses"] = [str(x) for x in g[g.t.isin(per)][["Año", "Mes"]].iloc[[0, -1]].values.tolist()]
out["general"] = {"tasa_salida_anual_pct": round(float(s_tot), 3), "tasa_entrada_anual_pct": round(float(e_tot), 3)}
for key, f in (("por_sector", sys.argv[2]), ("por_tamano", sys.argv[3]), ("por_continuidad_empresa", sys.argv[4])):
    d = load(f); d = d[d.t.isin(per)]
    rows = []
    for gl, x in d.groupby("Glosa"):
        sal = pd.to_numeric(x[tasa(d, "Tasa de Salida")], errors="coerce").mean(); ent = pd.to_numeric(x[tasa(d, "Tasa de Entrada")], errors="coerce").mean()
        rows.append({"glosa": str(gl).strip(), "tasa_salida_anual_pct": round(float(sal), 3), "tasa_entrada_anual_pct": round(float(ent), 3),
                     "multiplicador_salida_vs_total": round(float(sal / s_tot), 2), "meses": int(len(x))})
    out[key] = sorted(rows, key=lambda r: -r["tasa_salida_anual_pct"])
out["nota"] = "la tasa de salida cuenta todo término de relación laboral (despido, renuncia, fin de plazo fijo u obra), no solo despidos; cada dato mensual del INE es una tasa anual móvil (ventana de 12 meses; permanencia = 100 - salida); aquí se promedian los últimos 12 datos publicados"
json.dump(out, open(sys.argv[5], "w"), ensure_ascii=False, indent=1); print(json.dumps(out, ensure_ascii=False, indent=0))
