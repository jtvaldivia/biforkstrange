# lista hojas y su título (primeras celdas con texto)
import sys, openpyxl
for f in sys.argv[1:]:
    wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
    print("==", f.split("/")[-1], len(wb.sheetnames))
    for ws in wb.worksheets:
        t = []
        for row in ws.iter_rows(min_row=1, max_row=6, values_only=True):
            t += [str(c) for c in row if isinstance(c, str)]
        print(" ", ws.title, "|", " / ".join(t)[:170])
