import sys, pandas as pd, numpy as np
df=pd.read_pickle(sys.argv[1])
d=pd.DataFrame({'id':df.idencuesta.astype(str),'ola':df.ola.astype(int),'m36':pd.to_numeric(df.m36,errors='coerce'),'m48':pd.to_numeric(df.m48,errors='coerce'),'edad':df.m0_edad})
t=d[d.m36>0].sort_values(['id','ola']).copy(); t['prev']=t.groupby('id').m36.shift(1); t['olap']=t.groupby('id').ola.shift(1)
print(pd.crosstab(t.prev,t.m36))
print(pd.crosstab(t.olap,t.ola))
w=d.pivot_table(index='id',columns='ola',values='m48')
print(pd.crosstab(w[2].fillna(-9),w[4].fillna(-9)))
