"""Genera casos para comparar el evaluador de Python con el de JavaScript.

Uso (desde datos_laborales/):
    python3 -I simulador/referencia/paridad.py <salida.json>
    node simulador/referencia/paridad.cjs <salida.json>
Evalúa en Python todas las expresiones del paquete que no usan azar, en 300 estados de prueba, y guarda estados y resultados.
"""
import contextlib, io, json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
salida = sys.argv[1]
sys.argv = [sys.argv[0], '1']
import types
V = types.SimpleNamespace()
_g = {'__name__': 'validar', '__file__': os.path.join(AQUI, 'validar.py')}
with contextlib.redirect_stdout(io.StringIO()):
    try:  # corre una validación mínima y deja disponibles el paquete y el generador de estados
        exec(compile(open(_g['__file__'], encoding='utf-8').read(), _g['__file__'], 'exec'), _g)
    except SystemExit:
        pass
V.__dict__.update(_g)
from expresiones import ErrorExpresion  # noqa: E402

exprs = set()
def junta(resultados, extra=False):
    for r in resultados:
        if r['prob'] != 'resto' and not extra: exprs.add(r['prob'])
        for e in r['efectos']:
            if not extra: exprs.add(e['valor'])
for d in V.DEC:
    exprs.update([d['cuando'], d['aparicion']['peso']])
    for o in d['opciones']:
        junta(o['resultados'])
        if o.get('requisito'): exprs.add(o['requisito'])
for e in V.EVE:
    exprs.update([e['cuando'], e['prob_anual'] if 'prob_anual' in e else e['prob_mensual']]); junta(e['resultados'])
exprs = sorted(x for x in exprs if isinstance(x, str) and 'azar' not in x)
estados, casos = [], []
for i in range(300):
    e = V.estado_al_azar(); estados.append(e)
    for x in exprs:
        try:
            v = V.pq.evaluar(x, e)
        except (ErrorExpresion, ZeroDivisionError, ValueError, TypeError):
            v = '__error__'
        casos.append([i, x, v])
json.dump({'estados': estados, 'casos': casos}, open(salida, 'w', encoding='utf-8'), ensure_ascii=False)
print(len(exprs), 'expresiones,', len(casos), 'casos')
