"""Parámetros de familia, bienestar, red de contactos y frecuencias de decisiones con ELSOC 2016-2022.

Uso: paneles_elsoc.py <ELSOC_long.pkl> <calibracion_paneles.json> <salida.json>
El .pkl sale de ELSOC_Long_2016_2022_v1.00.RData con pyreadr (ver scripts/paneles/e2.py).

Olas: 1=2016, 2=2017, 3=2018, 4=2019, 5=2021, 6=2022. Variables laborales detalladas (m09 año de
inicio del trabajo actual, m12 horas, m06 personas supervisadas, m07 relación de empleo) y el
generador de posiciones r01 (conocidos en 13 ocupaciones) solo en 2016, 2018 y 2021.
Efectos fijos: MCO within con efectos fijos de persona y de ola, sin ponderar, EE agrupados por persona.
Tasas y prevalencias: ponderadas con ponderador02 de la ola de origen.
"""

import sys, json
import numpy as np
import pandas as pd
import statsmodels.api as sm

df = pd.read_pickle(sys.argv[1]); CP = json.load(open(sys.argv[2])); OUT = sys.argv[3]
YEAR = {1: 2016, 2: 2017, 3: 2018, 4: 2019, 5: 2021, 6: 2022}


def num(c):
    x = pd.to_numeric(df[c], errors='coerce'); return x.where(x >= 0)


d = pd.DataFrame({'id': df.idencuesta.astype(str), 'ola': df.ola.astype(int), 'edad': num('m0_edad'), 'sexo': num('m0_sexo'),
                  'w': num('ponderador02'), 's01': num('s01'), 's03': num('s03'), 'm02': num('m02'), 'm36': num('m36'),
                  'm12': num('m12'), 'm13': num('m13'), 'm29': num('m29'), 'm09': num('m09'), 'm06': num('m06'), 'm07': num('m07'),
                  'm01': num('m01'), 'r13': num('r13_nredes'), 'r15': num('r15'), 'm55': num('m55'), 'm56': num('m56')})
d['anio'] = d.ola.map(YEAR)
phq = pd.concat([num(f's11_0{i}') - 1 for i in range(1, 10)], axis=1)
d['phq9'] = phq.sum(axis=1, min_count=9)
d['dep_mod'] = (d.phq9 >= 10).astype(float).where(d.phq9.notna())
d['emp'] = np.select([d.m02.isin([1, 2, 3]), d.m02.eq(6), d.m02.isin([4, 5, 7, 8, 9])], ['O', 'D', 'I'], default='')
d.loc[d.m02.isna(), 'emp'] = ''
d['pareja'] = np.where(d.m36.isin([1, 2, 3]), 1.0, np.where(d.m36.isin([4, 6, 7, 8, 9]), 0.0, np.where(d.m36 == 5, -1.0, np.nan)))
mid = {1: 0, 2: 1, 3: 3, 4: 6, 5: 9, 6: 13, 7: 16}
R01 = pd.concat([num(f'r01_{i:02d}').map(mid) for i in range(1, 14)], axis=1)
d['red_vol'] = R01.sum(axis=1, min_count=13)
d['red_ext'] = (R01 > 0).sum(axis=1).where(d.red_vol.notna())
d['lred'] = np.log1p(d.red_vol)
d['ten'] = (d.anio - d.m09).where(d.m09 > 1900)
d['nuevo_empleo'] = (d.ten <= 1).astype(float).where(d.ten.notna() & (d.emp == 'O'))
d = d.sort_values(['id', 'ola']).reset_index(drop=True)
R = {'fuente': 'ELSOC 2016-2022 (COES), ELSOC_Long_2016_2022_v1.00.RData', 'script': 'scripts/modelo/paneles_elsoc.py'}


