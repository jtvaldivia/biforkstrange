"""Magisteres en la oferta academica SIES 2026: arancel, duracion y jornada por universidad.

Fuente: SIES/mifuturo, Oferta_Academica_2026_SIES_05_06_2026_WEB_E.xlsx
  https://www.mifuturo.cl/bases-de-datos-de-oferta-academica/
Universo: Nivel Carrera == "Magister" y Vigencia == "Vigente con estudiantes nuevos".
Arancel: "Arancel Anual"; si "Formato Valor" == "Monto en UF" se convierte con la UF del 05-06-2026
  (fecha de corte de la base) publicada por el SII: https://www.sii.cl/valores_y_fechas/uf/uf2026.htm
Duracion: "Duracion Total" (semestres; incluye titulacion). Aranceles en 0 se excluyen del arancel.
Selectividad: salida de magister_selectividad.py (regla DIPRES 2026 replicada con DEMRE PAES 2024 y 2025).
Uso: python -I magister_oferta.py <oferta.xlsx|.pkl> <sel2024.json> <sel2025.json> <salida.json>
"""
import json, sys
import pandas as pd

UF_05_06_2026 = 40695.38  # SII, tabla UF 2026, junio dia 5

# Sigla DEMRE -> Codigo IES SIES (mismas universidades; correspondencia por nombre)
SIGLA_IES = {
    "UC": 86, "UAI": 23, "UTFSM": 88, "UANDES": 34, "UCH": 70, "UDEC": 87, "USACH": 71, "UDP": 3,
    "UDD": 45, "PUCV": 89, "UFRO": 76, "UTAL": 78, "ULS": 74, "UCN": 91, "UMAYOR": 10, "UV": 72,
    "UBB": 75, "UCM": 92, "UACH": 90, "UCSC": 93, "UNAB": 20, "UOH": 895, "UANT": 73, "UMAG": 77,
    "UFT": 2, "USS": 39, "UA": 31, "UTA": 80, "UAH": 69, "UDA": 79, "UCT": 94, "UTEM": 85,
    "UMCE": 82, "UBO": 50, "UCENTRAL": 4, "UNAP": 81, "ULAG": 84, "UNACH": 38, "UST": 13,
    "UPA": 83, "UGM": 1, "UAYSEN": 896, "UCSH": 42, "UACADEMIA": 11, "UDLA": 19,
}

src, s24, s25, out = sys.argv[1:5]
d = pd.read_pickle(src) if src.endswith(".pkl") else pd.read_excel(src)
m = d[(d["Nivel Carrera"] == "Magister") & (d["Vigencia"] == "Vigente con estudiantes nuevos")].copy()
uf = m["Formato Valor"] == "Monto en UF"
m["arancel_clp"] = m["Arancel Anual"].where(~uf, m["Arancel Anual"] * UF_05_06_2026)
m.loc[m["arancel_clp"] <= 0, "arancel_clp"] = float("nan")
m["matricula_clp"] = m["Matrícula Anual"].where(~uf, m["Matrícula Anual"] * UF_05_06_2026)
m["dur_sem"] = m["Duración Total"]
m["no_diurna"] = m["Jornada"] != "Diurna"

sel = {}
for an, path in (("2024", s24), ("2025", s25)):
    for u in json.load(open(path))["universidades"]:
        sel.setdefault(SIGLA_IES[u["SIGLA_UNIVERSIDAD"]], {"sigla": u["SIGLA_UNIVERSIDAD"]})[an] = u

def clase(c):
    if c not in sel:
        return None
    a, b = sel[c].get("2024", {}).get("competitiva"), sel[c].get("2025", {}).get("competitiva")
    return "si" if (a and b) else ("no" if (a is False and b is False) else "borde")

rows = []
for (cod, nom), g in m.groupby(["Código IES", "Nombre IES"]):
    s = sel.get(cod, {})
    rows.append({
        "nombre": nom, "codigo_ies": int(cod), "sigla_demre": s.get("sigla"),
        "selectiva": clase(cod),
        "frac_top30_paes2024": s.get("2024", {}).get("frac_top30"),
        "frac_top30_paes2025": s.get("2025", {}).get("frac_top30"),
        "n_magister": int(len(g)),
        "arancel_anual_mediano": None if g["arancel_clp"].isna().all() else round(float(g["arancel_clp"].median())),
        "duracion_semestres_mediana": float(g["dur_sem"].median()),
        "frac_no_diurna": round(float(g["no_diurna"].mean()), 3),
    })
rows.sort(key=lambda r: (-(r["frac_top30_paes2025"] or -1), r["nombre"]))

def _r(x):
    return None if pd.isna(x) else round(float(x))

def resumen(g):
    return {"n": int(len(g)), "n_con_arancel": int(g["arancel_clp"].notna().sum()),
            "arancel_anual_mediano": _r(g["arancel_clp"].median()),
            "arancel_anual_p25_p75": [_r(g["arancel_clp"].quantile(q)) for q in (0.25, 0.75)],
            "duracion_semestres_mediana": float(g["dur_sem"].median()),
            "duracion_semestres_p25_p75": [float(g["dur_sem"].quantile(q)) for q in (0.25, 0.75)]}

m["selectiva"] = m["Código IES"].map(clase)
res = {
    "universo": {"n_magister": int(len(m)), "uf_usada": UF_05_06_2026, "n_en_uf": int(uf.sum()),
                 "n_sin_arancel": int(m["arancel_clp"].isna().sum())},
    "por_jornada": {j: resumen(g) for j, g in m.groupby("Jornada")},
    "diurna_vs_no_diurna": {("no_diurna" if k else "diurna"): resumen(g) for k, g in m.groupby("no_diurna")},
    "por_selectiva": {str(k): resumen(g) for k, g in m.groupby(m["selectiva"].fillna("fuera_demre"))},
    "por_selectiva_y_jornada": {f"{k[0]}|{'no_diurna' if k[1] else 'diurna'}": resumen(g)
                                for k, g in m.groupby([m["selectiva"].fillna("fuera_demre"), "no_diurna"])},
    "sistema": resumen(m),
    "universidades": rows,
}
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "universidades"}, ensure_ascii=False, indent=1))
for r in rows: print(r)
