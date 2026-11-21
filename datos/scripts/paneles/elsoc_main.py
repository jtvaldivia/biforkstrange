import sys, json, numpy as np, pandas as pd
df = pd.read_pickle(sys.argv[1]); OUT=sys.argv[2]
def num(c):
    x=pd.to_numeric(df[c],errors='coerce'); return x.where(x>=0)
d=pd.DataFrame({'id':df.idencuesta.astype(str),'ola':df.ola.astype(int),'edad':num('m0_edad'),'sexo':num('m0_sexo'),
  'w':num('ponderador02'),'s01':num('s01'),'s03':num('s03'),'m02':num('m02'),'m36':num('m36'),'m48':num('m48'),
  'm12':num('m12'),'s12':num('s12'),'t06_08':num('t06_08'),'s13_06':num('s13_06'),'s13_02':num('s13_02'),'s13_05':num('s13_05')})
phq=pd.concat([num(f's11_0{i}')-1 for i in range(1,10)],axis=1)
d['phq9']=phq.sum(axis=1,min_count=9)
d['dep_mod']=(d.phq9>=10).astype(float).where(d.phq9.notna())
d['emp']=np.select([d.m02.isin([1,2,3]),d.m02.eq(6),d.m02.isin([4,5,7,8,9])],['O','D','I'],default=None)
d.loc[d.m02.isna(),'emp']=None
d['pareja']=np.where(d.m36.isin([1,2,3]),1.0,np.where(d.m36.isin([4,5,6,7,8,9]),0.0,np.nan))
print('m48 by ola', d.groupby('ola').m48.count().to_dict())
d=d.sort_values(['id','ola']).reset_index(drop=True)
R={}
R['sd']={k:{'mean':round(float(d[k].mean()),3),'sd':round(float(d[k].std()),3),'n':int(d[k].count())} for k in ['s01','phq9','s03']}
R['sd']['dep_mod_prev']=round(float(d.dep_mod.mean()),3)

def fe(data,y,xs,label):
    t=data[['id','ola',y]+xs].dropna()
    t=t[t.groupby('id').id.transform('size')>=2]
    W=pd.get_dummies(t.ola,prefix='o',drop_first=True).astype(float)
    X=pd.concat([t[xs].astype(float),W],axis=1)
    cols=list(X.columns)
    Z=pd.concat([t[['id',y]],X],axis=1)
    Zd=Z[[y]+cols]-Z.groupby('id')[[y]+cols].transform('mean')
    keep=[c for c in cols if Zd[c].abs().sum()>1e-9]
    Xm=Zd[keep].values; ym=Zd[y].values
    XtX=np.linalg.pinv(Xm.T@Xm); b=XtX@Xm.T@ym; u=ym-Xm@b
    G=t.id.nunique(); N=len(t); K=len(keep)+G
    S=np.zeros((len(keep),len(keep)))
    for _,idx in t.groupby('id').indices.items():
        s=Xm[idx].T@u[idx]; S+=np.outer(s,s)
    V=XtX@S@XtX*(G/(G-1))*((N-1)/max(N-K,1))
    se=np.sqrt(np.diag(V))
    out={'n_obs':N,'n_personas':G}
    for i,c in enumerate(keep):
        if c in xs or c.startswith('ev_'):
            sw=int((t.groupby('id')[c].nunique()>1).sum()) if c in t else None
            out[c]={'coef':round(float(b[i]),4),'se':round(float(se[i]),4),'personas_con_cambio':sw}
    return out

# ---------- 1a static within effects
a=d[(d.edad>=18)&(d.edad<=65)].copy()
a['desocupado']=(a.emp=='D').astype(float).where(a.emp.notna())
a['inactivo']=(a.emp=='I').astype(float).where(a.emp.notna())
R['fe_estado']={}
for y in ['s01','phq9','dep_mod','s03']:
    R['fe_estado'][y]={'cesante_vs_ocupado':fe(a,y,['desocupado','inactivo'],y),
                        'con_pareja':fe(a[a.ola!=2],y,['pareja'],y)}
# ---------- 1b event studies
def prev_state(col):
    return d.groupby('id')[col].shift(1)
def event_study(name, cond_fn, sample_fn):
    t=d[(d.edad>=18)&(d.edad<=65)].copy()
    ev=cond_fn(t)
    t['ev']=ev.fillna(False)
    first=t[t.ev].groupby('id').ola.min()
    t['ev_ola']=t.id.map(first)
    t=t[sample_fn(t)]
    oi={1:1,2:2,3:3,4:4,5:5,6:6}
    k=t.ola-t.ev_ola
    t['ev_pre2']=((k<=-2)).astype(float); t['ev_0']=(k==0).astype(float); t['ev_1']=(k==1).astype(float); t['ev_2mas']=(k>=2).astype(float)
    res={'n_eventos':int(first.reindex(t.id.unique()).notna().sum())}
    for y in ['s01','phq9']:
        res[y]=fe(t,y,['ev_pre2','ev_0','ev_1','ev_2mas'],name)
    return res
