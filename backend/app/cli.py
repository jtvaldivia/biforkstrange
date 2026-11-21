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

from app.sim.counterfactual import comparar, p_reconvertir
from app.sim.decisions import normalizar
from app.sim.engine import simular
from app.sim.game import Partida, ficha
from app.sim.modules.labor import factores_ia
from app.sim.params import PARAMS, P
from app.sim.profile import BIG5, NIVELES, Perfil
from app.sim.state import CES, Estado
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
    print(f"  {'Con pareja' if pf.pareja else 'Sin pareja'}, {pf.hijos} hijos · {pf.contactos:.0f} contactos · riesgo {pf.riesgo:+.1f} DE · ambición {pf.ambicion:+.1f} DE")
    print(f"  Tipo de persona más cercano: {pf.arquetipo}")
    print(f"  Exposición de tu ocupación a la IA: {nivel_ia(tb.ia[o])} (percentil {100 * tb.ia[o]:.0f}); escenario de adopción: {a.ia}")
    if pf.supuestos:
        print(f"{DIM}  Supuse: " + "; ".join(pf.supuestos) + f".{FIN}")


def mostrar_ficha(f: dict, etiqueta: str = "") -> None:
    trabajo = f"{f['ocupacion']} ({f['nivel']}, {f['empleador']}) · {plata(f['sueldo'])}/mes" if f["situacion"] == "con empleo" else f["situacion"]
    print(f"  {etiqueta}{f['edad']} años · {trabajo}")
    print(f"  {' ' * len(etiqueta)}ahorros {plata(f['ahorros'])} · energía {f['energia']:.0f} · ánimo {f['animo']:.0f} · "
          f"{'con pareja' if f['pareja'] else 'sin pareja'}, {f['hijos']} hijos · {f['contactos']:.0f} contactos"
          + (" · magíster" if f["postgrado"] else " · estudiando magíster" if f["estudia"] else ""))


def mostrar_menu(ops, horizonte: int) -> None:
    titulo(f"Qué pasaría si... (1.000 futuros por opción, misma suerte; resultados a {horizonte} años)")
    print(f"{DIM}  Ingreso = promedio mensual del período, del caso malo (p10) al bueno (p90). 'Cesante' = 3 meses o más sin trabajo en algún año. 'E. mín' = energía más baja del período.")
    print(f"  'Contra seguir' = en cuántos futuros ganas más o menos que si no cambias nada. 'Gemelos' = cuántos como tú lo elegirían.{FIN}")
    print(f"\n  {'#':>2}  {'Decisión':<46} {'Ingreso mensual':<25} {'Cesante':>7} {'Ánimo':>5} {'E. mín':>7} {'Ahorros':>9} {'Deuda':>5}  {'Contra seguir':<16} {'Gemelos':>7}")
    for k, o in enumerate(ops, 1):
        ing = f"{plata(o.ingreso[0])} · {B}{plata(o.ingreso[1])}{FIN} · {plata(o.ingreso[2])}"
        pad = 25 + (len(B) + len(FIN))
        vs = "—" if o.decision == "seguir" else f"+{porc(o.p_mejor)} / -{porc(o.p_peor)}"
        print(f"  {k:>2}  {o.nombre[:46]:<46} {ing:<{pad}} {porc(o.p_cesantia):>7} {o.animo:>5.0f} {o.energia_min:>7.0f} {plata(o.ahorros[1]):>9} {porc(o.p_deuda):>5}  {vs:<16} {porc(o.gemelos):>7}")
        if o.extra:
            print(f"{DIM}      afinidad con tu ocupación {porc(o.extra['afinidad'])} · lo logras este año con probabilidad {porc(o.extra['logra'])} · exposición a IA: {nivel_ia(o.extra['ia_origen'])} → {nivel_ia(o.extra['ia_destino'])}{FIN}")


