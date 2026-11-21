"""Exporta a CSV las tablas agregadas que usa el motor, para revisarlas sin leer código.
Uso, desde backend/:  uv run python scripts/exportar_csv.py ../datos/tablas"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.sim.companies import GRANDES, PUBLICOS, PYMES, STARTUPS  # noqa: E402
from app.sim.params import PARAMS  # noqa: E402
from app.sim.tables import tablas  # noqa: E402

out = Path(sys.argv[1] if len(sys.argv) > 1 else "../datos/tablas")
out.mkdir(parents=True, exist_ok=True)
tb = tablas()
t = tb.raw


def escribir(nombre: str, cabecera: list[str], filas) -> None:
    with open(out / nombre, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cabecera)
        n = 0
        for f in filas:
            w.writerow(f)
            n += 1
    print(f"{nombre}: {n} filas")


escribir("parametros.csv", ["clave", "valor", "estado", "pais", "fuente"],
         ([k, json.dumps(p.valor, ensure_ascii=False), p.estado, p.pais, p.fuente] for k, p in PARAMS.items()))

jh = t["jobhop"]
escribir("ocupaciones.csv", ["isco3", "ocupacion", "empleos_jobhop", "p_cambia_de_grupo", "duracion_mediana_anios",
                             "exposicion_ia_percentil", "sueldo_relativo_gran_grupo"],
         ([c, tb.nombres[i], jh["n_empleos"][c], jh["p_cambia_de_grupo"].get(c, ""), jh["duracion_mediana_anios"].get(c, ""),
           t["exposicion_ia"]["percentil"][c], "" if tb.rel[i] != tb.rel[i] else round(float(tb.rel[i]), 3)]
          for i, c in enumerate(tb.codigos)))

escribir("transiciones_ocupacion.csv", ["isco3_origen", "isco3_destino", "probabilidad"],
         ([a, b, p] for a, fila in jh["transiciones"].items() for b, p in fila.items()))

escribir("sueldo_edad_educacion.csv", ["educacion", "tramo_edad", "p10", "p25", "p50", "p75", "p90", "n"],
         ([edu, tr, v["p10"], v["p25"], v["p50"], v["p75"], v["p90"], v["n"]]
          for edu, d in t["esi_edad_educacion"].items() for tr, v in sorted(d.items())))

escribir("universidades_magister.csv", ["codigo_sies", "universidad", "sigla", "selectiva", "magisteres", "arancel_anual_mediano", "anios", "frac_no_diurna"],
         ([u["codigo"], u["nombre"], u["sigla"], u["selectiva"], u["n"], u["arancel"], u["anios"], u["frac_no_diurna"]] for u in tb.universidades))


def tabla_plana(prefijo, obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from tabla_plana(f"{prefijo}.{k}" if prefijo else k, v)
    else:
        yield prefijo, json.dumps(obj, ensure_ascii=False) if isinstance(obj, list) else obj


escribir("tablas_ine_y_paneles.csv", ["tabla", "valor"],
         ([k, v] for fuente in ("ine", "paneles", "epf_quintiles") for k, v in tabla_plana(fuente, t[fuente])))

escribir("empresas.csv", ["tipo", "rubro", "nombre"],
         [["startup", "", n] for n in STARTUPS] + [["estado", "", n] for n in PUBLICOS]
         + [["grande", r, n] for r, ns in GRANDES.items() for n in ns] + [["pyme", r, n] for r, ns in PYMES.items() for n in ns])
