# Estadísticas vitales y mortalidad INE. Uso: vitales_calc.py <carpeta_vitales> <salida.json>
import sys, re, json, numpy as np, pandas as pd, openpyxl
V = sys.argv[1].rstrip("/") + "/"
def rows(f, sh):
    wb = openpyxl.load_workbook(V + f, read_only=True, data_only=True)
    return [list(r) for r in wb[sh].iter_rows(values_only=True)]
def lab(r): return str(r[0]).strip() if r and r[0] is not None else ""
# --- población base 2024 al 30 de junio, por sexo y edad simple
P = rows("proy2024_tab.xlsx", "Población al 30 de junio")
hdr = next(r for r in P if lab(r).startswith("Sexo"))
col = {int(float(v)): i for i, v in enumerate(hdr) if re.fullmatch(r"\d{4}(\.0)?", str(v).strip())}
pop, sec = {}, None
for r in P:
    l = lab(r)
    if l in ("Ambos sexos", "Hombres", "Mujeres"): sec = l; continue
    if sec and re.fullmatch(r"\d+(\s*y más)?|\d+\+", l):
        pop[(sec, int(re.match(r"\d+", l).group()))] = r
def pp(sex, a, b, yr):  # población edades a..b
    return sum(pop[(sex, x)][col[yr]] for x in range(a, b + 1) if (sex, x) in pop)
I = rows("proy2024_tab.xlsx", "Resultados Indicadores")
ih = I[1]; icol = {int(float(v)): i for i, v in enumerate(ih) if re.fullmatch(r"\d{4}(\.0)?", str(v).strip())}
def lab2(r): return next((str(c).strip() for c in r if isinstance(c, str)), "")
ind = {lab2(r): {y: r[icol[y]] for y in (2023, 2024, 2025, 2030, 2040, 2050)} for r in I if lab2(r)}
out = {"fuente_poblacion": "INE, Estimaciones y proyecciones de población 1992-2070, base 2024 (población al 30 de junio)"}
# --- fecundidad 2023: nacidos vivos por edad simple de la madre
N = rows("nac_def_2023.xlsx", "1221-41")
nac = {}
for r in N:
    m = re.fullmatch(r"(\d+) años", lab(r))
    if m: nac[int(m.group(1))] = r[1]
ages = sorted(a for a in nac if 12 <= a <= 54)
asfr = {a: nac[a] / pp("Mujeres", a, a, 2023) for a in ages}
tgf = sum(asfr[a] for a in ages if a <= 49)
mab = sum((a + 0.5) * asfr[a] for a in ages if a <= 49) / tgf
grp = {}
for a0 in range(15, 50, 5):
    b = sum(nac.get(a, 0) for a in range(a0, a0 + 5)); w = pp("Mujeres", a0, a0 + 4, 2023)
    grp[f"{a0}-{a0+4}"] = round(1000 * b / w, 1)
# orden de nacimiento por grupo de edad (1221-04, filas de total)
O = rows("nac_def_2023.xlsx", "1221-04")
order, seen = {}, set()
for r in O:
    m = re.fullmatch(r"(\d+) a (\d+) años|Menores de 15 años|(\d+) años y más|(\d+) a (\d+) años y más", lab(r))
    if m and lab(r) not in seen:
        seen.add(lab(r)); order[lab(r)] = r[1:13]
mid = {}
for k in order:
    m = re.match(r"(\d+) a (\d+)", k)
    mid[k] = (int(m.group(1)) + int(m.group(2)) + 1) / 2 if m else (13.5 if "Menores" in k else float(re.match(r"\d+", k).group()) + 2.5)
def mean_order(j):
    tot = sum(order[k][j] or 0 for k in order); return sum(mid[k] * (order[k][j] or 0) for k in order) / tot, tot
# tasa de primeros nacimientos por grupo (edad media al 1er hijo, estandarizada por población)
first_rate = {}
for k in order:
    m = re.match(r"(\d+) a (\d+)", k)
    if m and 15 <= int(m.group(1)) <= 45:
        first_rate[int(m.group(1))] = order[k][1] / pp("Mujeres", int(m.group(1)), int(m.group(2)), 2023)
