"""Parámetros del mercado laboral estimados con la EPS VIII ronda (2023-2024), historia laboral.

Uso: paneles_eps.py <carpeta BBDD_VIVOS> <carpeta FACT_EXP> <salida.json>

Base: MODULO_B_HISTORIA_LABORAL.dta (episodios con inicio, término, situación, tipo de empleo,
motivo de término y sueldo líquido mensual promedio b12), MODULO_A (edad a9, sexo a8),
MODULO_I (estado civil, hijos), Factor_XS_EPS_2023 (factor_XS). Todo ponderado con factor_XS.

Reglas de construcción (heredadas de scripts/paneles/eps_main.py):
- Fechas en meses; mes faltante -> junio. Fecha de entrevista = máximo término/inicio del historial.
- El primer episodio cronológico de cada persona parte en la entrevista anterior (2015-16 o 2019-20)
  o en la entrada a la muestra: su inicio real es desconocido. Para todo lo que depende de la
  antigüedad o de la duración se usan solo episodios con inicio observado (no el primero).
- Episodio vigente a la entrevista = censurado.
"""

import sys, json
import numpy as np
import pandas as pd
import pyreadstat
import statsmodels.api as sm

B, F, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
rd = lambda p, **k: pyreadstat.read_dta(p, apply_value_formats=False, **k)[0]  # noqa: E731
rng = np.random.default_rng(20261121)

h = rd(B + '/MODULO_B_HISTORIA_LABORAL.dta')
A = rd(B + '/MODULO_A_ENTREVISTADO.dta', usecols=['folio_n20', 'a8', 'a9', 'a12_n', 'a11'])
W = rd(F + '/Factor_XS_EPS_2023.dta')[['folio_n20', 'factor_XS']]
I = rd(B + '/MODULO_I_ENTREVISTADO.dta')
Hj = rd(B + '/MODULO_I_HIJOS.dta')


def ym(y, m):
    y = y.where((y > 1900) & (y < 2030)); mm = m.where(m.between(1, 12), 6)
    return y * 12 + (mm - 1)


h['s'] = ym(h.b2_a_inicio_anio, h.b2_a_inicio_mes)
h['e'] = ym(h.b2_a_termino_anio, h.b2_a_termino_mes)
h['mes_imp'] = ~h.b2_a_termino_mes.between(1, 12)
g = h.groupby('folio_n20')
h['iv'] = g.e.transform('max').combine(g.s.transform('max'), np.fmax)
h = h[h.s.notna()].copy()
h['e'] = h.e.fillna(h.iv)
h = h.sort_values(['folio_n20', 's', 'e']).reset_index(drop=True)
h['seq'] = h.groupby('folio_n20').cumcount()
h['nseq'] = h.groupby('folio_n20').seq.transform('max')
h['cens'] = (h.seq == h.nseq) & (h.e >= h.iv - 1)
h['obs_start'] = h.seq > 0
h = h.merge(A, on='folio_n20', how='left').merge(W, on='folio_n20', how='left')
h = h[h.factor_XS.notna() & h.a9.notna()].copy()
h['w'] = h.factor_XS
h['birth'] = h.iv - h.a9 * 12 - 6
h['ventana0'] = h.groupby('folio_n20').s.transform('min')   # inicio de la ventana de historia (≈ entrevista anterior)

mot = h.b22.where(h.b22 != 12, h.b22_e_cod.where(h.b22_e_cod.between(2, 11), 12))
cat = {2: 'mutuo_acuerdo', 3: 'renuncia', 8: 'renuncia_mejor_trabajo', 4: 'fin_contrato', 5: 'despido_imputable',
       6: 'despido_necesidades', 7: 'cierre', 11: 'fuerza_mayor', 9: 'salud', 10: 'pension', 12: 'otra'}
h['mot'] = mot.map(cat).fillna('nr')
INV = ['despido_imputable', 'despido_necesidades', 'cierre', 'fuerza_mayor']
VOL = ['renuncia', 'renuncia_mejor_trabajo']
h['b12n'] = pd.to_numeric(h.b12, errors='coerce').where(lambda x: (x > 9) & (x < 3e7))
h['b13n'] = pd.to_numeric(h.b13, errors='coerce').where(lambda x: (x > 0) & (x <= 100))
for c in ['b2a_so', 'b2a_ed', 'b8', 's', 'e', 'mot', 'b12n', 'b13n', 'cens']:
    h['next_' + c] = h.groupby('folio_n20')[c].shift(-1)
    h['prev_' + c] = h.groupby('folio_n20')[c].shift(1)
h['next_gap'] = h.next_s - h.e
h['prev_gap'] = h.s - h.prev_e

TR = [17, 29, 44, 59]; LT = ['18-29', '30-44', '45-59']
START = 2016 * 12
ASAL = [3, 4, 5, 6, 8]
INDEP = [1, 2]
R = {'fuente': 'EPS VIII ronda (2023-2024), módulo B historia laboral; factor_XS (Factor_XS_EPS_2023)',
     'script': 'scripts/modelo/paneles_eps.py'}


def expand(sp, start=START):
    """Persona-mes de exposición de cada episodio desde max(inicio, start) hasta el término."""
    sp = sp.copy()
    sp['s0'] = sp.s.clip(lower=start)
    sp = sp[sp.e >= sp.s0]
    nm = (sp.e - sp.s0 + 1).astype(int).values
    idx = np.repeat(sp.index.values, nm)
    off = np.concatenate([np.arange(n) for n in nm])
    M = pd.DataFrame({'i': idx, 't': sp.s0.values.repeat(nm) + off})
    M['last'] = M.t == sp.e.values.repeat(nm)
    return M


def boot_ratio(df, fnum, fden, reps=300):
    """IC 95% por bootstrap de personas para un cociente de tasas."""
    ids = df.folio_n20.unique(); grp = df.groupby('folio_n20').indices; vals = []
    for _ in range(reps):
        s = rng.choice(ids, len(ids)); ix = np.concatenate([grp[k] for k in s]); d = df.iloc[ix]
        try:
            vals.append(fnum(d) / fden(d))
        except ZeroDivisionError:
            pass
    return [round(float(np.nanpercentile(vals, 2.5)), 3), round(float(np.nanpercentile(vals, 97.5)), 3)]


