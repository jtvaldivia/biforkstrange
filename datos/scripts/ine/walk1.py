# walk1.py <url_pagina> <html> : lista raíces y sus hijos inmediatos (sin bajar más)
import json, re, sys, urllib.parse, urllib.request
BASE = sys.argv[1].rstrip("/") + "/"; html = open(sys.argv[2], encoding="utf-8", errors="ignore").read()
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
def post(ep, fid):
    req = urllib.request.Request(BASE + ep + "/", data=urllib.parse.urlencode({"idFolder": fid}).encode(), headers={"User-Agent": UA, "X-Requested-With": "XMLHttpRequest"})
    return json.load(urllib.request.urlopen(req, timeout=30))
ids = sys.argv[3:] if len(sys.argv) > 3 else list(dict.fromkeys(re.findall(r'data-folder="([^"]+)"', html)))
for fid in ids:
    print("ROOT", fid)
    for k in post("hijosCarpeta", fid).get("folder") or []: print("  D", k["Id"], k["Titulo"])
    for d in (post("getArchivos", fid).get("documento") or [])[:15]: print("  F", d.get("Titulo"), d.get("Tipo"), d.get("Url"))
