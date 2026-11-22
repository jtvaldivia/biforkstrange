"""Evaluador de referencia de las expresiones del paquete (Python 3, solo biblioteca estándar).

Uso:
    from expresiones import Paquete
    pq = Paquete('ruta/a/simulador')            # carga parámetros y tablas
    estado = pq.derivar({'edad': 30, 'sexo': 'm', ...})
    pq.evaluar("k('P_DESPIDO', banda3) * 2", estado, azar=random.Random(1))

La gramática es un subconjunto común a Python y JavaScript: números, textos entre comillas simples, variables,
+ - * / %, una comparación (< <= > >= == !=) y llamadas a las funciones de FUNCIONES. No hay and/or/if:
se usan si(), y(), o(), no(), que se evalúan de forma perezosa. Las comparaciones devuelven 1 o 0.
tabla_o(respaldo, tabla, columna, ...) devuelve el respaldo si la fila no existe o la celda está vacía (muestra chica).
"""
import ast, csv, json, math, os, random

FUNCIONES = {'si', 'y', 'o', 'no', 'en', 'min', 'max', 'clamp', 'exp', 'ln', 'pow', 'abs', 'redondear', 'k', 'tabla', 'tabla_o', 'q_muerte', 'luto',
             'falso', 'azar', 'azar_uniforme', 'azar_normal', 'azar_lognormal', 'azar_entero'}
BIN = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b, ast.Mod: lambda a, b: a % b}
CMP = {ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b, ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b}


class ErrorExpresion(Exception):
    pass


def parsear(expr):
    """Devuelve el árbol y valida que solo use la gramática permitida."""
    if isinstance(expr, (int, float)):
        expr = repr(expr)
    arbol = ast.parse(expr, mode='eval')
    for n in ast.walk(arbol):
        if isinstance(n, (ast.Expression, ast.Load, ast.Name, ast.Constant, ast.Call, ast.UnaryOp, ast.USub, ast.UAdd, ast.BinOp, ast.Compare)) or type(n) in BIN or type(n) in CMP:
            if isinstance(n, ast.Compare) and len(n.ops) != 1:
                raise ErrorExpresion('comparación encadenada: usa y()')
            if isinstance(n, ast.Call) and (not isinstance(n.func, ast.Name) or n.func.id not in FUNCIONES or n.keywords):
                raise ErrorExpresion('función no permitida: ' + ast.dump(n.func))
            if isinstance(n, ast.Constant) and not isinstance(n.value, (int, float, str)):
                raise ErrorExpresion('constante no permitida')
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and '"' in expr:
                raise ErrorExpresion('usa comillas simples')
            continue
        raise ErrorExpresion('sintaxis no permitida: ' + type(n).__name__)
    return arbol


def nombres(arbol):
    """Variables (no funciones) que usa una expresión."""
    funcs = {id(n.func) for n in ast.walk(arbol) if isinstance(n, ast.Call)}
    return {n.id for n in ast.walk(arbol) if isinstance(n, ast.Name) and id(n) not in funcs}


def llamadas(arbol, nombre):
    """Argumentos literales de cada llamada a una función (para revisar tablas y parámetros)."""
    out = []
    for n in ast.walk(arbol):
        if isinstance(n, ast.Call) and n.func.id == nombre:
            out.append([a.value if isinstance(a, ast.Constant) else None for a in n.args])
    return out


def _clave(v):
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v)


def _verdad(v):
    return bool(v) if not isinstance(v, str) else v != ''


