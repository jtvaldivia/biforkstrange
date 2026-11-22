"""Arma el catálogo de instituciones de educación superior (simulador/tablas/universidades.csv).

Fuentes (bases públicas de SIES / mifuturo.cl, descargadas en <carpeta datos_laborales>/mifuturo/):
- Buscador de Carreras 2025-2026 (Buscador_de_Carreras_2025_2026_SIES.xlsx): matrícula total 2025 y
  arancel anual 2026 de cada programa de pregrado, con el código SIES de la institución.
  https://www.mifuturo.cl/bases-de-datos-de-matriculados/ y https://www.mifuturo.cl/buscador-de-carreras/
- Buscador de Empleabilidad e Ingresos 2025-2026 (Buscador_Empleabilidad_ingresos_2025_2026_SIES.xlsx):
  tramo de ingreso promedio al 4° año de cada carrera en cada institución.
  https://www.mifuturo.cl/buscador-de-empleabilidad-e-ingresos/
- simulador/tablas/mifuturo_carreras.csv (ingreso genérico por carrera y tipo) y sies_magister_2026.csv.
- scripts/datos/universidades_curadas.json: siglas, dominios y las universidades extranjeras con la URL
  oficial de su arancel de magíster.

prima_pregrado = promedio, entre las carreras de la institución, de (ingreso al 4° año en la institución /
ingreso genérico de esa carrera en ese tipo de institución), normalizado a media 1 ponderada por matrícula
dentro de cada tipo de institución.

Uso: uv run --with openpyxl python -I backend/scripts/universidades.py <carpeta datos_laborales>
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
TABLAS = BACKEND / "simulador" / "tablas"
CURADAS = Path(__file__).resolve().parent / "datos" / "universidades_curadas.json"
LOGOS = BACKEND.parent / "frontend" / "public" / "logos" / "universidades"
PARAMETROS = BACKEND / "simulador" / "parametros.json"
FUENTES = BACKEND / "simulador" / "fuentes.json"

TIPO = {"Universidades": "U", "Insitutos Profesionales": "IP", "Institutos Profesionales": "IP", "Centros de Formación Técnica": "CFT"}
COLS = ["universidad_id", "nombre", "sigla", "pais", "tipo_institucion", "selectiva", "matricula", "peso_magister",
        "arancel_anual_pregrado", "prima_pregrado", "calidad_prima", "arancel_anual_magister", "arancel_magister_usd",
        "anios_magister", "dominio", "logo"]
NUM = {"mil": 1_000, "millón": 1_000_000, "millones": 1_000_000}


def monto(texto: str) -> float:
    """'$1 millón 100 mil' -> 1.100.000."""
    total, n = 0.0, None
    for tok in texto.replace("$", " ").split():
        if tok.replace(".", "").isdigit():
            n = float(tok.replace(".", ""))
        elif tok in NUM and n is not None:
            total += n * NUM[tok]
            n = None
    return total


def tramo(texto: str) -> float | None:
    """Punto medio del tramo de ingreso de mifuturo. 'Sobre $3 millones 500 mil' -> cota inferior."""
    if not texto or texto in ("s/i", "n/a"):
        return None
    if texto.startswith("Sobre"):
        return monto(texto)
    m = re.match(r"(?:De|Desde)\s+(.*?)\s+a\s+(.*)$", texto)
    assert m, texto
    return (monto(m.group(1)) + monto(m.group(2))) / 2


# UAI, UDD y Los Andes (y un par de IP y CFT) publican su arancel en UF ("UF 214"), no en pesos. Se pasan con
# la UF del 1 de enero de 2026, el año de los aranceles: $39.731,79 (Banco Central).
UF_2026 = 39_731.79


def pesos(texto) -> float | None:
    txt = str(texto or "")
    en_uf = txt.strip().upper().startswith("UF")
    s = re.sub(r"[^\d,]", "", txt).replace(",", ".") if en_uf else re.sub(r"[^\d]", "", txt)
    if not s:
        return None
    return round(float(s) * UF_2026) if en_uf else float(s)


def leer_xlsx(ruta: Path, fila_cabecera: int) -> list[tuple]:
    import openpyxl  # solo se usa aquí; se corre con `uv run --with openpyxl`
    wb = openpyxl.load_workbook(ruta, read_only=True)
    return [r for r in wb.worksheets[0].iter_rows(min_row=fila_cabecera + 1, values_only=True) if r[0] is not None]


def titulo(nombre: str) -> str:
    chicas = {"de", "del", "la", "las", "los", "y", "e", "en"}
    return " ".join(p.lower() if i and p.lower() in chicas else p.capitalize() for i, p in enumerate(nombre.split()))


def main(crudos: Path) -> None:
    cfg = json.loads(CURADAS.read_text(encoding="utf-8"))
    mf = crudos / "mifuturo"

    # matrícula y arancel de pregrado por institución
    matricula, arancel_x_mat, nombre_sies, tipo_de = defaultdict(int), defaultdict(float), {}, {}
    for r in leer_xlsx(mf / "Buscador_de_Carreras_2025_2026_SIES.xlsx", 2):
        if r[3] not in TIPO:  # notas al pie
            continue
        cod, tipo = str(r[1]), TIPO[r[3]]
        nombre_sies[cod], tipo_de[cod] = r[4], tipo
        m = int(r[15]) if str(r[15]).isdigit() else 0
        a = pesos(r[9])
        if m and a:
            matricula[cod] += m
            arancel_x_mat[cod] += m * a

    # ingreso al 4° año por institución y carrera, relativo al genérico de la carrera
    generico = {(f["tipo_institucion"], f["carrera"].strip()): float(f["ingreso_bruto_ano4"])
                for f in csv.DictReader(open(TABLAS / "mifuturo_carreras.csv", encoding="utf-8")) if f["ingreso_bruto_ano4"]}
    ratios, sin_par = defaultdict(list), 0
    for r in leer_xlsx(mf / "Buscador_Empleabilidad_ingresos_2025_2026_SIES.xlsx", 1):
        if r[1] not in TIPO:
            continue
        cod, tipo = str(r[0]), TIPO[r[1]]
        tipo_de.setdefault(cod, tipo)
        nombre_sies.setdefault(cod, r[2])
        ing = tramo(r[12])
        g = generico.get((tipo, str(r[5]).replace("\xa0", " ").strip()))
        if ing is None:
            continue
        if g is None:
            sin_par += 1
            continue
        ratios[cod].append(ing / g)

    mag = {f["universidad_id"]: f for f in csv.DictReader(open(TABLAS / "sies_magister_2026.csv", encoding="utf-8"))}

    # qué instituciones entran
    total_tipo = defaultdict(int)
    for cod, m in matricula.items():
        total_tipo[tipo_de[cod]] += m
    elegidas = {c for c in mag} | {c for c, t in tipo_de.items() if t == "U" and matricula.get(c)}
    elegidas |= {c for c, m in matricula.items() if tipo_de[c] in ("IP", "CFT") and m >= cfg["umbral_ip_cft"] * total_tipo[tipo_de[c]]}

    filas = []
    for cod in elegidas:
        cur = cfg["chilenas"].get(cod, {})
        tipo = tipo_de.get(cod, "U")
        m = mag.get(cod)
        filas.append({
            "universidad_id": cod,
            "nombre": cur.get("nombre") or (m["universidad"] if m else titulo(nombre_sies[cod])),
            "sigla": cur.get("sigla", m["sigla"] if m else ""),
            "pais": "Chile", "tipo_institucion": tipo,
            "selectiva": int(m["selectiva"]) if m else 0,
            "matricula": matricula.get(cod, 0),
            "programas": int(m["programas"]) if m else 0,
            "arancel_anual_pregrado": round(arancel_x_mat[cod] / matricula[cod]) if matricula.get(cod) else "",
            "prima_cruda": sum(ratios[cod]) / len(ratios[cod]) if ratios.get(cod) else None,
            "arancel_anual_magister": m["arancel_anual"] if m else "",
            "arancel_magister_usd": "",
            "anios_magister": m["anios"] if m else "",
            "dominio": cur.get("dominio", ""),
        })
        assert cod in cfg["chilenas"] or tipo == "U", f"falta {cod} {nombre_sies.get(cod)} en universidades_curadas.json"

    # normalización de la prima: media 1 ponderada por matrícula dentro de cada tipo
    for tipo in ("U", "IP", "CFT"):
        grupo = [f for f in filas if f["tipo_institucion"] == tipo and f["prima_cruda"] is not None and f["matricula"]]
        media = sum(f["prima_cruda"] * f["matricula"] for f in grupo) / sum(f["matricula"] for f in grupo)
        for f in filas:
            if f["tipo_institucion"] == tipo:
                f["prima_pregrado"] = f"{f['prima_cruda'] / media:.4f}" if f["prima_cruda"] is not None and f["matricula"] else ""
                f["calidad_prima"] = "derivado" if f["prima_pregrado"] else ""

    # peso de magíster: programas vigentes (SIES 2026) para las chilenas; las extranjeras suman un 3% fijo
    ext = cfg["extranjeras"]
    peso_ext = cfg["peso_magister_extranjeras"] if ext else 0.0
    tot_prog = sum(f["programas"] for f in filas)
    for f in filas:
        f["peso_magister"] = f"{f['programas'] / tot_prog * (1 - peso_ext):.6f}" if f["programas"] else "0"
    for x in ext:
        filas.append({
            "universidad_id": f"ext_{x['slug']}", "nombre": x["nombre"], "sigla": x.get("sigla", ""), "pais": x["pais"],
            "tipo_institucion": "EXT", "selectiva": 1, "matricula": 0, "peso_magister": f"{peso_ext / len(ext):.6f}",
            "arancel_anual_pregrado": "", "prima_pregrado": "", "calidad_prima": "", "arancel_anual_magister": "",
            "arancel_magister_usd": round(x["arancel_anual_usd"]) if x.get("arancel_anual_usd") is not None else "",
            "anios_magister": x.get("anios") or "", "dominio": x.get("dominio", ""),
        })

    orden = {"U": 0, "IP": 1, "CFT": 2, "EXT": 3}
    filas.sort(key=lambda f: (orden[f["tipo_institucion"]], -f["matricula"], f["universidad_id"]))
    ids = [f["universidad_id"] for f in filas]
    assert len(ids) == len(set(ids)), "universidad_id repetido"
    for f in filas:
        f["logo"] = int((LOGOS / f"{f['universidad_id']}.png").exists())
    with open(TABLAS / "universidades.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, COLS, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(filas)

    por_tipo = defaultdict(int)
    for f in filas:
        por_tipo[f["tipo_institucion"]] += 1
    print(f"instituciones: {len(filas)} {dict(por_tipo)}; sin prima: {sum(1 for f in filas if f['tipo_institucion'] != 'EXT' and not f['prima_pregrado'])}; "
          f"filas de ingreso sin carrera genérica en mifuturo_carreras: {sin_par}; con logo: {sum(f['logo'] for f in filas)}")
    actualizar_parametros()
    registrar(len(filas), len(ext))


def actualizar_parametros() -> None:
    d = json.loads(PARAMETROS.read_text(encoding="utf-8"))
    premio = next(p for p in d["parametros"] if p["id"] == "PREMIO_MAGISTER")
    nuevo = {"id": "PRIMA_EXTRANJERA", "valor": premio["valor"]["1"], "unidad": "fracción del sueldo",
             "descripcion": "Prima de una universidad extranjera = la de una selectiva chilena (DIPRES); no hay dato de retorno para chilenos.",
             "fuente": premio["fuente"], "calidad": "sintetico", "rango": [0.0, 0.12]}
    i = next((k for k, p in enumerate(d["parametros"]) if p["id"] == "PRIMA_EXTRANJERA"), None)
    if i is None:
        d["parametros"].append(nuevo)
    else:
        d["parametros"][i] = nuevo
    PARAMETROS.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def registrar(n: int, n_ext: int) -> None:
    entrada = {
        "tabla": "universidades",
        "archivo": "tablas/universidades.csv",
        "descripcion": "Universidades, institutos profesionales y CFT de Chile, más universidades extranjeras para magíster: matrícula, aranceles, prima de sueldo de pregrado y peso de magíster.",
        "columnas": {
            "universidad_id": "código SIES de la institución (el mismo de sies_magister_2026 en universidades); ext_<slug> para extranjeras",
            "nombre": "nombre de la institución",
            "sigla": "sigla usual, si tiene",
            "pais": "país",
            "tipo_institucion": "U, IP, CFT o EXT (extranjera)",
            "selectiva": "1 si es selectiva según la regla DIPRES 2026 (sies_magister_2026); 0 para IP, CFT y universidades sin magísteres en SIES 2026; 1 para extranjeras",
            "matricula": "matrícula total de pregrado 2025 (SIES, Buscador de Carreras 2025-2026); 0 para extranjeras",
            "peso_magister": "probabilidad relativa de elegirla para un magíster: programas vigentes SIES 2026 / total × 0,97; las extranjeras se reparten 0,03 en partes iguales (supuesto sintético)",
            "arancel_anual_pregrado": "arancel anual 2026 promedio de sus programas de pregrado ponderado por matrícula, CLP",
            "prima_pregrado": "ingreso al 4° año de sus carreras / ingreso genérico de esas carreras (mifuturo_carreras), promedio por carrera, normalizado a media 1 ponderada por matrícula dentro de su tipo; vacío sin datos",
            "calidad_prima": "'derivado' si hay prima; vacío si no",
            "arancel_anual_magister": "arancel anual mediano de sus magísteres, CLP (sies_magister_2026); vacío si no tiene",
            "arancel_magister_usd": "solo extranjeras: arancel anual en USD del magíster típico, desde la página oficial del programa (URL en scripts/datos/universidades_curadas.json)",
            "anios_magister": "duración del magíster en años (mediana SIES o la del programa extranjero)",
            "dominio": "sitio web oficial, para el ícono; vacío si no hay uno seguro",
            "logo": "1 si existe frontend/public/logos/universidades/<universidad_id>.png",
        },
        "poblacion": f"{n} instituciones: todas las universidades con pregrado o magíster en SIES, los IP y CFT con al menos 1% de la matrícula de su tipo, y {n_ext} extranjeras",
        "ponderador": "matricula (pregrado) o peso_magister (magíster)",
        "fuente_id": "mineduc_mifuturo",
        "script": "scripts/universidades.py",
        "advertencia": "El ingreso por institución viene en tramos de $100 mil (se usa el punto medio; el tramo abierto 'Sobre $3,5 millones' usa su cota inferior), así que la prima de las instituciones de ingresos más altos queda subestimada. La prima compara carreras iguales, pero no corrige por quién entra a cada institución.",
        "filas": n,
    }
    ruta = TABLAS / "indice.json"
    d = json.loads(ruta.read_text(encoding="utf-8"))
    cab = next(csv.reader(open(TABLAS / "universidades.csv", encoding="utf-8")))
    assert list(entrada["columnas"]) == cab
    d["tablas"] = [t for t in d["tablas"] if t["tabla"] != "universidades"] + [entrada]
    d["tablas"].sort(key=lambda t: t["tabla"])
    ruta.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
