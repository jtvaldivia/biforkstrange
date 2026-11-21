"""Mercado laboral: despido, ofertas y ascenso compiten cada año; búsqueda desde la cesantía;
emprendimiento; magíster y capacitación. Las ocupaciones de destino salen de JobHop."""

from statistics import NormalDist

import numpy as np

from app.sim.companies import elegir_empresa
from app.sim.params import P
from app.sim.profile import TAMANOS
from app.sim.state import CES, EMP, EMPR, SAB
from app.sim.tables import tramo3

_Q = np.array([0.10, 0.25, 0.50, 0.75, 0.90])


def oferta_rel(u: np.ndarray) -> np.ndarray:
    """Sueldo de una oferta sobre el sueldo actual (log), por la inversa de los cuantiles de la SCE.
    Fuera de p10-p90 se prolonga la pendiente del tramo vecino."""
    q = np.array([P.OFERTA_REL[k] for k in ("p10", "p25", "p50", "p75", "p90")])
    bajo = q[0] + (u - 0.10) * (q[1] - q[0]) / 0.15
    alto = q[4] + (u - 0.90) * (q[4] - q[3]) / 0.15
    return np.where(u < 0.10, bajo, np.where(u > 0.90, alto, np.interp(u, _Q, q)))


def p_supera(umbral: float) -> float:
    """Fracción de ofertas de la SCE que supera un umbral (log)."""
    us = np.linspace(0.0005, 0.9995, 2000)
    return float((oferta_rel(us) > umbral).mean())


def tasa_ofertas(edad: int) -> float:
    """Ofertas al año en Chile: cambios voluntarios observados (EPS) / fracción de ofertas que se aceptan sin buscar (SCE)."""
    return P.CAMBIO_VOLUNTARIO[tramo3(edad)] / p_supera(P.UMBRAL["no_busca"])


def factor_ia(e, ctx) -> np.ndarray:
    """Ofertas y búsqueda para jóvenes en las ocupaciones más expuestas a IA (Brynjolfsson et al.)."""
    expuesta = ctx.tb.ia[e.ocup] >= P.IA_QUINTIL
    return np.where(expuesta & (e.edad <= P.IA_EDAD_MAX), 1 - P.IA_BRECHA_JOVENES, 1.0)


def oferta_del_anio(e, ctx) -> dict[str, np.ndarray]:
    """La mejor oferta que el año le trae al gemelo sin buscar, si la trae. Es la misma en todos los
    universos (sale de la suerte escalar), así el menú puede mostrarla antes de decidir."""
    su = ctx.suerte
    lam = tasa_ofertas(e.edad) * factor_ia(e, ctx)
    existe = (e.sit == EMP) & (su.escalar(e.t, "oferta") < 1 - np.exp(-lam))
    rel = np.full(e.n, float(oferta_rel(np.array([su.escalar(e.t, "oferta_rel")]))[0]))
    tam = _tipo_destino(e.tam, np.full(e.n, su.escalar(e.t, "oferta_se_queda")), np.full(e.n, su.escalar(e.t, "oferta_tam")))
    empresa = elegir_empresa(e.rubro, tam, np.full(e.n, su.escalar(e.t, "oferta_emp")), e.empresa)
    return {"existe": existe, "rel": rel, "tam": tam, "empresa": empresa}


def _tipo_destino(tam_actual, u_queda, u_tam):
    acum = np.cumsum([P.TAM_MEZCLA[k] for k in TAMANOS])
    sorteo = np.searchsorted(acum, u_tam).clip(max=len(TAMANOS) - 1)
    return np.where(u_queda < P.TAM_SE_QUEDA, tam_actual, sorteo).astype(np.int8)


