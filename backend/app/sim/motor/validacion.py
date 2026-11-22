"""Validación del motor contra Chile: una cohorte simulada frente a las metas del paquete y a ELSOC.

Simula `n` personas desde los 18 años (mitad hombres, mitad mujeres) que deciden
como la población (`politicas.Poblacion`) hasta los 50, solo lo laboral, y mide:

- las 37 metas laborales de `simulador/objetivos_validacion.json` (la del grupo
  "Vida", el cáncer, queda fuera: el juego no lo sortea);
- la matriz anual ocupado / desocupado / inactivo de ELSOC, que el motor no usa
  como insumo.

Convenciones de medición (el paquete dice "años con estado X"):

- Un año-persona es un año vivido. Su edad es la que la persona tenía al empezarlo
  y su estado, sueldo y empleador son los del cierre de ese año.
- "Ocupado" es empleado, independiente o fundador. "Buscando" es desocupado.
- `tipo_empleador` solo se lee en años cerrados como empleado: el motor no lo borra
  cuando alguien se independiza y quedaría contando un empleador que ya no tiene.
- Los eventos por año empleado (separación, cambio) se dividen por los años en que
  la persona estaba empleada cuando se sortean los eventos (ese año recibió el
  evento `alza_anual`, que les llega a todos los empleados y a nadie más).

Cada meta lleva `calidad`: "validacion" (el motor no usa ese número), "parcial"
(usa la misma encuesta como insumo de otra cosa), "calibrada" (los pesos de
`politicas.py` se ajustaron contra ella) o "insumo" (el motor lee ese mismo número:
reproducirlo no valida nada).

Uso: `python -m app.sim.motor.validacion [n] [semilla]`, o `--precalcular` para dejar guardada
la que sirve el endpoint (n=1000, semilla 0).
"""

from __future__ import annotations

import csv
import os
import sys
import time
from collections import Counter
from pathlib import Path

from app.sim.motor.azar import Dados
from app.sim.motor.motor import Vida
from app.sim.motor.paquete import paquete
from app.sim.motor.perfil import Perfil, estado_inicial
from app.sim.motor.politicas import Poblacion

N_COHORTE = 5000
EDAD_FIN = 50
GRUPOS_FUERA = frozenset({"Vida"})  # el juego es solo laboral
OCUPADO = frozenset({"empleado", "independiente", "fundador"})
ELSOC_CSV = Path(__file__).resolve().parents[1] / "data" / "elsoc_transiciones_actividad.csv"

# Resultados de decisiones que cambian de empleador sin pasar por cesantía
# (la definición de la EPS: "pasar a otro empleador sin cesantía entremedio").
CAMBIOS_DIRECTOS = frozenset({
    ("oferta_externa", "mejora"), ("oferta_externa", "igual_o_peor"), ("oferta_externa", "te_vas"),
    ("unirse_a_startup", "crece"), ("unirse_a_startup", "cierra"), ("unirse_a_startup", "sigue"),
    ("cambiar_de_rubro", "entra"), ("remoto_para_afuera", "queda"), ("emigrar", "consigue"),
})

# Qué tan independiente del motor es cada meta: (prefijo del id, calidad, por qué)
CALIDAD_META = (
    ("separacion_", "insumo", "Es el parámetro P_SEPARACION (EPS 2024), el mismo número."),
    ("cambio_", "insumo", "Sale de P_CAMBIO_EMPLEADOR (EPS 2024) y el peso de aceptar la oferta se calibró contra ella."),
    ("sigue_cesante_12m", "insumo", "MESES_CESANTIA se construyó para reproducir esta sobrevida a 12 meses (EPS 2024)."),
    ("empresa_grande", "insumo", "Es MIX_EMPLEADOR['grande'] = 0,40 (ESI 2025), el mismo número."),
    ("startup_anos", "insumo", "Meta puesta por el equipo, no medida; MIX_EMPLEADOR['startup'] = 0,01 es insumo."),
    ("publico_", "calibrada", "El peso de postular al Estado en la primera pega se calibró contra ella; P_REEMPLEO_PUBLICO = 0,12 es insumo."),
    ("independientes_", "calibrada", "Los pesos de trabajar por cuenta propia y su tasa de salida se calibraron contra ella."),
    ("edu_", "calibrada", "Los pesos de qué hacer al salir del colegio se calibraron contra ella."),
    ("ingreso_", "parcial", "El primer sueldo y su alza anual salen del perfil ESI por edad y educación; la mezcla de gente y de empleos no."),
    ("desocupacion_", "validacion", "El motor no usa la tasa de desocupación de la ESI: sale de las entradas y salidas de la EPS."),
)