def mostrar_turno(t: dict) -> None:
    titulo(f"Elegiste: {t['nombre']}")
    for linea in t["eventos"]:
        print(f"  • {linea}")
    mostrar_ficha(t["yo"], "Tú:      ")
    mostrar_ficha(t["sombra"], "Sombra:  ")
    n = t["nube_eventos"]
    print(f"{DIM}  En los 1.000 futuros de este año: despido {porc(n['despido'])}, cambio de pega {porc(n['cambio'])}, ascenso {porc(n['ascenso'])}, "
          f"licencia por agotamiento {porc(n['burnout'])}, hijo {porc(n['hijo'])}. La sombra es tu gemelo que nunca cambia nada, con tu misma suerte.{FIN}")


def cmd_perfil(a) -> None:
    pf = cargar_perfil(a)
    mostrar_perfil(pf, a)
    e = Estado.desde_perfil(pf)
    from app.sim.context import Ctx
    from app.sim.luck import Suerte

    ctx = Ctx(pf, Suerte(a.seed, 1), a.ia)
    titulo("Cómo la IA mueve tus probabilidades (según tu ocupación y nivel de hoy)")
    for anio in (2026, 2030, 2035, 2040, 2045):
        e.anio = anio
        of, de = factores_ia(e, ctx)
        print(f"  {anio}: ofertas x{of[0]:.2f} · riesgo de despido x{de[0]:.2f}")


def cmd_menu(a) -> None:
    pf = cargar_perfil(a)
    mostrar_perfil(pf, a)
    g = Partida.reproducir(pf, _lista(a.historia), seed=a.seed, n=a.n, escenario=a.ia, horizonte=a.horizonte)
    if g.historial:
        titulo("Estado tras tu historia")
        mostrar_ficha(ficha(g.yo))
    mostrar_menu(g.menu(), a.horizonte)


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
    g = Partida(pf, seed=a.seed, n=a.n, escenario=a.ia, horizonte=a.horizonte)
    guion = _lista(a.auto)
    while g.yo.edad < a.hasta:
        titulo(f"━━ {g.yo.anio} · {g.yo.edad} años ━━")
        mostrar_ficha(ficha(g.yo))
        ops = g.menu()
        mostrar_menu(ops, a.horizonte)
        if a.auto is not None:
            if not guion:
                break
            dec = guion.pop(0)
        else:
            try:
                txt = input(f"\n{B}¿Qué haces este año?{FIN} [número · reconvertir:CÓDIGO · o=ocupaciones · q=salir] > ").strip()
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
        yo, so = ficha(g.yo), ficha(g.sombra)
        titulo(f"Balance a los {yo['edad']} años: tú contra tu sombra (misma suerte, sin cambiar nada)")
        print(f"  Decisiones: {', '.join(t['decision'] for t in g.historial)}")
        mostrar_ficha(yo, "Tú:      ")
        mostrar_ficha(so, "Sombra:  ")
        print(f"  Diferencia: sueldo {plata(yo['sueldo'] - so['sueldo'])}/mes · ahorros {plata(yo['ahorros'] - so['ahorros'])} · ánimo {yo['animo'] - so['animo']:+.0f} · energía {yo['energia'] - so['energia']:+.0f}")
        print(f"{DIM}  Es una sola vida de las posibles. Para ver el efecto promedio de un plan usa 'comparar'.{FIN}")