def fe(data, y, xs, extra_fe=None):
    t = data[['id', 'ola', y] + xs].dropna()
    t = t[t.groupby('id').id.transform('size') >= 2]
    Wd = pd.get_dummies(t.ola, prefix='o', drop_first=True).astype(float)
    X = pd.concat([t[xs].astype(float), Wd], axis=1); cols = list(X.columns)
    Z = pd.concat([t[['id', y]], X], axis=1)
    Zd = Z[[y] + cols] - Z.groupby('id')[[y] + cols].transform('mean')
    keep = [c for c in cols if Zd[c].abs().sum() > 1e-9]
    Xm = Zd[keep].values; yv = Zd[y].values
    XtX = np.linalg.pinv(Xm.T @ Xm); b = XtX @ Xm.T @ yv; u = yv - Xm @ b
    G = t.id.nunique(); N = len(t); K = len(keep) + G
    S = np.zeros((len(keep), len(keep)))
    for _, idx in t.groupby('id').indices.items():
        s = Xm[idx].T @ u[idx]; S += np.outer(s, s)
    V = XtX @ S @ XtX * (G / (G - 1)) * ((N - 1) / max(N - K, 1)); se = np.sqrt(np.diag(V))
    out = {'n_obs': N, 'n_personas': G}
    for i, c in enumerate(keep):
        if c in xs:
            out[c] = {'coef': round(float(b[i]), 4), 'ee': round(float(se[i]), 4),
                      'personas_con_cambio': int((t.groupby('id')[c].nunique() > 1).sum())}
    return out


def wmean(x, w):
    m = np.average(x, weights=w); n = len(x)
    v = np.average((x - m) ** 2, weights=w); neff = w.sum() ** 2 / (w ** 2).sum()
    return round(float(m), 4), round(float(np.sqrt(v / neff)), 4), n


def nxt(col, k=1):
    return d.groupby('id')[col].shift(-k)


for c in ['ola', 'emp', 'pareja', 'dep_mod', 'm02', 'm01', 's03', 'lred', 'm13', 'm09', 'anio']:
    d['n_' + c] = nxt(c)
    d['p_' + c] = d.groupby('id')[c].shift(1)
AB = lambda e: pd.cut(e, [17, 29, 44, 59], labels=['18-29', '30-44', '45-59'])  # noqa: E731
d['tramo'] = AB(d.edad)

# =============== 1. Familia: formar pareja y separarse ===============
pm = d[d.pareja.notna()].copy()
pm['pn'] = pm.groupby('id').pareja.shift(-1); pm['on'] = pm.groupby('id').ola.shift(-1)
pm['pn2'] = pm.groupby('id').pareja.shift(-2)
pm['pp'] = pm.groupby('id').pareja.shift(1)
pm = pm[pm.pn.notna() & (pm.pareja >= 0) & (pm.pn >= -1)]
pm['anual'] = ((pm.ola == 3) & (pm.on == 4)) | ((pm.ola == 5) & (pm.on == 6))
pm['bienal'] = ((pm.ola == 1) & (pm.on == 3)) | ((pm.ola == 4) & (pm.on == 5))
FB = [17, 24, 29, 34, 44, 59]; FLB = ['18-24', '25-29', '30-34', '35-44', '45-59']
pm['fb'] = pd.cut(pm.edad, FB, labels=FLB)
pm['eng'] = np.where(pm.edad.between(20, 35), '20-35', np.where(pm.edad.between(36, 59), '36-59', None))
fam = {'nota': 'm36 (no preguntado en 2017). Con pareja = casado, conviviente con o sin AUC; viudez no cuenta como separación. Pares de olas a un año: '
               '2018-2019 y 2021-2022 (principal); pares a dos años 2016-2018 y 2019-2021 anualizados como 1-(1-p)^(1/2). Ponderado con ponderador02 de la ola de origen; '
               'EE = error estándar binomial con n efectivo. "persistente" exige que el nuevo estado se mantenga en la ola siguiente (descarta idas y vueltas conviviente-soltero); '
               '"estricto" exige además el mismo estado en la ola anterior al origen.'}


