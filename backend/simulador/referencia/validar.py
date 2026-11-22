"""Revisa el paquete completo: referencias, gramática y que cada probabilidad dé un número entre 0 y 1.

Uso: python3 -I simulador/referencia/validar.py [n_estados]
1. Toda tabla del índice existe y sus columnas coinciden con el CSV.
2. Toda expresión respeta la gramática, usa variables declaradas en estado.json, parámetros de parametros.json
   y tablas y columnas que existen.
3. Toda fuente citada existe en fuentes.json; todo 'luego' apunta a una decisión o evento; todo efecto mueve una variable declarada.
4. Con n estados al azar (por omisión 4.000), cada decisión que aplica se evalúa entera: peso >= 0, probabilidades entre 0 y 1,
   la suma de las explícitas no pasa de 1 y los valores de los efectos son números finitos o categorías válidas.
Sale con código 1 si encuentra errores.
"""
import collections, csv, json, math, os, random, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from expresiones import Paquete, parsear, nombres, llamadas, ErrorExpresion  # noqa: E402

RAIZ = os.path.dirname(AQUI)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
carga = lambda f: json.load(open(os.path.join(RAIZ, f), encoding='utf-8'))
pq = Paquete(RAIZ)
EST = {v['nombre']: v for v in carga('estado.json')['variables']}
PAR = pq.parametros
FUE = {f['id'] for f in carga('fuentes.json')['fuentes']}
DEC = carga('decisiones.json')['decisiones']
EVE = carga('eventos.json')['eventos']
IDS = {d['id'] for d in DEC} | {e['id'] for e in EVE}
errores, avisos = [], []
err = lambda m: errores.append(m)

# ---------------------------------------------------------------- 1. tablas
for nombre, t in pq.indice.items():
    ruta = os.path.join(RAIZ, t['archivo'])
    if not os.path.exists(ruta):
        err(f'tabla {nombre}: falta {t["archivo"]}')
        continue
    with open(ruta, encoding='utf-8') as fh:
        cab = next(csv.reader(fh))
    if list(t['columnas']) != cab:
        err(f'tabla {nombre}: columnas del índice {list(t["columnas"])} no calzan con el CSV {cab}')
    if t['fuente_id'] not in FUE:
        err(f'tabla {nombre}: fuente {t["fuente_id"]} no está en fuentes.json')
for p in PAR.values():
    if p['fuente'] not in FUE:
        err(f'parámetro {p["id"]}: fuente {p["fuente"]} desconocida')

# ---------------------------------------------------------------- 2 y 3. revisión estática
EXPRS = []  # (dónde, expresión, contexto extra de variables)


def revisar(donde, expr, extra=()):
    if isinstance(expr, (int, float)) or expr == 'resto':
        return
    try:
        arbol = parsear(expr)
    except (ErrorExpresion, SyntaxError) as e:
        err(f'{donde}: {e} en {expr!r}')
        return
    for v in nombres(arbol) - set(EST) - set(extra):
        err(f'{donde}: variable no declarada {v!r}')
    for args in llamadas(arbol, 'k'):
        if args and args[0] not in PAR:
            err(f'{donde}: parámetro desconocido {args[0]!r}')
    for args in llamadas(arbol, 'tabla') + [a[1:] for a in llamadas(arbol, 'tabla_o')]:
        t, col = args[0], args[1] if len(args) > 1 else None
        if t not in pq.indice:
            err(f'{donde}: tabla desconocida {t!r}')
            continue
        cols = pq.indice[t]['columnas']
        if col not in cols:
            err(f'{donde}: {t} no tiene columna {col!r}')
        for dim in args[2::2]:
            if dim is not None and dim not in cols:
                err(f'{donde}: {t} no tiene columna {dim!r} para filtrar')
    EXPRS.append(donde)


def revisar_resultados(donde, resultados, extra=()):
    for r in resultados:
        d = f'{donde}/{r["id"]}'
        revisar(d + ' prob', r['prob'], extra)
        if r.get('luego') and r['luego'] not in IDS:
            err(f'{d}: luego {r["luego"]!r} no existe')
        for e in r['efectos']:
            if e['var'] not in EST:
                err(f'{d}: efecto sobre variable no declarada {e["var"]!r}')
            if e['op'] not in ('suma', 'multiplica', 'fija'):
                err(f'{d}: op desconocida {e["op"]!r}')
            revisar(d + ' efecto ' + e['var'], e['valor'], extra)
            if e.get('cuando'):
                revisar(d + ' cuando ' + e['var'], e['cuando'], extra)
        if sum(1 for x in resultados if x['prob'] == 'resto') > 1:
            err(f'{donde}: más de un resultado con prob resto')