# ============ 1. Despido por antigüedad (asalariados, inicio observado) ============
emp = h[(h.b2a_so == 1) & h.b8.isin(ASAL) & (h.e >= START)].copy()
emp['ev_inv'] = (~emp.cens) & emp.mot.isin(INV)
emp['ev_invfc'] = (~emp.cens) & emp.mot.isin(INV + ['fin_contrato'])
M = expand(emp)
M = M.join(emp[['folio_n20', 's', 'birth', 'w', 'ev_inv', 'ev_invfc', 'obs_start', 'b8']], on='i')
M['ten'] = (M.t - M.s) / 12
M['tb'] = pd.cut(M.ten, [-1, 0.999, 4.999, 99], labels=['<1', '1-4', '5+'])
M['edad'] = pd.cut((M.t - M.birth) / 12, TR, labels=LT)
M['anio'] = M.t // 12
M['d_inv'] = M['last'] & M.ev_inv; M['d_invfc'] = M['last'] & M.ev_invfc
M = M[M.edad.notna()]


def cells(Mx, keys):
    c = Mx.groupby(['i'] + keys, observed=True).agg(expo=('t', 'size'), d_inv=('d_inv', 'sum'), d_invfc=('d_invfc', 'sum'),
                                                    w=('w', 'first'), folio_n20=('folio_n20', 'first')).reset_index()
    c['expo'] = c.expo / 12
    return c


def poisson(c, ev, terms, ref):
    X = pd.get_dummies(c[terms].astype(str), drop_first=False).astype(float)
    X = X.drop(columns=[f'{t}_{r}' for t, r in ref.items()])
    X = sm.add_constant(X)
    m = sm.GLM(c[ev], X, family=sm.families.Poisson(), offset=np.log(c.expo), var_weights=c.w).fit(
        cov_type='cluster', cov_kwds={'groups': pd.factorize(c.folio_n20)[0]})
    return m


def wrate(c, ev):
    return float((c[ev] * c.w).sum() / (c.expo * c.w).sum())


Mo = M[M.obs_start]
c_ten = cells(Mo, ['tb', 'edad'])
c_ten['anio_g'] = 'x'
R['antiguedad'] = {'nota': 'Asalariados (b8 3,4,5,6,8), episodios con inicio observado, exposición 2016-2024. Poisson ponderado con factor_XS, '
                           'controla tramo de edad, EE agrupados por persona. razon_vs_1_4 = tasa del tramo / tasa de 1-4 años; '
                           'razon_vs_promedio = tasa del tramo / tasa media de todos los años-persona del mismo grupo.'}
for ev in ['d_inv', 'd_invfc']:
    m = poisson(c_ten, ev, ['tb', 'edad'], {'tb': '1-4', 'edad': '30-44'})
    out = {'n_personas': int(c_ten.folio_n20.nunique()), 'anios_persona': round(float(c_ten.expo.sum()), 0),
           'eventos': int(c_ten[ev].sum())}
    for tb in ['<1', '5+']:
        b, se = m.params[f'tb_{tb}'], m.bse[f'tb_{tb}']
        out[f'razon_{tb}_vs_1_4'] = {'valor': round(float(np.exp(b)), 3), 'ic95': [round(float(np.exp(b - 1.96 * se)), 3), round(float(np.exp(b + 1.96 * se)), 3)]}
    raw = {}
    for tb in ['<1', '1-4', '5+']:
        cc = c_ten[c_ten.tb == tb]; raw[tb] = {'tasa_anual': round(wrate(cc, ev), 4), 'anios_persona': round(float(cc.expo.sum()), 0), 'eventos': int(cc[ev].sum())}
    tot = wrate(c_ten, ev)
    out['tasas_brutas'] = raw; out['tasa_media'] = round(tot, 4)
    for tb in raw: raw[tb]['razon_vs_promedio'] = round(raw[tb]['tasa_anual'] / tot, 3)
    R['antiguedad'][ev.replace('d_', '')] = out

# todos los asalariados (incluye primeros episodios) para la tasa media por edad
c_all = cells(M, ['edad'])
R['despido_asalariados_por_edad'] = {
    'nota': 'Asalariados, todos los episodios desde 2016 (incluye los de inicio no observado). Despido = imputable + necesidades de la empresa + cierre + fuerza mayor.',
    **{tb: {'tasa_inv': round(wrate(c_all[c_all.edad == tb], 'd_inv'), 4),
            'ee_inv': round(float(np.sqrt((c_all[c_all.edad == tb].d_inv * c_all[c_all.edad == tb].w ** 2).sum()) / (c_all[c_all.edad == tb].expo * c_all[c_all.edad == tb].w).sum()), 4), 'tasa_inv_mas_fin_contrato': round(wrate(c_all[c_all.edad == tb], 'd_invfc'), 4),
            'anios_persona': round(float(c_all[c_all.edad == tb].expo.sum()), 0)} for tb in LT}}

# ============ 2. Sector público vs privado ============
Ms = M[M.b8.isin([3, 4])].copy(); Ms['sector'] = np.where(Ms.b8 == 3, 'publico', 'privado')
c_sec = cells(Ms, ['sector', 'edad'])
R['sector'] = {'nota': 'Empleados públicos (b8=3) vs privados (b8=4), todos los episodios 2016-2024. razon = exp(coef) de Poisson ponderado con tramo de edad; '
                       'mult_vs_media = tasa pública / tasa media de todos los asalariados (b8 3,4,5,6,8) estandarizada por edad.'}
