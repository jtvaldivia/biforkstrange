"""Mercado laboral: despido, ofertas y ascenso como riesgos que compiten; búsqueda desde la
cesantía; emprendimiento; reconversión de ocupación; magíster. Aquí entran también la
exposición a IA de la ocupación, las trayectorias de JobHop y la red de contactos."""

import numpy as np

from app.sim.companies import elegir_empresa, otro_rubro
from app.sim.modules.network import factor_red
from app.sim.params import P
from app.sim.profile import TAMANOS
from app.sim.state import CES, EMP, EMPR, SAB
from app.sim.tables import tramo3


def factores_ia(e, ctx) -> tuple[np.ndarray, np.ndarray]:
    """(multiplicador de ofertas, multiplicador de despido) por exposición a IA de la ocupación."""
    g = ctx.ia_g(e.anio)
    x = np.maximum(ctx.tb.ia[e.ocup] - 0.5, 0) * 2          # solo pesa la mitad más expuesta
    x = x * (1 - P.ATRIBUTOS["hab_ia"] * e.habilidad / 100)   # estar al día en tu oficio amortigua el golpe
    oferta = np.clip(1 - P.IA_BRECHA * g * x * np.array(P.IA_PESO_OFERTA)[e.nivel], 0.3, 1.0)
    despido = 1 + P.IA_BRECHA * g * x * np.array(P.IA_PESO_DESPIDO)[e.nivel]
    return oferta, despido


def oferta_del_anio(e, ctx) -> dict[str, np.ndarray]:
    """La oferta con nombre que el año le trae al gemelo, si la trae. Es la misma para todos los
    universos (sale de la suerte escalar), así el menú puede mostrarla antes de decidir."""
    su, c = ctx.suerte, P.CARTAS
    oferta_ia, _ = factores_ia(e, ctx)
    por_edad = {"18-29": 1.0, "30-44": 0.8, "45-59": 0.6}[tramo3(e.edad)]
    p = np.clip(c["oferta"] * factor_red(e.contactos) * oferta_ia * (1 + P.ATRIBUTOS["hab_oferta"] * (e.habilidad - 50)) * por_edad, 0.05, 0.85)
    existe = (e.sit == EMP) & (e.antig >= 1) & (su.escalar(e.t, "oferta") < p)   # nadie te viene a buscar recién llegado
    acum = np.cumsum([c["oferta_mezcla"][k] for k in TAMANOS])   # quien te viene a buscar suele ser una empresa conocida
    tam = np.full(e.n, min(int(np.searchsorted(acum, su.escalar(e.t, "oferta_tam"))), len(TAMANOS) - 1), np.int8)
    lo, rango = c["oferta_alza"]
    alza = np.full(e.n, lo + rango * su.escalar(e.t, "oferta_alza") ** 2) + np.where(tam == 0, c["oferta_startup"], 0.0)
    empresa = elegir_empresa(e.rubro, tam, np.full(e.n, su.escalar(e.t, "oferta_emp")), e.empresa)
    return {"existe": existe, "tam": tam, "alza": alza, "empresa": empresa}


def cupo_del_anio(e, ctx) -> np.ndarray:
    """Si este año se abre un cupo de ascenso donde trabajas."""
    antig_min = np.where(e.nivel >= 2, 2, 1)   # a jefatura y gerencia se postula con más tiempo en la empresa
    return (e.sit == EMP) & (e.nivel < 4) & (e.antig >= antig_min) & (ctx.suerte.escalar(e.t, "cupo") < P.CARTAS["cupo"])


