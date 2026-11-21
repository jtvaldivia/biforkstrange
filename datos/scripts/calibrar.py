"""Deriva las tablas de calibración del juego a partir de los datos descargados.

Uso: uv run --no-project --with openpyxl python -I calibrar.py <carpeta datos_laborales>
Salida: <carpeta>/derivados/calibracion.json
"""
import collections
import csv
import gzip
import json
import os
import re
import statistics
import sys

import openpyxl

D = sys.argv[1]
OUT = {}


def wquantile(pairs, qs):
    """Cuantiles ponderados. pairs = [(valor, peso)]"""
    pairs = sorted(pairs)
    total = sum(w for _, w in pairs)
    res, acc, i = [], 0.0, 0
    targets = [q * total for q in qs]
    ti = 0
    for v, w in pairs:
        acc += w
        while ti < len(targets) and acc >= targets[ti]:
            res.append(v)
            ti += 1
    while len(res) < len(qs):
        res.append(pairs[-1][0])
    return res


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- ESI 2025
# cine11_1d: 2 secundaria, 3 técnica de nivel superior, 4 universitaria o profesional, 5 magíster, 6 doctorado
EDU = {2: "media", 3: "tecnica", 4: "universitaria", 5: "postgrado", 6: "postgrado"}
BANDS = [(18, 24), (25, 29), (30, 34), (35, 39), (40, 44), (45, 49), (50, 54)]
SECTOR = {
    1: "Agricultura y pesca", 2: "Minería", 3: "Industria manufacturera", 4: "Electricidad y gas",
    5: "Agua y residuos", 6: "Construcción", 7: "Comercio", 8: "Transporte", 9: "Hoteles y restaurantes",
    10: "Información y comunicaciones", 11: "Finanzas y seguros", 12: "Inmobiliarias",
    13: "Servicios profesionales", 14: "Servicios administrativos", 15: "Administración pública",
    16: "Enseñanza", 17: "Salud", 18: "Artes y entretención", 19: "Otros servicios",
}


def band(age):
    for a, b in BANDS:
        if a <= age <= b:
            return f"{a}-{b}"
    return None


allp, by_be, by_sec, by_sec_sup, by_sex_edu = [], collections.defaultdict(list), collections.defaultdict(list), \
    collections.defaultdict(list), collections.defaultdict(list)
hours = []
by_cat = collections.defaultdict(list)
with open(f"{D}/esi_ine/esi_2025_personas.csv", newline="", encoding="latin-1") as fh:
    for r in csv.DictReader(fh):
        if r["ocup_ref"] != "1":
            continue
        y, w, age = num(r["ing_t_p"]), num(r["fact_cal_esi"]), num(r["edad"])
        if y is None or w is None or age is None or w <= 0:
            continue
        allp.append((y, w))
        edu = EDU.get(int(num(r["cine11_1d"]) or 0))
        b = band(int(age))
        sec = SECTOR.get(int(num(r["r_p_rev4cl_caenes"]) or 0))
        if edu and b:
            by_be[(b, edu)].append((y, w))
        if sec and 18 <= age <= 54:
            by_sec[sec].append((y, w))
            if edu in ("universitaria", "postgrado"):
                by_sec_sup[sec].append((y, w))
        if edu and 25 <= age <= 54:
            by_sex_edu[(r["sexo"], edu)].append((y, w))
        h = num(r["habituales"])
        if h is not None and 1 <= h <= 100 and 18 <= age <= 54:
            hours.append((h, w))
        cat = r["categoria_ocupacion"]
        if 18 <= age <= 54:
            by_cat[cat].append((y, w))

tot_w = sum(w for _, w in allp)
esi = {
    "fuente": "INE, Encuesta Suplementaria de Ingresos 2025, ingreso mensual neto de la ocupación principal (ing_t_p), ocupados con ocup_ref=1, ponderado con fact_cal_esi",
    "validacion": {
        "media_calculada": round(sum(v * w for v, w in allp) / tot_w),
        "mediana_calculada": round(wquantile(allp, [0.5])[0]),
        "media_oficial_manual": 962945,
        "mediana_oficial_manual": 680000,
    },
    "por_edad_educacion": {},
    "por_sector": {},
    "por_sector_educacion_superior": {},
    "por_sexo_educacion_25_54": {},
}
for (b, edu), ps in sorted(by_be.items()):
    q = wquantile(ps, [0.1, 0.25, 0.5, 0.75, 0.9])
    esi["por_edad_educacion"].setdefault(edu, {})[b] = {"p10": round(q[0]), "p25": round(q[1]), "p50": round(q[2]),
                                                          "p75": round(q[3]), "p90": round(q[4]), "n": len(ps)}
