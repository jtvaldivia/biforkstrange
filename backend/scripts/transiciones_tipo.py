"""Tabla simulador/tablas/transiciones_tipo.csv: P(tipo de empleador nuevo | tipo del empleo anterior).

Entrada: EPS 2009 (Subsecretaría de Previsión Social), archivo hlaboral.dta, historia laboral de
enero de 2006 a la entrevista de 2009, con factor_EPS09. Es la ronda más reciente que pregunta el
tamaño de la empresa en cada episodio (b15 número de personas, b15t tramo); las rondas 2015, 2020 y
2024 ya no lo preguntan. Si la carpeta extraída no existe, se crea vacía y se descomprime ahí el .rar.

Reglas (decisiones de método, no parámetros del juego):
- Empleo asalariado = episodio "trabajando" (b2=1) como empleado público o FF.AA. (b8=3,8: publico)
  o empleado privado (b8=4). Privado con 200 o más personas = grande; con menos = pyme (el juego no
  tiene microempresa, así que <10 cae en pyme). Servicio doméstico, cuenta propia, patrón y familiar
  no remunerado no son destino; como origen cuentan como "ninguno" (no venía de un empleo asalariado).
- Transición = episodio asalariado que empieza después del primer mes de la ventana. Su origen es el
  último empleo que empezó antes. Si ese empleo terminó a lo más UMBRAL_MESES antes (pasando o no por
  cesantía), el origen es su tipo; si terminó antes o no hay empleo previo pero sí un episodio de no
  empleo registrado, el origen es "ninguno". Privado sin tamaño conocido en origen o destino: se descarta.
- Startup no se distingue en la EPS ni en una fuente con origen y destino cruzados (el J2JOD de LEHD
  publica la edad de la empresa de origen y la de destino solo por separado). Por eso P(destino
  startup) es la proporción incondicional del juego para todo origen, y la fila startup copia la de
  pyme: ambas son supuestos y la tabla lo dice.
- Ajuste: la matriz se escala por IPF (raking) a la mezcla incondicional del juego (MIX_EMPLEADOR y
  P_REEMPLEO_PUBLICO de parametros.json), ponderando las filas asalariadas por esa misma mezcla. El IPF
  conserva las razones de odds de la EPS. La fila "ninguno" recibe los mismos factores por columna y la
  fila "extranjero" copia "ninguno".

Uso: uv run --with pyreadstat --with pandas python -I backend/scripts/transiciones_tipo.py <datos_laborales>
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pyreadstat

BACKEND = Path(__file__).resolve().parents[1]
TABLAS = BACKEND / "simulador" / "tablas"
PARAMETROS = BACKEND / "simulador" / "parametros.json"
SALIDA = TABLAS / "transiciones_tipo.csv"

UMBRAL_MESES = 12      # hueco máximo entre fin de un empleo e inicio del siguiente para contarlo como transición
GRANDE_MIN = 200       # personas en la empresa desde las que es "grande" (corte del INE)
TRAMO_GRANDE = {8, 9}  # b15t: 200-499 y 500 o más
TRAMO_PYME = {1, 2, 3, 4, 5, 6, 7}
NO_SABE = 88888        # b15 >= esto: no responde / no sabe
ASAL = ["grande", "pyme", "publico"]
DESTINOS = ["grande", "pyme", "startup", "publico"]
ORIGENES = ["grande", "pyme", "startup", "publico", "extranjero", "ninguno"]


def leer_eps(datos: Path) -> pd.DataFrame:
    carpeta = datos / "eps" / "extraido_2009"
    archivo = carpeta / "2009" / "2009" / "hlaboral.dta"
    if not archivo.exists():
        carpeta.mkdir(parents=True, exist_ok=False)
        subprocess.run(["bsdtar", "-xf", str(datos / "eps" / "base-datos-eps-2009.rar")], cwd=carpeta, check=True)
    cols = ["folio_n20", "orden", "b1ia", "b1im", "b1ta", "b1tm", "b2", "b8", "b15", "b15t"]
    h = pyreadstat.read_dta(str(archivo), apply_value_formats=False, usecols=cols)[0]
    f = pyreadstat.read_dta(str(archivo.parent / "factor_EPS09.dta"), apply_value_formats=False,
                            usecols=["folio_n20", "factor_EPS09"])[0]
    h = h.merge(f, on="folio_n20", how="left")
    for c in cols[1:]:
        h[c] = pd.to_numeric(h[c], errors="coerce")

    def mes(a, m):
        return a.where(a.between(1990, 2010)) * 12 + m.where(m.between(1, 12), 6) - 1

    h["s"], h["e"] = mes(h.b1ia, h.b1im), mes(h.b1ta, h.b1tm)
    h = h[h.s.notna() & h.factor_EPS09.notna()].copy()
    h["e"] = h.e.fillna(h.s)
    tam = h.b15.where((h.b15 > 0) & (h.b15 < NO_SABE))
    priv = pd.Series(pd.NA, index=h.index, dtype="object")
    priv[tam >= GRANDE_MIN] = "grande"
    priv[tam < GRANDE_MIN] = "pyme"
    priv[tam.isna() & h.b15t.isin(TRAMO_GRANDE)] = "grande"
    priv[tam.isna() & h.b15t.isin(TRAMO_PYME)] = "pyme"
    trab = h.b2 == 1
    h["tipo"] = "no_empleo"
    h.loc[trab, "tipo"] = "otro_empleo"
    h.loc[trab & h.b8.isin([3, 8]), "tipo"] = "publico"
    h.loc[trab & (h.b8 == 4), "tipo"] = priv[trab & (h.b8 == 4)].fillna("priv_sin_tamano")
    return h.sort_values(["folio_n20", "s", "orden"], kind="mergesort").reset_index(drop=True)


def transiciones(h: pd.DataFrame) -> pd.DataFrame:
    inicio = int(h.s.min())
    filas = []
    for _, g in h.groupby("folio_n20", sort=True):
        previos = []
        for ep in g.itertuples(index=False):
            if ep.tipo in ASAL and ep.s > inicio:
                emp = [p for p in previos if p.tipo != "no_empleo" and p.s < ep.s]
                if emp and ep.s - emp[-1].e <= UMBRAL_MESES:
                    t = emp[-1].tipo
                    origen = None if t == "priv_sin_tamano" else ("ninguno" if t == "otro_empleo" else t)
                elif emp or any(p.tipo == "no_empleo" for p in previos):
                    origen = "ninguno"
                else:
                    origen = None
                if origen:
                    filas.append((origen, ep.tipo, ep.factor_EPS09))
            previos.append(ep)
    return pd.DataFrame(filas, columns=["origen", "destino", "w"])


def ipf(p0: dict, filas: dict, cols: dict, iter_max: int = 1000) -> tuple[dict, dict]:
    """Escala N[o][d] = filas[o]*p0[o][d] a márgenes filas/cols. Devuelve P(d|o) y factores por columna."""
    n = {o: {d: filas[o] * p0[o][d] for d in cols} for o in filas}
    b = {d: 1.0 for d in cols}
    for _ in range(iter_max):
        for d in cols:
            k = cols[d] / sum(n[o][d] for o in filas)
            b[d] *= k
            for o in filas:
                n[o][d] *= k
        for o in filas:
            k = filas[o] / sum(n[o].values())
            for d in cols:
                n[o][d] *= k
        if max(abs(sum(n[o][d] for o in filas) - cols[d]) for d in cols) < 1e-12:
            break
    return {o: {d: n[o][d] / filas[o] for d in cols} for o in filas}, b


def main() -> None:
    datos = Path(sys.argv[1] if len(sys.argv) > 1 else "../../datos_laborales").resolve()
    par = {p["id"]: p["valor"] for p in json.loads(PARAMETROS.read_text(encoding="utf-8"))["parametros"]}
    pub = par["P_REEMPLEO_PUBLICO"]
    meta = {"publico": pub, **{t: (1 - pub) * par["MIX_EMPLEADOR"][t] for t in ("grande", "pyme", "startup")}}

    t = transiciones(leer_eps(datos))
    w = t.pivot_table(index="origen", columns="destino", values="w", aggfunc="sum", fill_value=0)
    n = t.pivot_table(index="origen", columns="destino", values="w", aggfunc="count", fill_value=0)
    eps = {o: {d: float(w.loc[o, d] / w.loc[o].sum()) for d in ASAL} for o in ASAL + ["ninguno"]}

    # matriz de partida con startup: P(startup|o) = meta startup para todo o; fila startup = fila pyme
    s0 = meta["startup"]
    p0 = {o: {**{d: eps[o][d] * (1 - s0) for d in ASAL}, "startup": s0} for o in ASAL + ["ninguno"]}
    p0["startup"] = dict(p0["pyme"])
    filas = {o: meta[o] for o in ("grande", "pyme", "startup", "publico")}
    antes = {d: sum(filas[o] * p0[o][d] for o in filas) for d in DESTINOS}
    p, b = ipf(p0, filas, {d: meta[d] for d in DESTINOS})
    z = sum(b[d] * p0["ninguno"][d] for d in DESTINOS)
    p["ninguno"] = {d: b[d] * p0["ninguno"][d] / z for d in DESTINOS}
    p["extranjero"] = dict(p["ninguno"])
    despues = {d: sum(filas[o] * p[o][d] for o in filas) for d in DESTINOS}

    def fila(o, d):
        if o == "extranjero":
            return "", "supuesto", "copia de la fila ninguno (sin dato de quien llega del extranjero)"
        if o == "startup" or d == "startup":
            src = "fila pyme de eps_2009" if d != "startup" else "MIX_EMPLEADOR (ine_esi_2025)"
            return "", "supuesto", f"{src}; startup no se observa con origen y destino (EPS, J2JOD)"
        return (int(n.loc[o, d]) if d in n.columns else 0), "derivado", \
            "eps_2009 historia laboral 2006-2009, ponderada; raking a la mezcla ine_esi_2025"

    with open(SALIDA, "w", encoding="utf-8", newline="") as fh:
        wr = csv.writer(fh, lineterminator="\n")
        wr.writerow(["origen", "destino", "prob", "n", "calidad", "fuente"])
        for o in ORIGENES:
            probs = [round(p[o][d], 4) for d in DESTINOS]
            probs[DESTINOS.index("pyme")] = round(1 - sum(probs) + probs[DESTINOS.index("pyme")], 4)
            for d, pr in zip(DESTINOS, probs):
                wr.writerow([o, d, f"{pr:.4f}", *fila(o, d)])

    print(f"EPS 2009: {len(t)} transiciones (umbral {UMBRAL_MESES} meses)")
    print("conteos sin ponderar:\n" + n.to_string())
    print("P_eps(d|o) ponderada:")
    for o in eps:
        print(f"  {o:8s} " + "  ".join(f"{d}={eps[o][d]:.3f}" for d in ASAL))
    print(f"{'destino':8s} {'actual':>7s} {'antes':>7s} {'despues':>7s}")
    for d in DESTINOS:
        print(f"{d:8s} {meta[d]:7.4f} {antes[d]:7.4f} {despues[d]:7.4f}")
    registrar_indice(len(ORIGENES) * len(DESTINOS), len(t))


def registrar_indice(n_filas: int, n_trans: int) -> None:
    nueva = {
        "tabla": "transiciones_tipo",
        "archivo": "tablas/transiciones_tipo.csv",
        "descripcion": "Probabilidad del tipo de empleador nuevo según el tipo del empleo anterior, al cambiarse de trabajo.",
        "columnas": {
            "origen": "tipo del empleo anterior: grande, pyme, startup, publico, extranjero o ninguno (no venía de un empleo asalariado en los últimos 12 meses)",
            "destino": "tipo del empleo nuevo: grande (privado, 200 o más personas), pyme (privado, menos de 200), startup o publico (incluye FF.AA. y de Orden)",
            "prob": "P(destino | origen); suma 1 por origen",
            "n": "transiciones EPS sin ponderar que respaldan la celda (vacío si la celda es supuesto)",
            "calidad": "derivado (EPS ponderada y ajustada por raking) o supuesto",
            "fuente": "de dónde sale la celda",
        },
        "poblacion": f"Asalariados chilenos que empezaron un empleo entre 2006 y 2009 según la EPS 2009 ({n_trans} transiciones)",
        "ponderador": "factor_EPS09; luego IPF a la mezcla MIX_EMPLEADOR y P_REEMPLEO_PUBLICO de parametros.json",
        "fuente_id": "eps_2009",
        "script": "scripts/transiciones_tipo.py",
        "advertencia": "Datos de 2006-2009: la EPS dejó de preguntar el tamaño de la empresa desde 2015. Startup no se mide: su columna es la proporción incondicional y su fila copia pyme. Extranjero copia ninguno. Privado sin tamaño se descarta.",
        "filas": n_filas,
    }
    ruta = TABLAS / "indice.json"
    d = json.loads(ruta.read_text(encoding="utf-8"))
    cab = next(csv.reader(open(SALIDA, encoding="utf-8")))
    assert list(nueva["columnas"]) == cab, cab
    i = next((k for k, x in enumerate(d["tablas"]) if x["tabla"] == nueva["tabla"]), None)
    if i is None:
        d["tablas"].append(nueva)
    else:
        d["tablas"][i] = nueva
    d["tablas"].sort(key=lambda x: x["tabla"])
    ruta.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