def trans(sub, frm, to_mask):
    x = sub[sub.pareja == frm]
    if len(x) == 0:
        return None
    m, se, n = wmean(to_mask(x).astype(float).values, x.w.fillna(x.w.mean()).values)
    return {'tasa': m, 'ee': se, 'n': n, 'eventos': int(to_mask(x).sum())}


for nm, frm, f in [('union', 0.0, lambda x: x.pn == 1), ('separacion', 1.0, lambda x: x.pn == 0)]:
    res = {}
    for grp, col, labs in [('por_edad', 'fb', FLB), ('tramos_motor', 'eng', ['20-35', '36-59'])]:
        res[grp] = {}
        for tb in labs:
            a = trans(pm[pm.anual & (pm[col] == tb)], frm, f)
            b2 = trans(pm[pm.bienal & (pm[col] == tb)], frm, f)
            if b2: b2['tasa_anualizada'] = round(1 - (1 - b2['tasa']) ** 0.5, 4)
            pers = pm[pm.anual & (pm[col] == tb) & pm.pn2.notna()]
            p = trans(pers, frm, lambda x: f(x) & (x.pn2 == x.pn))
            est = pm[pm.anual & (pm[col] == tb) & pm.pn2.notna() & (pm.pp == pm.pareja)]
            q = trans(est, frm, lambda x: f(x) & (x.pn2 == x.pn))
            res[grp][tb] = {'anual': a, 'bienal': b2, 'anual_persistente': p, 'anual_estricto': q}
    fam[nm] = res
cs = d[d.pareja.isin([0, 1]) & d.edad.between(18, 59) & (d.ola == 3)]
fam['share_con_pareja_2018'] = {str(k): round(float(np.average(x.pareja, weights=x.w)), 3)
                                for k, x in cs.groupby(pd.cut(cs.edad, [17, 24, 29, 34, 39, 44, 59]), observed=True)}
fam['share_con_pareja_2018_nota'] = 'Corte transversal 2018 (ponderado), para chequear que unión y separación sean consistentes con cómo sube la fracción con pareja con la edad.'
R['familia'] = fam

# =============== 2. Bienestar ===============
a = d[(d.edad >= 18) & (d.edad <= 65)].copy()
a['desocupado'] = (a.emp == 'D').astype(float).where(a.emp != '')
a['inactivo'] = (a.emp == 'I').astype(float).where(a.emp != '')
o = a[a.emp == 'O'].copy()
o['lm13'] = np.log(o.m13.where(o.m13.between(2e4, 2e7)))
o['lm29'] = np.log(o.m29.where(o.m29.between(5e4, 5e7)))
bien = {'nota': 'Efectos fijos de persona y de ola, sin ponderar, EE agrupados por persona, 18-65 años. Escala s01 y s03 de 1 a 5 (x25 para pasar a 0-100); '
                'phq9 0-27; dep_mod = PHQ-9 >= 10 (síntomas depresivos moderados o severos).'}
bien['ingreso'] = {'s01_log_ingreso_personal': fe(o, 's01', ['lm13']), 's01_log_ingreso_hogar': fe(o, 's01', ['lm29']),
                   'nota': 'Ocupados. lm13 = log ingreso mensual líquido del entrevistado (m13, 20 mil a 20 millones); lm29 = log ingreso total del hogar.'}
