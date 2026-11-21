"""Terminal para probar el simulador. Desde backend/:

    uv run python -m app.cli jugar --perfil perfiles/ejemplo.json
    uv run python -m app.cli menu --perfil perfiles/ejemplo.json
    uv run python -m app.cli comparar --perfil perfiles/ejemplo.json --plan "base=seguir*10" --plan "magister=magister,seguir*9"
    uv run python -m app.cli ocupaciones --perfil perfiles/ejemplo.json
    uv run python -m app.cli supuestos
    uv run python -m app.cli validar
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from app.sim.counterfactual import comparar
from app.sim.decisions import normalizar
from app.sim.engine import simular
from app.sim.game import Partida, ficha
from app.sim.modules.labor import p_supera, tasa_ofertas
from app.sim.params import PARAMS, P
from app.sim.profile import BIG5, NIVELES, Perfil
from app.sim.state import CES
from app.sim.tables import tablas, tramo3

B, DIM, FIN = "\033[1m", "\033[2m", "\033[0m"
if not sys.stdout.isatty():
    B = DIM = FIN = ""


def plata(x: float) -> str:
    s = "-" if x < 0 else ""
    x = abs(x)
    return f"{s}${x / 1e6:.1f} M".replace(".", ",") if x >= 1e6 else f"{s}${x / 1e3:.0f} mil"


def porc(x: float) -> str:
    return f"{100 * x:.0f}%"


def nivel_ia(p: float) -> str:
    return "muy alta" if p >= 0.85 else "alta" if p >= 0.65 else "media" if p >= 0.35 else "baja"


def titulo(t: str) -> None:
    print(f"\n{B}{t}{FIN}")


def cargar_perfil(a) -> Perfil:
    d = json.loads(Path(a.perfil).read_text(encoding="utf-8"))
    if a.ahorros is not None:
        d["ahorros"] = a.ahorros
    if a.ocupacion:
        d["ocupacion"] = a.ocupacion
    for r in BIG5:
        v = getattr(a, r, None)
        if v is not None:
            d.setdefault("big5", {})[r] = v
    return Perfil.desde_dict(d)


def mostrar_perfil(pf: Perfil, a) -> None:
    tb = tablas()
    o = tb.idx[pf.ocupacion]
    titulo(f"Gemelo de {pf.nombre}")
    print(f"  {pf.edad} años · {tb.nombres[o]} ({pf.ocupacion}), {NIVELES[pf.nivel]} · {pf.tipo_empleador} · {pf.rubro or 'rubro sin dato'}")
    med = tb.mediana_esi(pf.edu, pf.edad)
    print(f"  Sueldo {plata(pf.sueldo)} líquidos ({pf.sueldo / med:.1f} veces la mediana ESI de tu edad y estudios) · ahorros {plata(pf.ahorros)}")
    print(f"  {'Con pareja' if pf.pareja else 'Sin pareja'}, {pf.hijos} hijos · tipo de persona más cercano: {pf.arquetipo}")
    print(f"  Exposición de tu ocupación a la IA: {nivel_ia(tb.ia[o])} (percentil {100 * tb.ia[o]:.0f})")
    if pf.supuestos:
        print(f"{DIM}  Lo que tu perfil no trae y cómo lo tomé: " + "; ".join(pf.supuestos) + f".{FIN}")


def mostrar_ficha(f: dict, etiqueta: str = "") -> None:
    trabajo = f"{f['ocupacion'].split(' (')[0]}, {f['nivel']} en {f['empresa']} ({f['empleador']}) · {plata(f['sueldo'])}/mes" if f["situacion"] == "con empleo" else f["situacion"]
    print(f"  {etiqueta}{f['edad']} años · {trabajo}")
    print(f"  {' ' * len(etiqueta)}ahorros {plata(f['ahorros'])} · satisfacción {f['animo']:.0f} · salud {f['salud']:.0f} · tiempo con tu gente {f['social']:.0f}"
          + (" · síntomas depresivos" if f["depresion"] else "") + f" · {f['exp_ocupacion']:.0f} años en tu ocupación · "
          f"{'con pareja' if f['pareja'] else 'sin pareja'}, {f['hijos']} hijos"
          + (" · magíster" if f["postgrado"] else " · estudiando magíster" if f["estudia"] else ""))


def mostrar_menu(ops, horizonte: int) -> None:
    titulo(f"Tus cartas de este año (1.000 futuros por carta, misma suerte; plata a {horizonte} años, bienestar al cierre del año)")
    for k, o in enumerate(ops, 1):
        marca = " ★ oportunidad" if o.tipo == "oportunidad" else ""
        gente = f"  {DIM}· {o.gemelos_texto}{FIN}" if o.gemelos_texto else ""
        print(f"\n  {B}{k}. {o.nombre}{FIN}{marca}{gente}")
        print(f"     {o.descripcion}")
        efectos = " · ".join(e["texto"] for e in o.efectos) or "Tu año base"
        print(f"     {efectos}")
        print(f"{DIM}     ingreso {plata(o.ingreso[0])} · {plata(o.ingreso[1])} · {plata(o.ingreso[2])} | cesante {porc(o.p_cesantia)} | deuda {porc(o.p_deuda)} | "
              f"depresión {porc(o.p_depresion)} | ahorros {plata(o.ahorros[1])} | contra seguir +{porc(o.p_mejor)} / -{porc(o.p_peor)}{FIN}")


def mostrar_turno(t: dict) -> None:
    titulo(f"Elegiste: {t['nombre']}")
    for linea in t["eventos"]:
        print(f"  • {linea}")
    for logro in t["logros"]:
        print(f"  ★ Logro: {logro}")
    mostrar_ficha(t["yo"])
    n = t["nube_eventos"]
    print(f"{DIM}  En los 1.000 futuros de este año: despido {porc(n['despido'])}, cambio de pega {porc(n['cambio'])}, ascenso {porc(n['ascenso'])}, "
          f"síntomas depresivos {porc(n['depresion'])}, hijo {porc(n['hijo'])}.{FIN}")


def cmd_perfil(a) -> None:
    pf = cargar_perfil(a)
    mostrar_perfil(pf, a)
    titulo("Tus tasas de partida")
    tr = tramo3(pf.edad)
    print(f"  Despido al año: {porc(P.DESPIDO[tr])} (EPS) · ofertas al año sin buscar: {tasa_ofertas(pf.edad):.2f} "
          f"(se aceptan {porc(p_supera(P.UMBRAL['no_busca']))}) · encontrar trabajo si quedas cesante: {porc(P.ENCONTRAR[tr])}")


def cmd_menu(a) -> None:
    pf = cargar_perfil(a)
    mostrar_perfil(pf, a)
    g = Partida.reproducir(pf, _lista(a.historia), seed=a.seed, n=a.n, horizonte=a.horizonte)
    if g.historial:
        titulo("Estado tras tu historia")
        mostrar_ficha(ficha(g.yo, pf))
    mostrar_menu(g.menu(todas=a.todas), a.horizonte)


def _lista(texto: str | None) -> list[str]:
    """'seguir*3,magister' -> ['seguir','seguir','seguir','magister']"""
    out = []
    for parte in (texto or "").split(","):
        parte = parte.strip()
        if not parte:
            continue
        dec, _, rep = parte.partition("*")
        normalizar(dec)
        out += [dec] * int(rep or 1)
    return out


def cmd_jugar(a) -> None:
    pf = cargar_perfil(a)
    mostrar_perfil(pf, a)
    g = Partida(pf, seed=a.seed, n=a.n, horizonte=a.horizonte)
    guion = _lista(a.auto)
    while g.yo.edad < a.hasta:
        titulo(f"━━ {g.yo.anio} · {g.yo.edad} años ━━")
        mostrar_ficha(ficha(g.yo, pf))
        ops = g.menu(todas=a.todas)
        mostrar_menu(ops, a.horizonte)
        if a.auto is not None:
            if not guion:
                break
            dec = guion.pop(0)
        else:
            try:
                txt = input(f"\n{B}¿Qué haces este año?{FIN} [número · o=ocupaciones · q=salir] > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if txt in ("q", "salir", ""):
                break
            if txt == "o":
                _ocupaciones(int(g.yo.ocup[0]), int(g.yo.nivel[0]), 15)
                continue
            dec = ops[int(txt) - 1].decision if txt.isdigit() and 1 <= int(txt) <= len(ops) else txt
        try:
            mostrar_turno(g.decidir(dec))
        except ValueError as err:
            print(f"  {err}")
    if g.historial:
        yo, so = ficha(g.yo, pf), ficha(g.sombra, pf)
        titulo(f"Balance a los {yo['edad']} años: tú contra tu sombra (misma suerte, sin cambiar nada)")
        print(f"  Decisiones: {', '.join(t['decision'] for t in g.historial)}")
        mostrar_ficha(yo, "Tú:      ")
        mostrar_ficha(so, "Sombra:  ")
        print(f"  Diferencia: sueldo {plata(yo['sueldo'] - so['sueldo'])}/mes · ahorros {plata(yo['ahorros'] - so['ahorros'])} · satisfacción {yo['animo'] - so['animo']:+.0f}")
        print(f"{DIM}  Es una sola vida de las posibles. Para ver el efecto promedio de un plan usa 'comparar'.{FIN}")


def cmd_comparar(a) -> None:
    pf = cargar_perfil(a)
    mostrar_perfil(pf, a)
    planes = {}
    for spec in a.plan or ["sin cambios=seguir", "buscar pega cada 3 años=buscar_pega,seguir*2,buscar_pega,seguir*2,buscar_pega,seguir*2,buscar_pega", "magíster=magister"]:
        nombre, _, txt = spec.partition("=")
        plan = _lista(txt or nombre)
        planes[nombre] = (plan + ["seguir"] * a.anios)[: a.anios]
    r = comparar(pf, planes, n=a.n, seed=a.seed)
    titulo(f"Planes a {a.anios} años (hasta los {pf.edad + a.anios}), {a.n} futuros con la misma suerte")
    print(f"\n  {'Plan':<28} {'Ingreso mensual prom.':<27} {'Sueldo final':>12} {'Ahorros':>10} {'Cesante':>7} {'Depres.':>7} {'Deuda':>5} {'Satisf.':>7} {'Hijos':>5}")
    for k, v in r.items():
        ing = f"{plata(v['ingreso'][0])} · {plata(v['ingreso'][1])} · {plata(v['ingreso'][2])}"
        print(f"  {k[:28]:<28} {ing:<27} {plata(v['sueldo_final'][1]):>12} {plata(v['ahorros'][1]):>10} {porc(v['p_cesantia']):>7} {porc(v['p_depresion']):>7} {porc(v['p_deuda']):>5} {v['animo']:>7.0f} {v['hijos']:>5.1f}")
    ref = next(iter(r))
    titulo(f"Contra '{ref}', futuro por futuro")
    for k, v in list(r.items())[1:]:
        print(f"  {k}: gana más en {porc(v['p_mas_ingreso'])} de los futuros y menos en {porc(v['p_menos_ingreso'])} (mediana {plata(v['delta_ingreso'])}/mes) · "
              f"más ahorros en {porc(v['p_mas_ahorros'])} (mediana {plata(v['delta_ahorros'])}) · satisfacción mejor en {porc(v['p_mejor_animo'])}, peor en {porc(v['p_peor_animo'])}")
    for k, plan in planes.items():
        print(f"{DIM}  {k}: {', '.join(plan)}{FIN}")


def _ocupaciones(o: int, nivel: int, k: int) -> None:
    tb = tablas()
    af = tb.afinidad[o].copy()
    af[o] = 0
    titulo(f"Ocupaciones más afines a {tb.nombres[o]} (por movilidad observada en 355 mil currículums)")
    print(f"  {'Código':<7} {'Ocupación':<62} {'P(destino)':>10} {'Afinidad':>8} {'Sueldo rel.':>11} {'IA':>9}")
    for d in np.argsort(-tb.T[o])[:k]:
        print(f"  {tb.codigos[d]:<7} {tb.nombres[d][:62]:<62} {porc(tb.T[o, d]):>10} {porc(af[d]):>8} {tb.rel[d] / tb.rel[o]:>10.2f}x {nivel_ia(tb.ia[d]):>9}")
    print(f"{DIM}  P(destino): a qué ocupación pasa la gente de la tuya cuando cambia de grupo (JobHop). Sueldo relativo: gran grupo en la ESI 2023-2025.{FIN}")


def cmd_ocupaciones(a) -> None:
    tb = tablas()
    if a.buscar:
        for i in tb.buscar(a.buscar):
            print(f"  {tb.codigos[i]}  {tb.nombres[i]}  · IA {nivel_ia(tb.ia[i])}")
        return
    pf = cargar_perfil(a) if a.perfil else None
    o = tb.idx[a.desde] if a.desde else tb.idx[pf.ocupacion]
    _ocupaciones(o, pf.nivel if pf else 2, a.k)


def cmd_supuestos(a) -> None:
    nombres = {"dato": "DATOS (leídos o estimados de una fuente)", "derivado": "DERIVADOS (operación escrita sobre datos)"}
    for estado, tit in nombres.items():
        ps = {k: v for k, v in PARAMS.items() if v.estado == estado}
        titulo(f"{tit}: {len(ps)}")
        for k, v in ps.items():
            val = json.dumps(v.valor, ensure_ascii=False)
            print(f"  {k:<20} {val[:60]:<60} {DIM}[{v.pais}] {v.fuente}{FIN}")
    print(f"\n  Supuestos del equipo: {sum(v.estado not in nombres for v in PARAMS.values())}")


def cmd_validar(a) -> None:
    """Compara una cohorte simulada (siempre 'seguir') con los datos que alimentan el motor."""
    tb = tablas()
    pf = Perfil.desde_dict({"nombre": "cohorte", "edad": 25, "sexo": "h", "institucion": "universidad", "rubro": "Servicios profesionales",
                            "tipo_empleador": "grande", "nivel": "junior", "sueldo": tb.mediana_esi("universitaria", 25), "ahorros": 0,
                            "pareja": False, "antiguedad": 1, "big5": {"O": 0}})
    es = simular(pf, ["seguir"] * 25, n=a.n, seed=a.seed)
    titulo("Cohorte de titulados universitarios que parte en la mediana a los 25 y nunca decide nada")
    print(f"  {'Edad':<5} {'Sueldo mediano sim.':>20} {'ESI 2025 + reajuste':>20} {'Sin trabajo sim.':>17} {'Desocupación ESI':>17}")
    des = tb.raw["ine"]["DESOCUPACION_por_edad"]
    for e in es[4::5]:
        emp = e.sit == 0
        esi = tb.mediana_esi("universitaria", e.edad) * (1 + P.REAJUSTE[0]) ** e.t
        tr = "25-29" if e.edad < 30 else "30-34" if e.edad < 35 else "35-44" if e.edad < 45 else "45-54"
        print(f"  {e.edad:<5} {plata(float(np.median(e.sueldo[emp]))):>20} {plata(esi):>20} {porc((e.sit == CES).mean()):>17} {porc(des[tr]):>17}")
    titulo("Tasas anuales simuladas contra la Encuesta de Protección Social")
    print(f"  {'Tramo':<7} {'Despido sim.':>13} {'EPS':>6} {'Cambio voluntario sim.':>24} {'EPS':>6}")
    for tr in ("18-29", "30-44", "45-59"):
        sel = [e for e in es if tramo3(e.edad - 1) == tr]
        if not sel:
            continue
        idx = [k for k, e in enumerate(es) if tramo3(e.edad - 1) == tr and k > 0]
        d = np.mean([es[k].ev["despido"][es[k - 1].sit == 0].mean() for k in idx])
        c = np.mean([e.ev["cambio"].mean() for e in sel])
        print(f"  {tr:<7} {porc(d):>13} {porc(P.DESPIDO[tr]):>6} {porc(c):>24} {porc(P.CAMBIO_VOLUNTARIO[tr]):>6}")
    # variación anual del ingreso de quienes siguen en el mismo empleo, contra el panel ESI (sd 0,36 en datos con error de medición)
    pares = [(es[k - 1], es[k]) for k in range(1, len(es))]
    dl = np.concatenate([np.log(b.sueldo[(a.sit == 0) & (b.sit == 0) & ~b.ev["cambio"]] / a.sueldo[(a.sit == 0) & (b.sit == 0) & ~b.ev["cambio"]]) for a, b in pares])
    titulo("Lo que el modelo todavía no reproduce")
    print(f"  Desviación del cambio anual de sueldo de quien se queda: simulada {dl.std():.2f}, ESI 0,36 (incluye error de medición).")
    print(f"{DIM}  El modelo no tiene shocks propios al sueldo: no hay un número chileno que los separe de los cambios y despidos que ya simula.")
    print(f"  El despido simulado baja con la edad porque esta cohorte nunca se cambia y acumula antigüedad (5 años o más: x0,33 en la EPS).")
    print(f"  La desocupación ESI es de toda la población de esa edad, no solo de universitarios, así que debe quedar por encima de la simulada.{FIN}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="app.cli", description="Simulador BiforkStrange en la terminal")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def comun(p, perfil_obligatorio=True):
        p.add_argument("--perfil", required=perfil_obligatorio, help="JSON en formato bifurca.perfil")
        p.add_argument("--seed", type=int, default=7, help="semilla de la suerte")
        p.add_argument("--n", type=int, default=1000, help="futuros simulados")
        p.add_argument("--ahorros", type=float, help="ahorros en pesos, si el perfil no los trae")
        p.add_argument("--ocupacion", help="código ISCO-3, si no quieres el inferido")
        for r in BIG5:
            p.add_argument(f"--{r}", type=float, help=f"rasgo {r} en desviaciones estándar (-2 a 2)")
        return p

    comun(sub.add_parser("perfil", help="muestra cómo se leyó tu perfil")).set_defaults(fn=cmd_perfil)
    p = comun(sub.add_parser("menu", help="las opciones de este año y qué pasaría con cada una"))
    p.add_argument("--historia", help="decisiones ya tomadas, p. ej. 'seguir*2,magister'")
    p.add_argument("--todas", action="store_true", help="muestra todas las decisiones posibles, no solo las cartas del año")
    p.add_argument("--horizonte", type=int, default=5)
    p.set_defaults(fn=cmd_menu)
    p = comun(sub.add_parser("jugar", help="partida interactiva, una decisión por año"))
    p.add_argument("--horizonte", type=int, default=5)
    p.add_argument("--hasta", type=int, default=50, help="edad final")
    p.add_argument("--auto", help="juega solo con estas decisiones, p. ej. 'capacitarte*2,magister'")
    p.add_argument("--todas", action="store_true", help="muestra todas las decisiones posibles, no solo las cartas del año")
    p.set_defaults(fn=cmd_jugar)
    p = comun(sub.add_parser("comparar", help="planes completos con la misma suerte"))
    p.add_argument("--plan", action="append", help="'nombre=decisión,decisión*3'; el primero es la referencia")
    p.add_argument("--anios", type=int, default=10)
    p.set_defaults(fn=cmd_comparar, n=2000)
    p = comun(sub.add_parser("ocupaciones", help="ocupaciones afines y su exposición a IA"), perfil_obligatorio=False)
    p.add_argument("--desde", help="código ISCO-3 de origen")
    p.add_argument("--buscar", help="busca una ocupación por nombre")
    p.add_argument("-k", type=int, default=15)
    p.set_defaults(fn=cmd_ocupaciones)
    sub.add_parser("supuestos", help="cada parámetro con su fuente").set_defaults(fn=cmd_supuestos)
    comun(sub.add_parser("validar", help="cohorte simulada contra los datos"), perfil_obligatorio=False).set_defaults(fn=cmd_validar, n=5000)
    a = ap.parse_args()
    try:
        a.fn(a)
    except (ValueError, FileNotFoundError) as err:
        sys.exit(f"Error: {err}")


if __name__ == "__main__":
    main()