for ev in ['d_inv', 'd_invfc']:
    m = poisson(c_sec, ev, ['sector', 'edad'], {'sector': 'privado', 'edad': '30-44'})
    b, se = m.params['sector_publico'], m.bse['sector_publico']
    # estandarización directa a la estructura de edad de todos los asalariados
    wedad = c_all.groupby('edad', observed=True).apply(lambda x: (x.expo * x.w).sum()); wedad = wedad / wedad.sum()
    std = lambda cc: sum(wedad[tb] * wrate(cc[cc.edad == tb], ev) for tb in LT)  # noqa: E731
    pub, priv, todos = std(c_sec[c_sec.sector == 'publico']), std(c_sec[c_sec.sector == 'privado']), std(c_all)
    R['sector'][ev.replace('d_', '')] = {
        'razon_publico_vs_privado': {'valor': round(float(np.exp(b)), 3), 'ic95': [round(float(np.exp(b - 1.96 * se)), 3), round(float(np.exp(b + 1.96 * se)), 3)]},
        'tasa_publico_std': round(pub, 4), 'tasa_privado_std': round(priv, 4), 'tasa_asalariados_std': round(todos, 4),
        'mult_publico_vs_media': round(pub / todos, 3), 'mult_privado_vs_media': round(priv / todos, 3),
        'eventos_publico': int(c_sec[c_sec.sector == 'publico'][ev].sum()), 'anios_persona_publico': round(float(c_sec[c_sec.sector == 'publico'].expo.sum()), 0),
        'eventos_privado': int(c_sec[c_sec.sector == 'privado'][ev].sum())}
    c_sx = cells(M.assign(sector=np.select([M.b8 == 3, M.b8 == 4], ['publico', 'privado'], 'otro')), ['sector', 'edad'])
    R['sector'][ev.replace('d_', '')]['mult_publico_ic95'] = boot_ratio(
        c_sx, lambda d: std(d[d.sector == 'publico']), lambda d: std(d), reps=200)

# ============ 3. Búsqueda: dependencia de la duración y origen de la cesantía ============
def episodios(mask):
    """Junta episodios consecutivos que cumplen `mask` (p. ej. cesante seguido de cesante) en uno solo.
    Los atributos next_* vienen del último episodio y prev_* del primero."""
    x = h.assign(_m=mask)
    x['_nuevo'] = x._m & ~x.groupby('folio_n20')._m.shift(1).fillna(False).astype(bool)
    x['_ep'] = x.groupby('folio_n20')._nuevo.cumsum()
    x = x[x._m]
    g = x.groupby(['folio_n20', '_ep'])
    first = g.head(1).set_index(['folio_n20', '_ep']); last = g.tail(1).set_index(['folio_n20', '_ep'])
    ep = first[['seq', 's', 'obs_start', 'w', 'birth'] + [c for c in first.columns if c.startswith('prev_')]].copy()
    ep['e'] = last.e; ep['cens'] = last.cens; ep['mes_imp'] = last.mes_imp; ep['last_seq'] = last.seq
    for c in [c for c in last.columns if c.startswith('next_')]:
        ep[c] = last[c]
    ep['n_tramos'] = g.size()
    return ep.reset_index()


U = episodios(h.b2a_so.isin([2, 3]))
U = U[U.obs_start & (U.s >= START)].copy()
U['dur'] = (U.e - U.s).clip(lower=1)
U['a_empleo'] = (~U.cens) & (U.next_b2a_so == 1) & (U.next_gap <= 1)
U['origen'] = np.select(
    [(U.prev_b2a_so == 1) & U.prev_mot.isin(INV) & (U.prev_gap <= 1),
     (U.prev_b2a_so == 1) & U.prev_mot.isin(VOL + ['mutuo_acuerdo']) & (U.prev_gap <= 1),
     (U.prev_b2a_so == 1) & (U.prev_mot == 'fin_contrato') & (U.prev_gap <= 1),
     (U.prev_b2a_so == 4) & (U.prev_b2a_ed != 6) & (U.prev_gap <= 1)],
    ['despido', 'renuncia', 'fin_contrato', 'tras_inactividad'], default='otro')
# la inactividad previa ¿venía de un empleo dejado por voluntad propia? (pausa elegida)
hh = h.set_index(['folio_n20', 'seq'])
pp = U.apply(lambda r: hh.loc[(r.folio_n20, r.seq - 2)] if r.seq >= 2 else None, axis=1)
U['pp_so'] = [x.b2a_so if x is not None else np.nan for x in pp]
U['pp_mot'] = [x.mot if x is not None else None for x in pp]
U.loc[(U.origen == 'tras_inactividad') & (U.pp_so == 1) & U.pp_mot.isin(VOL + ['mutuo_acuerdo']), 'origen'] = 'tras_pausa_voluntaria'
U['edad'] = pd.cut((U.s - U.birth) / 12, TR, labels=LT)


def piece(df, cuts=(0, 12, 24, 999), ev='a_empleo'):
    """Tasas mensuales por tramo de duración (constantes por tramo), ponderadas."""
    out = []
    for lo, hi in zip(cuts[:-1], cuts[1:]):
        expo = (df.dur.clip(upper=hi) - lo).clip(lower=0)
        d = df[ev] & (df.dur > lo) & (df.dur <= hi)
        out.append(((d * df.w).sum(), (expo * df.w).sum(), int(d.sum()), float(expo.sum())))
    return out


def hr(df, ev='a_empleo'):
    p = piece(df, ev=ev)
    return (p[1][0] / p[1][1]) / (p[0][0] / p[0][1])


def h12(df):
    p = piece(df, cuts=(0, 12)); return p[0][0] / p[0][1]