h = o[(o.m12 > 0) & (o.m12 <= 100)].copy()
h['h_menos30'] = (h.m12 < 30).astype(float); h['h30_39'] = h.m12.between(30, 39).astype(float)
h['h46_54'] = h.m12.between(46, 54).astype(float); h['h55mas'] = (h.m12 >= 55).astype(float)
HX = ['h_menos30', 'h30_39', 'h46_54', 'h55mas']
bien['horas'] = {y: fe(h, y, HX) for y in ['s01', 'phq9', 'dep_mod', 's03']}
bien['horas']['nota'] = 'Ocupados con horas m12 (olas 2016, 2018, 2021). Referencia: 40 a 45 horas semanales.'
bien['cambio_empleo'] = {y: fe(o[o.ola.isin([1, 3, 5])], y, ['nuevo_empleo']) for y in ['s01', 'phq9', 's03']}
bien['cambio_empleo']['nota'] = 'nuevo_empleo = el trabajo actual empezó el año de la encuesta o el anterior (m09). Ocupados en olas 2016, 2018, 2021.'
o['supervisa'] = (o.m06 > 0).astype(float).where(o.m06.notna() & (o.m06 < 5000))
o['p_m09s'] = o.groupby('id').m09.transform(lambda s: s.nunique() == 1)
bien['supervisa_proxy_ascenso'] = {'s01_todos': fe(o, 's01', ['supervisa']), 's01_mismo_empleo': fe(o[o.p_m09s], 's01', ['supervisa']),
                                   'nota': 'supervisa = m06 > 0 (tiene personas a cargo). mismo_empleo = el año de inicio del trabajo (m09) no cambia entre olas: '
                                           'pasar a supervisar dentro del mismo empleo es lo más cercano a un ascenso que trae ELSOC.'}
cp = CP['1_bienestar_ELSOC']['efecto_within_estado']
bien['cesantia_desde_calibracion_paneles'] = {y: cp[y]['cesante_vs_ocupado']['desocupado'] for y in ['s01', 'phq9', 'dep_mod', 's03']}
bien['cesantia_desde_calibracion_paneles']['nota'] = 'Copiado de derivados/calibracion_paneles.json (scripts/paneles/elsoc_main.py): desocupado vs ocupado, efectos fijos.'

# prevalencia e incidencia de síntomas depresivos por horas
h['hb'] = pd.cut(h.m12, [0, 29, 39, 45, 54, 100], labels=['<30', '30-39', '40-45', '46-54', '55+'])
prev = {}
for tb, x in h[h.dep_mod.notna()].groupby('hb', observed=True):
    m, se, n = wmean(x.dep_mod.values, x.w.values); prev[str(tb)] = {'prevalencia': m, 'ee': se, 'n': n}
inc = {}
hi = h[(h.dep_mod == 0) & h.n_dep_mod.notna() & (h.n_ola == h.ola + 1)]
for tb, x in hi.groupby('hb', observed=True):
    m, se, n = wmean(x.n_dep_mod.values, x.w.values); inc[str(tb)] = {'incidencia_anual': m, 'ee': se, 'n': n, 'casos': int(x.n_dep_mod.sum())}
mi, sei, ni = wmean(hi.n_dep_mod.values, hi.w.values)
bien['depresion_por_horas'] = {'prevalencia_ocupados': prev, 'incidencia_anual': inc, 'incidencia_anual_todos_ocupados': {'tasa': mi, 'ee': sei, 'n': ni},
                               'nota': 'Ocupados 18-65 con horas (2016, 2018, 2021). Incidencia = sin síntomas moderados en t y con PHQ-9 >= 10 en la ola siguiente '
                                       '(2017, 2019, 2022), según horas en t. Ponderado con ponderador02.'}
# salud autorreportada por edad
sd = d[d.s03.notna() & d.n_s03.notna() & (d.edad >= 18) & (d.edad <= 70)].copy()
sd['dy'] = sd.n_ola.map(YEAR) - sd.anio
sd = sd[sd.dy > 0]
sd['ds'] = (sd.n_s03 - sd.s03) / sd.dy
sd['eb'] = pd.cut(sd.edad, [17, 29, 39, 49, 59, 70], labels=['18-29', '30-39', '40-49', '50-59', '60-70'])
sal = {}
for tb, x in sd.groupby('eb', observed=True):
    m, se, n = wmean(x.ds.values, x.w.values); sal[str(tb)] = {'cambio_anual_s03': m, 'ee': se, 'n_pares': n, 'en_0_100': round(m * 25, 2)}
