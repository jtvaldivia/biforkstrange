import sys, json, numpy as np, pandas as pd, pyreadstat
B=sys.argv[1]; OUT=sys.argv[2]
rd=lambda f,**k: pyreadstat.read_dta(B+'/'+f, apply_value_formats=False, **k)[0]
h=rd('BBDD_VIVOS/MODULO_B_HISTORIA_LABORAL.dta')
A,mA=pyreadstat.read_dta(B+'/BBDD_VIVOS/MODULO_A_ENTREVISTADO.dta', apply_value_formats=False, usecols=['folio_n20','a4','a8','a9'])
print('A rows',len(A),A.folio_n20.nunique(), mA.variable_value_labels.get('a4'), mA.variable_value_labels.get('a8'))
print(A.a4.value_counts().head().to_dict(), A.a9.describe().to_dict())
W=rd('FACT_EXP/Factor_XS_EPS_2023.dta')[['folio_n20','factor_XS']]
H=rd('BBDD_VIVOS/MODULO_I_HIJOS.dta')
def ym(y,m):
    y=y.where(y>1900); mm=m.where(m.between(1,12),6)
    return y*12+(mm-1)
h['s']=ym(h.b2_a_inicio_anio,h.b2_a_inicio_mes); h['e']=ym(h.b2_a_termino_anio,h.b2_a_termino_mes)
h['mes_imp']=~h.b2_a_inicio_mes.between(1,12)
g=h.groupby('folio_n20')
o2=h[h.orden<=2].pivot_table(index='folio_n20',columns='orden',values='s')
print('orden2 start > orden1 start share', float((o2[2]>o2[1]).mean()), 'orden2<orden1', float((o2[2]<o2[1]).mean()))
h['iv']=g.e.transform('max').combine(g.s.transform('max'),np.fmax)
print('interview year dist', (h.drop_duplicates('folio_n20').iv//12).value_counts().to_dict())
print('missing end', int(h.e.isna().sum()), 'missing start', int(h.s.isna().sum()))
h=h[h.s.notna()].copy()
h['e']=h.e.fillna(h.iv)
h=h.sort_values(['folio_n20','s','e']).reset_index(drop=True)
h['last']=h.groupby('folio_n20').s.transform('max')==h.s
h['cens']=h['last']&(h.e>=h.iv-1)
h=h.merge(A[['folio_n20','a8','a9']],on='folio_n20',how='left').merge(W,on='folio_n20',how='left')
h['birth']=h.iv-h.a9*12-6
h['next_so']=h.groupby('folio_n20').b2a_so.shift(-1); h['next_s']=h.groupby('folio_n20').s.shift(-1)
# motivo
mot=h.b22.where(h.b22!=12, h.b22_e_cod.where(h.b22_e_cod.between(2,11),12))
cat={2:'mutuo_acuerdo',3:'renuncia',8:'renuncia_mejor_trabajo',4:'fin_contrato_plazo_obra',5:'despido_imputable',6:'despido_necesidades_empresa',7:'cierre_empresa',11:'fuerza_mayor',9:'salud',10:'pension',12:'otra',88:'nr',99:'nr',1:'nr'}
h['mot']=mot.map(cat).fillna('nr')
grp={'involuntario':['despido_imputable','despido_necesidades_empresa','cierre_empresa','fuerza_mayor'],'fin_contrato':['fin_contrato_plazo_obra'],
     'voluntario':['renuncia','renuncia_mejor_trabajo'],'mutuo_acuerdo':['mutuo_acuerdo'],'otro_o_sin_dato':['salud','pension','otra','nr']}
inv={v:k for k,vs in grp.items() for v in vs}
h['motg']=h.mot.map(inv)
START=2016*12
emp=h[(h.b2a_so==1)&(h.e>=START)].copy()
emp['s0']=emp.s.clip(lower=START)
emp['j2j']=(~emp.cens)&(emp.next_so==1)&((emp.next_s-emp.e)<=1)
# monthly expansion for exposure by age band and year
rows=[]
emp['nm']=(emp.e-emp.s0+1).clip(lower=1).astype(int)
idx=np.repeat(emp.index.values,emp.nm.values)
off=np.concatenate([np.arange(n) for n in emp.nm.values])
M=pd.DataFrame({'i':idx,'t':emp.s0.values.repeat(emp.nm.values)+off})
M['w']=emp.factor_XS.values.repeat(emp.nm.values); M['birth']=emp.birth.values.repeat(emp.nm.values)
M['age']=(M.t-M.birth)/12; M['yr']=M.t//12
bands=[17,29,44,59]; lab=['18-29','30-44','45-59']
M['tramo']=pd.cut(M.age,bands,labels=lab)
emp['age_end']=(emp.e-emp.birth)/12; emp['tramo']=pd.cut(emp.age_end,bands,labels=lab); emp['yr']=emp.e//12
ev=emp[~emp.cens]
def rates(Msub,evsub):
    out={}
    for tb in lab:
        m=Msub[Msub.tramo==tb]; e=evsub[evsub.tramo==tb]
        expo_w=m.w.sum()/12; expo=len(m)/12
        r={'anios_persona_ocupado':round(expo,0),'personas':int(emp.loc[m.i.unique(),'folio_n20'].nunique()),'n_terminos':int(len(e))}
        r['tasa_anual_termino_total']=round(e.factor_XS.sum()/expo_w,4)
        for gname in grp: r['tasa_'+gname]=round(e[e.motg==gname].factor_XS.sum()/expo_w,4); r['n_'+gname]=int((e.motg==gname).sum())
        r['tasa_cambio_empleador_j2j']=round(e[e.j2j].factor_XS.sum()/expo_w,4); r['n_j2j']=int(e.j2j.sum())
        r['tasa_paso_a_cesantia']=round(e[e.next_so.isin([2,3])].factor_XS.sum()/expo_w,4)
        r['tasa_paso_a_inactividad']=round(e[e.next_so==4].factor_XS.sum()/expo_w,4)
        out[tb]=r
    return out
R={'fuente':'EPS VIII Ronda (2023-2024), BBDD_VIVOS/MODULO_B_HISTORIA_LABORAL.dta; ponderado con factor_XS (Factor_XS_EPS_2023).'}
R['empleo_2016_2024']=rates(M,ev)
R['empleo_sin_2020']=rates(M[M.yr!=2020],ev[ev.yr!=2020])
R['empleo_2021_2024']=rates(M[M.yr>=2021],ev[ev.yr>=2021])
# reason distribution among terminations
R['motivos_termino_distribucion']=(ev.groupby('mot').factor_XS.sum()/ev.factor_XS.sum()).round(4).to_dict()
# unemployment durations (Kaplan-Meier)
def km(dur,cens,w):
    df=pd.DataFrame({'d':dur,'c':cens,'w':w}).dropna()
    S=1.0; surv={}; med=None
    for t in sorted(df.d.unique()):
        atrisk=df[df.d>=t].w.sum(); ev_=df[(df.d==t)&(~df.c)].w.sum()
        S*=1-ev_/atrisk if atrisk>0 else 1; surv[int(t)]=S
        if med is None and S<=0.5: med=int(t)
    ts=sorted(surv); rmean=0; prev=0; Sprev=1.0
    for t in ts:
        if t>60: break
        rmean+=Sprev*(t-prev); prev=t; Sprev=surv[t]
    rmean+=Sprev*(60-prev) if prev<60 else 0
    return med, round(rmean,1), {k:round(surv[max([t for t in ts if t<=k] or [ts[0]])],3) for k in [3,6,12,24]}
U=h[(h.b2a_so.isin([2,3]))&(h.s>=START)].copy()
U['dur']=(U.e-U.s).clip(lower=1); U['age_s']=(U.s-U.birth)/12; U['tramo']=pd.cut(U.age_s,bands,labels=lab)
R['cesantia']={}
for tb in lab+['todos']:
    u=U if tb=='todos' else U[U.tramo==tb]
    med,rm,sv=km(u.dur,u.cens,u.factor_XS)
    comp=u[~u.cens]
    R['cesantia'][tb]={'n_episodios':len(u),'n_censurados':int(u.cens.sum()),'mediana_KM_meses':med,'media_restringida_60m_KM_meses':rm,'sobrevida_KM':sv,
      'mediana_completos_meses':float(np.median(comp.dur)) if len(comp) else None,'media_completos_meses':round(float(np.average(comp.dur,weights=comp.factor_XS)),1) if len(comp) else None}
R['cesantia']['nota']='Episodios con situacion ocupacional final (b2a_so) = 2 Cesante o 3 Buscando trabajo por 1a vez, iniciados desde 2016. Duracion = termino - inicio en meses (minimo 1). Episodio vigente a la entrevista = censurado. Kaplan-Meier ponderado con factor_XS; media restringida a 60 meses.'
# children
H=H[H.i21_anio.between(2000,2025)].copy(); H['B']=ym(H.i21_anio,H.i21_mes)
H=H.sort_values('B').drop_duplicates('folio_n20')
P=h.groupby('folio_n20').agg(cov0=('s','min'),iv=('iv','first'),sexo=('a8','first'),w=('factor_XS','first'),a9=('a9','first'))
def state_at(f,t):
    sp=h[(h.folio_n20==f)&(h.s<=t)&(h.e>=t)]
    if sp.empty: return np.nan
    return float((sp.b2a_so==1).any())
res=[]
hs=h.groupby('folio_n20')
for _,r in H.iterrows():
    f=r.folio_n20
    if f not in P.index: continue
    p=P.loc[f]; Bm=r.B
    if p.cov0>Bm-12: continue
    pre=state_at(f,Bm-12)
    if pre!=1: 
        res.append({'f':f,'sexo':p.sexo,'w':p.w,'pre':pre}); continue
    o={'f':f,'sexo':p.sexo,'w':p.w,'pre':pre}
    for k in (12,24):
        o[f'emp_{k}']=state_at(f,Bm+k) if p.iv>=Bm+k else np.nan
    sp=h[(h.folio_n20==f)&(h.e>=Bm-9)&(h.s<=Bm+24)]
    o['salida_alguna']=float(((sp.b2a_so!=1)&(sp.s>=Bm-9)).any()) if p.iv>=Bm+24 else np.nan
    res.append(o)
C=pd.DataFrame(res)
R['hijo']={'nota':'MODULO_I_HIJOS (hijos nacidos despues de la ultima entrevista, i21_anio/i21_mes). Primer nacimiento en el periodo; se exige historia laboral que cubra 12 meses antes del parto. Denominador: ocupados 12 meses antes del parto. "No ocupado" = no esta en episodio b2a_so=1 (cuenta licencia larga/cuidado como no ocupado si asi se registro).'}
for sx,nm in [(2,'mujeres'),(1,'hombres')]:
    c=C[C.sexo==sx]; ce=c[c.pre==1]
    out={'nacimientos_con_cobertura':len(c),'ocupados_12m_antes':len(ce)}
    for k in ['emp_12','emp_24']:
        x=ce[ce[k].notna()]
        out[f'prop_no_ocupado_{k[4:]}m_despues']=round(float(np.average(1-x[k],weights=x.w)),3) if len(x) else None; out[f'n_{k}']=len(x)
    x=ce[ce.salida_alguna.notna()]
    out['prop_con_alguna_salida_entre_-9m_y_+24m']=round(float(np.average(x.salida_alguna,weights=x.w)),3) if len(x) else None; out['n_salida']=len(x)
    R['hijo'][nm]=out
json.dump(R,open(OUT,'w'),ensure_ascii=False,indent=1)
print(json.dumps(R,ensure_ascii=False,indent=0))