# ELSOC: tolerancia en puntos. Las filas D tienen 135 a 190 casos, por eso la suya es más ancha.
TOL_ELSOC = {"O": 0.03, "D": 0.08}


# --------------------------------------------------------------------------- simulación
def _vida(g: int, semilla: int, pq) -> Vida:
    perfil = Perfil.a_los_18(sexo="h" if g % 2 == 0 else "m")
    vida = Vida(estado_inicial(perfil, pq), Dados(semilla, g), pq, alcance="laboral")
    decisor = Poblacion()
    while vida.e["edad"] < EDAD_FIN:
        vida.vivir_anio(decisor)
    return vida


def _filas(vida: Vida, estado0: str) -> list[tuple]:
    """Una fila por año vivido: lo mínimo para medir, para no mover la historia entera entre procesos."""
    filas, previo = [], estado0
    for r in vida.historia:
        fin = r["fin"]
        eventos = {ev["evento"]: ev["resultado"] for ev in r["eventos"]}
        decisiones = [(d["decision"], d["opcion"], d["resultado"]) for d in r["decisiones"]]
        filas.append((
            r["edad"], previo, fin["estado"], fin["sueldo"], fin["tipo_empleador"], fin["edu"],
            # en riesgo de despido: tenía trabajo cuando corrieron los eventos del año (lo anota el motor al llegar al
            # despido, que va primero). Antes se leía de si le tocó el alza, pero quien entró a su pega este año no tiene
            fin.get("primer_empleo", 0), fin["edad"] - r["edad"], r.get("empleado_en_eventos", False),
            eventos.get("separacion_empleo"),
            any((d, res) in CAMBIOS_DIRECTOS for d, _, res in decisiones),
            decisiones, tuple(eventos),
        ))
        previo = fin["estado"]
    return filas


def _lote(args: tuple[int, int, int]) -> tuple[list[list[tuple]], list[dict]]:
    desde, hasta, semilla = args
    pq = paquete()
    vidas, fallas = [], []
    for g in range(desde, hasta):
        vida = None
        try:
            perfil = Perfil.a_los_18(sexo="h" if g % 2 == 0 else "m")
            vida = Vida(estado_inicial(perfil, pq), Dados(semilla, g), pq, alcance="laboral")
            decisor = Poblacion()
            while vida.e["edad"] < EDAD_FIN:
                vida.vivir_anio(decisor)
            vidas.append(_filas(vida, "estudiando"))
        except Exception as exc:  # noqa: BLE001 (una vida que revienta es un hallazgo, no un error del validador)
            e = vida.e if vida is not None else {}
            fallas.append({
                "gemelo": g, "semilla": semilla, "error": f"{type(exc).__name__}: {exc}",
                "anio_en_curso": (vida.registro or {}) if vida is not None else {},
                "estado": {k: e.get(k) for k in ("edad", "sexo", "estado", "edu", "carrera_id", "tipo_institucion",
                                                 "tipo_empleador", "rubro", "nivel", "sueldo", "sueldo_ref",
                                                 "ocupacion", "primer_empleo", "pais", "semestres_restantes")},
            })
    return vidas, fallas


