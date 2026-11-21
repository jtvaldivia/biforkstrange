# /// script
# requires-python = ">=3.12"
# dependencies = ["pandas", "pyarrow", "numpy"]
# ///
"""Arma backend/app/sim/data/tablas.json a partir de la carpeta datos_laborales/.

Los microdatos no van al repo (son grandes y algunos tienen condiciones de uso);
este script deja solo tablas agregadas. Uso, desde backend/:

    uv run scripts/build_sim_data.py --datos "../../datos_laborales"
"""
import argparse
import collections
import csv
import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from isco import ISCO1, ISCO3  # noqa: E402

TOP_K = 18      # destinos guardados por ocupación de origen
N_MIN = 400     # mínimo de empleos en JobHop para que una ocupación entre al modelo


def trimestre(s):
    m = re.match(r"Q([1-4]) (\d{4})$", s) if isinstance(s, str) else None
    return int(m.group(2)) * 4 + int(m.group(1)) - 1 if m else None


def jobhop(datos):
    df = pd.concat(
        pd.read_parquet(os.path.join(datos, "jobhop", f"JobHop_v2_{p}.parquet")).assign(parte=p)
        for p in ("train", "val", "test")
    )
    df["ini"] = df["start_date"].map(trimestre)
    df["fin"] = df["end_date"].map(trimestre)
    df = df[df["ini"].notna() & df["matched_code"].notna() & (df["matched_code"] != "unknown")]
    df["isco3"] = df["matched_code"].str.replace(r"\D", "", regex=True).str[:3]
    df = df[df["isco3"].isin(ISCO3.keys())]
    df = df.sort_values(["parte", "resume_id", "ini"])
    key = df["parte"] + "_" + df["resume_id"].astype(str)
    nxt = df["isco3"].shift(-1).where(key == key.shift(-1))

    n_emp = df["isco3"].value_counts()
    ocup = [c for c in sorted(ISCO3) if n_emp.get(c, 0) >= N_MIN]
    pares = pd.DataFrame({"a": df["isco3"], "b": nxt}).dropna()
    pares = pares[pares["a"].isin(ocup) & pares["b"].isin(ocup)]
    dur = ((df["fin"] - df["ini"]) / 4).where(df["fin"].notna())

    trans, p_cambia, p_a_jefatura, dur_med = {}, {}, {}, {}
    for a, g in pares.groupby("a"):
        cambia = g[g["b"] != a]
        p_cambia[a] = round(len(cambia) / len(g), 4)
        p_a_jefatura[a] = round((g["b"].str[0] == "1").mean(), 4) if a[0] != "1" else 0.0
        vc = cambia["b"].value_counts(normalize=True).head(TOP_K)
        trans[a] = {b: round(float(p), 4) for b, p in vc.items()}
    for a in ocup:
        d = dur[df["isco3"] == a].dropna()
        dur_med[a] = round(float(d[d > 0].median()), 2) if len(d) else None
    seq = df.groupby(key).size()
    return {
        "fuente": "JobHop v2 (VDAB, Flandes; CC BY 4.0): 355 mil currículums, ocupaciones ESCO agrupadas a ISCO-08 de 3 dígitos",
        "ocupaciones": ocup,
        "n_empleos": {a: int(n_emp[a]) for a in ocup},
        "p_cambia_de_grupo": p_cambia,
        "p_pasa_a_jefatura": p_a_jefatura,
        "transiciones": trans,
        "duracion_mediana_anios": dur_med,
        "largo_secuencia_mediana": float(seq.median()),
        "n_pares": int(len(pares)),
    }