def _nuevo_empleo(e, mask, rel, ctx, nombre, ev):
    """Cambio de empleador: sueldo nuevo, tipo de empresa, empresa con nombre y, según JobHop, ocupación."""
    if not mask.any():
        return
    tb, su = ctx.tb, ctx.suerte
    e.sueldo[mask] *= np.exp(rel[mask])
    e.antig[mask] = 0.0
    e.tam[mask] = _tipo_destino(e.tam, su.u(e.t, nombre + "_queda"), su.u(e.t, nombre + "_tam"))[mask]
    e.empresa[mask] = elegir_empresa(e.rubro, e.tam, su.u(e.t, nombre + "_emp"), e.empresa)[mask]
    e.mult_rubro[mask] = tb.mult_rubro_idx[e.rubro[mask]]
    mueve = mask & tb.tiene_destinos[e.ocup] & (su.u(e.t, nombre + "_oc") < tb.p_cambia[e.ocup])
    ix = np.flatnonzero(mueve)
    if ix.size:
        viejo = e.ocup[ix]
        nuevo = (tb.T_acum[viejo] < su.u(e.t, nombre + "_od")[ix, None]).sum(1).clip(max=len(tb.codigos) - 1)
        cambia = nuevo != viejo
        # traspaso del sueldo relativo del nuevo gran grupo (ESI) y pérdida de la experiencia en la ocupación (Kambourov y Manovskii)
        exp_perdida = np.minimum(e.exp_ocup[ix], P.OCUP_EXP_TOPE) * P.OCUP_EXPERIENCIA
        e.sueldo[ix] *= np.where(cambia, np.exp(P.OCUP_REL * np.log(tb.rel[nuevo] / tb.rel[viejo]) - exp_perdida), 1.0)
        e.exp_ocup[ix] = np.where(cambia, 0.0, e.exp_ocup[ix])
        e.ocup[ix] = nuevo
        ev["cambia_ocup"] = ev["cambia_ocup"] | np.isin(np.arange(e.n), ix[cambia])