def _nuevo_empleo(e, mask, m_nueva, ctx, nombre, ev, voluntario):
    """Cambia de empleador: nuevo premio salarial, tipo de empresa y, a veces, ocupación."""
    if not mask.any():
        return
    tb, su = ctx.tb, ctx.suerte
    e.sueldo[mask] *= np.exp(m_nueva - e.m)[mask]
    e.m[mask] = m_nueva[mask]
    e.antig[mask] = 0.0
    e.contactos[mask] += P.RED_GANA["cambio"]

    acum = np.cumsum([P.TAM_MEZCLA[k] for k in TAMANOS])
    nuevo_tam = np.searchsorted(acum, su.u(e.t, nombre + "_tam2")).clip(max=len(TAMANOS) - 1)
    cambia_tam = mask & (su.u(e.t, nombre + "_tam") >= P.TAM_SE_QUEDA)
    e.tam[cambia_tam] = nuevo_tam[cambia_tam]

    # rubro y empresa con nombre
    cambia_rubro = mask & (su.u(e.t, nombre + "_rubro") < P.RUBRO_CAMBIA)
    e.rubro[cambia_rubro] = otro_rubro(su.u(e.t, nombre + "_rubro2"))[cambia_rubro]
    e.mult_rubro[mask] = tb.mult_rubro_idx[e.rubro[mask]]
    e.empresa[mask] = elegir_empresa(e.rubro, e.tam, su.u(e.t, nombre + "_emp"), e.empresa)[mask]

    # ocupación siguiente según las transiciones observadas en JobHop
    mueve = mask & tb.tiene_destinos[e.ocup] & (su.u(e.t, nombre + "_oc") < tb.p_cambia[e.ocup] * P.CAMBIA_OCUP_DESC)
    ix = np.flatnonzero(mueve)
    if ix.size:
        viejo = e.ocup[ix]
        nuevo = (tb.T_acum[viejo] < su.u(e.t, nombre + "_od")[ix, None]).sum(1).clip(max=len(tb.codigos) - 1)
        if voluntario:   # nadie se cambia por gusto a un grupo que paga bastante menos
            nuevo = np.where(tb.rel[nuevo] >= 0.9 * tb.rel[viejo], nuevo, viejo)
        nuevo = np.where(tb.es_directivo[nuevo] & ~tb.es_directivo[viejo] & (e.nivel[ix] < 2), viejo, nuevo)   # a un cargo directivo se llega con trayectoria
        e.sueldo[ix] *= np.exp(P.OCUP_REL * np.log(tb.rel[nuevo] / tb.rel[viejo]))
        e.ocup[ix] = nuevo
        ev["cambia_ocup"] = ev["cambia_ocup"] | np.isin(np.arange(e.n), ix[nuevo != viejo])