for sec, ps in by_sec.items():
    q = wquantile(ps, [0.25, 0.5, 0.75])
    esi["por_sector"][sec] = {"p25": round(q[0]), "p50": round(q[1]), "p75": round(q[2]), "n": len(ps)}
for sec, ps in by_sec_sup.items():
    if len(ps) >= 80:
        q = wquantile(ps, [0.25, 0.5, 0.75])
        esi["por_sector_educacion_superior"][sec] = {"p25": round(q[0]), "p50": round(q[1]), "p75": round(q[2]), "n": len(ps)}
for (sx, edu), ps in by_sex_edu.items():
    esi["por_sexo_educacion_25_54"][f"{'hombre' if sx == '1' else 'mujer'}_{edu}"] = round(wquantile(ps, [0.5])[0])
hw = sum(w for _, w in hours)
esi["horas_habituales_18_54"] = {
    "mediana": wquantile(hours, [0.5])[0],
    "pct_45_o_mas": round(100 * sum(w for h, w in hours if h >= 45) / hw, 1),
    "pct_50_o_mas": round(100 * sum(w for h, w in hours if h >= 50) / hw, 1),
    "pct_55_o_mas": round(100 * sum(w for h, w in hours if h >= 55) / hw, 1),
}
esi["por_categoria_ocupacion_18_54"] = {k: {"p25": round(q[0]), "p50": round(q[1]), "p75": round(q[2]), "n": len(v)}
                                         for k, v in by_cat.items() if len(v) > 200
                                         for q in [wquantile(v, [0.25, 0.5, 0.75])]}
OUT["esi_2025"] = esi

# ---------------------------------------------------------------- mifuturo
wb = openpyxl.load_workbook(f"{D}/mifuturo/Buscador_EstadisticasCarrera_2025_2026_SIES.xlsx", read_only=True)
ws = wb[wb.sheetnames[0]]
rows = list(ws.iter_rows(values_only=True))
hdr = [str(c).strip() if c is not None else "" for c in rows[1]]
ix = {h: i for i, h in enumerate(hdr)}


def col(row, name):
    return num(row[ix[name]]) if name in ix else None


TIPO = {"Centros de Formación Técnica": "CFT", "Institutos Profesionales": "IP", "Universidades": "U"}
carreras = []
for row in rows[2:]:
    if row[ix["Carrera genérica"]] is None:
        continue
    tipo_raw = str(row[ix["Tipo de institución"]]).strip()
    c = {
        "area": str(row[ix["Área"]]).strip(),
        "tipo": TIPO.get(tipo_raw, tipo_raw),
        "carrera": str(row[ix["Carrera genérica"]]).strip(),
        "y1": col(row, "1er año"), "y2": col(row, "2° año"), "y3": col(row, "3er año"),
        "y4": col(row, "4° año"), "y5": col(row, "5° año"),
        "p10_y1": col(row, "10% inferior 1er año"), "p50_y1": col(row, "Percentil 50 1er año"),
        "p90_y1": col(row, "10% superior 1er año"),
        "p10_y5": col(row, "10% inferior 5° año"), "p50_y5": col(row, "Percentil 50 5° año"),
        "p90_y5": col(row, "10% superior 5° año"),
        "emp1": col(row, "Empleabilidad 1er año"), "emp2": col(row, "Empleabilidad 2° año"),
        "titulados": col(row, "Titulados Total"), "dur_formal": col(row, "Duración Formal"),
    }
    carreras.append(c)

# duración real, retención y arancel por carrera genérica y tipo de institución
wb = openpyxl.load_workbook(f"{D}/mifuturo/Buscador_Empleabilidad_ingresos_2025_2026_SIES.xlsx", read_only=True)
ws = wb[wb.sheetnames[0]]
rr = list(ws.iter_rows(values_only=True))
h2 = [str(c).replace("\xa0", " ").strip() if c is not None else "" for c in rr[0]]
i2 = {h: i for i, h in enumerate(h2)}
dur, ret = collections.defaultdict(list), collections.defaultdict(list)
for row in rr[1:]:
    key = (str(row[i2["Nombre carrera genérica"]]).strip(), TIPO.get(str(row[i2["Tipo de institución"]]).strip()))
    d = num(row[i2["Duración Real (semestres)"]])
    t = num(row[i2["Retención 1er año"]])
    if d:
        dur[key].append(d)
    if t:
        ret[key].append(t)