tgf1 = 5 * sum(first_rate.values())
mab1_std = sum((a + 2.5) * f for a, f in first_rate.items()) / sum(first_rate.values())
m1, n1 = mean_order(1); m2, n2 = mean_order(2); mall, nall = mean_order(0)
c15 = {lab(r): r[1] for r in rows("prov_2024.xlsx", "Cuadro 15") if lab(r).startswith("TEF") or "TGF" in lab(r)}
out["fecundidad"] = {
  "fuente": "INE, Anuario de estadísticas vitales 2023 (cuadros 1.2.2.1-41 y 1.2.2.1-04) y cifras provisionales 2024 (cuadro 15); población base 2024",
  "anio": 2023, "nacidos_vivos": int(sum(nac.values())),
  "tef_por_mil_mujeres_2023_calculada": grp,
  "tgf_2023_calculada": round(tgf, 3), "tgf_2023_publicada_INE": 1.16,
  "nota_tgf": "El INE publica 1,16 para 2023 con nacidos vivos corregidos por inscripción tardía y población base 2017; con población base 2024 y sin corrección da el valor calculado",
  "edad_media_de_la_madre_2023": round(mab, 2),
  "edad_media_al_primer_hijo_2023_cruda": round(m1, 2), "edad_media_al_primer_hijo_2023_estandarizada": round(mab1_std, 2),
  "edad_media_al_segundo_hijo_2023": round(m2, 2), "nota_edades": "con marcas de clase de grupos quinquenales (orden de nacimiento solo viene agrupado)",
  "proporcion_nacimientos_primer_hijo": round(n1 / nall, 3),
  "tasa_primeros_hijos_por_mil_mujeres_2023": {f"{a}-{a+4}": round(1000 * f, 1) for a, f in sorted(first_rate.items())},
  "tgf_de_primer_orden_2023": round(tgf1, 3),
  "tef_por_mil_2024p_publicada": {k.replace("TEF ", ""): v for k, v in c15.items() if k.startswith("TEF")}, "tgf_2024p_publicada": c15.get("Tasa Global de Fecundidad (TGF)"),
  "proyeccion_base_2024": {"tgf": {y: ind["Tasa Global de Fecundidad"][y] for y in (2023, 2024, 2025, 2030, 2040, 2050)},
                            "edad_media_fecundidad": {y: ind["Edad Media a la fecundidad"][y] for y in (2023, 2024, 2025, 2030, 2040, 2050)}},
}
# --- nupcialidad 2023
def age_cols(hdr):
    res = []
    for i, h in enumerate(hdr):
        m = re.match(r"\s*(\d+)\s*a\s*(\d+)", str(h or "")); m2 = re.match(r"\s*(\d+)\s*años y", str(h or ""))
        if m: res.append((i, int(m.group(1)), int(m.group(2))))
        elif m2: res.append((i, int(m2.group(1)), 100))
    return res
nup = {}
for sh, sex in (("1224-21a", "Mujeres"), ("1224-21b", "Hombres")):
    R = rows("matr_2023.xlsx", sh); h = next(r for r in R if lab(r).startswith("(REGIÓN")); t = next(r for r in R if lab(r) == "TOTAL")
    nup[sex] = {f"{a}-{b}" if b < 100 else f"{a}+": {"personas": t[i], "por_mil": round(1000 * t[i] / pp(sex, a, min(b, 100), 2023), 2)} for i, a, b in age_cols(h) if t[i]}
    nup[sex]["total_personas"] = t[1]
E = rows("matr_2023.xlsx", "1224-23"); te = next(r for r in E if lab(r) == "TOTAL PAIS")
A = rows("matr_2023.xlsx", "1225-03a"); ah = next(r for r in A if "18 a 19" in str(r[1] or "") or "18 a 19" in str(r[2] or ""))
at = next(r for r in A if lab(r) == "TOTAL")
auc_first = {}
for i, h in enumerate(ah):
    m = re.match(r"\s*(\d+)\s*a\s*(\d+)", str(h or ""))
    if m: auc_first[(int(m.group(1)), int(m.group(2)))] = at[i]
auc_second = {}
for r in A:
    m = re.match(r"\s*(\d+)\s*a\s*(\d+)", lab(r))
    if m: auc_second[(int(m.group(1)), int(m.group(2)))] = r[1]