for dcs in DEC:
    D = 'decisión ' + dcs['id']
    revisar(D + ' cuando', dcs['cuando'])
    revisar(D + ' peso', dcs['aparicion']['peso'])
    for ev in dcs['evidencia']:
        if ev['fuente'] not in FUE:
            err(f'{D}: evidencia con fuente desconocida {ev["fuente"]!r}')
    for o in dcs['opciones']:
        for f in o.get('fuentes', []):
            if f not in FUE:
                err(f'{D}/{o["id"]}: fuente desconocida {f!r}')
        if o.get('requisito'):
            revisar(f'{D}/{o["id"]} requisito', o['requisito'])
        revisar_resultados(f'{D}/{o["id"]}', o['resultados'])
    if dcs.get('opciones_desde_tabla'):
        od = dcs['opciones_desde_tabla']
        extra = ['fila_' + c for c in pq.indice[od['tabla']]['columnas']]
        revisar(D + ' filtro', od['filtro'], extra)
        revisar_resultados(D + '/fila', od['resultados'], extra)
    if not dcs['opciones'] and not dcs.get('opciones_desde_tabla'):
        err(f'{D}: sin opciones')
for e in EVE:
    E = 'evento ' + e['id']
    revisar(E + ' cuando', e['cuando'])
    revisar(E + ' prob', e['prob_anual'])
    for f in e['fuentes']:
        if f not in FUE:
            err(f'{E}: fuente desconocida {f!r}')
    revisar_resultados(E, e['resultados'])

# ---------------------------------------------------------------- 4. prueba con estados al azar
R = random.Random(20261121)
RUBROS = ['Minería', 'Finanzas y seguros', 'Información y comunicaciones', 'Comercio', 'Salud', 'Enseñanza', 'Servicios profesionales', 'Construcción',
          'Industria manufacturera', 'Transporte', 'Agricultura y pesca', 'Hoteles y restaurantes', 'Artes y entretención', 'Servicios administrativos', 'Administración pública', 'Otros servicios']
REGIONES = ['Valparaíso', 'Biobío', 'Antofagasta', 'Maule', 'La Araucanía', 'Los Lagos']
carreras = pq.filas('mifuturo_carreras')


def _ids(tabla, col, filtro=lambda f: True):
    """Ids de una tabla del catálogo; lista vacía si la tabla todavía no existe."""
    try:
        return [f[col] for f in pq.filas(tabla) if filtro(f)]
    except (KeyError, OSError):
        return []


UNIS_PRE = _ids('universidades', 'universidad_id', lambda f: f.get('tipo_institucion') != 'EXT')
UNIS_EXT = _ids('universidades', 'universidad_id', lambda f: f.get('tipo_institucion') == 'EXT')
EMPRESAS = [int(x) for x in _ids('empresas_catalogo', 'empresa_id')]
CARGOS = [int(x) for x in _ids('cargos_catalogo', 'cargo_id')]