def trabajo(e, i, ctx, ev):
    tb, pf, su, n = ctx.tb, ctx.perfil, ctx.suerte, e.n
    tr = tramo3(e.edad)
    u = lambda k: su.u(e.t, k)   # noqa: E731
    z = lambda k: su.z(e.t, k)   # noqa: E731
    reloj = lambda k, h: -np.log(1 - u(k)) / np.maximum(h, 1e-9)   # noqa: E731  tiempo hasta el evento, en años
    efectivo = lambda: e.sueldo * np.exp(-e.cicatriz) * (1 - e.penal_hijo)   # noqa: E731

    # 1. cambios de situación que vienen de la decisión
    pausa_nueva = i.sabatico & (e.sit == EMP)
    e.sit[pausa_nueva] = SAB
    emprende = i.emprende & np.isin(e.sit, (EMP, CES))
    e.sit[emprende] = EMPR
    e.emp_anios[emprende] = 0
    e.emp_q[emprende] = z("emp_q")[emprende]
    cierra_vol = i.volver & (e.sit == EMPR)
    e.sit[cierra_vol] = CES
    e.origen_emp[cierra_vol], e.anios_ces[cierra_vol], e.hueco_vol[cierra_vol] = True, 0, False
    e.estudia[i.magister & (e.sit == EMP) & ~e.postgrado & (e.estudia == 0)] = 2

    # oportunidad del año: una empresa te vino a buscar y aceptas
    of = oferta_del_anio(e, ctx)
    acepta_carta = i.acepta & of["existe"]
    e.sueldo[acepta_carta] *= (1 + of["alza"])[acepta_carta]
    e.m[acepta_carta] += np.log1p(of["alza"])[acepta_carta]
    e.tam[acepta_carta], e.empresa[acepta_carta], e.antig[acepta_carta] = of["tam"][acepta_carta], of["empresa"][acepta_carta], 0.0
    e.contactos[acepta_carta] += P.RED_GANA["cambio"]

    emp0, ces0, sab0, empr0 = (e.sit == k for k in (EMP, CES, SAB, EMPR))
    ingreso_anual, meses_ces = np.zeros(n), np.zeros(n)
    red = factor_red(e.contactos)
    ia_oferta, ia_despido = factores_ia(e, ctx)
    h_encontrar = -np.log(1 - P.ENCONTRAR[tr]) * red * ia_oferta * (1 + P.ATRIBUTOS["hab_oferta"] * (e.habilidad - 50))
    ruido = np.exp(P.RUIDO * z("ruido"))
    sueldo_antes = efectivo()

    # 2. con empleo: despido, oferta y ascenso compiten; ocurre el primero
    atr = P.ATRIBUTOS
    mult_tam = np.array([P.MULT_TAM[k] for k in TAMANOS])[e.tam]
    antig = np.where(e.antig < 1, P.ANTIG_NUEVO, np.where(e.antig >= 5, P.ANTIG_VIEJO, 1.0))
    h_d = (P.DESPIDO[tr] * e.mult_rubro * mult_tam * antig * ia_despido * np.exp(P.B_DESP_C * pf.z("C"))
           * np.where(e.energia < 30, 1.3, 1.0) * np.where(e.burnout_prev, 1.3, 1.0))
    h_d = h_d * np.clip(1 - atr["rep_riesgo"] * (e.reputacion - 50), 0.6, 1.4)
    por_habilidad = 1 + atr["hab_oferta"] * (e.habilidad - 50)
    h_o = P.CAMBIO_EMPLEADOR[tr] * P.OFERTA_FACTOR * np.where(i.busca, P.BUSCA_MULT, 1.0) * red * ia_oferta * por_habilidad
    if ctx.jugador:   # en tu turno solo te cambias si lo eliges: buscando pega o aceptando la oferta del año
        h_o = np.where(i.busca, h_o, 0.0)
    h_a = (np.array(P.ASCENSO)[e.nivel] * np.where(i.horas >= 50, P.ASC_HORAS, 1.0) * np.exp(P.B_ASC_AMB * pf.ambicion)
           * np.where(e.postgrado, P.ASC_POSTGRADO, 1.0) * (1 + atr["hab_ascenso"] * (e.habilidad - 50))
           * np.where(i.tu_gente, P.ACCIONES["gente_ascenso"], 1.0))
    t_d, t_o, t_a = reloj("t_despido", h_d), reloj("t_oferta", h_o), reloj("t_ascenso", h_a)
    primero = np.minimum(np.minimum(t_d, t_o), t_a)
    despido = emp0 & (t_d < 1) & (t_d == primero)
    oferta = emp0 & (t_o < 1) & (t_o == primero)
    asciende = emp0 & (t_a < 1) & (t_a == primero)

    # cupo de ascenso del año: quien postula se la juega ahí y no espera el ascenso de siempre
    postula = i.postula & emp0 & cupo_del_anio(e, ctx)
    p0, p_attr, p_amb = P.CARTAS["postular"]
    p_post = np.clip(p0 + p_attr * (e.reputacion - 50) + p_attr * (e.habilidad - 50) + p_amb * pf.ambicion, 0.08, 0.85)
    p_post = p_post * np.array(P.CARTAS["postular_nivel"])[e.nivel]   # mientras más arriba, más difícil
    gana = postula & ~despido & (u("postula") < p_post)
    asciende = (asciende & ~postula) | gana
    t_a = np.where(gana, 0.5, t_a)

    m_oferta = P.M_SD * z("m_oferta")
    acepta = oferta & (m_oferta > e.m + np.where(i.busca, P.UMBRAL_ACTIVO, P.UMBRAL_PASIVO))
    _nuevo_empleo(e, acepta, m_oferta, ctx, "oferta", ev, voluntario=True)

    alza = np.maximum(P.ASC_ALZA + 0.02 * z("alza"), 0.03)
    e.sueldo[asciende] *= 1 + alza[asciende]
    e.nivel[asciende] = np.minimum(e.nivel[asciende] + 1, 4)
    a_jefatura = (asciende & (e.nivel >= 3) & ~tb.es_directivo[e.ocup] & (tb.jefatura_dest[e.ocup] >= 0)
                  & (u("a_jefatura") < P.ASC_A_JEFATURA))
    e.ocup[a_jefatura] = tb.jefatura_dest[e.ocup[a_jefatura]]

    pide = i.pide & emp0 & ~despido
    aumento = pide & (u("aumento") < P.AUMENTO_OK[pf.sexo] * np.exp(P.B_AUM_A * pf.z("A")) * (1 + atr["rep_aumento_p"] * (e.reputacion - 50)))
    e.sueldo[aumento] *= 1 + P.AUMENTO_ALZA

    sigue = emp0 & ~despido
    frac = np.where(acepta, t_o, np.where(asciende, t_a, np.where(aumento, 0.5, 1.0)))   # parte del año con el sueldo viejo
    ingreso_anual[sigue] = (12 * (frac * sueldo_antes + (1 - frac) * efectivo()) * ruido)[sigue]

    # despido: indemnización, seguro y búsqueda dentro del mismo año
    tau = reloj("busca_tras_despido", h_encontrar)
    reempleo = despido & (t_d + tau < 1)
    indemnizacion = np.where(e.antig >= 1, np.minimum(np.floor(e.antig), 11), 0) * sueldo_antes
    mc = np.where(reempleo, tau, 1 - t_d) * 12
    meses_ces[despido] = mc[despido]
    e.cicatriz[reempleo] = P.CICATRIZ
    _nuevo_empleo(e, reempleo, P.M_REEMPLEO + P.M_SD * z("m_reempleo"), ctx, "reempleo", ev, voluntario=False)
    ing = (12 * t_d * sueldo_antes + np.where(reempleo, 12 * (1 - t_d - tau) * efectivo(), 0.0)
           + indemnizacion + P.SEGURO * sueldo_antes * mc)
    ingreso_anual[despido] = ing[despido]
    queda = despido & ~reempleo
    e.sit[queda] = CES
    e.anios_ces[queda], e.hueco_vol[queda], e.origen_emp[queda] = 0, False, False

    # 3. sin trabajo al empezar el año: búsqueda
    baja = i.baja & ces0
    h_f = (h_encontrar * np.where(e.anios_ces >= 1, P.DURACION_DEP, 1.0) * np.where(e.hueco_vol, P.HUECO_VOLUNTARIO, 1.0)
           * np.where(baja, P.BAJA_PRETENSION[0], 1.0))
    tau2 = reloj("busca", h_f)
    halla = ces0 & (tau2 < 1)
    cic = np.where(e.origen_emp, 0.0, np.where(e.hueco_vol, 0.5 * P.CICATRIZ, P.CICATRIZ) + P.CICATRIZ_ANUAL * e.anios_ces)
    e.cicatriz[halla] = cic[halla]
    e.sueldo[baja & halla] *= P.BAJA_PRETENSION[1]
    _nuevo_empleo(e, halla, P.M_REEMPLEO + P.M_SD * z("m_busca"), ctx, "busca", ev, voluntario=False)
    e.sit[halla] = EMP
    ingreso_anual[halla] = (12 * (1 - tau2) * efectivo())[halla]
    meses_ces[ces0] = np.where(halla, 12 * tau2, 12.0)[ces0]
    e.anios_ces[ces0 & ~halla] += 1
    e.hueco_vol[halla], e.origen_emp[halla], e.anios_ces[halla] = False, False, 0

    # 4. pausa (sabático o cuidado de un hijo): el año siguiente vuelve a buscar
    e.sit[sab0] = CES
    e.hueco_vol[sab0], e.anios_ces[sab0], e.origen_emp[sab0] = True, 0, False

    # 5. emprendimiento
    ing_emp = (e.sueldo * P.EMP_MEDIANA * np.exp(P.EMP_SD_Q * e.emp_q + P.EMP_SD_T * z("emp_t"))
               * np.where(e.emp_anios == 0, P.EMP_RAMPA, 1.0))
    ingreso_anual[empr0] = (12 * ing_emp)[empr0]
    h_x = (np.where(e.emp_anios < 2, P.EMP_SALIDA_12, P.EMP_SALIDA_3) * np.exp(P.B_EMP_SALIDA_A * pf.z("A"))
           * (1 + 0.1 * pf.riesgo**2) * np.where(ing_emp > e.sueldo, 0.5, 1.2))
    cierra = empr0 & (u("emp_cierra") < 1 - np.exp(-h_x))
    e.sit[cierra] = CES
    e.origen_emp[cierra], e.anios_ces[cierra], e.hueco_vol[cierra] = True, 0, False
    e.emp_anios[empr0] += 1

    # 6. reconversión a otra ocupación (habilidades transferibles)
    quiere = (i.reconv >= 0) & np.isin(e.sit, (EMP, CES)) & (i.reconv != e.ocup)
    dest = np.where(quiere, i.reconv, e.ocup)
    afin = tb.afinidad[e.ocup, dest]
    por_nivel = np.where(tb.es_directivo[dest] & ~tb.es_directivo[e.ocup], np.array(P.RECONV_DIRECTIVO)[e.nivel], 1.0)
    logra = quiere & (u("reconv") < (P.RECONV_BASE + P.RECONV_AFIN * afin) * por_nivel)
    dlog = P.RECONV_REL * np.log(tb.rel[dest] / tb.rel[e.ocup]) - P.RECONV_PEN * (1 - afin)
    e.sueldo[logra] *= np.exp(dlog[logra])
    baja_nivel = logra & (afin < 0.5)
    e.nivel[baja_nivel] = np.maximum(e.nivel[baja_nivel] - 1, 0)
    e.ocup[logra] = dest[logra]
    e.antig[logra], e.m[logra] = 0.0, 0.0
    e.empresa[logra] = elegir_empresa(e.rubro, e.tam, u("reconv_emp"), e.empresa)[logra]
    e.contactos[logra] += P.RED_GANA["cambio"]
    entra = logra & (e.sit == CES)
    e.sit[entra] = EMP
    e.hueco_vol[entra], e.origen_emp[entra], e.anios_ces[entra], e.cicatriz[entra] = False, False, 0, 0.0

    # 7. magíster
    estudia = e.estudia > 0
    e.estudia[estudia] -= 1
    titulo = estudia & (e.estudia == 0)
    e.postgrado[titulo] = True
    premio = np.maximum(P.MAG_PREMIO + P.MAG_PREMIO_SD * z("mag_premio"), -0.02)
    e.sueldo[titulo] *= 1 + premio[titulo]

    # 8. cierre del año: crecimiento del sueldo y contadores
    trabaja = e.sit == EMP
    golpe = np.where(u("shock_p") < P.SHOCK_P, P.SHOCK_SD * z("shock"), 0.0)
    e.sueldo *= np.exp(tb.crecimiento_edad(pf.edu, e.edad) - P.DRIFT_DESCUENTO + P.REAJUSTE[0] + P.REAJUSTE[1] * z("reajuste")
                       + np.where(trabaja, golpe, 0.0))
    e.antig = np.where(trabaja, e.antig + 1, 0.0)
    e.cicatriz *= P.CICATRIZ_DECAE
    e.penal_hijo = np.maximum(e.penal_hijo - P.HIJO_PENAL_MUJER / 2, 0.0)
    e.horas = np.where(emp0, i.horas, np.where(empr0, np.maximum(i.horas, 55.0), 0.0))
    # trabajos extra: un porcentaje del sueldo si tienes empleo, un ingreso de subsistencia si no
    acc = P.ACCIONES
    ingreso_anual += 12 * e.sueldo * np.where(i.pituto & emp0, acc["pituto_ingreso"], np.where(i.pituto & ces0, acc["pituto_cesante"], 0.0))
    e.ingreso, e.meses_ces = ingreso_anual / 12, meses_ces
    ev.update(
        pausa=sab0, emprende=emprende, cierra_emp=cierra | cierra_vol, cambio=acepta, ascenso=asciende, a_jefatura=a_jefatura,
        aumento=aumento, aumento_no=pide & ~aumento, despido=despido, reempleo_mismo_anio=reempleo, encuentra=halla,
        reconv_ok=logra, reconv_no=quiere & ~logra, estudia=estudia, titulo=titulo,
        oferta_aceptada=acepta_carta, postula_ok=gana, postula_no=postula & ~gana & ~despido,
    )