cs = d[d.s03.notna() & d.edad.between(18, 70)]
Xc = sm.add_constant(pd.DataFrame({'edad': cs.edad, **{f'o{k}': (cs.ola == k).astype(float) for k in [2, 3, 4, 5, 6]}}))
mc = sm.WLS(cs.s03, Xc, weights=cs.w).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(cs.id)[0]})
bien['salud_por_edad'] = {'cambio_dentro_persona': sal,
                          'pendiente_transversal_por_anio_edad': {'coef': round(float(mc.params['edad']), 4), 'ee': round(float(mc.bse['edad']), 4),
                                                                  'en_0_100': round(float(mc.params['edad']) * 25, 2), 'n_obs': int(mc.nobs)},
                          'nota': 'cambio_dentro_persona: (s03 en la ola siguiente - s03) / años entre olas, por tramo de edad en t; mezcla el efecto de la edad con el del período '
                                  '(incluye 2019-2021). pendiente_transversal: MCO ponderado de s03 sobre la edad con efectos de ola (compara cohortes distintas).'}
R['bienestar'] = bien

# =============== 3. Red de contactos ===============
rr = a[a.lred.notna()].copy()
red = {'nota': 'Generador de posiciones r01 (conocidos en 13 ocupaciones, olas 2016, 2018, 2021). red_vol = suma de conocidos usando el punto medio de cada tramo '
               '(16 o más = 16); lred = log(1 + red_vol), su coeficiente es el cambio porcentual aproximado. red_ext = número de ocupaciones con al menos un conocido (0-13). '
               'Efectos fijos de persona y de ola, sin ponderar.'}
rr['nuevo_empleo0'] = rr.nuevo_empleo.fillna(0.0).where(rr.emp != '')
red['fe_lred'] = fe(rr, 'lred', ['nuevo_empleo0', 'desocupado', 'inactivo'])
red['fe_red_ext'] = fe(rr, 'red_ext', ['nuevo_empleo0', 'desocupado', 'inactivo'])
red['descriptivo'] = {'red_vol_media': wmean(rr.red_vol.values, rr.w.values)[0], 'red_vol_mediana': float(rr.red_vol.median()),
                      'red_ext_media': wmean(rr.red_ext.values, rr.w.values)[0]}
rp = rr.sort_values(['id', 'ola']).copy()
rp['nl'] = rp.groupby('id').lred.shift(-1); rp['na'] = rp.groupby('id').anio.shift(-1)
rp = rp[rp.nl.notna()].copy()
rp['dy'] = rp.na - rp.anio
rp['dl'] = (rp.nl - rp.lred) / rp.dy
red['cambio_anual_por_edad'] = {str(tb): dict(zip(['cambio_anual_lred', 'ee', 'n'], wmean(x.dl.values, x.w.values)))
                                for tb, x in rp.groupby('tramo', observed=True)}
red['perfil_transversal_por_edad'] = {str(tb): round(float(np.average(x.red_vol, weights=x.w)), 2) for tb, x in rr.groupby('tramo', observed=True)}
# red y encontrar empleo: desocupados en una ola con r01, empleo en la ola siguiente (un año después)
u = a[(a.emp == 'D') & a.lred.notna() & a.n_emp.isin(['O', 'D', 'I']) & (a.n_ola == a.ola + 1)].copy()
u['y'] = (u.n_emp == 'O').astype(float)
u['mujer'] = (u.sexo == 2).astype(float); u['sup'] = (u.m01 >= 7).astype(float)
Xu = sm.add_constant(u[['lred', 'edad', 'mujer', 'sup']].astype(float))
cll = sm.GLM(u.y, Xu, family=sm.families.Binomial(link=sm.families.links.CLogLog())).fit(cov_type='HC1')
lg = sm.GLM(u.y, Xu, family=sm.families.Binomial()).fit(cov_type='HC1')
red['encontrar_empleo'] = {'n_desocupados': int(len(u)), 'encuentran': int(u.y.sum()),
                           'cloglog_coef_lred': {'coef': round(float(cll.params['lred']), 4), 'ee': round(float(cll.bse['lred']), 4)},
                           'logit_coef_lred': {'coef': round(float(lg.params['lred']), 4), 'ee': round(float(lg.bse['lred']), 4)},
                           'nota': 'Desocupados (m02=6) en 2016, 2018 o 2021; resultado: ocupado en la ola siguiente (2017, 2019, 2022). Controles: edad, sexo, educación superior. '
                                   'El coeficiente cloglog es la elasticidad del riesgo de encontrar empleo respecto de los contactos, la misma forma que usa el motor '
                                   '(factor_red = 1 + RED_ELAST log(contactos/RED_REF)). Sin ponderar.'}