pc = piece(U)
R['duracion_cesantia'] = {
    'nota': 'Episodios de cesantía o búsqueda (b2a_so 2,3; episodios de búsqueda consecutivos se juntan en uno) con inicio observado desde 2016. Salida = siguiente episodio es trabajo y empieza <=1 mes después. '
            'Tasa mensual constante por tramo de duración; ponderado. razon = tasa meses 12-23 / tasa meses 0-11; equivale al multiplicador del motor sobre el riesgo anual.',
    'n_episodios': int(len(U)), 'n_salidas_a_empleo': int(U.a_empleo.sum()), 'n_censurados': int(U.cens.sum()),
    'episodios_formados_por_varios_tramos': int((U.n_tramos > 1).sum()),
    'tasa_mensual': {f'{lo}-{hi}': round(a / b, 4) for (a, b, _, _), lo, hi in zip(pc, [0, 12, 24], [11, 23, 'mas'])},
    'eventos_por_tramo': [x[2] for x in pc],
    'meses_persona_por_tramo': [round(x[3]) for x in pc],
    'prob_encontrar_en_12m': {'anio_1': round(1 - np.exp(-12 * pc[0][0] / pc[0][1]), 3), 'anio_2': round(1 - np.exp(-12 * pc[1][0] / pc[1][1]), 3)},
    'razon_anio2_vs_anio1': {'valor': round(hr(U), 3), 'ic95': boot_ratio(U, lambda d: hr(d), lambda d: 1.0)},
    'por_edad': {tb: round(hr(U[U.edad == tb]), 3) for tb in LT},
    'termino_con_mes_imputado': round(float(U.mes_imp.mean()), 3),
}

# por origen (primeros 12 meses)


orig = {}
for o in ['despido', 'fin_contrato', 'renuncia', 'tras_inactividad', 'tras_pausa_voluntaria', 'otro']:
    d = U[U.origen == o]
    if len(d) == 0:
        continue
    p = piece(d, cuts=(0, 12))
    orig[o] = {'n_episodios': int(len(d)), 'salidas_a_empleo_12m': p[0][2], 'tasa_mensual_0_11': round(p[0][0] / p[0][1], 4),
               'prob_12m': round(1 - np.exp(-12 * p[0][0] / p[0][1]), 3)}
base = U[U.origen == 'despido']
for o in orig:
    d = U[U.origen.isin([o, 'despido'])]
    orig[o]['razon_vs_despido'] = round(orig[o]['tasa_mensual_0_11'] / orig['despido']['tasa_mensual_0_11'], 3)
    if o != 'despido':
        orig[o]['ic95'] = boot_ratio(d, lambda x, o=o: h12(x[x.origen == o]), lambda x: h12(x[x.origen == 'despido']))
# probabilidad de encontrar empleo en 12 meses por edad (solo salidas a trabajo) y destino de las salidas
enc = {}
for tb in LT + ['todos']:
    x = U if tb == 'todos' else U[U.edad == tb]
    p = piece(x, cuts=(0, 12))
    enc[tb] = {'prob_12m': round(1 - np.exp(-12 * p[0][0] / p[0][1]), 3), 'n_episodios': int(len(x)), 'salidas_a_empleo_12m': p[0][2],
               'ic95': boot_ratio(x, lambda d: 1 - np.exp(-12 * h12(d)), lambda d: 1.0, reps=200)}
fin = U[~U.cens]
enc['destino_de_las_salidas'] = (fin.groupby(np.where(fin.a_empleo, 'trabajo', np.where(fin.next_b2a_so == 4, 'inactividad', 'otro'))).w.sum() / fin.w.sum()).round(3).to_dict()
enc['nota'] = ('Riesgo de pasar a un trabajo en los primeros 12 meses de búsqueda; las salidas a inactividad cuentan como censura (riesgo neto). '
               'Comparar con ENCONTRAR del motor, que salió de un Kaplan-Meier donde cualquier término del episodio de cesantía contaba como encontrar.')
R['encontrar_12m'] = enc

R['busqueda_por_origen'] = {'nota': 'Mismos episodios de búsqueda según lo que vino justo antes: despido (imputable, necesidades, cierre, fuerza mayor), fin de contrato, '
                                    'renuncia o mutuo acuerdo, un episodio de inactividad (no jubilación), y el subconjunto de esa inactividad que siguió a una renuncia '
                                    '(pausa elegida). Tasa de encontrar trabajo en los primeros 12 meses de búsqueda.', **orig}

# ============ 4. Pausas voluntarias (inactividad tras un empleo) ============
W1 = h[(h.b2a_so == 1) & (h.e >= START)].copy()
Mw = expand(W1).join(W1[['folio_n20', 'birth', 'w']], on='i')
Mw['edad'] = pd.cut((Mw.t - Mw.birth) / 12, TR, labels=LT)
expo_w = Mw[Mw.edad.notna()].groupby('edad', observed=True).apply(lambda x: x.w.sum() / 12)
expo_n = Mw[Mw.edad.notna()].groupby('edad', observed=True).size() / 12
T = W1[~W1.cens].copy()
T['edad'] = pd.cut((T.e - T.birth) / 12, TR, labels=LT)
T['a_inact'] = (T.next_b2a_so == 4) & (T.next_gap <= 1) & (T.next_b2a_ed != 6) & (T.mot != 'pension')
tipo = {4: 'estudiar', 7: 'cuidar_hijos', 12: 'embarazo', 18: 'cuidar_otros', 14: 'quehaceres', 8: 'licencia_medica', 10: 'enfermedad',
        11: 'otras_responsabilidades', 16: 'no_le_interesaba', 22: 'vacaciones_permiso', 28: 'otro', 88: 'nr', 99: 'nr'}
T['tipo'] = T.next_b2a_ed.map(tipo).fillna('otro')
T['vol'] = T.mot.isin(VOL + ['mutuo_acuerdo'])
T['j2j'] = (T.next_b2a_so == 1) & (T.next_gap <= 1)
T['j2j_vol'] = T.j2j & T.mot.isin(VOL)


def rate_by_age(mask):
    """Tasa anual ponderada por tramo; ee de Poisson con pesos: sqrt(sum w^2) / exposición ponderada."""
    out = {}
    for tb in LT:
        x = T[mask & (T.edad == tb)]
        out[tb] = round(float(x.w.sum() / expo_w[tb]), 4)
        out['ee_' + tb] = round(float(np.sqrt((x.w ** 2).sum()) / expo_w[tb]), 4)
    return out


