"""La mano del año: tres cartas. Siempre está 'seguir'; si el año trae una oferta de trabajo
ocupa una carta, y el resto son decisiones posibles sorteadas con la suerte del año."""

import numpy as np

from app.sim.companies import nombre_empresa
from app.sim.context import Ctx
from app.sim.decisions import CATALOGO, disponibles
from app.sim.modules.labor import oferta_del_anio
from app.sim.profile import Perfil
from app.sim.state import CES, EMP, EMPR, Estado
from app.sim.tables import tablas

MAX_CARTAS = 3   # seguir + dos jugadas
_TIPO = {"startup": "una startup", "pyme": "una pyme", "grande": "una empresa grande", "estado": "el Estado"}


def _plata(x: float) -> str:
    return f"${x / 1e6:.1f} M".replace(".", ",") if x >= 1e6 else f"${x / 1e3:.0f} mil"


def mano(yo: Estado, perfil: Perfil, ctx: Ctx) -> list[dict]:
    """Cartas del año para un gemelo: [{decision, nombre, descripcion, tipo}]."""
    from app.sim.profile import TAMANOS

    su, t, sit = ctx.suerte, yo.t, int(yo.sit[0])
    seguir = {EMP: ("Seguir igual", "Dejas que el año corra sin cambiar nada."),
              CES: ("Seguir buscando", "Sigues mandando currículums."),
              EMPR: ("Seguir con tu emprendimiento", "Otro año empujando lo tuyo.")}.get(sit, ("Seguir igual", ""))
    cartas = [{"decision": "seguir", "nombre": seguir[0], "descripcion": seguir[1], "tipo": "base"}]

    of = oferta_del_anio(yo, ctx)
    if of["existe"][0]:
        emp, tam, rel = nombre_empresa(int(of["empresa"][0])), TAMANOS[int(of["tam"][0])], float(of["rel"][0])
        sueldo = float(yo.sueldo[0] * np.exp(rel))
        cambio = f"{100 * (np.exp(rel) - 1):+.0f}%".replace("+", "+").replace("-", "−")
        cartas.append({"decision": "aceptar_oferta", "nombre": f"Irte a {emp}", "tipo": "oportunidad",
                       "descripcion": f"{emp} ({_TIPO[tam]}) te ofrece {_plata(sueldo)} al mes, {cambio} de lo que ganas. Partes de cero, sin antigüedad."})

    resto = [d for d in disponibles(yo) if d != "seguir"]
    orden = sorted(resto, key=lambda d: su.escalar(t, f"mano_{d}"))
    for d in orden[: MAX_CARTAS - len(cartas)]:
        c = CATALOGO[d]
        if d == "magister":
            cartas.append(carta_magister(yo, ctx))
            continue
        if d == "emprender":
            cartas.append(carta_emprender(yo, perfil, ctx))
            continue
        if d == "volver_empleo":
            cartas.append(carta_cerrar(yo, perfil))
            continue
        cartas.append({"decision": d, "nombre": c.nombre, "descripcion": c.descripcion, "tipo": c.grupo})
    return cartas


def carta_magister(yo: Estado, ctx: Ctx) -> dict:
    """Un magíster en una universidad concreta: se sortea con el peso de cuántos magísteres ofrece cada una (SIES 2026)."""
    from app.sim.params import P

    tb = tablas()
    pesos = np.array([u["n"] for u in tb.universidades], float)
    k = int(np.searchsorted(np.cumsum(pesos / pesos.sum()), ctx.suerte.escalar(yo.t, "mano_universidad")).clip(max=len(pesos) - 1))
    u = tb.universidades[k]
    if u["selectiva"]:
        prima = f"Es selectiva: en los datos de DIPRES, quienes egresan ganan {100 * P.MAG_PRIMA['selectiva']:.0f}% más."
    else:
        prima = "No es selectiva: en los datos de DIPRES la prima no se distingue de cero y la renta baja mientras estudias."
    modal = f" El {100 * u['frac_no_diurna']:.0f}% de sus magísteres es vespertino, semipresencial o a distancia." if u.get("frac_no_diurna") else ""
    return {"decision": f"magister:{u['codigo']}", "nombre": f"Magíster en la {u['nombre']}" if u["nombre"].startswith("Universidad") or u["nombre"].startswith("Pontificia") else f"Magíster en {u['nombre']}",
            "tipo": "crecer", "descripcion": f"{_plata(u['arancel'])} al año por {u['anios']} {'año' if u['anios'] == 1 else 'años'}, trabajando en paralelo. {prima}{modal}"}


def _emp_texto(tipo: str, edu: str) -> str:
    from app.sim.params import P

    s = P.EMP_SOBREVIVE[tipo]
    if tipo == "empleador":
        rel = P.EMP_INGRESO_EMPLEADOR.get(edu, P.EMP_INGRESO_EMPLEADOR["media"])
        gana = f"Los que siguen ganan en mediana {rel:.2f} veces lo de un asalariado con tus estudios".replace(".", ",")
    else:
        rel = P.EMP_INGRESO.get(edu, P.EMP_INGRESO["media"])
        gana = f"Ganan en mediana {100 * rel:.0f}% de lo que gana un asalariado comparable"
    return f"De cada 100 que parten, {100 * s[1]:.0f} siguen al año y {100 * s[5]:.0f} a los 5 (EPS). {gana} (ESI)."


def carta_emprender(yo: Estado, perfil: Perfil, ctx: Ctx) -> dict:
    """Emprender por tu cuenta o con empleados, en un giro de tu rubro."""
    from app.sim.companies import giro

    tipo = "empleador" if ctx.suerte.escalar(yo.t, "mano_tipo_emp") < 0.5 else "cuenta_propia"
    g = giro(int(yo.rubro[0]), ctx.suerte.escalar(yo.t, "mano_giro"))
    if tipo == "empleador":
        nombre, que = f"Montar {g}, con empleados", "Dejas tu pega y contratas gente."
    else:
        nombre, que = f"Independizarte: {g}", "Dejas tu pega y trabajas por tu cuenta, sin empleados."
    return {"decision": f"emprender:{tipo}", "nombre": nombre[0].upper() + nombre[1:], "tipo": "riesgo",
            "descripcion": f"{que} {_emp_texto(tipo, perfil.edu)}"}


def carta_cerrar(yo: Estado, perfil: Perfil) -> dict:
    from app.sim.params import P

    tipo = "empleador" if yo.emp_tipo[0] == 1 else "cuenta_propia"
    anio = int(yo.emp_anios[0])
    cierra = P.EMP_SALIDA[tipo][min(anio, 2)]
    return {"decision": "volver_empleo", "nombre": "Cerrar y volver a emplearte", "tipo": "trabajo",
            "descripcion": f"Cierras y sales a buscar trabajo. En el año {anio + 1} de un negocio como el tuyo, cierra el {100 * cierra:.0f}% (EPS). "
                           "Volver de un negocio cuesta lo mismo que volver de un despido."}