class Paquete:
    def __init__(self, raiz):
        self.raiz = raiz
        self.parametros = {p['id']: p for p in json.load(open(os.path.join(raiz, 'parametros.json'), encoding='utf-8'))['parametros']}
        self.indice = {t['tabla']: t for t in json.load(open(os.path.join(raiz, 'tablas', 'indice.json'), encoding='utf-8'))['tablas']}
        self._tablas, self._cache, self._arboles = {}, {}, {}

    # ------------------------------------------------------------------ datos
    def filas(self, nombre):
        if nombre not in self._tablas:
            with open(os.path.join(self.raiz, self.indice[nombre]['archivo']), encoding='utf-8') as fh:
                self._tablas[nombre] = list(csv.DictReader(fh))
        return self._tablas[nombre]

    def tabla(self, nombre, columna, *pares):
        clave = (nombre, columna) + tuple(_clave(v) for v in pares)
        if clave in self._cache:
            return self._cache[clave]
        cond = [(pares[i], _clave(pares[i + 1])) for i in range(0, len(pares), 2)]
        for f in self.filas(nombre):
            if all(_clave(f.get(c, '')) == v for c, v in cond):
                txt = f.get(columna, '')
                if txt == '':
                    raise ErrorExpresion(f'celda vacía: {nombre}.{columna} con {dict(cond)}')
                try:
                    val = float(txt)
                except ValueError:
                    val = txt
                self._cache[clave] = val
                return val
        raise ErrorExpresion(f'sin fila: {nombre} con {dict(cond)}')

    def k(self, nombre, clave=None, defecto=None):
        if nombre not in self.parametros:
            raise ErrorExpresion('parámetro desconocido: ' + nombre)
        v = self.parametros[nombre]['valor']
        if clave is None:
            return v
        if isinstance(v, list):
            return v[int(clave)]
        c = _clave(clave)
        if c in v:
            return v[c]
        if defecto is not None:
            return defecto
        raise ErrorExpresion(f'clave {c!r} no está en {nombre}')

    def q_muerte(self, edad, sexo):
        a, b = self.k('MORT_GOMPERTZ', sexo)
        return min(0.6, math.exp(a + b * edad))

    def luto(self, quien, anos, estado):
        per = 'ano_0' if anos <= 0 else 'ano_1' if anos == 1 else 'anos_2_3' if anos <= 3 else 'anos_4_5' if anos <= 5 else None
        if per is None:
            return 0
        base = self.tabla('duelo_satisfaccion', 'base_hija_46', 'fallece', quien, 'periodo', per)
        edad = self.tabla('duelo_satisfaccion', 'por_ano_de_edad', 'fallece', quien, 'periodo', per)
        hijo = self.tabla('duelo_satisfaccion', 'si_es_hijo_hombre', 'fallece', quien, 'periodo', per)
        return min(0, base + edad * (estado['edad'] - 46) + hijo * (1 if estado['sexo'] == 'h' else 0))

    # ------------------------------------------------------------------ derivadas
    def derivar(self, e):
        """Agrega las variables derivadas al estado (devuelve un dict nuevo)."""
        e = dict(e)
        x = e['edad']
        e['mujer'] = 1 if e['sexo'] == 'm' else 0
        e['sexo_txt'] = 'mujer' if e['sexo'] == 'm' else 'hombre'
        e['edu_esi'] = 'media_o_menos' if e['edu'] == 'media' else e['edu']
        e['banda3'] = '18-29' if x < 30 else '30-44' if x < 45 else '45-59'
        e['banda7'] = '18-24' if x < 25 else '50-54' if x >= 50 else f'{5 * (x // 5)}-{5 * (x // 5) + 4}'
        e['banda5'] = '15-19' if x < 20 else '45-49' if x >= 45 else f'{5 * (x // 5)}-{5 * (x // 5) + 4}'
        cid = e.get('carrera_id', -1)
        e['exposicion_ia'] = self.tabla('mifuturo_carreras', 'exposicion_ia_area', 'carrera_id', cid) if cid >= 0 else 0.143
        e['estamento'] = {'media': 'Administrativos', 'tecnica': 'Técnicos'}.get(e['edu'], 'Profesionales')
        e['seniority'] = ['Junior', 'Semi Senior', 'Senior', 'Expert', 'Expert'][int(e.get('nivel', 0))]
        e['region_nombre'] = 'Metropolitana' if e.get('region', 'rm') == 'rm' else e.get('region_perfil', 'Valparaíso')
        e['percentil'] = self.percentil(e)
        e['quintil'] = ['I', 'II', 'III', 'IV', 'V'][min(4, int(e['percentil'] // 20))]
        e['pareja_previa'] = e.get('pareja', 'no')
        e['crecimiento_esi'] = self.crecimiento_esi(e)
        e['crecimiento_carrera'] = self.crecimiento_carrera(e)
        e['crecimiento_cuenta_propia'] = self.crecimiento_cuenta_propia(e)
        e.setdefault('prob_ascenso', 0.05)
        return e

    def percentil(self, e):
        if not e.get('sueldo'):
            return 50
        b = e['banda7']
        qs = [(0.10, 'p10'), (0.25, 'p25'), (0.50, 'p50'), (0.75, 'p75'), (0.90, 'p90')]
        v = [self.tabla('esi_perfil_edad_edu', c, 'educacion', e['edu'], 'banda', b) for _, c in qs]
        s = e['sueldo']
        if s <= v[0]:
            return max(1, round(10 * s / v[0]))
        for i in range(4):
            if s <= v[i + 1]:
                return round(100 * (qs[i][0] + (qs[i + 1][0] - qs[i][0]) * (s - v[i]) / (v[i + 1] - v[i])))
        return min(99, round(90 + 10 * (s - v[4]) / v[4]))

    def crecimiento_esi(self, e):
        bandas = ['18-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54']
        i = bandas.index(e['banda7'])
        if i == len(bandas) - 1:
            return 0
        a = self.tabla('esi_perfil_edad_edu', 'p50', 'educacion', e['edu'], 'banda', bandas[i])
        b = self.tabla('esi_perfil_edad_edu', 'p50', 'educacion', e['edu'], 'banda', bandas[i + 1])
        return max(0, min(0.06, (b / a) ** (1 / 5) - 1))

    def crecimiento_cuenta_propia(self, e):
        """Alza anual del ingreso de quien trabaja por cuenta propia: mediana de la banda siguiente sobre la
        actual en esi_ingreso_categoria_formalidad (cuenta propia, formal o informal según `formal`), anualizada.
        Puede ser negativa: en la ESI ese ingreso no siempre sube con la edad."""
        bandas = ['18-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54']
        i = bandas.index(e['banda7'])
        if i == len(bandas) - 1:
            return 0
        formalidad = 'formal' if e.get('formal', 1) else 'informal'
        a, b = (self.tabla('esi_ingreso_categoria_formalidad', 'p50', 'categoria', 'cuenta_propia', 'banda_edad', banda,
                           'formalidad', formalidad) for banda in bandas[i:i + 2])
        return max(-0.06, min(0.06, (b / a) ** (1 / 5) - 1))

    def crecimiento_carrera(self, e):
        cid, t = e.get('carrera_id', -1), e.get('anos_titulado', 9)
        if cid < 0 or t >= 4:
            return 0
        a = self.tabla('mifuturo_carreras', f'ingreso_bruto_ano{t + 1}', 'carrera_id', cid)
        b = self.tabla('mifuturo_carreras', f'ingreso_bruto_ano{t + 2}', 'carrera_id', cid)
        return max(0, min(0.2, b / a - 1))

    # ------------------------------------------------------------------ evaluación
    def evaluar(self, expr, estado, azar=None):
        if isinstance(expr, (int, float)):
            return expr
        if expr not in self._arboles:
            self._arboles[expr] = parsear(expr)
        self._azar = azar or random.Random(0)
        return self._ev(self._arboles[expr].body, estado)

    def _ev(self, n, e):
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            if n.id not in e:
                raise ErrorExpresion('variable sin valor: ' + n.id)
            return e[n.id]
        if isinstance(n, ast.UnaryOp):
            v = self._ev(n.operand, e)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.BinOp):
            return BIN[type(n.op)](self._ev(n.left, e), self._ev(n.right, e))
        if isinstance(n, ast.Compare):
            return 1 if CMP[type(n.ops[0])](self._ev(n.left, e), self._ev(n.comparators[0], e)) else 0
        f, A = n.func.id, n.args
        ev = lambda i: self._ev(A[i], e)
        if f == 'si':
            return ev(1) if _verdad(ev(0)) else ev(2)
        if f == 'y':
            return 1 if all(_verdad(self._ev(a, e)) for a in A) else 0
        if f == 'o':
            return 1 if any(_verdad(self._ev(a, e)) for a in A) else 0
        if f == 'no':
            return 0 if _verdad(ev(0)) else 1
        args = [self._ev(a, e) for a in A]
        r = self._azar
        if f == 'en':
            return 1 if args[0] in args[1:] else 0
        if f in ('min', 'max'):
            return (min if f == 'min' else max)(args)
        if f == 'clamp':
            return max(args[1], min(args[2], args[0]))
        if f == 'exp':
            return math.exp(args[0])
        if f == 'ln':
            return math.log(args[0])
        if f == 'pow':
            return args[0] ** args[1]
        if f == 'abs':
            return abs(args[0])
        if f == 'redondear':
            return round(args[0])
        if f == 'k':
            return self.k(*args)
        if f == 'tabla':
            return self.tabla(*args)
        if f == 'tabla_o':
            try:
                return self.tabla(*args[1:])
            except ErrorExpresion:
                return args[0]
        if f == 'q_muerte':
            return self.q_muerte(*args)
        if f == 'luto':
            return self.luto(args[0], args[1], e)
        if f == 'falso':
            return 0
        if f == 'azar':
            return r.random()
        if f == 'azar_uniforme':
            return r.uniform(args[0], args[1])
        if f == 'azar_normal':
            return r.gauss(0, 1)
        if f == 'azar_entero':
            return r.randint(int(args[0]), int(args[1]))
        if f == 'azar_lognormal':
            p10, p50, p90 = args
            s = (math.log(p90) - math.log(p10)) / (2 * 1.2816)
            return math.exp(math.log(p50) + s * r.gauss(0, 1))
        raise ErrorExpresion('función sin implementar: ' + f)