def estado_al_azar():
    edad = R.randint(18, 50)
    edu = R.choice(['media', 'media', 'tecnica', 'universitaria', 'postgrado']) if edad >= 22 else 'media'
    est = 'estudiando' if (edad <= 24 and R.random() < 0.4) else R.choice(['empleado', 'empleado', 'empleado', 'buscando', 'independiente', 'fundador', 'inactivo'])
    c = R.choice(carreras) if (edu != 'media' or est == 'estudiando') and R.random() < 0.9 else None
    pareja = R.choice(['no', 'pololeo', 'convive', 'casado'])
    hijos = R.choice([0, 0, 1, 2]) if edad >= 22 else 0
    tipo = R.choice(['grande', 'pyme', 'startup', 'publico', 'extranjero']) if est == 'empleado' else ''
    nivel = R.randint(0, 4)
    sueldo = round(R.lognormvariate(math.log(800000), 0.6)) if est in ('empleado', 'independiente', 'fundador') else 0
    madre = edad + R.randint(18, 42) if R.random() < 0.9 else -1
    e = {'edad': edad, 'sexo': R.choice(['h', 'm']), 'edu': edu, 'estado': est, 'primer_empleo': 1 if (est == 'buscando' and R.random() < 0.3) else 0,
         'carrera_id': int(c['carrera_id']) if c else -1, 'area': c['area'] if c else '', 'tipo_institucion': c['tipo_institucion'] if c else R.choice(['', 'U', 'IP', 'CFT']),
         'semestres_restantes': R.randint(0, 10) if est == 'estudiando' else 0, 'anos_titulado': R.randint(0, 20), 'tipo_empleador': tipo,
         'rubro': 'Administración pública' if tipo == 'publico' else R.choice(RUBROS), 'nivel': nivel, 'sueldo': sueldo, 'sueldo_ref': sueldo or round(R.lognormvariate(math.log(800000), 0.5)),
         'antiguedad': R.randint(0, 10), 'meses_cesante': R.choice([0, 6, 12, 24]) if est == 'buscando' else 0, 'hueco': R.randint(0, 1), 'horas': R.choice([22, 44, 55]),
         'parcial': R.randint(0, 1), 'remoto': R.randint(0, 1), 'formal': R.randint(0, 1), 'pais': R.choice(['chile', 'chile', 'afuera']), 'region': R.choice(['rm', 'otra']),
         'region_perfil': R.choice(REGIONES), 'pareja': pareja, 'hijos': hijos, 'edad_hijo_menor': R.randint(0, 15) if hijos else -1,
         'ahorro': round(R.uniform(-5e6, 6e7)), 'deuda_estudios': R.choice([0, 0, 8e6]), 'animo': R.uniform(20, 90), 'energia': R.uniform(10, 95), 'salud': 'bien',
         'red': R.uniform(0, 100), 'skill': R.uniform(0, 100), 'riesgo': R.uniform(0, 100), 'ambicion': R.uniform(0, 100), 'usa_ia': R.randint(0, 1),
         'empresa_anos': R.randint(0, 8), 'empresa_fondos': R.randint(0, 1), 'madre_edad': madre, 'padre_edad': madre + 2 if madre > 0 and R.random() < 0.85 else -1,
         'familiar_enfermo': R.choice(['', '', '', 'madre', 'padre']), 'recesion': 1 if R.random() < 0.12 else 0,
         'anos_en_carrera': R.randint(0, 5), 'anos_en_startup': R.randint(0, 6), 'financia': R.choice(['', 'cae']), 'ingles': R.randint(0, 1), 'isapre': R.randint(0, 1),
         'marcado': R.randint(0, 1), 'validado': 0, 'propietario': R.randint(0, 1), 'primer_grande': R.randint(0, 1), 'oferta_al_titularse': 0, 'ocupacion': R.randint(1, 9),
         'edad_decide_estudios': 18, 'cierra_en': 0,
         'rubro_destino': R.choice(RUBROS), 'region_destino': R.choice(REGIONES), 'ocupacion_destino': R.randint(1, 9), 'quien_enferma': R.choice(['madre', 'padre']),
         'universidad_destino': R.choice([f['universidad_id'] for f in pq.filas('sies_magister_2026')] + UNIS_EXT),
         'universidad_id': R.choice(UNIS_PRE + ['']), 'institucion_destino': R.choice(UNIS_PRE or ['']),
         'empresa_id': R.choice([-1] + EMPRESAS) if est == 'empleado' else -1, 'cargo_id': R.choice([-1] + CARGOS) if est == 'empleado' else -1,
         'ia_adopcion': R.random(), 'ia_castigo_joven': R.uniform(0.75, 0.9)}
    for v in EST.values():
        if v['tipo'] == 'modificador':
            e.setdefault(v['nombre'], 1 if v['inicio'] == '1' else 0)
    return pq.derivar(e)


fallas = collections.Counter()
ejemplo = {}
aplica = collections.Counter()


def falla(donde, msg, e):
    clave = f'{donde}: {msg}'
    fallas[clave] += 1
    ejemplo.setdefault(clave, {k: e[k] for k in ('edad', 'sexo', 'edu', 'estado', 'tipo_empleador', 'rubro', 'carrera_id', 'nivel', 'banda7')})


