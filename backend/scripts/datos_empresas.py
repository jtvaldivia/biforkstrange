"""Arma las tablas de empleadores y ofertas reales que usa el juego (backend/data/empresas/).

Fuentes, ya descargadas en una carpeta de datos crudos:
- SII, Nómina de empresas personas jurídicas, año comercial 2024 (PUB_EMPRESAS_PJ_2024.txt):
  https://www.sii.cl/sobre_el_sii/nominapersonasjuridicas.html
- Get on Board, API pública v0 (jobs.json con la empresa expandida y catalogos.json):
  https://www.getonbrd.com/api-doc.html

Uso: python3 -I backend/scripts/datos_empresas.py <carpeta datos_laborales>
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SALIDA = Path(__file__).resolve().parents[1] / "data" / "empresas"

RUBRO_SII = {
    "COMERCIO": "Comercio", "CONSTRUCCION": "Construcción", "ACTIVIDADES PROFESIONALES": "Servicios profesionales",
    "INDUSTRIA MANUFACTURERA": "Industria manufacturera", "TRANSPORTE": "Transporte", "ACTIVIDADES FINANCIERAS": "Finanzas y seguros",
    "ACTIVIDADES DE SERVICIOS ADMINISTRATIVOS": "Servicios administrativos", "ACTIVIDADES INMOBILIARIAS": "Otros servicios",
    "ACTIVIDADES DE ATENCION DE LA SALUD": "Salud", "ACTIVIDADES DE ALOJAMIENTO": "Hoteles y restaurantes",
    "AGRICULTURA": "Agricultura y pesca", "OTRAS ACTIVIDADES DE SERVICIOS": "Otros servicios", "INFORMACION Y COMUNICACIONES": "Información y comunicaciones",
    "ENSEÑANZA": "Enseñanza", "ACTIVIDADES ARTISTICAS": "Artes y entretención", "SUMINISTRO DE AGUA": "Otros servicios",
    "EXPLOTACION DE MINAS": "Minería", "SUMINISTRO DE ELECTRICIDAD": "Otros servicios", "ADMINISTRACION PUBLICA": "Administración pública",
}
SUBTIPOS_EXCLUIDOS = {"COMUNIDADES DE EDIFICIOS", "JUNTA DE VECINOS, ORG. COMUNITARIA", "SUCESIONES O COMUNIDADES HERED", "SOCIEDADES DE HECHO", "OTRA OSFL"}
SUFIJOS = re.compile(r"[\s,]+(S\.?\s?P\.?\s?A\.?|SPA|S\.?\s?A\.?|LIMITADA|LTDA\.?|E\.?\s?I\.?\s?R\.?\s?L\.?|Y\s+C(OMPA[NÑ]IA|IA\.?)\s+(LIMITADA|LTDA\.?)?)\.?$", re.I)
MAYUSCULAS = {"S.A.", "SPA", "AFP", "TI", "IT", "BCI", "CCU", "CMPC", "SQM", "LATAM", "ISS", "WOM", "SMU", "UC", "II", "III"}
CHICAS = {"de", "del", "la", "las", "los", "y", "e", "en", "el"}
GRANDES_POR_RUBRO = 40
PYMES_POR_RUBRO = 100


def nombre_corto(razon: str) -> str:
    """'FALABELLA RETAIL S.A.' -> 'Falabella Retail'. La razón social completa queda en otra columna."""
    n = razon.strip().strip(".")
    for _ in range(2):
        n = SUFIJOS.sub("", n).strip(" ,.")
    palabras = []
    for i, p in enumerate(n.split()):
        if p.upper() in MAYUSCULAS:
            palabras.append(p.upper())
        elif i and p.lower() in CHICAS:
            palabras.append(p.lower())
        else:
            palabras.append(p.capitalize())
    return " ".join(palabras)[:60]


def rubro_de(texto: str) -> str | None:
    for clave, rubro in RUBRO_SII.items():
        if texto.startswith(clave):
            return rubro
    return None


def sii(crudos: Path) -> None:
    csv.field_size_limit(10**7)
    grandes, pymes = defaultdict(list), defaultdict(list)
    with open(crudos / "sii_empresas" / "PUB_EMPRESAS_PJ_2024.txt", encoding="utf-8", errors="replace") as fh:
        filas = csv.reader(fh, delimiter="\t")
        next(filas)
        for f in filas:
            if len(f) < 20 or f[7] or f[11] in SUBTIPOS_EXCLUIDOS:
                continue
            rubro = rubro_de(f[14])
            if not rubro or not f[4].isdigit() or not f[5].isdigit():
                continue
            tramo, trabajadores = int(f[4]), int(f[5])
            region = "rm" if "METROPOLITANA" in f[17] else "otra"
            fila = {"rubro": rubro, "nombre": nombre_corto(f[3]), "razon_social": f[3].strip(), "tramo_ventas": tramo, "trabajadores": trabajadores,
                    "region": region, "comuna": f[19].strip().title()}
            if tramo >= 10 and trabajadores >= 200:
                grandes[rubro].append(fila)
            elif 5 <= tramo <= 9 and 10 <= trabajadores < 200:
                pymes[rubro].append(fila)
    with open(SALIDA / "sii_empleadores.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["tamano", "rubro", "nombre", "razon_social", "tramo_ventas", "trabajadores", "region", "comuna"])
        w.writeheader()
        total = 0
        for tamano, grupo, cuantas in (("grande", grandes, GRANDES_POR_RUBRO), ("pyme", pymes, PYMES_POR_RUBRO)):
            for _rubro, filas in sorted(grupo.items()):
                vistos = set()
                # Las grandes: las de más trabajadores (las conocidas). Las pymes: las más grandes dentro del tramo.
                for fila in sorted(filas, key=lambda x: (-x["trabajadores"], x["nombre"])):
                    if fila["nombre"] in vistos or len(fila["nombre"]) < 3:
                        continue
                    vistos.add(fila["nombre"])
                    w.writerow({"tamano": tamano, **fila})
                    total += 1
                    if len(vistos) >= cuantas:
                        break
    print("SII empleadores:", total, {r: len(v) for r, v in grandes.items()})


def getonbrd(crudos: Path) -> None:
    carpeta = crudos / "getonbrd" / "api_2026_11"
    catalogos = json.loads((carpeta / "catalogos.json").read_text())
    trabajos = json.loads((carpeta / "jobs.json").read_text())
    filas = []
    for j in trabajos:
        a = j["attributes"]
        empresa = ((a.get("company") or {}).get("data") or {}).get("attributes") or {}
        paises = a.get("countries") or []
        if not empresa.get("name") or not a.get("min_salary") or not a.get("max_salary"):
            continue
        if "Chile" not in paises and not (a.get("remote") and a.get("remote_modality") == "fully_remote"):
            continue
        seniority = catalogos["seniorities"].get(str(((a.get("seniority") or {}).get("data") or {}).get("id")), "")
        filas.append({
            "empresa": empresa["name"].strip(), "empresa_pais": empresa.get("country") or "", "cargo": a["title"].strip()[:90],
            "categoria": j["attributes"].get("category_name") or "", "seniority": seniority, "min_usd": a["min_salary"], "max_usd": a["max_salary"],
            "chile": int("Chile" in paises), "remoto": int(bool(a.get("remote"))), "postulantes": a.get("applications_count") or 0,
            "url": f"https://www.getonbrd.com/jobs/{j['id']}",
        })
    with open(SALIDA / "getonbrd_ofertas.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print("Get on Board ofertas con sueldo:", len(filas), "en Chile:", sum(f["chile"] for f in filas))


if __name__ == "__main__":
    crudos = Path(sys.argv[1])
    SALIDA.mkdir(parents=True, exist_ok=True)
    getonbrd(crudos)
    sii(crudos)
