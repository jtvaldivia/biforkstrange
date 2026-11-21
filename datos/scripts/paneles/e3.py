import sys, pandas as pd
df = pd.read_pickle(sys.argv[1])
vs = "m54 m55 m56 m57 m58 m59 m60 m61 m62 nhogar1 nhogar2 miembro02_edad tipo_atricion muestra".split()
for v in vs:
    t = pd.crosstab(df[v].astype(float).fillna(-1), df['ola'])
    if len(t)>14: t = t.iloc[:14]
    print('=====',v); print(t.to_string())
print(df.groupby('m36')['m0_edad'].agg(['mean','count']))
print(df.groupby('ola')[['ponderador01','ponderador02','ponderador_long_panel','ponderador_long_total','fact_exp01','fact_exp02']].agg(lambda s:(s>0).sum()))
print(df.groupby('ola')['m0_edad'].describe())
print(df.groupby('ola')['annio_enc'].describe())
for c in [c for c in df.columns if c.startswith('r13_contacto') or c in ('r01_01','r15','r16','r17','c01','t01')]:
    print(c, df[c].value_counts().sort_index().to_dict())