# build lagged states using previous observed wave of the person (shift within id over available rows)
d['emp_prev']=d.groupby('id').emp.shift(1)
dp=d[d.pareja.notna()].copy(); dp['pareja_prev']=dp.groupby('id').pareja.shift(1); dp['m36_prev']=dp.groupby('id').m36.shift(1)
d=d.merge(dp[['id','ola','pareja_prev','m36_prev']],on=['id','ola'],how='left')
ever=lambda col,val: d.groupby('id')[col].transform(lambda s:(s==val).any())
d['ever_O']=ever('emp','O'); d['ever_D']=ever('emp','D'); d['ever_sin']=ever('pareja',0.0); d['ever_con']=ever('pareja',1.0)
R['event_study']={
 'quedar_cesante':event_study('cesante',lambda t:(t.emp_prev=='O')&(t.emp=='D'),lambda t:t.ever_O),
 'volver_a_trabajar':event_study('reempleo',lambda t:(t.emp_prev=='D')&(t.emp=='O'),lambda t:t.ever_D),
 'formar_pareja':event_study('union',lambda t:(t.pareja_prev==0)&(t.pareja==1),lambda t:t.ever_sin),
 'separarse':event_study('separacion',lambda t:(t.pareja_prev==1)&(t.m36.isin([4,7,8,9])),lambda t:t.ever_con),
}
nchg=dp.assign(ch=(dp.pareja!=dp.pareja_prev)&dp.pareja_prev.notna()).groupby('id').ch.sum()
d['mono']=d.id.map(nchg).fillna(0)<=1
R['event_study']['formar_pareja_robusto']=event_study('union_r',lambda t:(t.pareja_prev==0)&(t.pareja==1),lambda t:t.ever_sin&t.mono)
R['event_study']['separarse_robusto']=event_study('sep_r',lambda t:(t.pareja_prev==1)&(t.pareja==0)&(t.m36.isin([4,7,8,9])),lambda t:t.ever_con&t.mono&~((d.loc[t.index,'m36']==5)&False))
R['event_study']['nota_robusto']='Version robusta: solo personas con a lo sumo un cambio de estado de pareja en todo el panel (elimina el ruido conviviente<->soltero y casado<->separado que vuelve y va). m36 no se pregunto en 2017.'
R['event_study']['nota']='k = olas desde el evento (olas 2016,17,18,19,21,22); referencia k=-1 (ola anterior al evento). ev_pre2: k<=-2; ev_0: ola del evento; ev_1: ola siguiente; ev_2mas: dos o mas olas despues. Efectos fijos de persona y de ola; SE agrupados por persona. Muestra 18-65 años. Controles: nunca tratados del grupo en riesgo.'

# ---------- 2 transition matrices
st=['O','D','I']
d['ola_next']=d.groupby('id').ola.shift(-1); d['emp_next']=d.groupby('id').emp.shift(-1)
def band(e): return pd.cut(e,[17,29,44,59],labels=['18-29','30-44','45-59'])
d['tramo']=band(d.edad)
tr=d[d.emp.notna()&d.emp_next.notna()&d.tramo.notna()&(d.ola_next==d.ola+1)]
def mat(t):
    M=pd.crosstab(t.emp,t.emp_next,values=t.w,aggfunc='sum').reindex(index=st,columns=st).fillna(0)
    n=pd.crosstab(t.emp,t.emp_next).reindex(index=st,columns=st).fillna(0)
    P=M.div(M.sum(1),axis=0)
    return P,n
def sqrtm(P):
    vals,vecs=np.linalg.eig(P.values); S=(vecs@np.diag(np.sqrt(vals.astype(complex)))@np.linalg.inv(vecs)).real
    S=np.clip(S,0,None); S=S/S.sum(1,keepdims=True); return pd.DataFrame(S,index=P.index,columns=P.columns)
R['transiciones']={'nota':'Filas: estado en t; columnas: estado en t+1 (O ocupado: m02 1-3; D desocupado buscando: m02=6; I inactivo: resto). Ponderado con ponderador02 de la ola de origen. anual = pares 2016-17, 2017-18, 2018-19, 2021-22. bienal_2019_2021 anualizado con raiz cuadrada de la matriz (periodo COVID).'}
for tb in ['18-29','30-44','45-59']:
    t=tr[tr.tramo==tb]
    Pa,na=mat(t[t.ola!=4]); P2,n2=mat(t[t.ola==4])
    R['transiciones'][tb]={'anual':Pa.round(4).to_dict('index'),'n_anual':na.astype(int).to_dict('index'),
        'bienal_2019_2021_anualizado':sqrtm(P2).round(4).to_dict('index'),'n_bienal':n2.astype(int).to_dict('index')}
# s13_06 stressor prevalence among employed
s=d[d.s13_06.notna()&(d.emp=='O')&d.tramo.notna()]
R['estresor_despido']={tb:{'prop_si':round(float(np.average(g.s13_06==1,weights=g.w)),4),'n':len(g)} for tb,g in s.groupby('tramo',observed=True)}
R['estresor_despido']['nota']='ELSOC s13_06 "Estresores: Despidos del trabajo" (si/no), olas 2016, 2018, 2022, ocupados, ponderado. Periodo de referencia no verificado en el cuestionario.'
# ---------- 4 hours vs family contact
h=d[(d.emp=='O')&(d.m12>0)&(d.m12<=100)&(d.edad>=18)&(d.edad<=65)].copy()
h['horas10']=h.m12/10
R['horas_familia']={'s12_hablar_problemas_familia_amigos':fe(h,'s12',['horas10'],'s12'),
   't06_08_satisf_cercania_familia_amigos':fe(h,'t06_08',['horas10'],'t06'),
   'pooled_medias_s12_por_horas':{str(k):round(float(v),3) for k,v in h.groupby(pd.cut(h.m12,[0,30,44,45,50,100]),observed=True).s12.mean().items()}}
R['hijo']='No calculable en ELSOC: numero de hijos (m37) solo en 2016 y en refresco 2018; m48 (tiene hijos) en 2017 y solo para la muestra de refresco en 2019; roster del hogar solo en 2016.'
json.dump(R,open(OUT,'w'),ensure_ascii=False,indent=1)
print(json.dumps(R,ensure_ascii=False)[:100])