m55 = d[(d.ola == 3) & d.m55.isin([1, 2]) & (d.emp == 'O')]
red['empleo_con_ayuda_de_red_2018'] = {'share_si': round(float(np.average(m55.m55 == 1, weights=m55.w)), 3), 'n': int(len(m55)),
                                       'nota': 'm55, ola 2018, ocupados: recibió apoyo de alguien para encontrar su trabajo.'}
R['red'] = red

# =============== 4. Frecuencias de decisiones ===============
fr = {}
t = d[d.m02.isin([1, 2]) & (d.m01 >= 9) & d.edad.between(25, 45) & d.n_m02.notna() & (d.n_ola == d.ola + 1) & (d.ola != 4)]
m, se, n = wmean((t.n_m02 == 3).astype(float).values, t.w.values)
fr['empieza_a_estudiar_y_trabajar_con_titulo'] = {'tasa': m, 'ee': se, 'n': n, 'eventos': int((t.n_m02 == 3).sum()),
                                                   'nota': 'Ocupados (m02 1,2) de 25 a 45 años con título universitario o posgrado (m01 >= 9) que a la ola siguiente (un año) declaran '
                                                           '"estudia y trabaja" (m02=3). No dice qué estudian.'}
t2 = d[(d.emp == 'O') & (d.m01 == 9) & d.edad.between(25, 50) & d.n_m01.notna() & (d.n_ola == d.ola + 1) & (d.ola != 4)]
m, se, n = wmean((t2.n_m01 == 10).astype(float).values, t2.w.values)
fr['obtiene_posgrado'] = {'tasa': m, 'ee': se, 'n': n, 'eventos': int((t2.n_m01 == 10).sum()),
                          'nota': 'Ocupados de 25 a 50 con universitaria completa (m01=9) que a la ola siguiente declaran posgrado (m01=10). Incluye ruido de reporte.'}
R['frecuencias'] = fr

# =============== 5. Chequeos cruzados del mercado laboral con ELSOC ===============
lab = d[(d.emp == 'O') & d.ola.isin([1, 3, 5]) & (d.n_ola == d.ola + 1) & d.n_emp.isin(['O', 'D', 'I']) & d.edad.between(18, 64)].copy()
lab['a_D'] = (lab.n_emp == 'D').astype(float)
lab['tb'] = pd.cut(lab.ten, [-1, 0.99, 4.99, 99], labels=['<1', '1-4', '5+'])
lab['tramo'] = AB(lab.edad)
ck = {}
for tb, x in lab[lab.tb.notna()].groupby('tb', observed=True):
    m, se, n = wmean(x.a_D.values, x.w.values); ck[str(tb)] = {'tasa_O_a_D': m, 'ee': se, 'n': n, 'eventos': int(x.a_D.sum())}