R['pausas'] = {
    'nota': 'Ocupados (todo tipo de empleo) 2016-2024. Pausa = el empleo termina y el episodio siguiente (<=1 mes) es inactividad, excluye jubilación. '
            'Tasa anual por año-persona ocupado, ponderada. "pausa_voluntaria" = además el empleo terminó por renuncia o mutuo acuerdo.',
    'anios_persona_ocupado': {tb: round(float(expo_n[tb])) for tb in LT},
    'pausa_total': rate_by_age(T.a_inact), 'n_pausa_total': int(T.a_inact.sum()),
    'pausa_voluntaria': rate_by_age(T.a_inact & T.vol), 'n_pausa_voluntaria': int((T.a_inact & T.vol).sum()),
    'pausa_voluntaria_sin_estudio_ni_cuidado': rate_by_age(T.a_inact & T.vol & ~T.tipo.isin(['estudiar', 'cuidar_hijos', 'embarazo', 'cuidar_otros', 'licencia_medica', 'enfermedad'])),
    'tipo_de_inactividad_en_pausas_voluntarias': (T[T.a_inact & T.vol].groupby('tipo').w.sum() / T[T.a_inact & T.vol].w.sum()).round(3).to_dict(),
    'tipo_de_inactividad_en_todas_las_pausas': (T[T.a_inact].groupby('tipo').w.sum() / T[T.a_inact].w.sum()).round(3).to_dict(),
}
# duración de las pausas voluntarias (episodio de inactividad siguiente)
P = episodios((h.b2a_so == 4) & (h.b2a_ed != 6))
P = P[(P.prev_b2a_so == 1) & P.prev_mot.isin(VOL + ['mutuo_acuerdo']) & (P.prev_gap <= 1) & (P.s >= START)].copy()
P['dur'] = (P.e - P.s).clip(lower=1)


def km(dur, cens, w, ks=(6, 12, 24)):
    df = pd.DataFrame({'d': dur, 'c': cens, 'w': w}).dropna(); S = 1.0; surv = {}
    for t in sorted(df.d.unique()):
        atr = df[df.d >= t].w.sum(); ev = df[(df.d == t) & (~df.c)].w.sum()
        S *= 1 - ev / atr if atr > 0 else 1; surv[t] = S
    ts = sorted(surv)
    return {k: round(float(surv[max([t for t in ts if t <= k] or [ts[0]])]), 3) for k in ks}


R['pausas']['duracion_pausa_voluntaria_KM'] = {'n': int(len(P)), 'sigue_inactivo_a_meses': km(P.dur, P.cens, P.w),
                                               'destino_al_terminar': (P[~P.cens].groupby('next_b2a_so').w.sum() / P[~P.cens].w.sum()).round(3).rename(
                                                   {1.0: 'trabajo', 2.0: 'cesantia', 3.0: 'busca_1a_vez', 4.0: 'inactivo'}).to_dict()}
R['cambio_voluntario'] = {'nota': 'Cambio de empleador sin pasar por cesantía (<=1 mes) cuyo motivo de término fue renuncia o "encontró un mejor trabajo". Tasa anual por año-persona ocupado.',
                          'tasa': rate_by_age(T.j2j_vol), 'n': int(T.j2j_vol.sum()),
                          'tasa_j2j_cualquier_motivo': rate_by_age(T.j2j)}

# ============ 5. Trabajo independiente: entrada y salida ============
emp_all = h[(h.b2a_so == 1) & (h.e >= START)].copy()
asal = emp_all[emp_all.b8.isin(ASAL)].copy()
Ma = expand(asal).join(asal[['folio_n20', 'birth', 'w']], on='i')
Ma['edad'] = pd.cut((Ma.t - Ma.birth) / 12, TR, labels=LT)
ea_w = Ma[Ma.edad.notna()].groupby('edad', observed=True).w.sum() / 12
Ta = asal[~asal.cens].copy(); Ta['edad'] = pd.cut((Ta.e - Ta.birth) / 12, TR, labels=LT)
Ta['a_indep'] = (Ta.next_b2a_so == 1) & Ta.next_b8.isin(INDEP) & (Ta.next_gap <= 1)
Ta['a_empleador'] = Ta.a_indep & (Ta.next_b8 == 1)
# formal: el episodio independiente siguiente da boleta o factura
nxt_b11 = h.groupby('folio_n20').b11.shift(-1).reindex(Ta.index)
Ta['a_indep_formal'] = Ta.a_indep & nxt_b11.isin([1, 2])
ent = {}
for k in ['a_indep', 'a_empleador', 'a_indep_formal']:
    ent[k] = {tb: round(float(Ta[Ta[k] & (Ta.edad == tb)].w.sum() / ea_w[tb]), 4) for tb in LT}
    ent[k].update({'ee_' + tb: round(float(np.sqrt((Ta[Ta[k] & (Ta.edad == tb)].w ** 2).sum()) / ea_w[tb]), 4) for tb in LT})
    ent[k]['ee_todos'] = round(float(np.sqrt((Ta[Ta[k]].w ** 2).sum()) / ea_w.sum()), 4)
    ent[k]['todos'] = round(float(Ta[Ta[k]].w.sum() / ea_w.sum()), 4)
    ent[k]['n'] = int(Ta[k].sum())
# desde la cesantía: fracción de salidas de la búsqueda que van a independiente
Ux = h[(h.b2a_so == 2) & (h.s >= START) & ~h.cens & (h.next_b2a_so == 1) & (h.next_gap <= 1)]
R['independiente_entrada'] = {
    'nota': 'Asalariados 2016-2024: tasa anual de pasar directamente (<=1 mes) a un trabajo por cuenta propia o de empleador (b8 1,2). '
            'a_empleador = solo patrón/empleador; a_indep_formal = el trabajo independiente siguiente emite boleta o factura (b11 1,2).',
    'anios_persona_asalariado': round(float(Ma.w.count() / 12)), **ent,
    'desde_cesantia_share_salidas_a_independiente': round(float(Ux[Ux.next_b8.isin(INDEP)].w.sum() / Ux.w.sum()), 3), 'n_salidas_cesantia_a_trabajo': int(len(Ux))}