def trabajo(e, i, ctx, ev):
    tb, pf, su, n = ctx.tb, ctx.perfil, ctx.suerte, e.n
    tr = tramo3(e.edad)
    u = lambda k: su.u(e.t, k)   # noqa: E731
    z = lambda k: su.z(e.t, k)   # noqa: E731
    reloj = lambda k, h: -np.log(1 - u(k)) / np.maximum(h, 1e-9)   # noqa: E731  años hasta el evento
    efectivo = lambda: e.sueldo * np.exp(-e.cicatriz) * (1 - e.penal_hijo)   # noqa: E731

    # 1. cambios de situación que vienen de la decisión
    of = oferta_del_anio(e, ctx)
    acepta = i.acepta & of["existe"]
    e.sueldo[acepta] *= np.exp(of["rel"][acepta])
    e.tam[acepta], e.empresa[acepta], e.antig[acepta] = of["tam"][acepta], of["empresa"][acepta], 0.0

    pausa_nueva = i.sabatico & (e.sit == EMP)
    e.sit[pausa_nueva] = SAB
    emprende = i.emprende & np.isin(e.sit, (EMP, CES))
    e.sit[emprende] = EMPR
    e.emp_anios[emprende] = 0
    e.emp_q[emprende] = z("emp_q")[emprende]
    cierra_vol = i.volver & (e.sit == EMPR)
    e.sit[cierra_vol] = CES
    e.anios_ces[cierra_vol], e.hueco_vol[cierra_vol] = 0, True   # dejar lo propio cuenta como salida voluntaria
    empieza_mag = i.magister & (e.sit == EMP)
    if empieza_mag.any():
        uni = tb.universidades[i.universidad]
        e.estudia[empieza_mag] = e.mag_total[empieza_mag] = uni["anios"]
        e.mag_sel[empieza_mag], e.mag_arancel[empieza_mag] = uni["selectiva"], uni["arancel"]

    emp0, ces0, sab0, empr0 = (e.sit == k for k in (EMP, CES, SAB, EMPR))
    ingreso_anual, meses_ces = np.zeros(n), np.zeros(n)
    ia = factor_ia(e, ctx)
    h_encontrar = -np.log(1 - P.ENCONTRAR[tr]) * ia
    sueldo_antes = efectivo()

    # 2. con empleo: despido, oferta y ascenso compiten; ocurre el primero
    antig = np.where(e.antig < 1, P.ANTIG["nuevo"], np.where(e.antig >= 5, P.ANTIG["viejo"], P.ANTIG["medio"]))
    mult_tam = np.array([P.MULT_TAM[k] for k in TAMANOS])[e.tam]
    h_d = P.DESPIDO[tr] * e.mult_rubro * mult_tam * antig
    h_o = tasa_ofertas(e.edad) * np.where(i.busca, P.BUSCA_MULT, 1.0) * ia
    if ctx.jugador:   # en tu turno solo te cambias si lo eliges: buscando o aceptando la oferta del año
        h_o = np.where(i.busca, h_o, 0.0)
    h_a = np.array(P.ASCENSO)[e.nivel]
    t_d, t_o, t_a = reloj("t_despido", h_d), reloj("t_oferta", h_o), reloj("t_ascenso", h_a)
    primero = np.minimum(np.minimum(t_d, t_o), t_a)
    despido = emp0 & (t_d < 1) & (t_d == primero)
    oferta = emp0 & (t_o < 1) & (t_o == primero)
    asciende = emp0 & (t_a < 1) & (t_a == primero)

    rel = oferta_rel(u("oferta_rel"))
    cambio = oferta & (rel > np.where(i.busca, P.UMBRAL["busca"], P.UMBRAL["no_busca"]))
    _nuevo_empleo(e, cambio, rel, ctx, "oferta", ev)

    e.sueldo[asciende] *= 1 + P.ASC_ALZA
    e.nivel[asciende] = np.minimum(e.nivel[asciende] + 1, 4)

    sigue = emp0 & ~despido
    frac = np.where(cambio, t_o, np.where(asciende, t_a, 1.0))   # parte del año con el sueldo anterior
    ingreso_anual[sigue] = (12 * (frac * sueldo_antes + (1 - frac) * efectivo()))[sigue]

    # despido: indemnización, seguro y búsqueda dentro del mismo año
    tau = reloj("busca_tras_despido", h_encontrar)
    reempleo = despido & (t_d + tau < 1)
    a_min, a_tope = P.INDEMNIZACION
    indemnizacion = np.where(e.antig >= a_min, np.minimum(np.floor(e.antig), a_tope), 0) * sueldo_antes
    mc = np.where(reempleo, tau, 1 - t_d) * 12
    meses_ces[despido] = mc[despido]
    e.cicatriz[reempleo] = P.CICATRIZ
    _nuevo_empleo(e, reempleo, np.zeros(n), ctx, "reempleo", ev)
    ing = (12 * t_d * sueldo_antes + np.where(reempleo, 12 * (1 - t_d - tau) * efectivo(), 0.0)
           + indemnizacion + P.SEGURO * sueldo_antes * mc)
    ingreso_anual[despido] = ing[despido]
    queda = despido & ~reempleo
    e.sit[queda] = CES
    e.anios_ces[queda], e.hueco_vol[queda] = 0, False

    # 3. sin trabajo al empezar el año: búsqueda
    h_f = h_encontrar * np.where(e.anios_ces >= 1, P.DURACION_DEP, 1.0) * np.where(e.hueco_vol, P.HUECO_VOLUNTARIO, 1.0)
    tau2 = reloj("busca", h_f)
    halla = ces0 & (tau2 < 1)
    e.cicatriz[halla] = P.CICATRIZ   # tras pausa, cierre o despido: misma pérdida (EPS)
    _nuevo_empleo(e, halla, np.zeros(n), ctx, "busca", ev)
    e.sit[halla] = EMP
    ingreso_anual[halla] = (12 * (1 - tau2) * efectivo())[halla]
    meses_ces[ces0] = np.where(halla, 12 * tau2, 12.0)[ces0]
    e.anios_ces[ces0 & ~halla] += 1
    e.hueco_vol[halla], e.anios_ces[halla] = False, 0

    # 4. pausa (sabático o cuidado de un hijo): el año siguiente vuelve a buscar
    e.sit[sab0] = CES
    e.hueco_vol[sab0], e.anios_ces[sab0] = True, 0

    # 5. emprendimiento: ingreso relativo al asalariado comparable (ESI) y cierre (EPS)
    rel_emp = P.EMP_INGRESO.get(pf.edu, P.EMP_INGRESO["media"])
    ing_emp = e.sueldo * rel_emp * np.exp(P.EMP_SD_Q * e.emp_q + P.EMP_SD_T * z("emp_t"))
    ingreso_anual[empr0] = (12 * ing_emp)[empr0]
    salida = np.array(P.EMP_SALIDA)[np.minimum(e.emp_anios, 2)] * np.exp(P.B_EMP_SALIDA_A * pf.z("A"))
    cierra = empr0 & (u("emp_cierra") < salida)
    e.sit[cierra] = CES
    e.anios_ces[cierra], e.hueco_vol[cierra] = 0, True
    e.emp_anios[empr0] += 1

    # 6. magíster y capacitación: mientras estudias la renta cambia según la universidad; al titularte, la prima (DIPRES 2026)
    estudia = e.estudia > 0
    anio_mag = np.clip(e.mag_total - e.estudia, 0, 1)
    en_estudio = np.where(e.mag_sel, np.array(P.MAG_EN_ESTUDIO["selectiva"])[anio_mag], np.array(P.MAG_EN_ESTUDIO["no_selectiva"])[anio_mag])
    ingreso_anual = np.where(estudia & (e.sit == EMP), ingreso_anual * (1 + en_estudio), ingreso_anual)
    e.estudia[estudia] -= 1
    titulo = estudia & (e.estudia == 0)
    e.postgrado[titulo] = True
    e.sueldo[titulo] *= 1 + np.where(e.mag_sel, P.MAG_PRIMA["selectiva"], P.MAG_PRIMA["no_selectiva"])[titulo]
    curso = i.capacita & (e.sit == EMP)
    e.sueldo[curso] *= 1 + P.CURSO_SUELDO

    # 7. cierre del año: el perfil por edad de la ESI, sin el alza esperada por ascensos (ya va aparte)
    trabaja = e.sit == EMP
    esperado_asc = np.array(P.ASCENSO)[e.nivel] * P.ASC_ALZA
    reajuste = P.REAJUSTE[0] + P.REAJUSTE[1] * NormalDist().inv_cdf(min(max(su.escalar(e.t, "reajuste"), 1e-6), 1 - 1e-6))   # común a todos
    e.sueldo *= np.exp(tb.crecimiento_edad(pf.edu, e.edad) - esperado_asc + reajuste)
    e.antig = np.where(trabaja, e.antig + 1, 0.0)
    e.exp_ocup = np.where(trabaja, e.exp_ocup + 1, e.exp_ocup)
    e.cicatriz *= P.CICATRIZ_DECAE
    e.penal_hijo = np.maximum(e.penal_hijo - P.HIJO_PENAL_MUJER / 2, 0.0)
    e.horas = np.where(emp0 & (e.sit == EMP), i.horas, np.where(e.sit == EMP, P.HORAS_BASE, 0.0))
    e.ingreso, e.meses_ces = ingreso_anual / 12, meses_ces
    ev.update(
        pausa=sab0, emprende=emprende, cierra_emp=cierra | cierra_vol, cambio=cambio, oferta_aceptada=acepta, ascenso=asciende,
        despido=despido, reempleo_mismo_anio=reempleo, encuentra=halla, estudia=estudia, titulo=titulo, curso=curso,
    )