def exposicion_ia(datos, ocup):
    ms = {}
    with open(os.path.join(datos, "exposicion_ia", "microsoft_ai_applicability_scores.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            ms[r["SOC Code"]] = float(r["ai_applicability_score"])
    el = collections.defaultdict(list)
    with open(os.path.join(datos, "exposicion_ia", "eloundou_gpts_occ_level.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            el[r["O*NET-SOC Code"][:7]].append(float(r["dv_rating_beta"]))
    el = {k: float(np.mean(v)) for k, v in el.items()}

    def rank(d):
        ks = sorted(d, key=d.get)
        return {k: (i + 0.5) / len(ks) for i, k in enumerate(ks)}

    r_ms, r_el = rank(ms), rank(el)
    out = {}
    for c in ocup:
        pref = ISCO3[c][1]
        a = [r_ms[s] for s in r_ms if any(s.startswith(p) for p in pref)]
        b = [r_el[s] for s in r_el if any(s.startswith(p) for p in pref)]
        vals = [float(np.mean(x)) for x in (a, b) if x]
        out[c] = round(float(np.mean(vals)), 3) if vals else None
    # sin puente: promedio del gran grupo
    for c in ocup:
        if out[c] is None:
            vec = [v for k, v in out.items() if v is not None and k[0] == c[0]]
            out[c] = round(float(np.mean(vec)), 3) if vec else 0.5
    return {
        "fuente": "Percentil de exposición a IA (0 a 1): promedio del ranking de Microsoft 'Working with AI' (CC BY 4.0) y de Eloundou et al. (beta), llevados de SOC a ISCO-3 con un puente propio por prefijo",
        "percentil": out,
    }


def esi_por_ocupacion(datos):
    f = os.path.join(datos, "esi_ine", "esi_2025_personas.csv")
    sep = ";" if open(f, encoding="latin-1").readline().count(";") > 5 else ","
    cols = ["ocup_ref", "ing_t_p", "fact_cal_esi", "edad", "cine11_1d", "b1", "sexo"]
    d = pd.read_csv(f, sep=sep, usecols=cols, encoding="latin-1", low_memory=False)
    for c in cols:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d[(d["ocup_ref"] == 1) & (d["ing_t_p"] > 0) & d["edad"].between(25, 54) & d["cine11_1d"].isin([4, 5, 6])]

    def wmed(g):
        g = g.sort_values("ing_t_p")
        cw = g["fact_cal_esi"].cumsum()
        return float(g["ing_t_p"][cw >= cw.iloc[-1] / 2].iloc[0])

    base = wmed(d)
    out = {}
    for b1, g in d.groupby("b1"):
        if len(g) >= 80 and int(b1) in range(1, 10):
            out[str(int(b1))] = {"mediana": round(wmed(g)), "relativo": round(wmed(g) / base, 3), "n": int(len(g))}
    return {
        "fuente": "INE, ESI 2025: mediana del ingreso de la ocupación principal por gran grupo CIUO-08 (b1), ocupados de 25 a 54 años con educación superior",
        "mediana_educacion_superior": round(base),
        "por_grupo": out,
    }


def esi_ocupacion_3_olas(der):
    """Sueldo relativo por gran grupo, ESI 2023-2025 (lo calcula datos_laborales/scripts/modelo/ofertas_esi.py).
    Solo grupos con al menos 100 casos universitarios; el resto no es destino en el motor."""
    o = json.load(open(os.path.join(der, "modelo_ofertas.json")))["sueldo_relativo_ocupacion"]["por_grupo"]
    return {"fuente": "INE, ESI 2023-2025: mediana del ingreso por gran grupo CIUO-08 sobre la mediana, ocupados de 25 a 54 años con educación universitaria o más",
            "por_grupo": {k: {"relativo": v["rel_universitaria_o_mas"], "n": v["n_universitaria"]} for k, v in o.items()
                          if v.get("rel_universitaria_o_mas") and v.get("n_universitaria", 0) >= 100}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True, help="carpeta datos_laborales/")
    a = ap.parse_args()
    der = os.path.join(a.datos, "derivados")
    cal = json.load(open(os.path.join(der, "calibracion.json")))
    ine = json.load(open(os.path.join(der, "calibracion_ine.json")))
    pan = json.load(open(os.path.join(der, "calibracion_paneles.json")))

    jh = jobhop(a.datos)
    ocup = jh["ocupaciones"]
    tablas = {
        "meta": {"generado_con": "backend/scripts/build_sim_data.py", "nota": "Tablas agregadas; los microdatos no se incluyen."},
        "isco3": {c: ISCO3[c][0] for c in ocup},
        "isco1": ISCO1,
        "jobhop": jh,
        "exposicion_ia": exposicion_ia(a.datos, ocup),
        "esi_ocupacion": esi_ocupacion_3_olas(der),
        "esi_edad_educacion": cal["esi_2025"]["por_edad_educacion"],
        "esi_sector_superior": cal["esi_2025"]["por_sector_educacion_superior"],
        "esi_sexo_educacion": cal["esi_2025"]["por_sexo_educacion_25_54"],
        "getonbrd_seniority_usd": cal["getonbrd"]["por_seniority"],
        "epf_quintiles": {
            q: {k: v[k] for k in ("gasto_per_capita", "ingreso_disponible_per_capita", "tasa_ahorro_aparente")}
            for q, v in ine["5_EPF_IX"]["quintiles_ingreso_disponible_hogar"].items()
        },
        "ine": ine["parametros_sugeridos_juego"],
        "paneles": pan["parametros_sugeridos_juego"],
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "sim", "data", "tablas.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(tablas, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"{os.path.normpath(out)}: {os.path.getsize(out) / 1024:.0f} KB, {len(ocup)} ocupaciones, {jh['n_pares']} transiciones")
    for c in ("251", "242", "133", "522"):
        if c in ocup:
            top = list(jh["transiciones"][c].items())[:5]
            print(c, ISCO3[c][0], "| IA", tablas["exposicion_ia"]["percentil"][c], "| cambia", jh["p_cambia_de_grupo"][c],
                  "| jefatura", jh["p_pasa_a_jefatura"][c], "|", [(ISCO3[b][0][:28], p) for b, p in top])
    print("ESI por grupo:", {k: v["relativo"] for k, v in tablas["esi_ocupacion"]["por_grupo"].items()})


if __name__ == "__main__":
    main()