def cmd_comparar(a) -> None:
    pf = cargar_perfil(a)
    mostrar_perfil(pf, a)
    planes = {}
    for spec in a.plan or ["sin cambios=seguir", "buscar pega cada 3 años=buscar_pega,seguir*2,buscar_pega,seguir*2,buscar_pega,seguir*2,buscar_pega", "magíster=magister"]:
        nombre, _, txt = spec.partition("=")
        plan = _lista(txt or nombre)
        planes[nombre] = (plan + ["seguir"] * a.anios)[: a.anios]
    r = comparar(pf, planes, n=a.n, seed=a.seed, escenario=a.ia)
    titulo(f"Planes a {a.anios} años (hasta los {pf.edad + a.anios}), {a.n} futuros con la misma suerte")
    print(f"\n  {'Plan':<28} {'Ingreso mensual prom.':<27} {'Sueldo final':>12} {'Ahorros':>10} {'Cesante':>7} {'Agotam.':>7} {'Deuda':>5} {'Ánimo':>5} {'Hijos':>5}")
    for k, v in r.items():
        ing = f"{plata(v['ingreso'][0])} · {plata(v['ingreso'][1])} · {plata(v['ingreso'][2])}"
        print(f"  {k[:28]:<28} {ing:<27} {plata(v['sueldo_final'][1]):>12} {plata(v['ahorros'][1]):>10} {porc(v['p_cesantia']):>7} {porc(v['p_burnout']):>7} {porc(v['p_deuda']):>5} {v['animo']:>5.0f} {v['hijos']:>5.1f}")
    ref = next(iter(r))
    titulo(f"Contra '{ref}', futuro por futuro")
    for k, v in list(r.items())[1:]:
        print(f"  {k}: gana más en {porc(v['p_mas_ingreso'])} de los futuros y menos en {porc(v['p_menos_ingreso'])} (mediana {plata(v['delta_ingreso'])}/mes) · "
              f"más ahorros en {porc(v['p_mas_ahorros'])} (mediana {plata(v['delta_ahorros'])}) · ánimo mejor en {porc(v['p_mejor_animo'])}, peor en {porc(v['p_peor_animo'])}")
    for k, plan in planes.items():
        print(f"{DIM}  {k}: {', '.join(plan)}{FIN}")


def _ocupaciones(o: int, nivel: int, k: int) -> None:
    tb = tablas()
    af = tb.afinidad[o].copy()
    af[o] = 0
    titulo(f"Ocupaciones más afines a {tb.nombres[o]} (por movilidad observada en 355 mil currículums)")
    print(f"  {'Código':<7} {'Ocupación':<62} {'Afinidad':>8} {'Lo logra/año':>12} {'Sueldo rel.':>11} {'IA':>9}")
    for d in np.argsort(-af)[:k]:
        p = p_reconvertir(o, int(d), nivel)
        print(f"  {tb.codigos[d]:<7} {tb.nombres[d][:62]:<62} {porc(af[d]):>8} {porc(p):>12} {tb.rel[d] / tb.rel[o]:>10.2f}x {nivel_ia(tb.ia[d]):>9}")
    print(f"{DIM}  Afinidad 50% = la gente pasa a esa ocupación tanto como al azar. Sueldo relativo: grupo ocupacional en la ESI 2025. Usa reconvertir:CÓDIGO.{FIN}")


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
    nombres = {"dato": "DATOS (leídos de una fuente)", "derivado": "DERIVADOS (cálculo propio sobre una fuente)", "supuesto": "SUPUESTOS (decisión del equipo)"}
    for estado, tit in nombres.items():
        ps = {k: v for k, v in PARAMS.items() if v.estado == estado}
        titulo(f"{tit}: {len(ps)}")
        for k, v in ps.items():
            val = json.dumps(v.valor, ensure_ascii=False)
            print(f"  {k:<20} {val[:60]:<60} {DIM}{v.fuente}{FIN}")