# episodios independientes: se juntan episodios independientes consecutivos (<=1 mes)
ind = h[(h.b2a_so == 1)].copy()
ind['es_ind'] = ind.b8.isin(INDEP)
ind = ind.sort_values(['folio_n20', 's'])
ind['prev_ind'] = ind.groupby('folio_n20').es_ind.shift(1).fillna(False).astype(bool)
ind['prev_e2'] = ind.groupby('folio_n20').e.shift(1)
ind['nuevo'] = ind.es_ind & ~(ind.prev_ind & ((ind.s - ind.prev_e2) <= 1))
ind = ind[ind.es_ind].copy()
ind['ep'] = ind.groupby('folio_n20').nuevo.cumsum()
Ep = ind.groupby(['folio_n20', 'ep']).agg(s=('s', 'first'), e=('e', 'last'), cens=('cens', 'last'), obs=('obs_start', 'first'),
                                          w=('w', 'first'), birth=('birth', 'first'), b8=('b8', 'first'), b11=('b11', 'first')).reset_index()
# un episodio independiente solo termina si lo que sigue no es otro independiente; el último episodio de la persona sin censura también cuenta
Ep = Ep[Ep.obs & (Ep.s >= START)].copy()
Ep['dur'] = (Ep.e - Ep.s).clip(lower=1)
Ep['edad'] = pd.cut((Ep.s - Ep.birth) / 12, TR, labels=LT)


def km_full(df):
    sv = km(df.dur, df.cens, df.w, ks=(12, 24, 36, 48, 60))
    out = {'n_episodios': int(len(df)), 'n_censurados': int(df.cens.sum()), 'sobrevive': sv}
    s12, s24, s60 = sv[12], sv[24], sv[60]
    out['salida_anio1'] = round(1 - s12, 3); out['salida_2_anios'] = round(1 - s24, 3); out['salida_5_anios'] = round(1 - s60, 3)
    out['riesgo_anual_anios_0_2'] = round(-np.log(s24) / 2, 3)
    out['riesgo_anual_anios_2_5'] = round(-np.log(s60 / s24) / 3, 3) if s60 > 0 else None
    return out


R['independiente_salida'] = {'nota': 'Episodios de trabajo independiente (cuenta propia o empleador; episodios independientes consecutivos se juntan) con inicio observado desde 2016. '
                                     'Kaplan-Meier ponderado; censura a la entrevista. riesgo_anual = -ln(S) anualizado, la misma forma que usa el motor (1-exp(-h)).',
                             'todos': km_full(Ep), 'empleador': km_full(Ep[Ep.b8 == 1]), 'cuenta_propia': km_full(Ep[Ep.b8 == 2]),
                             'formal_boleta_o_factura': km_full(Ep[Ep.b11.isin([1, 2])]),
                             'por_edad_al_iniciar': {tb: km_full(Ep[Ep.edad == tb]) for tb in LT}}
R['independiente_salida']['ic95_riesgo_2_5'] = boot_ratio(Ep, lambda d: -np.log(km(d.dur, d.cens, d.w, ks=(60,))[60] / km(d.dur, d.cens, d.w, ks=(24,))[24]) / 3, lambda d: 1.0, reps=200)
R['independiente_salida']['ic95_riesgo_0_2'] = boot_ratio(Ep, lambda d: -np.log(km(d.dur, d.cens, d.w, ks=(24,))[24]) / 2, lambda d: 1.0, reps=200)

# ============ 6. Sueldo al cambiar de empleo ============
wk = h[(h.b2a_so == 1)].copy()
wk['wseq'] = wk.groupby('folio_n20').cumcount()
nx = wk[['folio_n20', 'wseq', 's', 'e', 'b12n', 'b13n', 'b8', 'seq']].copy(); nx['wseq'] -= 1
Pr = wk.merge(nx, on=['folio_n20', 'wseq'], suffixes=('', '_B'))
Pr = Pr[(~Pr.cens) & Pr.b12n.notna() & Pr.b12n_B.notna() & (Pr.e >= START - 12)].copy()
Pr['gap'] = (Pr.s_B - Pr.e).clip(lower=0)
# qué hubo entre medio
between = h[['folio_n20', 'seq', 'b2a_so', 'b2a_ed']]
ent_rows = []
for r in Pr[['folio_n20', 'seq', 'seq_B']].itertuples(index=False):
    ent_rows.append((r.folio_n20, r.seq, r.seq_B))
mid = pd.DataFrame(ent_rows, columns=['folio_n20', 'a', 'b'])
bb = between.merge(mid, on='folio_n20')
bb = bb[(bb.seq > bb.a) & (bb.seq < bb.b)]
has_ces = bb[bb.b2a_so.isin([2, 3])].groupby(['folio_n20', 'a']).size()
has_ina = bb[(bb.b2a_so == 4) & (bb.b2a_ed != 6)].groupby(['folio_n20', 'a']).size()
key = list(zip(Pr.folio_n20, Pr.seq))
Pr['ces'] = [k in has_ces.index for k in key]; Pr['ina'] = [k in has_ina.index for k in key]
Pr['tipo'] = np.select([(Pr.gap <= 1) & ~Pr.ces & ~Pr.ina & Pr.mot.isin(VOL), (Pr.gap <= 1) & ~Pr.ces & ~Pr.ina,
                        Pr.ces & Pr.mot.isin(INV), Pr.ces & (Pr.mot == 'fin_contrato'), Pr.ces,
                        Pr.ina & ~Pr.ces & Pr.mot.isin(VOL + ['mutuo_acuerdo'])],
                       ['j2j_voluntario', 'j2j_otro', 'despido_cesantia', 'fincontrato_cesantia', 'otra_cesantia', 'pausa_voluntaria'], default='otro')
