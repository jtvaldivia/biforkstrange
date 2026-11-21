# IR real empalmado (INE, base 2023=100). Uso: ir_calc.py <xlsx> <salida.json>
import sys, json, pandas as pd, numpy as np
x = pd.read_excel(sys.argv[1], sheet_name="General")
a = x.groupby("año")["índice"].agg(["mean", "count"])
a = a[a["count"] == 12]["mean"]; g = (a / a.shift(1) - 1) * 100
last = x.iloc[-1]; prev10 = x[(x["año"] == last["año"] - 10) & (x.mes == last.mes)].iloc[0]
cagr10 = ((last["índice"] / prev10["índice"]) ** (1 / 10) - 1) * 100
yrs = [y for y in g.index if y >= a.index.max() - 9]
out = {"fuente": "INE, Índice Real de Remuneraciones (IR real), serie empalmada base anual 2023=100, deflactado con IPC; mide remuneración por hora ordinaria",
       "url": "http://www.ine.gob.cl/docs/default-source/sueldos-y-salarios/cuadros-estadisticos/ir-icl-base-anual-2023-100/series-empalmadas/tabulado_ir_real_empalmado.xlsx",
       "variacion_real_anual_promedio_pct": {int(y): round(float(g[y]), 2) for y in yrs},
       "promedio_simple_10_anios_pct": round(float(np.mean([g[y] for y in yrs])), 2),
       "mediana_10_anios_pct": round(float(np.median([g[y] for y in yrs])), 2),
       "tasa_compuesta_10_anios_pct": round(float(cagr10), 2), "periodo_compuesto": f"{int(prev10['año'])}-{int(prev10.mes):02d} a {int(last['año'])}-{int(last.mes):02d} ({last['estado']}=provisional)",
       "min_max_10_anios_pct": [round(float(min(g[y] for y in yrs)), 2), round(float(max(g[y] for y in yrs)), 2)],
       "desv_estandar_10_anios_pct": round(float(np.std([g[y] for y in yrs], ddof=1)), 2)}
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1); print(json.dumps(out, ensure_ascii=False))
