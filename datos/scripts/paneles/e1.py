import sys, pyreadr, pandas as pd
r = pyreadr.read_r(sys.argv[1])
for k,v in r.items():
    print(k, v.shape)
    df=v
cols=list(df.columns)
print(len(cols))
print(' '.join(cols))
df.to_parquet(sys.argv[2]) if False else None