wb = openpyxl.load_workbook(f"{D}/mifuturo/Buscador_de_Carreras_2025_2026_SIES.xlsx", read_only=True)
ws = wb[wb.sheetnames[0]]
aran = collections.defaultdict(list)
h3 = None
for row in ws.iter_rows(values_only=True):
    if h3 is None:
        if row and row[0] and "Código único" in str(row[0]):
            h3 = [str(c).strip() if c is not None else "" for c in row]
            i3 = {h: i for i, h in enumerate(h3)}
        continue
    gen = row[i3["Área Carrera Genérica"]]
    tipo = TIPO.get(str(row[i3["Tipo de institución"]]).strip())
    a = re.sub(r"[^\d]", "", str(row[i3["Arancel Anual 2026"]] or ""))
    m = num(row[i3["Matrícula 1er año Total 2025"]]) or 0
    if gen and tipo and a and int(a) > 100000:
        aran[(str(gen).strip(), tipo)].append((int(a), max(m, 1)))

for c in carreras:
    key = (c["carrera"], c["tipo"])
    c["dur_real"] = round(statistics.mean(dur[key]), 1) if dur.get(key) else None
    c["retencion1"] = round(statistics.mean(ret[key]), 3) if ret.get(key) else None
    c["arancel"] = round(wquantile(aran[key], [0.5])[0]) if aran.get(key) else None
    for k, v in list(c.items()):
        if isinstance(v, float):
            c[k] = round(v, 3) if v < 5 else round(v)
OUT["mifuturo_2025_2026"] = {
    "fuente": "Mineduc SIES, mifuturo.cl, Buscador de Estadísticas por Carrera 2025-2026 (ingreso bruto mensual promedio por año desde la titulación), Buscador de Empleabilidad e Ingresos 2025-2026 (duración real, retención) y Buscador de Carreras 2026 (arancel anual, mediana ponderada por matrícula de primer año)",
    "carreras": carreras,
}

# ---------------------------------------------------------------- Empleos Públicos
est = collections.defaultdict(lambda: {"rentas": [], "post": 0, "sel": 0, "conv": 0, "vac": 0})
serv = collections.Counter()
with open(f"{D}/empleos_publicos/eepp_convocatorias.csv", newline="", encoding="utf-8-sig") as fh:
    for r in csv.DictReader(fh):
        e = r["Estamento"].strip()
        renta = num(str(r["Renta Bruta"]).replace(",", "."))
        d = est[e]
        d["conv"] += 1
        if renta and renta > 350000:
            d["rentas"].append(renta)
        p, s, v = num(r["Número Postulaciones"]), num(r["Seleccionados"]), num(r["Cantidad Vacantes"])
        if p and p > 0 and s is not None and r["Estado"].strip() in ("Aprobado", "Finalizada", "Finalizado"):
            d["post"] += p
            d["sel"] += s
        d["vac"] += v or 0
        serv[r["Servicio"].strip()] += 1
OUT["empleos_publicos"] = {
    "fuente": "Servicio Civil, convocatorias de empleospublicos.cl desde 2025 (eepp_convocatorias.csv). Renta bruta mensual; se descartan valores bajo $350.000, que el archivo usa como dato faltante",
    "por_estamento": {
        e: {"renta_p25": round(q[0]), "renta_p50": round(q[1]), "renta_p75": round(q[2]),
            "convocatorias": d["conv"], "postulantes_por_seleccionado": round(d["post"] / d["sel"], 1) if d["sel"] else None}
        for e, d in est.items() if len(d["rentas"]) >= 50
        for q in [statistics.quantiles(d["rentas"], n=4)]
    },
    "servicios_con_mas_convocatorias": [s for s, _ in serv.most_common(15)],
}

