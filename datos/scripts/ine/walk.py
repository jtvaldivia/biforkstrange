# Uso: walk.py <url_pagina> <html_guardado> [max_depth] [filtro_regex_titulo]
import json, re, sys, time, urllib.parse, urllib.request
BASE = sys.argv[1].rstrip("/") + "/"
html = open(sys.argv[2], encoding="utf-8", errors="ignore").read()
MAXD = int(sys.argv[3]) if len(sys.argv) > 3 else 3
FILT = re.compile(sys.argv[4], re.I) if len(sys.argv) > 4 else None
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
roots = re.findall(r'data-folder="([^"]+)"[^>]*>\s*([^<]*)', html)
def post(ep, fid):
    req = urllib.request.Request(BASE + ep + "/", data=urllib.parse.urlencode({"idFolder": fid}).encode(),
        headers={"User-Agent": UA, "X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)
def walk(fid, path, depth):
    try: kids = post("hijosCarpeta", fid).get("folder") or []
    except Exception as e: print("ERR", path, e); kids = []
    try:
        for d in post("getArchivos", fid).get("documento") or []:
            print("F", path, "|", d.get("Titulo"), "|", d.get("Tipo"), "|", d.get("Url"))
    except Exception as e: print("ERRF", path, e)
    for k in kids:
        print("D", path + " / " + k["Titulo"])
        if depth < MAXD and (FILT is None or depth > 0 or FILT.search(k["Titulo"])):
            time.sleep(0.15); walk(k["Id"], path + " / " + k["Titulo"], depth + 1)
seen=set()
for fid, name in roots:
    if fid in seen: continue
    seen.add(fid); print("ROOT", fid, name.strip())
    walk(fid, name.strip(), 0)
