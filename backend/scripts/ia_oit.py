"""Exposición a la IA generativa por ocupación (OIT 2025) y su cruce con los cargos del catálogo.

Fuente: Gmyrek, Berg, Kamiński, Konopczyński, Ładna, Nafradi, Rosłaniec y Troszyński, "Generative AI and Jobs:
A Refined Global Index of Occupational Exposure", OIT, documento de trabajo 140 (2025). Datos CC-BY-4.0:
https://github.com/pgmyrek/2025_GenAI_scores_ISCO08 (Final_Scores_ISCO08_Gmyrek_et_al_2025.xlsx).

Escribe:
- simulador/tablas/ia_oit_ciuo08.csv: las 427 ocupaciones CIUO-08 a 4 dígitos con puntaje y tipo de exposición.
- simulador/tablas/ia_cargos_ciuo08.csv: cada cargo de cargos_catalogo.csv con su código CIUO-08 y su tipo.

El código CIUO-08 de cada cargo lo asignó el equipo leyendo el nombre del cargo (CARGO_CIUO, abajo): la
equivalencia es "directa" si el cargo calza con una ocupación de la OIT y "aproximada" si es la más cercana.

Uso: uv run --no-project --with openpyxl python -I scripts/ia_oit.py <ruta del xlsx de la OIT>
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

TABLAS = Path(__file__).resolve().parents[1] / "simulador" / "tablas"

# potential23 de la OIT (2023, la clasificación con cifras para Chile: OIT-Banco Mundial 2024) -> tipo del juego
TIPO = {"Automation Potential": "automatiza", "Augmentation Potential": "aumenta",
        "The Big Uknown": "incognita", "Not affected": "no_afectado"}

# cargo_id -> (CIUO-08 a 4 dígitos, equivalencia). Asignado por el equipo desde el nombre del cargo.
CARGO_CIUO = {
    0: (1120, "directa"), 1: (1211, "directa"), 2: (1221, "directa"), 3: (1330, "directa"), 4: (1212, "directa"),
    5: (1221, "directa"), 6: (1219, "aproximada"), 7: (1323, "directa"), 8: (1219, "aproximada"), 9: (1345, "directa"),
    10: (1420, "directa"), 11: (1412, "directa"), 12: (1342, "directa"), 13: (1321, "directa"), 14: (1324, "directa"),
    15: (2512, "directa"), 16: (2513, "directa"), 17: (2512, "directa"), 18: (2512, "aproximada"), 19: (2522, "directa"),
    20: (2519, "directa"), 21: (2529, "directa"), 22: (2521, "directa"), 23: (2120, "aproximada"), 24: (2120, "aproximada"),
    25: (2519, "aproximada"), 26: (2421, "aproximada"), 27: (2166, "directa"), 28: (2166, "directa"), 29: (2431, "directa"),
    30: (2413, "directa"), 31: (2411, "directa"), 32: (2611, "directa"), 33: (2421, "directa"), 34: (2422, "directa"),
    35: (2423, "directa"), 36: (2142, "directa"), 37: (2146, "directa"), 38: (2114, "directa"), 39: (2141, "directa"),
    40: (2161, "directa"), 41: (2211, "directa"), 42: (2221, "directa"), 43: (2264, "directa"), 44: (2634, "directa"),
    45: (2262, "directa"), 46: (2265, "directa"), 47: (2269, "aproximada"), 48: (2341, "directa"), 49: (2330, "directa"),
    50: (2342, "directa"), 51: (2310, "directa"), 52: (2632, "aproximada"), 53: (2635, "directa"), 54: (2642, "directa"),
    55: (2132, "directa"), 56: (2250, "directa"), 57: (3221, "directa"), 58: (3212, "directa"), 59: (3512, "directa"),
    60: (3123, "directa"), 61: (3257, "directa"), 62: (3142, "directa"), 63: (3322, "directa"), 64: (3312, "directa"),
    65: (3313, "directa"), 66: (3343, "directa"), 67: (2432, "directa"), 68: (5312, "directa"), 69: (4323, "aproximada"),
    70: (3359, "aproximada"), 71: (3521, "directa"), 72: (3423, "directa"), 73: (3434, "directa"), 74: (4120, "directa"),
    75: (4110, "directa"), 76: (4211, "directa"), 77: (4222, "directa"), 78: (4226, "directa"), 79: (4313, "directa"),
    80: (4321, "directa"), 81: (3341, "directa"), 82: (5223, "directa"), 83: (5230, "directa"), 84: (5222, "directa"),
    85: (5131, "directa"), 86: (5120, "directa"), 87: (5414, "directa"), 88: (5321, "directa"), 89: (5311, "directa"),
    90: (5141, "directa"), 91: (5413, "directa"), 92: (5244, "directa"), 93: (5111, "directa"), 94: (6111, "directa"),
    95: (6221, "directa"), 96: (6111, "aproximada"), 97: (6210, "directa"), 98: (7112, "directa"), 99: (7411, "directa"),
    100: (7212, "directa"), 101: (7233, "directa"), 102: (7231, "directa"), 103: (7233, "directa"), 104: (7422, "directa"),
    105: (8332, "directa"), 106: (8331, "directa"), 107: (8111, "aproximada"), 108: (3133, "aproximada"), 109: (8183, "directa"),
    110: (8322, "aproximada"), 111: (8342, "directa"), 112: (9112, "directa"), 113: (9334, "directa"), 114: (9333, "directa"),
    115: (9211, "directa"), 116: (9412, "directa"), 117: (9313, "directa"), 118: (9112, "directa"), 119: (9611, "directa"),
    120: (2413, "aproximada"), 121: (2631, "directa"), 122: (2413, "aproximada"), 123: (3352, "directa"), 124: (2120, "directa"),
    125: (3323, "directa"), 126: (2141, "aproximada"), 127: (2151, "directa"), 128: (2143, "directa"), 129: (2619, "aproximada"),
    130: (3411, "directa"), 131: (2222, "directa"), 132: (2131, "aproximada"), 133: (2352, "directa"), 134: (2164, "directa"),
    135: (2421, "directa"),
}


def leer_oit(ruta: Path) -> dict[int, dict]:
    from openpyxl import load_workbook

    hoja = load_workbook(ruta, read_only=True).active
    filas = hoja.iter_rows(values_only=True)
    cab = list(next(filas))
    i = {c: cab.index(c) for c in ("ISCO_08", "Title", "mean_score_2025", "SD_2025", "potential23", "potential25")}
    ocup: dict[int, dict] = {}
    por_ocup = defaultdict(set)
    for f in filas:
        if f[i["ISCO_08"]] is None:
            continue
        cod = int(f[i["ISCO_08"]])
        por_ocup[cod].add(f[i["potential23"]])
        ocup.setdefault(cod, {"ciuo08_4d": cod, "titulo": f[i["Title"]], "mu_2025": float(f[i["mean_score_2025"]]),
                              "sd_2025": float(f[i["SD_2025"]]), "potencial23": f[i["potential23"]],
                              "potencial25": f[i["potential25"]]})
    assert all(len(v) == 1 for v in por_ocup.values()), "potential23 debería ser uno por ocupación"
    for o in ocup.values():
        o["tipo_ia"] = TIPO[o["potencial23"]]
        if o["tipo_ia"] == "no_afectado" and o["potencial25"].startswith("Exposed"):
            # la clasificación 2023 la daba por no afectada, pero el puntaje 2025 la pone expuesta (p. ej. los
            # desarrolladores, gradiente 3): expuesta sin saber si la IA la reemplaza o la complementa
            o["tipo_ia"] = "incognita"
    return ocup


def main(ruta: Path) -> None:
    ocup = leer_oit(ruta)
    cols = ["ciuo08_4d", "titulo", "mu_2025", "sd_2025", "potencial23", "potencial25", "tipo_ia"]
    with open(TABLAS / "ia_oit_ciuo08.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, cols, lineterminator="\n")
        w.writeheader()
        for cod in sorted(ocup):
            o = ocup[cod]
            w.writerow({**o, "mu_2025": f"{o['mu_2025']:.4f}", "sd_2025": f"{o['sd_2025']:.4f}"})

    cargos = list(csv.DictReader(open(TABLAS / "cargos_catalogo.csv", encoding="utf-8")))
    assert {int(c["cargo_id"]) for c in cargos} == set(CARGO_CIUO), "cada cargo necesita su código CIUO-08"
    cols_c = ["cargo_id", "nombre", "ciuo08_4d", "titulo_oit", "mu_2025", "tipo_ia", "equivalencia"]
    with open(TABLAS / "ia_cargos_ciuo08.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, cols_c, lineterminator="\n")
        w.writeheader()
        for c in cargos:
            cod, eq = CARGO_CIUO[int(c["cargo_id"])]
            assert cod in ocup, f"{c['nombre']}: {cod} no está en la OIT"
            if str(cod)[0] != c["ciuo08_1d"]:  # el catálogo lo pone en otro gran grupo: se avisa, no se cambia
                print(f"aviso: {c['nombre']} es {cod} en la OIT y grupo {c['ciuo08_1d']} en el catálogo")
            o = ocup[cod]
            w.writerow({"cargo_id": c["cargo_id"], "nombre": c["nombre"], "ciuo08_4d": cod, "titulo_oit": o["titulo"],
                        "mu_2025": f"{o['mu_2025']:.4f}", "tipo_ia": o["tipo_ia"], "equivalencia": eq})

    entradas = [
        {"tabla": "ia_oit_ciuo08", "archivo": "tablas/ia_oit_ciuo08.csv",
         "descripcion": "Exposición de cada ocupación CIUO-08 a la IA generativa y si la IA tiende a automatizarla o a complementarla.",
         "columnas": {"ciuo08_4d": "ocupación CIUO-08 a 4 dígitos (la del INE)",
                      "titulo": "nombre de la ocupación en inglés (OIT)",
                      "mu_2025": "exposición media de sus tareas a la IA generativa (0-1), puntaje 2025",
                      "sd_2025": "desviación de la exposición entre sus tareas",
                      "potencial23": "clasificación OIT 2023: Automation Potential, Augmentation Potential, The Big Uknown (sic) o Not affected",
                      "potencial25": "gradiente OIT 2025 (Exposed: Gradient 1-4, Minimal Exposure, Not Exposed)",
                      "tipo_ia": "potencial23 en el juego: automatiza, aumenta, incognita o no_afectado; las no afectadas en 2023 que el gradiente 2025 pone expuestas pasan a incognita"},
         "poblacion": "427 ocupaciones CIUO-08; puntajes de tareas por GPT-4o y Gemini validados con encuestas en Polonia",
         "ponderador": "", "fuente_id": "oit_genai_2025", "script": "scripts/ia_oit.py",
         "advertencia": "El puntaje es de tareas, global: no mide adopción en Chile. Con potencial23, Chile tiene 3% del empleo en automatización, 13% en aumento y 20% en incógnita (OIT-Banco Mundial 2024).",
         "filas": len(ocup)},
        {"tabla": "ia_cargos_ciuo08", "archivo": "tablas/ia_cargos_ciuo08.csv",
         "descripcion": "Cada cargo del catálogo con su ocupación CIUO-08 y su tipo de exposición a la IA (OIT).",
         "columnas": {"cargo_id": "cargo de cargos_catalogo", "nombre": "nombre del cargo",
                      "ciuo08_4d": "ocupación CIUO-08 a 4 dígitos asignada por el equipo",
                      "titulo_oit": "nombre de esa ocupación en la OIT", "mu_2025": "exposición media (ia_oit_ciuo08)",
                      "tipo_ia": "automatiza, aumenta, incognita o no_afectado (ia_oit_ciuo08)",
                      "equivalencia": "directa si el cargo calza con la ocupación, aproximada si es la más cercana"},
         "poblacion": f"{len(cargos)} cargos del catálogo", "ponderador": "", "fuente_id": "oit_genai_2025",
         "script": "scripts/ia_oit.py",
         "advertencia": "El código CIUO-08 de cada cargo lo asignó el equipo desde el nombre del cargo.",
         "filas": len(cargos)},
    ]
    ruta_ind = TABLAS / "indice.json"
    d = json.loads(ruta_ind.read_text(encoding="utf-8"))
    nombres = {e["tabla"] for e in entradas}
    d["tablas"] = [t for t in d["tablas"] if t["tabla"] not in nombres] + entradas
    d["tablas"].sort(key=lambda t: t["tabla"])
    ruta_ind.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tipos = defaultdict(int)
    for c in cargos:
        tipos[ocup[CARGO_CIUO[int(c["cargo_id"])][0]]["tipo_ia"]] += 1
    print(f"{len(ocup)} ocupaciones; cargos por tipo: {dict(tipos)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
