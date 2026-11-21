import sys, pyreadstat
_, m = pyreadstat.read_dta(sys.argv[1], metadataonly=True)
print(m.number_rows, len(m.column_names))
for c in m.column_names:
    print(c, "|", (m.column_names_to_labels.get(c) or "")[:110])