def probar_resultados(donde, resultados, e):
    suma = 0
    for r in resultados:
        if r['prob'] == 'resto':
            continue
        try:
            p = pq.evaluar(r['prob'], e, R)
        except Exception as x:  # noqa: BLE001
            falla(donde + '/' + r['id'], 'prob: ' + str(x), e)
            continue
        if not isinstance(p, (int, float)) or not (0 <= p <= 1) or math.isnan(p):
            falla(donde + '/' + r['id'], f'prob fuera de [0,1]: {p}', e)
        else:
            suma += p
    if suma > 1 + 1e-9:
        falla(donde, f'las probabilidades suman {suma:.3f}', e)
    for r in resultados:
        for ef in r['efectos']:
            try:
                if ef.get('cuando') and not pq.evaluar(ef['cuando'], e, R):
                    continue
                v = pq.evaluar(ef['valor'], e, R)
            except Exception as x:  # noqa: BLE001
                falla(f'{donde}/{r["id"]} efecto {ef["var"]}', str(x), e)
                continue
            tipo = EST[ef['var']]['tipo'] if ef['var'] in EST else None
            if tipo in ('categoria', 'eleccion') and ef['op'] == 'fija':
                dom = EST[ef['var']]['dominio']
                if dom and v not in dom:
                    falla(f'{donde}/{r["id"]} efecto {ef["var"]}', f'valor {v!r} fuera del dominio', e)
            elif not isinstance(v, (int, float)) or math.isnan(v) or math.isinf(v):
                falla(f'{donde}/{r["id"]} efecto {ef["var"]}', f'valor no numérico {v!r}', e)


for _ in range(N):
    e = estado_al_azar()
    for dcs in DEC:
        try:
            if dcs['aparicion']['tipo'] != 'interna' and not pq.evaluar(dcs['cuando'], e, R):
                continue
            w = pq.evaluar(dcs['aparicion']['peso'], e, R)
            if not isinstance(w, (int, float)) or w < 0:
                falla('decisión ' + dcs['id'], f'peso inválido {w}', e)
        except Exception as x:  # noqa: BLE001
            falla('decisión ' + dcs['id'], 'cuando/peso: ' + str(x), e)
            continue
        aplica[dcs['id']] += 1
        for o in dcs['opciones']:
            try:
                if o.get('requisito') and not pq.evaluar(o['requisito'], e, R):
                    continue
            except Exception as x:  # noqa: BLE001
                falla(f'decisión {dcs["id"]}/{o["id"]}', 'requisito: ' + str(x), e)
                continue
            probar_resultados(f'decisión {dcs["id"]}/{o["id"]}', o['resultados'], e)
        od = dcs.get('opciones_desde_tabla')
        if od:
            for fila in R.sample(pq.filas(od['tabla']), 5):
                ef = dict(e, **{'fila_' + c: (float(v) if v.replace('.', '', 1).isdigit() else v) for c, v in fila.items()})
                probar_resultados(f'decisión {dcs["id"]}/fila', od['resultados'], ef)
    for ev in EVE:
        try:
            if not pq.evaluar(ev['cuando'], e, R):
                continue
            p = pq.evaluar(ev['prob_anual'], e, R)
            if not (0 <= p <= 1):
                falla('evento ' + ev['id'], f'prob_anual fuera de [0,1]: {p}', e)
        except Exception as x:  # noqa: BLE001
            falla('evento ' + ev['id'], 'cuando/prob: ' + str(x), e)
            continue
        aplica['evento ' + ev['id']] += 1
        probar_resultados('evento ' + ev['id'], ev['resultados'], e)

nunca = [d['id'] for d in DEC if aplica[d['id']] == 0] + [e['id'] for e in EVE if aplica['evento ' + e['id']] == 0]
for k_, n in fallas.most_common():
    err(f'{k_}  ({n} de {N} estados; ej. {ejemplo[k_]})')
for x in nunca:
    avisos.append(f'{x}: no aplicó en ningún estado de prueba')

print(f'Paquete: {len(DEC)} decisiones, {len(EVE)} eventos, {len(PAR)} parámetros, {len(EST)} variables, {len(pq.indice)} tablas, {len(FUE)} fuentes')
print(f'Expresiones revisadas: {len(EXPRS)}. Estados de prueba: {N}.')
for a in avisos:
    print('AVISO', a)
for x in errores[:60]:
    print('ERROR', x)
if len(errores) > 60:
    print(f'... y {len(errores) - 60} errores más')
print('OK' if not errores else f'{len(errores)} errores')
sys.exit(1 if errores else 0)