# ---------------------------------------------------------------- Get on Board
gb = collections.defaultdict(list)
with open(f"{D}/getonbrd/getonbrd_vacantes.csv", newline="", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        if r["min_salary_usd"] and "Chile" in r["countries"]:
            lo, hi = float(r["min_salary_usd"]), float(r["max_salary_usd"] or r["min_salary_usd"])
            gb[r["seniority"]].append((lo + hi) / 2)
OUT["getonbrd"] = {
    "fuente": "API pública de Get on Board, vacantes vigentes al 2026-11-21 con Chile entre sus países; punto medio de la banda salarial en USD mensuales",
    "por_seniority": {k: {"mediana_usd": round(statistics.median(v)), "n": len(v)} for k, v in gb.items()},
}

# ---------------------------------------------------------------- Y Combinator
yc = json.load(open(f"{D}/yc_startups/yc_companies_all.json"))
by_year = collections.defaultdict(collections.Counter)
for x in yc:
    m = re.search(r"(20\d\d)", x.get("batch") or "")
    if m:
        by_year[int(m.group(1))][x.get("status")] += 1
cohortes = {}
for y in sorted(by_year):
    c = by_year[y]
    n = sum(c.values())
    cohortes[y] = {"n": n, "activa": round(c["Active"] / n, 3), "inactiva": round(c["Inactive"] / n, 3),
                   "adquirida": round(c["Acquired"] / n, 3), "publica": round(c["Public"] / n, 3)}
old = collections.Counter()
for y in range(2012, 2020):
    old.update(by_year[y])
n_old = sum(old.values())
OUT["yc"] = {
    "fuente": "Directorio de Y Combinator (copia yc-oss), estado autodeclarado al 2026-11-21",
    "por_cohorte": cohortes,
    "cohortes_2012_2019": {"n": n_old, **{k: round(v / n_old, 3) for k, v in old.items()}},
    "con_sede_en_chile": sorted(x["name"] for x in yc if "Chile" in (x.get("all_locations") or "")),
}

# ---------------------------------------------------------------- Census J2J
# El archivo nacional trae los conteos de flujos; sus columnas de ingresos vienen vacías.
AGE = {"A03": "22-24", "A04": "25-34", "A05": "35-44", "A06": "45-54"}
rate = collections.defaultdict(list)
with gzip.open(f"{D}/j2j_census/j2j_us_all.csv.gz", "rt") as fh:
    for r in csv.DictReader(fh):
        if (r["industry"] == "00" and r["sex"] == "0" and r["agegrp"] in AGE and r["seasonadj"] == "U"
                and r["agg_level"] == "3" and 2017 <= int(r["year"]) <= 2023):
            hire, base = num(r["EEHire"]), num(r["MainB"])
            if hire and base:
                rate[AGE[r["agegrp"]]].append(hire / base)
OUT["j2j_eeuu"] = {
    "fuente": "US Census, Job-to-Job Flows, total nacional 2017-2023, sin ajuste estacional. Contrataciones por cambio directo de empleo (EEHire) sobre empleos al inicio del trimestre (MainB)",
    "tasa_trimestral_cambio_directo": {a: round(statistics.mean(v), 4) for a, v in rate.items()},
    "tasa_anual_aprox": {a: round(1 - (1 - statistics.mean(v)) ** 4, 3) for a, v in rate.items()},
}

# ---------------------------------------------------------------- Exposición a IA
ms = {}
with open(f"{D}/exposicion_ia/microsoft_ai_applicability_scores.csv", newline="", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        ms[r["title"]] = float(r["ai_applicability_score"])
vals = sorted(ms.values())
OUT["exposicion_ia"] = {
    "fuente": "Microsoft, Working with AI: puntaje de aplicabilidad de IA por ocupación SOC (EE.UU.)",
    "mediana": round(statistics.median(vals), 3),
    "p90": round(vals[int(0.9 * len(vals))], 3),
    "ocupaciones": {k: round(v, 3) for k, v in ms.items()},
}

os.makedirs(f"{D}/derivados", exist_ok=True)
with open(f"{D}/derivados/calibracion.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, ensure_ascii=False, indent=1)
print(json.dumps({k: (v if k not in ("mifuturo_2025_2026", "exposicion_ia") else "...") for k, v in OUT.items()},
                 ensure_ascii=False, indent=1)[:9000])
print("carreras:", len(carreras), "con arancel:", sum(1 for c in carreras if c["arancel"]),
      "con dur_real:", sum(1 for c in carreras if c["dur_real"]))
