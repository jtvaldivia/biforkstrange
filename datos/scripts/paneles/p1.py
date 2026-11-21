import sys, pyreadstat, pandas as pd
base=sys.argv[1]
for f in sys.argv[2:]:
    df,m=pyreadstat.read_dta(base+'/'+f, apply_value_formats=False)
    print('#####',f,df.shape)
    for c in df.columns:
        lab=m.column_names_to_labels.get(c)
        vl=m.variable_value_labels.get(c,{})
        nun=df[c].nunique()
        ex = str(dict(list(vl.items())[:14]))[:300] if vl else str(df[c].dropna().unique()[:6])[:100]
        print(c,'|',lab,'|',nun,'|',ex)