def cmd_validar(a) -> None:
    """Compara una cohorte simulada (siempre 'seguir') con los datos que alimentan el motor."""
    tb = tablas()
    pf = Perfil.desde_dict({"nombre": "cohorte", "edad": 25, "sexo": "h", "institucion": "universidad", "rubro": "Servicios profesionales",
                            "tipo_empleador": "grande", "nivel": "junior", "sueldo": tb.mediana_esi("universitaria", 25), "ahorros": 0,
                            "pareja": False, "antiguedad": 1, "big5": {"O": 0}})
    es = simular(pf, ["seguir"] * 25, n=a.n, seed=a.seed, escenario_ia=a.ia)
    titulo("Cohorte de titulados universitarios que parte en la mediana a los 25 y nunca decide nada")
    print(f"  {'Edad':<5} {'Sueldo mediano sim.':>20} {'ESI 2025 + reajuste':>20} {'Sin trabajo sim.':>17} {'Desocupación ESI':>17}")
    des = tb.raw["ine"]["DESOCUPACION_por_edad"]
    for e in es[4::5]:
        emp = e.sit == 0
        esi = tb.mediana_esi("universitaria", e.edad) * (1 + P.REAJUSTE[0]) ** e.t
        tr = "25-29" if e.edad < 30 else "30-34" if e.edad < 35 else "35-44" if e.edad < 45 else "45-54"
        print(f"  {e.edad:<5} {plata(float(np.median(e.sueldo[emp]))):>20} {plata(esi):>20} {porc((e.sit == CES).mean()):>17} {porc(des[tr]):>17}")
    titulo("Tasas anuales simuladas contra la Encuesta de Protección Social")
    print(f"  {'Tramo':<7} {'Despido sim.':>13} {'EPS':>6} {'Cambio de empleador sim.':>26} {'EPS':>6}")
    for tr in ("18-29", "30-44", "45-59"):
        sel = [e for e in es if tramo3(e.edad - 1) == tr]
        d = np.mean([e.ev["despido"].mean() for e in sel])
        c = np.mean([(e.ev["cambio"] | e.ev["reempleo_mismo_anio"]).mean() for e in sel])
        print(f"  {tr:<7} {porc(d):>13} {porc(P.DESPIDO[tr]):>6} {porc(c):>26} {porc(P.CAMBIO_EMPLEADOR[tr]):>6}")
    print(f"{DIM}  La desocupación ESI es de toda la población de esa edad, no solo de universitarios, así que debe quedar por encima de la simulada.")
    print(f"  El cambio de empleador simulado es más bajo que la EPS porque esta cohorte nunca busca pega.{FIN}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="app.cli", description="Simulador BiforkStrange en la terminal")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def comun(p, perfil_obligatorio=True):
        p.add_argument("--perfil", required=perfil_obligatorio, help="JSON en formato bifurca.perfil")
        p.add_argument("--seed", type=int, default=7, help="semilla de la suerte")
        p.add_argument("--n", type=int, default=1000, help="futuros simulados")
        p.add_argument("--ia", choices=list(P.IA_ESCENARIOS), default="base", help="velocidad de adopción de IA")
        p.add_argument("--ahorros", type=float, help="ahorros en pesos, si el perfil no los trae")
        p.add_argument("--ocupacion", help="código ISCO-3, si no quieres el inferido")
        for r in BIG5:
            p.add_argument(f"--{r}", type=float, help=f"rasgo {r} en desviaciones estándar (-2 a 2)")
        return p

    comun(sub.add_parser("perfil", help="muestra cómo se leyó tu perfil")).set_defaults(fn=cmd_perfil)
    p = comun(sub.add_parser("menu", help="las opciones de este año y qué pasaría con cada una"))
    p.add_argument("--historia", help="decisiones ya tomadas, p. ej. 'seguir*2,magister'")
    p.add_argument("--horizonte", type=int, default=5)
    p.set_defaults(fn=cmd_menu)
    p = comun(sub.add_parser("jugar", help="partida interactiva, una decisión por año"))
    p.add_argument("--horizonte", type=int, default=5)
    p.add_argument("--hasta", type=int, default=50, help="edad final")
    p.add_argument("--auto", help="juega solo con estas decisiones, p. ej. 'trabajar_mas*2,magister'")
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
    sub.add_parser("supuestos", help="qué parámetros son dato y cuáles supuesto").set_defaults(fn=cmd_supuestos)
    comun(sub.add_parser("validar", help="cohorte simulada contra los datos"), perfil_obligatorio=False).set_defaults(fn=cmd_validar, n=5000)
    a = ap.parse_args()
    try:
        a.fn(a)
    except (ValueError, FileNotFoundError) as err:
        sys.exit(f"Error: {err}")


if __name__ == "__main__":
    main()
