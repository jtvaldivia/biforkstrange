"""Baja todas las vacantes publicadas en la API pública de Get on Board (v0)
y las guarda en un CSV con sueldo, seniority y modalidad.

Uso: python3 getonbrd_pull.py <carpeta_salida>
"""
import csv, json, sys, time, urllib.request

BASE = "https://www.getonbrd.com/api/v0"
UA = "Mozilla/5.0 (research script)"


def get(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def lookup(path):
    out = {}
    try:
        for row in get(path)["data"]:
            out[str(row["id"])] = row["attributes"].get("name")
    except Exception as e:  # el catálogo es opcional
        print("sin catálogo", path, e, file=sys.stderr)
    return out


def main(outdir):
    seniorities = lookup("/seniorities")
    modalities = lookup("/modalities")
    cats = [c["id"] for c in get("/categories?per_page=100")["data"]]
    rows, seen = [], set()
    for cat in cats:
        page = 1
        while True:
            d = get(f"/categories/{cat}/jobs?per_page=100&page={page}")
            for j in d["data"]:
                if j["id"] in seen:
                    continue
                seen.add(j["id"])
                a = j["attributes"]
                sid = str(((a.get("seniority") or {}).get("data") or {}).get("id"))
                mid = str(((a.get("modality") or {}).get("data") or {}).get("id"))
                rows.append({
                    "id": j["id"],
                    "title": a.get("title"),
                    "category": cat,
                    "min_salary_usd": a.get("min_salary"),
                    "max_salary_usd": a.get("max_salary"),
                    "seniority": seniorities.get(sid, sid),
                    "modality": modalities.get(mid, mid),
                    "remote": a.get("remote"),
                    "remote_modality": a.get("remote_modality"),
                    "countries": "|".join(a.get("countries") or []),
                    "published_at": a.get("published_at"),
                    "applications_count": a.get("applications_count"),
                    "company_id": ((a.get("company") or {}).get("data") or {}).get("id"),
                })
            total = (d.get("meta") or {}).get("total_pages", 1)
            if page >= total or not d["data"]:
                break
            page += 1
            time.sleep(0.4)
        print(cat, len(rows), file=sys.stderr)
        time.sleep(0.4)
    path = f"{outdir}/getonbrd_vacantes.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    con = [r for r in rows if r["min_salary_usd"]]
    cl = [r for r in rows if "Chile" in r["countries"]]
    print(f"{len(rows)} vacantes, {len(con)} con sueldo, {len(cl)} con Chile -> {path}")


if __name__ == "__main__":
    main(sys.argv[1])
