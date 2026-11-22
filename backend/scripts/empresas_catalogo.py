"""Arma el catálogo de empresas y de cargos del juego (simulador/tablas/empresas_catalogo.csv y cargos_catalogo.csv).

Entradas, todas dentro del repo:
- scripts/datos/empresas_curadas.json y cargos_curados.json: la lista elegida a mano (sin números).
- data/empresas/*.csv: nómina SII 2024, avisos de Get on Board y concursos de empleospublicos.cl
  (los genera scripts/datos_empresas.py desde los crudos).
- simulador/tablas/*.csv: ESI 2025, flujos laborales INE, Y Combinator, Get on Board, aplicabilidad de IA.

Cada número del catálogo es derivado de esas tablas o sintético (sorteado con semilla fija sobre una
distribución calibrada con ellas); las columnas calidad_* lo dicen. También actualiza los parámetros
EMPRESA_SIGMA_SUELDO y EMPRESA_SIGMA_ASCENSO en simulador/parametros.json con el valor calibrado.

Uso: python3 -I backend/scripts/empresas_catalogo.py [<carpeta datos_laborales>]
La carpeta es opcional: este catálogo solo lee tablas ya versionadas.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import NormalDist

BACKEND = Path(__file__).resolve().parents[1]
TABLAS = BACKEND / "simulador" / "tablas"
DATOS = BACKEND / "data" / "empresas"
CURADAS = Path(__file__).resolve().parent / "datos"
LOGOS = BACKEND.parent / "frontend" / "public" / "logos" / "empresas"
PARAMETROS = BACKEND / "simulador" / "parametros.json"

SEMILLA = 20261121
RUBROS = ["Minería", "Finanzas y seguros", "Información y comunicaciones", "Comercio", "Salud", "Enseñanza",
          "Servicios profesionales", "Construcción", "Industria manufacturera", "Transporte", "Agricultura y pesca",
          "Hoteles y restaurantes", "Artes y entretención", "Servicios administrativos", "Administración pública", "Otros servicios"]
TIPOS = ["grande", "pyme", "startup", "publico", "extranjero"]
TIPOS_SORTEADOS = ("grande", "pyme", "startup")
AREAS = ["Administración y Comercio", "Agropecuaria", "Arte y Arquitectura", "Ciencias Básicas", "Ciencias Sociales",
         "Derecho", "Educación", "Humanidades", "Salud", "Tecnología"]
EDUS = ["media", "tecnica", "universitaria", "postgrado"]
NIVELES = range(5)
GRILLA_SIGMA = [i / 200 for i in range(0, 201)]  # 0.000 .. 1.000

COLS_EMPRESAS = ["empresa_id", "nombre", "rubro", "tipo", "tamano_esi", "dominio", "logo", "origen", "pais", "peso",
                 "mult_sueldo", "mult_despido", "mult_cierre", "mult_ascenso", "exposicion_ia", "horas",
                 "calidad_sueldo", "calidad_despido", "calidad_ascenso", "calidad_ia", "calidad_horas"]
COLS_CARGOS = ["cargo_id", "nombre", "ciuo08_1d", "ocupacion_ia", "exposicion_ia", "area_getonbrd", "prima_getonbrd",
               "nivel_min", "nivel_max", "edu_min", "areas", "rubros", "tipos", "peso", "calidad_ia", "calidad_prima"]


def leer(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def tabla(nombre: str) -> list[dict]:
    return leer(TABLAS / f"{nombre}.csv")


def tamano_esi(trabajadores: int) -> str:
    """Clase de b15_1 de la ESI (personas que trabajan en la empresa)."""
    if trabajadores < 5:
        return "menos_de_5"
    if trabajadores <= 10:
        return "5_a_10"
    if trabajadores <= 49:
        return "11_a_49"
    if trabajadores <= 199:
        return "50_a_199"
    return "200_o_mas"


def tamano_ine_por_tramo(tramo: int) -> str:
    """Tamaño por ventas (tramos SII), el mismo criterio de los flujos laborales del INE."""
    if tramo >= 10:
        return "Grandes Empresas"
    if tramo >= 8:
        return "Medianas Empresas"
    if tramo >= 5:
        return "Pequeñas Empresas"
    return "Microempresas"


def tamano_ine_por_trabajadores(n: int) -> str:
    """Sin ventas conocidas (startups de YC), por trabajadores según la Ley 20.416."""
    if n >= 200:
        return "Grandes Empresas"
    if n >= 50:
        return "Medianas Empresas"
    if n >= 10:
        return "Pequeñas Empresas"
    return "Microempresas"


def cuantil(xs: list[float], q: float) -> float:
    """Cuantil con interpolación lineal (tipo 7 de Hyndman y Fan, el de numpy por defecto)."""
    s = sorted(xs)
    h = (len(s) - 1) * q
    lo = math.floor(h)
    return s[lo] + (h - lo) * (s[min(lo + 1, len(s) - 1)] - s[lo])


def normalizar(empresas: list[dict], col: str) -> None:
    """Promedio 1 dentro de cada (tipo, rubro), ponderado por peso. Una sola empresa queda en 1.

    El sueldo se normaliza en logaritmo (media geométrica = 1): las metas del paquete son medianas
    (ESI, mifuturo), y con media aritmética 1 la mediana de exp(σz) quedaría en exp(−σ²/2) ≈ 0,97.
    Las probabilidades (despido, cierre, ascenso) se normalizan con media aritmética, que es la que conserva
    la tasa promedio.
    """
    celdas = defaultdict(list)
    for e in empresas:
        celdas[(e["tipo"], e["rubro"])].append(e)
    for grupo in celdas.values():
        m = _promedio(grupo, col)
        for e in grupo:
            e[col] = e[col] / m


def _promedio(grupo: list[dict], col: str) -> float:
    w = sum(e["peso"] for e in grupo)
    if col in GEOMETRICAS:
        return math.exp(sum(e["peso"] * math.log(e[col]) for e in grupo) / w)
    return sum(e["peso"] * e[col] for e in grupo) / w


GEOMETRICAS = {"mult_sueldo"}


# ---------------------------------------------------------------- empresas

def resolver(curadas: list[dict]) -> list[dict]:
    sii = defaultdict(list)
    for f in leer(DATOS / "sii_empleadores.csv"):
        sii[f["nombre"]].append(f)
    yc = {f["nombre"]: f for f in tabla("yc_chile")}
    avisos = defaultdict(list)
    for f in leer(DATOS / "getonbrd_ofertas.csv"):
        avisos[f["empresa"]].append(f)
    concursos = defaultdict(list)
    for f in leer(DATOS / "concursos_estado.csv"):
        concursos[f["servicio"]].append(f)

    vistos, salida = set(), []
    for c in curadas:
        e = {"nombre": c["nombre"], "rubro": c["rubro"], "tipo": c["tipo"], "dominio": c.get("dominio", ""),
             "origen": c["origen"], "pais": c.get("pais", "Chile"), "trabajadores": None, "tramo": None,
             "yc_industria": "", "avisos": [], "concursos": []}
        clave = c.get("clave", c["nombre"])
        assert c["rubro"] in RUBROS and c["tipo"] in TIPOS, c
        assert e["nombre"] not in vistos, f"empresa repetida: {e['nombre']}"
        vistos.add(e["nombre"])
        if c["origen"] == "sii":
            filas = sii.get(clave)
            assert filas, f"{clave!r} no está en sii_empleadores.csv"
            f = max(filas, key=lambda x: int(x["trabajadores"]))
            e["trabajadores"], e["tramo"] = int(f["trabajadores"]), int(f["tramo_ventas"])
        elif c["origen"] == "yc":
            assert clave in yc, f"{clave!r} no está en yc_chile.csv"
            e["trabajadores"], e["yc_industria"] = int(yc[clave]["tamano_equipo"]), yc[clave]["industria"]
        elif c["origen"] == "getonbrd":
            assert clave in avisos, f"{clave!r} no está en getonbrd_ofertas.csv"
            e["avisos"] = avisos[clave]
        elif c["origen"] == "concursos":
            assert clave in concursos, f"{clave!r} no está en concursos_estado.csv"
            e["concursos"] = concursos[clave]
        else:
            assert c["origen"] == "curada" and c.get("nota"), f"{c['nombre']}: origen curada exige nota"
        salida.append(e)
    salida.sort(key=lambda e: (e["rubro"], e["tipo"], e["nombre"]))
    for i, e in enumerate(salida):
        e["empresa_id"] = i
    return salida


def base_sueldo(empresas: list[dict]) -> None:
    """Parte derivada de mult_sueldo (sin sorteo): R_tamano, aviso o concurso relativo a su referencia."""
    esi = {f["tamano_empresa"]: f for f in tabla("esi_ingreso_tamano") if f["educacion"] == "todas"}
    seniority = {f["seniority"]: float(f["mediana_usd"]) for f in tabla("getonbrd_sueldos_seniority")}
    estamento = {f["estamento"]: float(f["renta_bruta_p50"]) for f in tabla("estado_estamentos")}
    for e in empresas:
        e["tamano_esi"] = tamano_esi(e["trabajadores"]) if e["trabajadores"] is not None and e["tipo"] in TIPOS_SORTEADOS else ""
    for tipo in TIPOS_SORTEADOS:
        clases = sorted({e["tamano_esi"] for e in empresas if e["tipo"] == tipo and e["tamano_esi"]})
        w = sum(float(esi[k]["share"]) for k in clases)
        media = sum(float(esi[k]["share"]) * float(esi[k]["p50"]) for k in clases) / w
        for e in empresas:
            if e["tipo"] == tipo:
                e["r_sueldo"] = float(esi[e["tamano_esi"]]["p50"]) / media if e["tamano_esi"] else 1.0
    # Públicas y extranjeras: promedio de todos los concursos o avisos de la empresa, relativo a su
    # estamento o seniority. La renta de un concurso mezcla el grado del cargo con el servicio, así que se
    # acota al rango [p25/p50, p75/p50] ESI del rubro; las acotadas quedan marcadas sintetico.
    rubro = {f["rubro"]: f for f in tabla("esi_ingreso_rubro") if f["educacion"] == "todas"}
    for e in empresas:
        e["acotado"] = False
        if e["tipo"] == "extranjero":
            r = [(float(a["min_usd"]) + float(a["max_usd"])) / 2 / seniority[a["seniority"]] for a in e["avisos"]]
        elif e["tipo"] == "publico":
            r = [float(c["renta_bruta"]) / estamento[c["estamento"]] for c in e["concursos"]]
        else:
            continue
        x = sum(r) / len(r)
        f = rubro[e["rubro"]]
        lo, hi = float(f["p25"]) / float(f["p50"]), float(f["p75"]) / float(f["p50"])
        e["r_sueldo"] = min(max(x, lo), hi)
        e["acotado"] = e["r_sueldo"] != x


def aplicar_sigma_sueldo(empresas: list[dict], sigma: float) -> None:
    for e in empresas:
        j = math.exp(sigma * e["z_sueldo"] - sigma**2 / 2) if e["tipo"] in TIPOS_SORTEADOS else 1.0
        e["mult_sueldo"] = e["r_sueldo"] * j
    normalizar(empresas, "mult_sueldo")


def calibrar_sigma_sueldo(empresas: list[dict]) -> tuple[float, dict]:
    """Mayor σ de la grilla tal que, para todo σ' ≤ σ, el p25-p75 de mult_sueldo × p50 del rubro
    (empresas grandes, pymes y startups del catálogo) queda dentro del p25-p75 ESI del rubro."""
    esi = {f["rubro"]: f for f in tabla("esi_ingreso_rubro") if f["educacion"] == "todas"}
    mejor, holgura = 0.0, {}
    for sigma in GRILLA_SIGMA:
        aplicar_sigma_sueldo(empresas, sigma)
        ok, h = True, {}
        for rubro in RUBROS:
            p25, p50, p75 = (float(esi[rubro][k]) for k in ("p25", "p50", "p75"))
            v = [e["mult_sueldo"] * p50 for e in empresas if e["rubro"] == rubro and e["tipo"] in TIPOS_SORTEADOS]
            if len(v) < 2:
                continue
            q25, q75 = cuantil(v, 0.25), cuantil(v, 0.75)
            h[rubro] = (round(q25 / p25, 3), round(q75 / p75, 3))
            ok &= q25 >= p25 and q75 <= p75
        if not ok:
            break
        mejor, holgura = sigma, h
    return mejor, holgura


def mult_despido(empresas: list[dict]) -> None:
    salida = {f["grupo"]: float(f["salida_anual"]) for f in tabla("ine_flujos_laborales_2025") if f["dimension"] == "tamano"}
    for e in empresas:
        if e["tipo"] in TIPOS_SORTEADOS and e["tramo"] is not None:
            e["tamano_ine"] = tamano_ine_por_tramo(e["tramo"])
        elif e["tipo"] in TIPOS_SORTEADOS and e["trabajadores"] is not None:
            e["tamano_ine"] = tamano_ine_por_trabajadores(e["trabajadores"])
        else:
            e["tamano_ine"] = ""
    for tipo in TIPOS:
        con = [e for e in empresas if e["tipo"] == tipo and e["tamano_ine"]]
        media = sum(salida[e["tamano_ine"]] for e in con) / len(con) if con else 1.0
        for e in empresas:
            if e["tipo"] == tipo:
                e["mult_despido"] = salida[e["tamano_ine"]] / media if e["tamano_ine"] else 1.0
    normalizar(empresas, "mult_despido")


def mult_cierre(empresas: list[dict], industria_por_rubro: dict) -> None:
    filas = [f for f in tabla("yc_por_industria") if f["nivel"] == "industria" and f["share_inactiva"]]
    inactiva = {f["industria"]: float(f["share_inactiva"]) for f in filas}
    media = sum(float(f["n"]) * float(f["share_inactiva"]) for f in filas) / sum(float(f["n"]) for f in filas)
    for e in empresas:
        if e["tipo"] == "startup":
            ind = e["yc_industria"] or industria_por_rubro[e["rubro"]]
            e["yc_industria"] = ind
            e["mult_cierre"] = inactiva[ind] / media
        else:
            e["mult_cierre"] = 1.0
    normalizar(empresas, "mult_cierre")


def exposicion_rubro(ocupaciones: dict) -> dict[str, float]:
    ia = {f["ocupacion_eeuu"]: float(f["aplicabilidad_ia"]) for f in tabla("ia_aplicabilidad_ocupaciones")}
    salida = {}
    for rubro in RUBROS:
        lista = ocupaciones[rubro]
        assert 5 <= len(lista) <= 10, rubro
        faltan = [o for o in lista if o not in ia]
        assert not faltan, f"ocupaciones que no están en ia_aplicabilidad_ocupaciones: {faltan}"
        salida[rubro] = sum(ia[o] for o in lista) / len(lista)
    return salida


def horas(empresas: list[dict]) -> float:
    share = next(float(f["share_50_mas"]) for f in tabla("esi_jornada") if f["sexo"] == "todos" and f["banda_edad"] == "18-54")
    k = round(share * len(empresas))
    elegidas = set(random.Random(SEMILLA + 3).sample([e["empresa_id"] for e in empresas], k))
    for e in empresas:
        e["horas"] = 50 if e["empresa_id"] in elegidas else 44
    return share


def catalogo_empresas() -> tuple[list[dict], float, dict]:
    cfg = json.loads((CURADAS / "empresas_curadas.json").read_text(encoding="utf-8"))
    empresas = resolver(cfg["empresas"])
    share = {f["rubro"]: float(f["share_ocupados_banda"]) for f in tabla("esi_ingreso_rubro_edad") if f["banda_edad"] == "18-54" and f["share_ocupados_banda"]}
    n_celda = defaultdict(int)
    for e in empresas:
        n_celda[(e["tipo"], e["rubro"])] += 1
    for e in empresas:
        e["peso"] = share[e["rubro"]] / n_celda[(e["tipo"], e["rubro"])]

    normal = NormalDist()
    r_sueldo, r_ascenso = random.Random(SEMILLA), random.Random(SEMILLA + 1)
    for e in empresas:  # orden de empresa_id: el sorteo es reproducible
        e["z_sueldo"] = normal.inv_cdf(r_sueldo.random())
        e["z_ascenso"] = normal.inv_cdf(r_ascenso.random())

    base_sueldo(empresas)
    sigma, holgura = calibrar_sigma_sueldo(empresas)
    aplicar_sigma_sueldo(empresas, sigma)
    mult_despido(empresas)
    mult_cierre(empresas, cfg["industria_yc_por_rubro"])
    for e in empresas:
        e["mult_ascenso"] = math.exp(sigma * e["z_ascenso"] - sigma**2 / 2)
    normalizar(empresas, "mult_ascenso")
    expo = exposicion_rubro(cfg["ocupaciones_por_rubro"])
    share_50 = horas(empresas)

    for e in empresas:
        e["exposicion_ia"] = expo[e["rubro"]]
        e["logo"] = int((LOGOS / f"{e['empresa_id']}.png").exists())
        e["calidad_sueldo"] = "sintetico" if (e["tipo"] in TIPOS_SORTEADOS and sigma > 0) or e["acotado"] else "derivado"
        e["calidad_despido"] = "derivado"
        e["calidad_ascenso"] = "sintetico"
        e["calidad_ia"] = "sintetico"
        e["calidad_horas"] = "sintetico"

    # verificaciones
    assert {e["rubro"] for e in empresas} == set(RUBROS), "falta algún rubro"
    assert {e["tipo"] for e in empresas} == set(TIPOS), "falta algún tipo"
    celdas = defaultdict(list)
    for e in empresas:
        celdas[(e["tipo"], e["rubro"])].append(e)
    for grupo in celdas.values():
        for col in ("mult_sueldo", "mult_despido", "mult_cierre", "mult_ascenso"):
            m = _promedio(grupo, col)
            assert abs(m - 1) < 1e-9, (col, grupo[0]["tipo"], grupo[0]["rubro"], m)
    for e in empresas:
        if e["acotado"]:
            print(f"  acotado: {e['nombre']} ({e['tipo']}, {e['rubro']}) r={e['r_sueldo']:.3f}")
    print(f"σ sueldo calibrado = {sigma:.3f}; holgura por rubro (q25/p25, q75/p75): {holgura}")
    print(f"horas 50: {sum(e['horas'] == 50 for e in empresas)} de {len(empresas)} (share ESI {share_50})")
    return empresas, sigma, holgura


def escribir_empresas(empresas: list[dict]) -> None:
    with open(TABLAS / "empresas_catalogo.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, COLS_EMPRESAS, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for e in empresas:
            fila = dict(e)
            for col in ("mult_sueldo", "mult_despido", "mult_cierre", "mult_ascenso"):
                fila[col] = f"{e[col]:.12f}"
            fila["peso"] = f"{e['peso']:.12f}"
            fila["exposicion_ia"] = f"{e['exposicion_ia']:.4f}"
            w.writerow(fila)


# ---------------------------------------------------------------- cargos

def lista(valor: str, dominio: list[str]) -> set[str]:
    if valor == "*":
        return set(dominio)
    xs = valor.split("|")
    malos = [x for x in xs if x not in dominio]
    assert not malos, f"valores fuera del dominio: {malos}"
    return set(xs)


def catalogo_cargos(empresas: list[dict]) -> list[dict]:
    cfg = json.loads((CURADAS / "cargos_curados.json").read_text(encoding="utf-8"))
    ia = {f["ocupacion_eeuu"]: float(f["aplicabilidad_ia"]) for f in tabla("ia_aplicabilidad_ocupaciones")}
    share = {int(f["ciuo08_1d"]): float(f["share_ocupados_banda"]) for f in tabla("esi_ingreso_ocupacion") if f["banda_edad"] == "18-54"}
    gob = {f["area"]: (float(f["sueldo_min_mediano_usd"]) + float(f["sueldo_max_mediano_usd"])) / 2
           for f in tabla("getonbrd_sueldos") if f["seniority"] == "todas" and f["remoto"] == "todos"}
    por_grupo = defaultdict(int)
    for c in cfg["cargos"]:
        por_grupo[c["ciuo"]] += 1

    cargos, nombres = [], set()
    for i, c in enumerate(cfg["cargos"]):
        assert c["nombre"] not in nombres, f"cargo repetido: {c['nombre']}"
        nombres.add(c["nombre"])
        assert c["ocupacion_ia"] in ia, f"{c['nombre']}: {c['ocupacion_ia']!r} no está en ia_aplicabilidad_ocupaciones"
        assert 1 <= c["ciuo"] <= 9 and c["edu_min"] in EDUS and 0 <= c["nivel"][0] <= c["nivel"][1] <= 4, c
        assert c["equivalencia"] in ("directa", "aproximada")
        lista(c["areas"], AREAS), lista(c["rubros"], RUBROS), lista(c["tipos"], TIPOS)
        area = c["area_getonbrd"]
        assert area == "" or area in gob, area
        cargos.append({
            "cargo_id": i, "nombre": c["nombre"], "ciuo08_1d": c["ciuo"], "ocupacion_ia": c["ocupacion_ia"],
            "exposicion_ia": f"{ia[c['ocupacion_ia']]:.3f}", "area_getonbrd": area,
            "prima_getonbrd": f"{gob[area] / gob['todas']:.4f}" if area else "1",
            "nivel_min": c["nivel"][0], "nivel_max": c["nivel"][1], "edu_min": c["edu_min"],
            "areas": c["areas"], "rubros": c["rubros"], "tipos": c["tipos"],
            "peso": f"{share[c['ciuo']] / por_grupo[c['ciuo']]:.12f}",
            "calidad_ia": "derivado" if c["equivalencia"] == "directa" else "sintetico",
            "calidad_prima": "dato" if area else "derivado",
        })

    # Garantía: cada empresa tiene al menos un cargo para cada (educación, nivel), ignorando el área.
    huecos = []
    for e in empresas:
        for edu in EDUS:
            for nivel in NIVELES:
                if not any(EDUS.index(edu) >= EDUS.index(c["edu_min"]) and c["nivel_min"] <= nivel <= c["nivel_max"]
                           and e["rubro"] in lista(c["rubros"], RUBROS) and e["tipo"] in lista(c["tipos"], TIPOS)
                           for c in cargos):
                    huecos.append((e["nombre"], edu, nivel))
    assert not huecos, f"empresas sin cargo compatible: {huecos[:10]}"
    with open(TABLAS / "cargos_catalogo.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, COLS_CARGOS, lineterminator="\n")
        w.writeheader()
        w.writerows(cargos)
    return cargos


# ---------------------------------------------------------------- parámetros

def actualizar_parametros(sigma: float) -> None:
    d = json.loads(PARAMETROS.read_text(encoding="utf-8"))
    nuevos = {
        "EMPRESA_SIGMA_SUELDO": (
            "Dispersión del sueldo entre empresas del mismo tipo y rubro: mult_sueldo = R_tamano × exp(σ·z − σ²/2), "
            "z normal sorteada con semilla fija. σ es el mayor valor de una grilla de 0 a 1 (paso 0,005) con el que, "
            "en todos los rubros, el p25 y el p75 de mult_sueldo × p50 del rubro (grandes, pymes y startups del "
            "catálogo, tras normalizar a media geométrica 1 por tipo y rubro) quedan dentro del p25-p75 ESI 2025 del rubro "
            "(esi_ingreso_rubro, educación todas). Lo calcula scripts/empresas_catalogo.py."),
        "EMPRESA_SIGMA_ASCENSO": (
            "Dispersión entre empresas de la probabilidad de ascenso: mult_ascenso = exp(σ·z − σ²/2), z normal con "
            "semilla fija. No hay en el paquete una medición de ascensos por empresa para calibrarlo, así que usa el "
            "mismo σ que EMPRESA_SIGMA_SUELDO."),
    }
    params = d["parametros"]
    for pid, desc in nuevos.items():
        p = {"id": pid, "valor": sigma, "unidad": "desviación log", "descripcion": desc, "fuente": "equipo_sintetico",
             "calidad": "sintetico", "rango": [0.0, round(sigma * 1.5, 4)]}
        i = next((k for k, x in enumerate(params) if x["id"] == pid), None)
        if i is None:
            params.append(p)
        else:
            params[i] = p
    PARAMETROS.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def registrar_indice(entradas: list[dict]) -> None:
    """Agrega o reemplaza las entradas de estas tablas en simulador/tablas/indice.json."""
    ruta = TABLAS / "indice.json"
    d = json.loads(ruta.read_text(encoding="utf-8"))
    for nueva in entradas:
        cab = next(csv.reader(open(TABLAS / Path(nueva["archivo"]).name, encoding="utf-8")))
        assert list(nueva["columnas"]) == cab, (nueva["tabla"], cab)
        i = next((k for k, t in enumerate(d["tablas"]) if t["tabla"] == nueva["tabla"]), None)
        if i is None:
            d["tablas"].append(nueva)
        else:
            d["tablas"][i] = nueva
    d["tablas"].sort(key=lambda t: t["tabla"])
    ruta.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def entradas_indice(n_empresas: int, n_cargos: int, sigma: float) -> list[dict]:
    calidad = "'derivado' (sale de tablas sin sorteo) o 'sintetico' (lleva sorteo con semilla fija o un cruce hecho a mano)"
    return [{
        "tabla": "empresas_catalogo",
        "archivo": "tablas/empresas_catalogo.csv",
        "descripcion": "Empresas reales que el juego ofrece como empleador, con multiplicadores de sueldo, despido, cierre y ascenso relativos a su tipo y rubro.",
        "columnas": {
            "empresa_id": "índice estable (0..n-1), ordenado por rubro, tipo y nombre",
            "nombre": "nombre corto de la empresa o servicio",
            "rubro": "rubro del juego (dominio rubro de estado.json)",
            "tipo": "tipo de empleador: grande, pyme, startup, publico o extranjero",
            "tamano_esi": "clase de tamaño de esi_ingreso_tamano según trabajadores (SII o YC); vacío si no hay dato o no aplica",
            "dominio": "sitio web oficial, para el ícono; vacío si no hay uno seguro",
            "logo": "1 si existe frontend/public/logos/empresas/<empresa_id>.png",
            "origen": "sii, yc, getonbrd, concursos o curada (ver scripts/datos/empresas_curadas.json)",
            "pais": "país de la empresa (Chile salvo las extranjeras)",
            "peso": "share_ocupados_banda del rubro (esi_ingreso_rubro_edad, 18-54) repartido en partes iguales entre las empresas del mismo tipo y rubro; probabilidad relativa de sorteo",
            "mult_sueldo": "multiplicador del sueldo del rubro; media geométrica ponderada por peso = 1 en cada (tipo, rubro), para no mover las medianas. Grandes, pymes y startups: p50 ESI de su tamaño / media de su tipo × exp(σ·z − σ²/2) con σ = EMPRESA_SIGMA_SUELDO. Públicas: renta de sus concursos / mediana del estamento. Extranjeras: punto medio de sus avisos / mediana de su seniority. Públicas y extranjeras acotadas a [p25/p50, p75/p50] ESI del rubro",
            "mult_despido": "salida anual INE de su tamaño de empresa / promedio de su tipo, normalizado a media 1 por (tipo, rubro); 1 si no hay tamaño",
            "mult_cierre": "solo startups: share_inactiva de su industria YC / promedio YC, normalizado a media 1 por (tipo, rubro); 1 para el resto",
            "mult_ascenso": "exp(σ·z − σ²/2) con σ = EMPRESA_SIGMA_ASCENSO, normalizado a media 1 por (tipo, rubro)",
            "exposicion_ia": "aplicabilidad de IA promedio de 7 ocupaciones típicas del rubro (0-1, valor absoluto)",
            "horas": "jornada semanal habitual: 44 o 50; la fracción con 50 replica share_50_mas de esi_jornada",
            "calidad_sueldo": calidad,
            "calidad_despido": calidad,
            "calidad_ascenso": calidad,
            "calidad_ia": calidad,
            "calidad_horas": calidad,
        },
        "poblacion": f"{n_empresas} empresas reales elegidas a mano, unas 10 por rubro",
        "ponderador": "peso",
        "fuente_id": "sii_nomina_2024",
        "script": "scripts/empresas_catalogo.py",
        "advertencia": f"Los multiplicadores mueven a la empresa dentro de su tipo y rubro, no el promedio. σ de sueldo calibrado = {sigma}. Fuentes: nómina SII 2024, Y Combinator, Get on Board, empleospublicos.cl, ESI 2025, INE flujos laborales, Microsoft (IA).",
        "filas": n_empresas,
    }, {
        "tabla": "cargos_catalogo",
        "archivo": "tablas/cargos_catalogo.csv",
        "descripcion": "Cargos con nombre real que el juego ofrece en cada empresa, con su gran grupo CIUO, exposición a IA y prima de Get on Board.",
        "columnas": {
            "cargo_id": "índice estable (0..n-1)",
            "nombre": "nombre del cargo",
            "ciuo08_1d": "gran grupo CIUO-08 (1-9); el sueldo base sale de esi_ingreso_ocupacion",
            "ocupacion_ia": "ocupación equivalente en ia_aplicabilidad_ocupaciones.ocupacion_eeuu",
            "exposicion_ia": "aplicabilidad_ia de esa ocupación (0-1)",
            "area_getonbrd": "área de getonbrd_sueldos para cargos tech o digitales; vacío para el resto",
            "prima_getonbrd": "punto medio de las medianas min y max del área / el de todas las áreas (getonbrd_sueldos); 1 sin área",
            "nivel_min": "nivel mínimo (0 junior .. 4 gerencia)",
            "nivel_max": "nivel máximo (0..4)",
            "edu_min": "educación mínima: media, tecnica, universitaria o postgrado",
            "areas": "áreas de carrera compatibles separadas por | o * (cualquiera)",
            "rubros": "rubros donde existe el cargo separados por | o *",
            "tipos": "tipos de empleador separados por | o *",
            "peso": "share_ocupados_banda del gran grupo (esi_ingreso_ocupacion, 18-54) repartido entre los cargos del grupo",
            "calidad_ia": "'derivado' si la ocupación de EE.UU. calza directo, 'sintetico' si es la más cercana",
            "calidad_prima": "'dato' si viene de getonbrd_sueldos, 'derivado' si es 1 por no tener área",
        },
        "poblacion": f"{n_cargos} cargos de avisos de Get on Board, concursos del Estado y nombres comunes en Chile",
        "ponderador": "peso",
        "fuente_id": "microsoft_ia",
        "script": "scripts/empresas_catalogo.py",
        "advertencia": "Para cada empresa y cada (educación, nivel) hay al menos un cargo compatible si se ignora el área; el script lo verifica. La prima de Get on Board compara áreas de un portal tech, no el mercado completo.",
        "filas": n_cargos,
    }]


if __name__ == "__main__":
    empresas, sigma, _ = catalogo_empresas()
    escribir_empresas(empresas)
    cargos = catalogo_cargos(empresas)
    actualizar_parametros(sigma)
    registrar_indice(entradas_indice(len(empresas), len(cargos), sigma))
    por = defaultdict(int)
    for e in empresas:
        por[e["tipo"]] += 1
    print(f"empresas: {len(empresas)} {dict(por)}; con logo: {sum(e['logo'] for e in empresas)}; cargos: {len(cargos)}")
