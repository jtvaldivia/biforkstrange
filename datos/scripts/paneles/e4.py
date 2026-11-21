import sys, rdata, json
from rdata.parser import RObjectType as T
p = rdata.parser.parse_file(sys.argv[1])
def nodes(o):
    a=o.attributes; out=[]
    while a is not None and a.info.type==T.LIST:
        out.append(a.value[0]); a=a.value[1]
    return out
def strs(o): return [x.value.decode('utf-8','replace') if x.value is not None else None for x in o.value]
df=p.object.value[0]
names=None
for n in nodes(df):
    if n.info.type==T.STR and len(n.value)==750: names=strs(n); break
res={}
for nm,col in zip(names, df.value):
    d={}
    for n in nodes(col):
        if n.info.type==T.STR and len(n.value)==1 and 'label' not in d and n.value[0].value and n.value[0].value not in (b'haven_labelled',b'vctrs_vctr',b'double'):
            d['label']=strs(n)[0]
        elif n.info.type in (T.REAL,T.INT) and n.attributes is not None:
            labs=[x for x in nodes(n) if x.info.type==T.STR]
            if labs: d['values']={str(v):l for v,l in zip(list(n.value), strs(labs[0]))}
    res[nm]=d
json.dump(res, open(sys.argv[2],'w'), ensure_ascii=False, indent=0)
for w in sys.argv[3].split():
    r=res.get(w,{}); v=r.get('values',{}); print(w,'|',r.get('label'),'|',{k:x for k,x in v.items() if float(k)>0})
