# dump.py <xlsx> <hoja> [max_filas] [max_cols]
import sys, openpyxl
wb = openpyxl.load_workbook(sys.argv[1], read_only=True, data_only=True)
names = wb.sheetnames if sys.argv[2] == "*" else [sys.argv[2]]
mr = int(sys.argv[3]) if len(sys.argv) > 3 else 60; mc = int(sys.argv[4]) if len(sys.argv) > 4 else 14
for n in names:
    print("###", n)
    for i, row in enumerate(wb[n].iter_rows(max_row=mr, values_only=True)):
        r = [("%.4g" % c if isinstance(c, float) else str(c)) for c in row[:mc] if c is not None]
        if r: print(i + 1, " | ".join(r)[:260])