Pr['dlw'] = np.log(Pr.b12n_B) - np.log(Pr.b12n)
Pr['dlh'] = np.log(Pr.b12n_B / Pr.b13n_B) - np.log(Pr.b12n / Pr.b13n)
Pr['gap_anios'] = Pr.gap / 12
Pr['mA'] = ((Pr.s.clip(lower=Pr.ventana0) + Pr.e) / 2 // 12).astype(int).clip(lower=2014)
Pr['mB'] = ((Pr.s_B + Pr.e_B) / 2 // 12).astype(int)
Pr['edad'] = pd.cut((Pr.e - Pr.birth) / 12, TR, labels=LT)
Pr = Pr[Pr.edad.notna() & Pr.dlw.between(-3, 3)].copy()
X = pd.get_dummies(Pr[['tipo', 'edad']].astype(str)).astype(float).drop(columns=['tipo_j2j_voluntario', 'edad_30-44'])
X = pd.concat([X, pd.get_dummies(Pr.mA.astype(str), prefix='mA', drop_first=True).astype(float),
               pd.get_dummies(Pr.mB.astype(str), prefix='mB', drop_first=True).astype(float)], axis=1)
X['gap_ces'] = Pr.gap_anios * Pr.ces; X['gap_ina'] = Pr.gap_anios * (Pr.ina & ~Pr.ces)
X = sm.add_constant(X)
mw = sm.WLS(Pr.dlw, X, weights=Pr.w).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(Pr.folio_n20)[0]})


def co(name):
    return {'coef': round(float(mw.params[name]), 4), 'ee': round(float(mw.bse[name]), 4)}


def desc(d):
    q = np.percentile(d.dlw, [25, 50, 75])
    return {'n': int(len(d)), 'media': round(float(np.average(d.dlw, weights=d.w)), 4), 'mediana': round(float(q[1]), 4),
            'de': round(float(np.sqrt(np.cov(d.dlw, aweights=d.w))), 4), 'de_robusta_iqr': round(float((q[2] - q[0]) / 1.349), 4),
            'share_sube': round(float(np.average(d.dlw > 0, weights=d.w)), 3), 'share_igual': round(float(np.average(d.dlw == 0, weights=d.w)), 3),
            'gap_meses_mediana': float(np.median(d.gap))}


ct = mw.t_test('tipo_pausa_voluntaria - tipo_despido_cesantia = 0')
ct2 = mw.t_test('tipo_despido_cesantia - tipo_j2j_otro = 0')
R['sueldo_cambio'] = {
    'contraste_pausa_menos_despido': {'coef': round(float(ct.effect[0]), 4), 'ee': round(float(ct.sd[0][0]), 4)},
    'contraste_despido_menos_j2j_otro': {'coef': round(float(ct2.effect[0]), 4), 'ee': round(float(ct2.sd[0][0]), 4)},
    'nota': 'Pares de empleos consecutivos de la misma persona con sueldo líquido mensual promedio (b12) en ambos; el primero termina desde 2015. '
            'dlw = log(sueldo nuevo) - log(sueldo anterior). Tipos: j2j = el nuevo empieza <=1 mes después sin cesantía ni inactividad entre medio; '
            'despido_cesantia = término involuntario y episodio de cesantía entre medio; pausa_voluntaria = renuncia o mutuo acuerdo seguida de inactividad (no jubilación). '
            'Regresión WLS ponderada con factor_XS, efectos fijos del año medio de cada empleo (absorben inflación: b12 no dice en pesos de qué año), tramo de edad; '
            'EE agrupados por persona. gap_ces = pendiente por año sin trabajo entre empleos, cuando hubo cesantía.',
    'descriptivo': {t: desc(Pr[Pr.tipo == t]) for t in Pr.tipo.unique()},
    'descriptivo_toda_reinsercion_desde_cesantia': desc(Pr[Pr.ces]),
    'regresion_vs_j2j_voluntario': {'n': int(mw.nobs), **{k.replace('tipo_', ''): co(k) for k in X.columns if k.startswith('tipo_')},
                                    'gap_ces_por_anio': co('gap_ces'), 'gap_ina_por_anio': co('gap_ina'), 'constante_j2j_vol': co('const')},
}
# por hora
Ph = Pr[Pr.dlh.notna() & Pr.dlh.between(-3, 3)]
R['sueldo_cambio']['descriptivo_por_hora'] = {t: {'n': int(len(d)), 'media': round(float(np.average(d.dlh, weights=d.w)), 4), 'mediana': round(float(d.dlh.median()), 4)}
                                              for t, d in Ph.groupby('tipo')}

