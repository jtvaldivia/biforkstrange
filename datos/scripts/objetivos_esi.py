"""Blancos de comparación para el benchmark del simulador, desde la ESI 2025 (INE).

Uso: python3 -I objetivos_esi.py <esi_2025_personas.csv> <salida.json>
Códigos (manual ENE/ESI): activ 1 ocupado, 2 desocupado, 3 fuera de la fuerza de trabajo;
categoria_ocupacion 1 empleador, 2 cuenta propia, 3 asalariado privado, 4 asalariado público, 5-6 servicio doméstico, 7 familiar no remunerado;
b15_1 personas en la empresa: 1 menos de 5, 2 de 5 a 10, 3 de 11 a 49, 4 de 50 a 199, 5 200 o más; ocup_form 1 formal, 2 informal;
cine11_1d 0-1 básica, 2 media, 3 técnica superior, 4 universitaria, 5 magíster, 6 doctorado.
Actividad y categorías se ponderan con fact_cal; el ingreso, con fact_cal_esi y ocup_ref = 1.
"""
import csv, json, sys, collections

BANDAS = [(18, 24), (25, 29), (30, 34), (35, 39), (40, 44), (45, 49)]
def banda(e):
    for a, b in BANDAS:
        if a <= e <= b: return f"{a}-{b}"
def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def wq(pares, q):
    pares = sorted(pares); tot = sum(w for _, w in pares); acc = 0
    for v, w in pares:
        acc += w
        if acc >= q * tot: return v
act = collections.defaultdict(collections.Counter); cat = collections.defaultdict(collections.Counter); tam = collections.Counter()
edu = collections.Counter(); ing = collections.defaultdict(list); form = collections.defaultdict(collections.Counter); tpi = collections.Counter()
edub = collections.defaultdict(collections.Counter); ingE = collections.defaultdict(lambda: collections.defaultdict(list))
with open(sys.argv[1], newline='', encoding='latin-1') as fh:
    for r in csv.DictReader(fh):
        e, w, we = num(r['edad']), num(r['fact_cal']), num(r['fact_cal_esi'])
        if e is None or w is None or not 18 <= e <= 49: continue
        b = banda(int(e)); a = r['activ']
        act[b][a] += w
        if a == '1':
            c = r['categoria_ocupacion']
            g = {'1': 'empleador', '2': 'cuenta_propia', '3': 'asalariado_privado', '4': 'asalariado_publico'}.get(c, 'otro')
            cat[b][g] += w
            form[b][r['ocup_form']] += w
            tpi[r['tpi']] += w
            if c == '3' and r['b15_1'] in '12345' and r['b15_1']:
                tam[{'1': 'menos_de_5', '2': '5_a_10', '3': '11_a_49', '4': '50_a_199', '5': '200_o_mas'}[r['b15_1']]] += w
        k = {'0': 'media', '1': 'media', '2': 'media', '3': 'tecnica', '4': 'universitaria', '5': 'postgrado', '6': 'postgrado'}.get(r['cine11_1d'])
        if k: edub[b][k] += w
        if 30 <= e <= 34 and k: edu[k] += w
        y = num(r['ing_t_p'])
        if r['ocup_ref'] == '1' and y is not None and we:
            ing[b].append((y, we))
            if k: ingE[b][k].append((y, we))
norm = lambda c: {k: round(v / sum(c.values()), 4) for k, v in c.items()}
out = {
    'fuente': 'INE, Encuesta Suplementaria de Ingresos 2025, microdatos; cálculo del equipo',
    'desocupacion': {b: round(act[b]['2'] / (act[b]['1'] + act[b]['2']), 4) for b in act},
    'ocupacion': {b: round(act[b]['1'] / sum(act[b].values()), 4) for b in act},
    'categoria_ocupados': {b: norm(cat[b]) for b in cat},
    'informalidad': {b: round(form[b]['2'] / (form[b]['1'] + form[b]['2']), 4) for b in form},
    'tamano_empresa_asalariados_privados': norm(tam),
    'educacion_30_34': norm(edu),
    'ingreso_mediano': {b: round(wq(v, 0.5)) for b, v in ing.items()},
    'ingreso_p25': {b: round(wq(v, 0.25)) for b, v in ing.items()},
    'ingreso_p75': {b: round(wq(v, 0.75)) for b, v in ing.items()},
    'educacion_por_banda': {b: norm(edub[b]) for b in edub},
}
# Ingreso de cada banda si tuviera la educación de quienes hoy tienen 30-34: reponderar cada nivel por la mezcla 30-34
mix = norm(edu)
def ajustado(b, q):
    pares = []
    for k, v in ingE[b].items():
        tot = sum(w for _, w in v)
        pares += [(y, w / tot * mix.get(k, 0)) for y, w in v]
    return round(wq(pares, q))
out['ingreso_mediano_edu_30_34'] = {b: ajustado(b, 0.5) for b in ing}
out['ingreso_p25_edu_30_34'] = {b: ajustado(b, 0.25) for b in ing}
out['ingreso_p75_edu_30_34'] = {b: ajustado(b, 0.75) for b in ing}
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
