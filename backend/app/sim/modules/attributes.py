"""Atributos del gemelo que no son plata ni ánimo: habilidades, reputación y salud."""

import numpy as np

from app.sim.params import P
from app.sim.state import EMP


def atributos(e, i, ctx, ev):
    a = P.ATRIBUTOS
    trabaja = e.horas > 0
    cambio = ev["cambio"] | ev["oferta_aceptada"] | ev["reconv_ok"]
    e.habilidad = np.clip(
        e.habilidad + a["hab_trabajo"] * trabaja + a["hab_curso"] * i.capacita + a["hab_estudio"] * ev["estudia"]
        + a["hab_cambio"] * cambio - a["hab_olvido"] * ~trabaja, 0, 100)

    nuevo_lugar = cambio | ev["reempleo_mismo_anio"] | ev["encuentra"]
    rep = np.where(nuevo_lugar, e.reputacion * a["rep_cambio"], e.reputacion)   # parte de tu fama se queda en la empresa anterior
    e.reputacion = np.clip(
        rep + a["rep_anual"] * (trabaja & (e.antig >= 1)) + a["rep_horas"] * ((e.horas >= 55) & (e.sit == EMP))
        + a["rep_ascenso"] * ev["ascenso"] + a["rep_aumento"] * ev["aumento"] + a["rep_red"] * i.networking
        - a["rep_despido"] * ev["despido"] - a["rep_burnout"] * e.burnout_prev, 0, 100)

    e.salud = np.clip(
        e.salud - a["salud_edad"] * (e.edad >= 30) - a["salud_horas"] * (e.horas >= 55) - a["salud_agotada"] * (e.energia < 35)
        - a["salud_burnout"] * e.burnout_prev + a["salud_cuidarte"] * i.cuida
        + a["salud_descanso"] * (ev["pausa"] | (trabaja & (e.horas <= 40))), 0, 100)
    problema = (e.salud < a["salud_umbral"]) & (ctx.suerte.u(e.t, "salud") < a["salud_p"])
    e.ingreso = np.where(problema & (e.sit == EMP), np.maximum(e.ingreso - e.sueldo / 12, 0), e.ingreso)   # un mes de licencia sin sueldo completo
    e.energia = np.where(problema, np.maximum(e.energia - 10, 0), e.energia)
    e.salud = np.where(problema, e.salud + 5, e.salud)   # el susto obliga a tratarse
    ev["problema_salud"] = problema
