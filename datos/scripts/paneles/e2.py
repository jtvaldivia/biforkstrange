import sys, pyreadr, pandas as pd
df = list(pyreadr.read_r(sys.argv[1]).values())[0]
df.to_pickle(sys.argv[2])
vs = "s01 s02 s03 s04 s11_01 s11_09 s19_01 s19_01_fecha s20 s21 m02 m10 m11 m12 m13 m14 m15 m16 m17 m18 m19 m20 m21 m36 m37_01 m38 m39 m41 m43 m44 m45 m46 m54 m55 m56 m57 m58 m59 m60 m61 m62 nhogar1 nhogar2 miembro02_edad tipo_atricion muestra".split()
for v in vs:
    t = pd.crosstab(df[v].fillna(-1).astype(str).str.slice(0,12), df['ola'])
    if len(t)>25: t = t.iloc[:12]
    print('=====',v); print(t.to_string())
print(df[['ponderador01','ponderador02','ponderador_long_panel','ponderador_long_total','fact_exp01','fact_exp02']].describe().to_string())