auc = {f"{a}-{b}": round(1000 * (auc_first.get((a, b), 0) + auc_second.get((a, b), 0)) / (pp("Hombres", a, b, 2023) + pp("Mujeres", a, b, 2023)), 2)
       for (a, b) in sorted(auc_second) if b < 75}
EA = rows("matr_2023.xlsx", "1225-23"); tea = next(r for r in EA if lab(r) == "TOTAL PAIS")
out["nupcialidad"] = {"fuente": "INE, Anuario de estadísticas vitales 2023, matrimonios y AUC (cuadros 1.2.2.4-21a/b, 1.2.2.4-23, 1.2.2.5-03a, 1.2.2.5-23); población base 2024",
  "anio": 2023, "tasa_bruta_nupcialidad_por_mil": 3.229, "tasa_bruta_auc_por_10mil": 5.9, "tasa_bruta_nupcialidad_2024p": 3.0, "tasa_bruta_auc_2024p_por_10mil": 8.1,
  "matrimonios_por_mil_personas_por_edad": nup,
  "auc_por_mil_personas_por_edad_ambos_sexos": auc, "auc_total_2023": at[1],
  "edad_promedio_matrimonio_distinto_sexo": {"hombre": te[1], "mujer": te[2]}, "edad_mediana_matrimonio_distinto_sexo": {"hombre": te[5], "mujer": te[6]},
  "edad_promedio_auc_distinto_sexo": {"hombre": tea[1], "mujer": tea[2]}, "edad_mediana_auc_distinto_sexo": {"hombre": tea[5], "mujer": tea[6]},
  "nota": "las tasas por edad incluyen segundas nupcias; no distinguen primer matrimonio"}
# --- mortalidad: tablas base 2017, país
M = pd.read_excel(V + "tablas_mort.xlsx", sheet_name="BD Tablas de Mortalidad", header=1)
M = M[M["Región"].astype(str).str.strip() == "País"]
M["Edad"] = M["Edad"].astype(str).str.extract(r"(\d+)")[0].astype(int)
print("sexos:", M.Sexo.unique(), "años", M["Año"].min(), M["Año"].max(), "edad max", M.Edad.max())
mort = {"fuente": "INE, Tablas de mortalidad de Chile 1992-2050 (proyecciones base 2017), total país, edad simple",
        "url": "http://www.ine.gob.cl/docs/default-source/proyecciones-de-poblacion/cuadros-estadisticos/base-2017/tablas-de-mortalidad-de-chile-1992-2050.xlsx"}
def fit(q):
    x = np.arange(50, 96); y = np.log(q.loc[x].values.astype(float)); b, a = np.polyfit(x, y, 1)
    pred = np.exp(a + b * x); return round(float(a), 4), round(float(b), 5), round(float(np.max(np.abs(pred / q.loc[x].values - 1))), 3)
for yr in (2025, 2040):
    d = M[M["Año"] == yr]; res = {}
    qs = {}
    for sx in d.Sexo.unique():
        q = d[d.Sexo == sx].set_index("Edad")["q(x)"]; qs[sx] = q
        a, b, err = fit(q)
        res[str(sx)] = {"qx": {x: round(float(q.loc[x]), 5) for x in (50, 60, 70, 80, 90)}, "e0": round(float(d[d.Sexo == sx].set_index("Edad")["e(x)"].loc[0]), 2),
                        "e50": round(float(d[d.Sexo == sx].set_index("Edad")["e(x)"].loc[50]), 2), "gompertz_50_95": {"a": a, "b": b, "error_rel_max": err}}
    if "Ambos sexos" not in res:
        hm = [s for s in qs if str(s).lower().startswith(("hombre", "mujer"))]
        q = (qs[hm[0]] + qs[hm[1]]) / 2; a, b, err = fit(q)
        res["promedio_simple_hombre_mujer"] = {"qx": {x: round(float(q.loc[x]), 5) for x in (50, 60, 70, 80, 90)}, "gompertz_50_95": {"a": a, "b": b, "error_rel_max": err}}
    mort[str(yr)] = res
mort["metodo"] = "MCO de ln q(x) sobre x, edades simples 50 a 95; q(x) = exp(a + b·x)"
mort["motor_actual"] = {"a": -10.2, "b": 0.094, "qx": {x: round(float(np.exp(-10.2 + 0.094 * x)), 5) for x in (50, 60, 70, 80, 90)}}
out["mortalidad"] = mort
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