def simular(n: int = N_COHORTE, semilla: int = 0, procesos: int | None = None) -> tuple[list[list[tuple]], list[dict]]:
    """Simula la cohorte. Devuelve (una lista de años por persona, vidas que fallaron)."""
    if procesos is None:
        procesos = min(os.cpu_count() or 1, 8) if n >= 1000 else 1
    if procesos <= 1:
        return _lote((0, n, semilla))
    import multiprocessing as mp

    paso = max(50, -(-n // (procesos * 4)))
    lotes = [(i, min(n, i + paso), semilla) for i in range(0, n, paso)]
    vidas, fallas = [], []
    # fork donde existe (macOS, Linux): los procesos heredan el paquete ya cargado y funciona
    # también desde un intérprete interactivo; spawn solo como respaldo (Windows).
    contexto = mp.get_context("fork" if "fork" in mp.get_all_start_methods() else "spawn")
    paquete()
    with contexto.Pool(procesos) as pool:
        for v, f in pool.imap(_lote, lotes):
            vidas += v
            fallas += f
    return vidas, fallas


# --------------------------------------------------------------------------- medición
def _cuantil(valores: list[float], q: float) -> float | None:
    if not valores:
        return None
    v = sorted(valores)
    pos = q * (len(v) - 1)
    i = int(pos)
    return v[i] + (v[min(i + 1, len(v) - 1)] - v[i]) * (pos - i)


def _razon(a: int, b: int) -> float | None:
    return a / b if b else None


def _tramo(texto: str) -> tuple[int, int]:
    a, b = texto.replace("_", "-").split("-")[-2:]
    return int(a), int(b)


class Cohorte:
    """Los años-persona de la cohorte, con las mediciones que piden las metas."""

    # columnas de cada fila (ver _filas)
    EDAD, PREVIO, ESTADO, SUELDO, TIPO, EDU, PRIMER, SALTO, EN_RIESGO, SEPARACION, CAMBIO, DECISIONES, EVENTOS = range(13)

    def __init__(self, vidas: list[list[tuple]]):
        self.vidas = vidas
        self.anios = [f for v in vidas for f in v]

    def entre(self, lo: int, hi: int) -> list[tuple]:
        return [f for f in self.anios if lo <= f[self.EDAD] <= hi]

    def sueldo(self, lo: int, hi: int, q: float) -> float | None:
        return _cuantil([f[self.SUELDO] for f in self.entre(lo, hi) if f[self.ESTADO] in OCUPADO], q)

    def desocupacion(self, lo: int, hi: int) -> float | None:
        filas = self.entre(lo, hi)
        buscando = sum(1 for f in filas if f[self.ESTADO] == "buscando")
        return _razon(buscando, buscando + sum(1 for f in filas if f[self.ESTADO] in OCUPADO))

    def publico(self, lo: int, hi: int) -> float | None:
        filas = [f for f in self.entre(lo, hi) if f[self.ESTADO] in OCUPADO]
        return _razon(sum(1 for f in filas if f[self.ESTADO] == "empleado" and f[self.TIPO] == "publico"), len(filas))

    def independientes(self, lo: int, hi: int) -> float | None:
        filas = [f for f in self.entre(lo, hi) if f[self.ESTADO] in OCUPADO]
        return _razon(sum(1 for f in filas if f[self.ESTADO] != "empleado"), len(filas))

    def empleador(self, tipo: str, entre: tuple[str, ...]) -> float | None:
        filas = [f for f in self.anios if f[self.ESTADO] == "empleado" and f[self.TIPO] in entre]
        return _razon(sum(1 for f in filas if f[self.TIPO] == tipo), len(filas))

    def startup(self) -> float | None:
        filas = [f for f in self.anios if f[self.ESTADO] == "empleado"]
        return _razon(sum(1 for f in filas if f[self.TIPO] == "startup"), len(filas))

    def edu(self, nivel: str, lo: int, hi: int) -> float | None:
        filas = self.entre(lo, hi)
        return _razon(sum(1 for f in filas if f[self.EDU] == nivel), len(filas))

    def separacion(self, lo: int, hi: int) -> float | None:
        filas = [f for f in self.entre(lo, hi) if f[self.EN_RIESGO]]
        return _razon(sum(1 for f in filas if f[self.SEPARACION]), len(filas))

    def cambio(self, lo: int, hi: int) -> float | None:
        filas = [f for f in self.entre(lo, hi) if f[self.EN_RIESGO]]
        return _razon(sum(1 for f in filas if f[self.CAMBIO]), len(filas))

    def sigue_cesante(self) -> tuple[float | None, int]:
        """Episodios de cesantía (cerró un año buscando, viniendo de un año ocupado) que siguen al cierre siguiente."""
        episodios = siguen = 0
        for v in self.vidas:
            for a, b in zip(v, v[1:]):
                if a[self.PREVIO] in OCUPADO and a[self.ESTADO] == "buscando" and not a[self.PRIMER]:
                    episodios += 1
                    siguen += b[self.ESTADO] == "buscando"
        return _razon(siguen, episodios), episodios

    def decisiones(self) -> Counter:
        return Counter((d, o) for f in self.anios for d, o, _ in f[self.DECISIONES])


def _medir(obj: dict, c: Cohorte) -> tuple[float | None, str]:
    """Valor simulado de una meta y, si no se puede medir tal como está escrita, el motivo."""
    id_ = obj["id"]
    if id_.startswith("ingreso_"):
        q = {"p25": 0.25, "p50": 0.5, "p75": 0.75}[id_.split("_")[1]]
        return c.sueldo(*_tramo(id_), q), ""
    if id_.startswith("desocupacion_"):
        return c.desocupacion(*_tramo(id_)), ""
    if id_.startswith("publico_"):
        return c.publico(*_tramo(id_)), ""
    if id_.startswith("independientes_"):
        return c.independientes(*_tramo(id_)), ""
    if id_ == "empresa_grande":
        return c.empleador("grande", ("grande", "pyme", "startup")), ""
    if id_ == "startup_anos":
        return c.startup(), ""
    if id_.startswith("edu_"):
        return c.edu(id_.split("_")[1], *_tramo(id_)), ""
    if id_.startswith(("separacion_", "cambio_")):
        lo, hi = _tramo(id_)
        nota = f"La cohorte llega a los {EDAD_FIN}: se mide con {lo}-{EDAD_FIN - 1}." if hi >= EDAD_FIN else ""
        medir = c.separacion if id_.startswith("separacion_") else c.cambio
        return medir(lo, hi), nota
    if id_ == "sigue_cesante_12m":
        valor, episodios = c.sigue_cesante()
        return valor, (f"{episodios} episodios. En pasos anuales 'un año después' es el cierre del año siguiente: "
                       "entre 12 y 24 meses desde que quedó cesante, no 12 justos.")
    return None, f"No hay medición para esta meta: {obj['medir']}"


def _calidad(id_: str) -> tuple[str, str]:
    for prefijo, calidad, motivo in CALIDAD_META:
        if id_.startswith(prefijo):
            return calidad, motivo
    return "validacion", ""


def medir_metas(c: Cohorte, objetivos: list[dict]) -> list[dict]:
    salida = []
    for obj in objetivos:
        if obj["grupo"] in GRUPOS_FUERA:
            continue
        simulado, nota = _medir(obj, c)
        relativa = "tolerancia_relativa" in obj
        tolerancia = obj["tolerancia_relativa"] if relativa else obj["tolerancia"]
        error = cumple = None
        if simulado is not None:
            error = simulado / obj["valor"] - 1 if relativa else simulado - obj["valor"]
            cumple = abs(error) <= tolerancia
        calidad, motivo = _calidad(obj["id"])
        salida.append({
            "id": obj["id"], "grupo": obj["grupo"], "indicador": obj["indicador"], "fuente": obj["fuente"],
            "meta": obj["valor"], "simulado": simulado, "tolerancia": tolerancia, "tolerancia_relativa": relativa,
            "error": error, "cumple": cumple, "medible": simulado is not None,
            "calidad": calidad, "es_insumo": calidad == "insumo", "motivo_calidad": motivo, "nota": nota,
        })
    return salida


# --------------------------------------------------------------------------- ELSOC
def _odi(estado: str) -> str:
    return "O" if estado in OCUPADO else "D" if estado == "buscando" else "I"


def medir_elsoc(c: Cohorte) -> list[dict]:
    """Transiciones anuales del motor frente a ELSOC.

    ELSOC mide dónde está la persona en una ola y dónde un año después. En el motor: estado al
    cierre de un año y al cierre del siguiente. El motor solo modela la cesantía: nadie sale a la
    inactividad (cuidados, salud, desaliento) ni deja de buscar. Por eso:

    - ocupado -> cesante se compara contra O -> D de ELSOC: es lo que el motor modela;
    - ocupado -> no ocupado contra O -> D + I se muestra pero no cuenta: la diferencia es la
      inactividad que el juego dejó fuera;
    - cesante -> ocupado se compara contra un rango: D -> O de ELSOC tal cual (piso: parte de los
      cesantes de ELSOC se va a la inactividad, cosa que en el motor no pasa) y D -> O entre quienes
      siguen activos, D->O / (D->O + D->D) (techo). Cuadra si queda a no más de la tolerancia del rango;
    - la fila I no se compara: los inactivos del motor son estudiantes, los de ELSOC no.
    """
    with open(ELSOC_CSV, encoding="utf-8") as f:
        ref = {(r["banda"], r["origen"], r["destino"]): (float(r["prob"]), int(r["n"])) for r in csv.DictReader(f)}
    bandas = {"18-29": (18, 29), "30-44": (30, 44), "45-59": (45, 59)}
    cuenta: Counter = Counter()
    for f in c.anios:
        if f[c.SALTO] != 1:
            continue  # un doctorado salta cuatro años de una vez: no es una transición anual
        banda = next(b for b, (lo, hi) in bandas.items() if lo <= f[c.EDAD] <= hi)
        cuenta[banda, _odi(f[c.PREVIO]), _odi(f[c.ESTADO])] += 1
    salida: list[dict] = []

    def fila(banda: str, nombre: str, origen: str, destinos: str, lo: float, hi: float, n_ref: int,
             comparable: bool, nota: str) -> None:
        total = sum(cuenta[banda, origen, d] for d in "ODI")
        simulado = _razon(sum(cuenta[banda, origen, d] for d in destinos), total)
        error = None if simulado is None else simulado - lo if simulado < lo else max(0.0, simulado - hi)
        cumple = None if (error is None or not comparable) else abs(error) <= TOL_ELSOC[origen]
        if banda == "45-59":
            nota += f" La cohorte llega a los {EDAD_FIN}: se mide con 45-{EDAD_FIN - 1}."
        salida.append({"id": f"elsoc_{nombre}_{banda}", "banda": banda, "indicador": nombre,
                       "meta": lo if lo == hi else (lo, hi), "simulado": simulado, "tolerancia": TOL_ELSOC[origen],
                       "error": error, "cumple": cumple, "comparable": comparable,
                       "n_simulado": total, "n_elsoc": n_ref, "nota": nota.strip()})

    for banda in bandas:
        od, oi, do, dd = (ref[banda, a, b] for a, b in (("O", "D"), ("O", "I"), ("D", "O"), ("D", "D")))
        n_o = sum(ref[banda, "O", d][1] for d in "ODI")
        fila(banda, "ocupado_a_cesante", "O", "D", od[0], od[0], n_o, True, "")
        fila(banda, "ocupado_a_no_ocupado", "O", "DI", od[0] + oi[0], od[0] + oi[0], n_o, False,
             "No cuenta: el motor no modela la salida a la inactividad.")
        fila(banda, "cesante_a_ocupado", "D", "O", do[0], do[0] / (do[0] + dd[0]),
             sum(ref[banda, "D", d][1] for d in "ODI"), True,
             "Rango ELSOC: todos los cesantes (piso) a solo quienes siguen activos (techo).")
    return salida


# --------------------------------------------------------------------------- resumen
def validar(n: int = N_COHORTE, semilla: int = 0, procesos: int | None = None) -> dict:
    """Simula la cohorte y la compara con las 37 metas laborales del paquete y con ELSOC."""
    t0 = time.perf_counter()
    vidas, fallas = simular(n, semilla, procesos)
    t1 = time.perf_counter()
    cohorte = Cohorte(vidas)
    metas = medir_metas(cohorte, paquete().objetivos)
    elsoc = medir_elsoc(cohorte)
    de_verdad = [m for m in metas if m["calidad"] in ("validacion", "parcial")]
    comparables = [x for x in elsoc if x["comparable"]]
    return {
        "n": n, "semilla": semilla, "personas": len(vidas), "anios_persona": len(cohorte.anios),
        "cumplen": sum(1 for m in metas if m["cumple"]), "total": len(metas),
        "no_medibles": [m["id"] for m in metas if not m["medible"]],
        "cumplen_sin_insumos": sum(1 for m in de_verdad if m["cumple"]), "total_sin_insumos": len(de_verdad),
        "por_calidad": {c: {"cumplen": sum(1 for m in metas if m["calidad"] == c and m["cumple"]),
                            "total": sum(1 for m in metas if m["calidad"] == c)}
                        for c in ("validacion", "parcial", "calibrada", "insumo")},
        "metas": metas,
        "elsoc": elsoc, "elsoc_cumplen": sum(1 for x in comparables if x["cumple"]), "elsoc_total": len(comparables),
        "fallas": fallas, "vidas_con_error": len(fallas),
        "decisiones": {f"{d}:{o}": k for (d, o), k in sorted(cohorte.decisiones().items())},
        "segundos_simular": round(t1 - t0, 1), "segundos_medir": round(time.perf_counter() - t1, 1),
    }


# La validación que sirve el endpoint, calculada al construir el deploy (`render.yaml` corre
# `python -m app.sim.motor.validacion --precalcular`). En el servidor de 0,1 CPU simularla en la
# primera llamada tardaba más de un minuto. La huella dice con qué motor y paquete se calculó:
# si cambiaron, el archivo no se usa y el endpoint vuelve a simular.
PRECALCULADA = Path(__file__).resolve().parent / "validacion_precalculada.json"
N_PRECALCULADA = 1000


def huella() -> str:
    """Hash del paquete de reglas y del código del motor: lo que cambia el resultado de la validación."""
    import hashlib

    backend = Path(__file__).resolve().parents[3]
    archivos = sorted(
        [*(backend / "simulador").rglob("*.json"), *(backend / "simulador").rglob("*.csv"),
         *(backend / "simulador").rglob("*.py"), *Path(__file__).resolve().parent.glob("*.py")]
    )
    h = hashlib.sha256()
    for a in archivos:
        h.update(str(a.relative_to(backend)).encode())
        h.update(a.read_bytes())
    return h.hexdigest()[:16]


def para_api(resultado: dict) -> dict:
    """Lo que devuelve el endpoint: sin la lista de fallas ni el conteo de decisiones."""
    return {k: v for k, v in resultado.items() if k not in ("fallas", "decisiones")}


def precalcular(n: int = N_PRECALCULADA, semilla: int = 0) -> Path:
    import json

    datos = {"huella": huella(), "resultado": para_api(validar(n, semilla))}
    PRECALCULADA.write_text(json.dumps(datos, ensure_ascii=False))
    return PRECALCULADA


def precalculada(n: int, semilla: int) -> dict | None:
    """La validación guardada en el deploy, si es de este n, esta semilla y este mismo motor."""
    import json

    if not PRECALCULADA.exists():
        return None
    try:
        datos = json.loads(PRECALCULADA.read_text())
    except (OSError, ValueError):
        return None
    r = datos.get("resultado", {})
    if r.get("n") != n or r.get("semilla") != semilla or datos.get("huella") != huella():
        return None
    return r


def _fmt(v: float | None, plata: bool) -> str:
    if v is None:
        return "s/d"
    return f"{v:,.0f}".replace(",", ".") if plata else f"{100 * v:.1f}%"


def tabla(r: dict) -> str:
    lineas = [f"Cohorte de {r['n']} personas, semilla {r['semilla']}, {r['anios_persona']} años-persona "
              f"({r['segundos_simular']} s simulando, {r['segundos_medir']} s midiendo)",
              "", f"{r['cumplen']} de {r['total']} metas cuadran. "
              f"Sin contar insumos ni metas calibradas: {r['cumplen_sin_insumos']} de {r['total_sin_insumos']}.", ""]
    ancho = max(len(m["indicador"]) for m in r["metas"])
    lineas.append(f"{'':2} {'Meta':<{ancho}}  {'Chile':>10} {'Simulado':>10} {'Error':>8} {'Tol.':>6}  Calidad")
    grupo = None
    orden = list(dict.fromkeys(m["grupo"] for m in r["metas"]))
    for m in sorted(r["metas"], key=lambda m: orden.index(m["grupo"])):
        if m["grupo"] != grupo:
            grupo = m["grupo"]
            lineas.append(f"-- {grupo}")
        plata = m["tolerancia_relativa"]
        if m["error"] is None:
            error = "s/d"
        elif plata:
            error = f"{100 * m['error']:+.1f}%"
        else:
            error = f"{100 * m['error']:+.1f}pp"
        marca = "ok" if m["cumple"] else "NO" if m["medible"] else "??"
        tol = f"{100 * m['tolerancia']:.0f}{'%' if plata else 'pp'}"
        lineas.append(f"{marca:2} {m['indicador']:<{ancho}}  {_fmt(m['meta'], plata):>10} {_fmt(m['simulado'], plata):>10} "
                      f"{error:>8} {tol:>6}  {m['calidad']}")
    lineas += ["", f"ELSOC (no es insumo del motor): {r['elsoc_cumplen']} de {r['elsoc_total']} filas comparables cuadran."]
    for x in r["elsoc"]:
        marca = "ok" if x["cumple"] else "--" if not x["comparable"] else "NO"
        error = "s/d" if x["error"] is None else f"{100 * x['error']:+.1f}pp"
        meta = x["meta"]
        meta = f"{100 * meta[0]:.1f}-{100 * meta[1]:.1f}%" if isinstance(meta, tuple) else _fmt(meta, False)
        lineas.append(f"{marca:2} {x['indicador']:<22} {x['banda']:>6}  {meta:>11} {_fmt(x['simulado'], False):>8} "
                      f"{error:>8} {100 * x['tolerancia']:.0f}pp  n={x['n_simulado']}")
    if r["fallas"]:
        lineas += ["", f"{r['vidas_con_error']} vidas terminaron con error:"]
        for f in r["fallas"][:10]:
            lineas.append(f"   gemelo {f['gemelo']}: {f['error']} | {f['estado']}")
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--precalcular"]:
        print(f"Validación guardada en {precalcular()}")
        return
    n = int(argv[0]) if argv else N_COHORTE
    semilla = int(argv[1]) if len(argv) > 1 else 0
    print(tabla(validar(n, semilla)))


if __name__ == "__main__":
    main()
