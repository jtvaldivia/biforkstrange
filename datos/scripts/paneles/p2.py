import sys, pyreadstat, pandas as pd, re
B=sys.argv[1]
h,m=pyreadstat.read_dta(B+'/BBDD_VIVOS/MODULO_B_HISTORIA_LABORAL.dta', apply_value_formats=False)
print(m.variable_value_labels['b22']); print(m.variable_value_labels['b2a_ed'])
print(h.b2_a_inicio_anio.value_counts().sort_index().to_dict())
print(h.b2_a_termino_anio.value_counts(dropna=False).sort_index().to_dict())
f=h[h.orden==1]; print('first spell start yr', f.b2_a_inicio_anio.value_counts().sort_index().to_dict())
print(h.groupby('folio_n20').orden.max().describe())
print(pd.crosstab(h.b2a_so, h.b22.fillna(-1)))
for f in ['BBDD_VIVOS/MODULO_A_ENTREVISTADO.dta','BBDD_VIVOS/MODULO_HOGAR.dta','BBDD_VIVOS/MODULO_I_ENTREVISTADO.dta']:
    d,mm=pyreadstat.read_dta(B+'/'+f, metadataonly=True)
    print('####',f, mm.number_rows)
    for c,l in mm.column_names_to_labels.items():
        if l and re.search(r'(?i)sexo|nacimiento|edad|tipo de entrevista|muestra|cohorte|fecha|parentesco|última entrevista|hijo|pareja|estado civil', l): print(' ',c,'|',l[:110])
