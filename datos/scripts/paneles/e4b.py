import sys, rdata
p = rdata.parser.parse_file(sys.argv[1])
obj=p.object
print(obj.info.type, obj.tag)
df=obj.value[0]
print(df.info.type, len(df.value) if isinstance(df.value,list) else '')
a=df.attributes
print(repr(a)[:1500])
col=df.value[30]
print(repr(col.attributes)[:1500])
