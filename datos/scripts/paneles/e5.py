import sys, json, pandas as pd, numpy as np
df = pd.read_pickle(sys.argv[1]); L=json.load(open(sys.argv[2]))
vs="s01 s11_01 s11_09 s03 m02 m36 m12 m09 s12 s13_02 s13_05 s13_06 t06_08 r13_relacion_01 r13_contacto_01 r13_nredes miembro01_edad miembro02_edad nhogar1 m46_nhogar m54 m61 m0_edad ponderador02 ponderador_long_total".split()
av={v:[int(((pd.to_numeric(df.loc[df.ola==o,v],errors='coerce'))>=0).sum()) for o in range(1,7)] for v in vs}
for v,a in av.items(): print(v.ljust(18),a)
for v in ['r13_relacion_01','r13_contacto_01','r13_tiempo_01','s13_06','m09','tipo_atricion','muestra']:
    print(v, L[v])
# is miembro01 the respondent?
d=df[df.ola==1]
x=pd.to_numeric(d.miembro01_edad,errors='coerce'); print('miembro01_edad==m0_edad share', (x==d.m0_edad).mean(), x.notna().sum())
for o in range(1,7):
    d=df[df.ola==o]; e=d[[f'miembro{i:02d}_edad' for i in range(1,14)]].apply(pd.to_numeric,errors='coerce')
    print(o, 'with age0 member', int((e==0).any(axis=1).sum()), 'age<=1', int((e<=1).any(axis=1).sum()), 'roster n', int(e.notna().any(axis=1).sum()))
print(df.groupby('ola').size(), df.idencuesta.nunique())