Xl = pd.get_dummies(lab[lab.tb.notna()][['tb', 'tramo']].astype(str)).astype(float).drop(columns=['tb_1-4', 'tramo_30-44'])
ll = lab[lab.tb.notna()]
pl = sm.GLM(ll.a_D, sm.add_constant(Xl), family=sm.families.Binomial(link=sm.families.links.CLogLog()), var_weights=ll.w).fit(cov_type='HC1')
ck['razon_<1_vs_1_4'] = round(float(np.exp(pl.params['tb_<1'])), 3); ck['razon_5+_vs_1_4'] = round(float(np.exp(pl.params['tb_5+'])), 3)
ck['ic95_5+'] = [round(float(np.exp(pl.params['tb_5+'] - 1.96 * pl.bse['tb_5+'])), 3), round(float(np.exp(pl.params['tb_5+'] + 1.96 * pl.bse['tb_5+'])), 3)]
ck['ic95_<1'] = [round(float(np.exp(pl.params['tb_<1'] - 1.96 * pl.bse['tb_<1'])), 3), round(float(np.exp(pl.params['tb_<1'] + 1.96 * pl.bse['tb_<1'])), 3)]
sec = {}
for k, nmx in [(1, 'privado'), (2, 'publico')]:
    x = lab[lab.m07 == k]; m, se, n = wmean(x.a_D.values, x.w.values); sec[nmx] = {'tasa_O_a_D': m, 'ee': se, 'n': n}
ck['sector'] = sec
ck['nota'] = ('Ocupados 18-64 en 2016, 2018 y 2021 con antigüedad m09; tasa de estar desocupado (buscando) un año después, cualquier causa. '
              'Razones de cloglog ponderado con tramo de edad. Sirve como contraste de la EPS, no la reemplaza: mide stock de desocupación al año, no despidos.')
R['chequeo_antiguedad_ELSOC'] = ck

# cambio de ingreso entre olas laborales según trayectoria
wp = d[(d.emp == 'O') & d.ola.isin([1, 3]) & d.m13.between(2e4, 2e7)].copy()
nx = d[d.ola.isin([3, 5])][['id', 'ola', 'emp', 'm13', 'm09']].rename(columns={'ola': 'olaB', 'emp': 'empB', 'm13': 'm13B', 'm09': 'm09B'})
wp['olaB'] = wp.ola.map({1: 3, 3: 5})
wp = wp.merge(nx, on=['id', 'olaB'])
wp = wp[(wp.empB == 'O') & wp.m13B.between(2e4, 2e7) & wp.m09B.notna()]
midw = d[d.ola.isin([2, 4])][['id', 'ola', 'emp']].rename(columns={'ola': 'olaM', 'emp': 'empM'})
wp['olaM'] = wp.ola + 1
wp = wp.merge(midw, on=['id', 'olaM'], how='left')
wp['cambio'] = wp.m09B > wp.anio
wp['grupo'] = np.select([~wp.cambio, wp.cambio & (wp.empM == 'D'), wp.cambio], ['mismo_empleo', 'cambio_con_desempleo_intermedio', 'cambio_sin_desempleo_observado'], 'x')
wp['dl'] = np.log(wp.m13B) - np.log(wp.m13)
Xw = pd.get_dummies(wp.grupo).astype(float).drop(columns=['mismo_empleo'])
Xw['par18_21'] = (wp.ola == 3).astype(float)
mw = sm.WLS(wp.dl, sm.add_constant(Xw), weights=wp.w).fit(cov_type='HC1')
R['ingreso_por_trayectoria_ELSOC'] = {
    'n': int(len(wp)), 'n_por_grupo': wp.grupo.value_counts().to_dict(),
    **{c: {'coef': round(float(mw.params[c]), 4), 'ee': round(float(mw.bse[c]), 4)} for c in ['cambio_con_desempleo_intermedio', 'cambio_sin_desempleo_observado']},
    'nota': 'Ocupados en 2016->2018 y 2018->2021 con ingreso m13 en ambos extremos. dl = cambio de log ingreso; coeficientes relativos a quien siguió en el mismo empleo '
            '(m09 no cambió), con efecto del par de olas (absorbe inflación). cambio_con_desempleo = cambió de empleo y estaba desocupado en la ola intermedia (2017 o 2019). '
            'WLS con ponderador02 de origen, EE robustos.'}

json.dump(R, open(OUT, 'w'), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
print(json.dumps(R, ensure_ascii=False, default=str)[:300])