# ============ 7. Hijos según pareja (estado en la entrevista anterior) ============
I2 = I[['folio_n20', 'i1', 'i2_a']].merge(A[['folio_n20', 'a8', 'a9']], on='folio_n20').merge(W, on='folio_n20')
v0 = h.groupby('folio_n20').agg(v0=('ventana0', 'first'), iv=('iv', 'first'))
I2 = I2.merge(v0, left_on='folio_n20', right_index=True)
I2 = I2[I2.i2_a.isin([1, 2])].copy()
I2['anios'] = (I2.iv - I2.v0) / 12
I2 = I2[I2.anios.between(1, 10)]
I2['edad0'] = I2.a9 - I2.anios
Hj['B'] = ym(Hj.i21_anio, Hj.i21_mes)
Hj = Hj.merge(I2[['folio_n20', 'v0']], on='folio_n20')
nac = Hj[Hj.B >= Hj.v0].groupby('folio_n20').size()
I2['nac'] = I2.folio_n20.map(nac).fillna(0)
I2['pareja0'] = I2.i2_a == 1
FT = [17, 24, 29, 34, 39, 44]; FL = ['18-24', '25-29', '30-34', '35-39', '40-44']
I2['tr'] = pd.cut(I2.edad0, FT, labels=FL)
hp = {}
for sx, nm in [(2, 'mujeres'), (1, 'hombres')]:
    d = I2[(I2.a8 == sx) & I2.tr.notna()]
    tab = {}
    num = den = 0.0
    for tb in FL:
        x = d[d.tr == tb]
        r_all = (x.nac * x.factor_XS).sum() / (x.anios * x.factor_XS).sum()
        r_p = (x[x.pareja0].nac * x[x.pareja0].factor_XS).sum() / (x[x.pareja0].anios * x[x.pareja0].factor_XS).sum()
        r_s = (x[~x.pareja0].nac * x[~x.pareja0].factor_XS).sum() / (x[~x.pareja0].anios * x[~x.pareja0].factor_XS).sum()
        tab[tb] = {'n': int(len(x)), 'n_con_pareja': int(x.pareja0.sum()), 'nacimientos': int(x.nac.sum()),
                   'tasa_todos': round(float(r_all), 4), 'tasa_con_pareja': round(float(r_p), 4), 'tasa_sin_pareja': round(float(r_s), 4),
                   'mult_con_pareja': round(float(r_p / r_all), 3) if r_all > 0 else None, 'mult_sin_pareja': round(float(r_s / r_all), 3) if r_all > 0 else None}
    # multiplicador resumen: ponderado por nacimientos esperados (tasa_todos x años-persona) en 18-39
    sel = d[d.tr.isin(FL[:4])]
    exp_p = sum(tab[tb]['tasa_todos'] * (sel[(sel.tr == tb) & sel.pareja0].anios * sel[(sel.tr == tb) & sel.pareja0].factor_XS).sum() for tb in FL[:4])
    obs_p = (sel[sel.pareja0].nac * sel[sel.pareja0].factor_XS).sum()
    exp_s = sum(tab[tb]['tasa_todos'] * (sel[(sel.tr == tb) & ~sel.pareja0].anios * sel[(sel.tr == tb) & ~sel.pareja0].factor_XS).sum() for tb in FL[:4])
    obs_s = (sel[~sel.pareja0].nac * sel[~sel.pareja0].factor_XS).sum()
    def smr(dd, grp):
        r = {tb: (dd[dd.tr == tb].nac * dd[dd.tr == tb].factor_XS).sum() / (dd[dd.tr == tb].anios * dd[dd.tr == tb].factor_XS).sum() for tb in FL[:4]}
        g = dd[dd.pareja0 == grp]
        return (g.nac * g.factor_XS).sum() / sum(r[tb] * (g[g.tr == tb].anios * g[g.tr == tb].factor_XS).sum() for tb in FL[:4])
    sel_b = sel.reset_index(drop=True)
    tab['ic95_con_pareja'] = boot_ratio(sel_b, lambda dd: smr(dd, True), lambda dd: 1.0, reps=300)
    tab['ic95_sin_pareja'] = boot_ratio(sel_b, lambda dd: smr(dd, False), lambda dd: 1.0, reps=300)
    tab['mult_estandarizado_18_39'] = {'con_pareja': round(float(obs_p / exp_p), 3), 'sin_pareja': round(float(obs_s / exp_s), 3),
                                       'nacimientos_con_pareja': int(sel[sel.pareja0].nac.sum()), 'nacimientos_sin_pareja': int(sel[~sel.pareja0].nac.sum())}
    hp[nm] = tab
R['hijo_segun_pareja'] = {'nota': 'Personas con entrevista anterior (i2_a: con pareja / sin pareja en la entrevista anterior). Nacimientos de hijos propios desde la entrevista anterior '
                                  '(MODULO_I_HIJOS, i21) por año-persona. Edad = edad en la entrevista anterior. mult = tasa del grupo / tasa de todos en el tramo; '
                                  'el estandarizado compara nacimientos observados con los esperados según la tasa de todos por edad (razón estandarizada). Ponderado con factor_XS.',
                          **hp}

# ============ 8. Pareja entre entrevistas (estado en la entrevista anterior vs actual) ============
I3 = I2.merge(I[['folio_n20', 'i2_b']], on='folio_n20', how='left')
I3['pareja_hoy'] = I3.i1.isin([1, 2, 4])
I3['viudo'] = I3.i1 == 7
I3['uniones'] = (I3.i2_b - 1).where(I3.i2_b.between(1, 6))
I3['tb'] = pd.cut(I3.edad0, [17, 24, 29, 34, 44, 59], labels=['18-24', '25-29', '30-34', '35-44', '45-59'])
I3['eng'] = np.where(I3.edad0.between(20, 35), '20-35', np.where(I3.edad0.between(36, 59), '36-59', None))
fam = {'nota': 'Personas con entrevista anterior (2015-16 o 2019-20). Unión: entre quienes estaban sin pareja, uniones (matrimonio o convivencia) declaradas desde la '
               'entrevista anterior (i2_b) por año-persona. Separación: entre quienes estaban con pareja, fracción que hoy no tiene pareja (sin contar viudez), '
               'convertida a riesgo anual -ln(1-p)/años; subestima porque quien se separó y volvió a emparejarse cuenta como con pareja. Ponderado con factor_XS. '
               'Edad = edad en la entrevista anterior.'}
for col, labs in [('tb', ['18-24', '25-29', '30-34', '35-44', '45-59']), ('eng', ['20-35', '36-59'])]:
    out = {}
    for tb in labs:
        s0 = I3[(I3[col] == tb) & ~I3.pareja0 & I3.uniones.notna()]
        s1 = I3[(I3[col] == tb) & I3.pareja0 & ~I3.viudo]
        r_u = float((s0.uniones * s0.factor_XS).sum() / (s0.anios * s0.factor_XS).sum())
        p_s = float(np.average(~s1.pareja_hoy, weights=s1.factor_XS)); yrs = float(np.average(s1.anios, weights=s1.factor_XS))
        out[tb] = {'union_tasa_anual': round(r_u, 4), 'n_sin_pareja': int(len(s0)), 'uniones': int(s0.uniones.sum()),
                   'separacion_riesgo_anual': round(-np.log(1 - p_s) / yrs, 4), 'n_con_pareja': int(len(s1)), 'separados_hoy': int((~s1.pareja_hoy).sum()),
                   'anios_entre_entrevistas': round(yrs, 2)}
    fam[col] = out
R['pareja_entre_entrevistas'] = fam

json.dump(R, open(OUT, 'w'), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
print(json.dumps(R, ensure_ascii=False, indent=1, default=str)[:20000])
