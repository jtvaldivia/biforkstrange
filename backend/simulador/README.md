# Paquete de datos del simulador de vida laboral

Todo lo que un simulador necesita para vivir una carrera en Chile de los 18 a los 50 años: las decisiones que se pueden tomar, lo que pasa sin que nadie decida, los parámetros con su fuente y las tablas de donde salen. No trae motor: cualquier simulador (el juego en JavaScript, un notebook en Python, un servicio) lo carga y lo ejecuta.

Versión 1.0.0, 21 de noviembre de 2026.

| Qué | Cuántos |
|---|---|
| Decisiones | 37, con 89 opciones y 132 resultados posibles |
| Eventos (pasan solos) | 10 |
| Parámetros con fuente y rango | 65 (27 dato, 28 mixto, 3 sintético, 7 supuesto) |
| Variables de estado | 86 |
| Tablas CSV | 50, con 3.860 filas |
| Fuentes citadas | 78 |
| Objetivos de validación | 38 |

## Archivos

| Archivo | Contenido |
|---|---|
| `decisiones.json` | Decisiones: cuándo aparecen, cuánto pesan, opciones, resultados con probabilidad y efectos, evidencia |
| `eventos.json` | Despidos, ascensos, ofertas, recesiones, cierre de la startup y cáncer: probabilidad anual y efectos |
| `parametros.json` | Cada número del modelo con unidad, fuente, calidad y rango para análisis de sensibilidad |
| `estado.json` | Variables del gemelo: tipo, dominio, unidad y cómo se inicia o se deriva |
| `fuentes.json` | Cita, enlace, país, tipo y estado de verificación de cada fuente |
| `objetivos_validacion.json` | Lo que una cohorte simulada debería reproducir (ESI, EPS, IARC) |
| `tablas/*.csv` y `tablas/indice.json` | Datos en formato largo; el índice describe cada columna, la población, el ponderador y los límites |
| `esquema.json` | JSON Schema de decisiones, eventos, opciones y efectos |
| `catalogo_plano.csv` | Una fila por resultado posible, para revisar el catálogo en una planilla |
| `referencia/expresiones.py` y `.js` | Evaluador de expresiones en Python y JavaScript, con la misma semántica |
| `referencia/validar.py` | Revisión completa del paquete |
| `referencia/paridad.py` y `.cjs` | Compara los dos evaluadores |

## Cómo lo usa un simulador

Un paso por año:

1. **Derivar.** Recalcula las variables con `inicio: deriva` en `estado.json` (`banda3`, `banda7`, `percentil`, `estamento`...). `Paquete.derivar()` en `expresiones.py` es la implementación de referencia.
2. **Elegir la decisión del año.** Primero las de `aparicion.tipo = forzada` cuyo `cuando` se cumple (cesantía, primera pega, licencia de salud mental). Si no hay, sortea entre las `carta` que aplican con probabilidad proporcional a `aparicion.peso`. Las que tienen `proactiva: true` el jugador las puede pedir aunque no salgan sorteadas.
3. **Mostrar opciones.** Solo las que cumplen `requisito`. `opciones_desde_tabla` genera una opción por fila de una tabla (las 252 carreras), con las columnas disponibles como `fila_<columna>`.
4. **Sortear el resultado.** Cada resultado tiene `prob`: un número, una expresión o `'resto'` (1 menos la suma de los demás). Aplica sus `efectos` en orden y, si tiene `luego`, encadena esa decisión o evento en el mismo año.
5. **Eventos.** Para cada evento cuyo `cuando` se cumple, sortea con `prob_anual` y luego uno de sus resultados.
6. **Cerrar el año.** Suma 1 a `edad`, aplica el ahorro, descuenta un año a los efectos con `duracion` y revierte los que vencen, y aplica los efectos con `en_anios` que se cumplen.

### Efectos

```json
{"var": "sueldo", "op": "multiplica", "valor": "1 + k('PREMIO_MAGISTER')", "duracion": 2, "cuando": "estado == 'empleado'"}
```

- `op`: `suma`, `multiplica` o `fija`.
- `duracion`: años que dura. Sin el campo, el efecto es permanente. Al vencer se revierte: se resta lo sumado, se divide por lo multiplicado o se vuelve al valor anterior.
- `en_anios`: el efecto se cumple al cerrar ese año, contando el año de la decisión como 1 (un título que estudias de noche: `"en_anios": 3`). Se evalúa con el estado de ese momento, incluido su `cuando`. Con `aviso` (`{"nombre": ..., "texto": ...}`), ese año sale como noticia.
- `cuando`: el efecto solo se aplica si la condición se cumple en ese momento.
- Las variables `modificador` (`tiempo_con_tu_gente`, `p_encontrar`, `riesgo_acv`...) no son resultados. El simulador las usa dentro de sus fórmulas, por ejemplo para calcular el indicador de vida personal o la probabilidad de encontrar trabajo.
- Las variables `eleccion` (`rubro_destino`, `region_destino`, `ocupacion_destino`) las elige el jugador dentro de la opción antes del sorteo.

## Expresiones

Un subconjunto que se lee igual en Python y en JavaScript:

- Números, textos entre comillas simples y variables de `estado.json`.
- `+ - * / %` y una sola comparación por nivel: `< <= > >= == !=`. Las comparaciones devuelven 1 o 0.
- No hay `and`, `or` ni `if`. Se usan funciones perezosas: `si(cond, a, b)`, `y(a, b, ...)`, `o(a, b, ...)`, `no(a)`.

| Función | Qué hace |
|---|---|
| `k('ID')`, `k('ID', clave)`, `k('ID', clave, respaldo)` | Parámetro de `parametros.json`; con clave, el valor de esa clave o índice |
| `tabla('nombre', 'columna', 'dim1', v1, 'dim2', v2, ...)` | Valor de la primera fila que calza con todas las dimensiones; error si la celda está vacía |
| `tabla_o(respaldo, 'nombre', 'columna', ...)` | Igual, pero devuelve el respaldo si no hay fila o la celda está vacía (celdas con menos de 30 casos) |
| `q_muerte(edad, sexo)` | Probabilidad anual de morir (Gompertz INE 2025) |
| `luto(quien, anos)` | Caída de satisfacción con la vida (0-10) por la muerte de `mama`, `papa` o `abuela` hace `anos` años. Ninguna regla del paquete la usa hoy |
| `en(x, a, b, ...)` | 1 si x es alguno de los valores |
| `min`, `max`, `clamp(x, lo, hi)`, `exp`, `ln`, `pow`, `abs`, `redondear` | Matemática |
| `azar()`, `azar_uniforme(a, b)`, `azar_normal()`, `azar_lognormal(p10, p50, p90)`, `azar_entero(a, b)` | Números al azar; el simulador pasa su propio generador para que una semilla repita la partida |
| `falso()` | 0; marca decisiones internas que solo se llaman con `luego` |

Ejemplo, probabilidad anual de perder el trabajo:

```
k('P_SEPARACION', banda3) * k('MULT_DESPIDO_TIPO', tipo_empleador) * si(tipo_empleador == 'publico', 1, k('MULT_DESPIDO_RUBRO', rubro, 1)) * si(recesion, 1.4, 1)
```

En Python:

```python
import random, sys
sys.path.insert(0, 'simulador/referencia')
from expresiones import Paquete
pq = Paquete('simulador')
gemelo = pq.derivar({'edad': 31, 'sexo': 'm', 'edu': 'universitaria', 'estado': 'empleado', 'tipo_empleador': 'pyme', 'rubro': 'Comercio', 'nivel': 1, 'sueldo': 1100000, 'carrera_id': 11, 'region': 'rm'})
pq.evaluar("k('P_SEPARACION', banda3) * k('MULT_DESPIDO_TIPO', tipo_empleador)", gemelo, random.Random(7))
```

En JavaScript, `Expresiones.crear({ parametros, tablas, azar })` recibe los parámetros como `{ID: valor}` y las tablas ya leídas como listas de objetos. `paridad.cjs` muestra cómo leer los CSV.

## Calidad

Cada decisión, opción, evento y parámetro trae `calidad`:

- **dato**: medido en Chile o leído en la fuente original.
- **mixto**: dato de otro país, o dato chileno con un ajuste del equipo.
- **sintetico**: sorteado o calibrado con semilla fija a partir de una distribución real (ESI, INE, Get on Board, SIES), pero no medido para esa unidad. Ejemplo: el sueldo relativo de una empresa del catálogo. Cada número sintético tiene un parámetro de dispersión que se puede llevar a cero.
- **supuesto**: sin fuente. Hay que decirlo si se muestra a un jurado.

De las 87 opciones, 38 son supuesto. La mayoría son las opciones de no hacer nada ("quedarte", "no"), que no mueven el estado. Las decisiones que dependen casi solo de supuestos son `practica`, `intercambio`, `jefatura`, `bootcamp` y `volver_a_chile`.

En `fuentes.json`, `verificacion` dice si el número salió del archivo original (descargado), del paper (leído en la fuente), de un resumen o de prensa (por confirmar).

Cinco decisiones traen `creencia_vs_dato`, el contraste entre lo que la gente cree y lo que muestran los datos: magíster, cambiarse de pega, pedir aumento, emprender y año sabático.

## Tablas

El índice (`tablas/indice.json`) describe cada columna con su unidad, la población, el ponderador y una `advertencia` con los límites. Los grupos:

- **ESI 2025 (INE), microdatos**: ingreso por sexo, edad y educación; región; categoría (empleador, cuenta propia, asalariado privado y público) con formal e informal; tamaño de empresa; ocupación; rubro por edad; jornada parcial e ingreso por hora; informalidad; desocupación y quién busca su primer trabajo.
- **Otras del INE**: ENE (jornada parcial, informalidad), ENUT (tiempo con tu gente según horas), mortalidad 2025 y flujos laborales 2025 por rubro y tamaño.
- **Paneles chilenos**: EPS 2024 (términos de empleo por motivo y edad, duración de la cesantía) y ELSOC (transiciones entre ocupado, desocupado e inactivo; efectos en bienestar).
- **Educación y Estado**: 252 carreras de mifuturo (116 con alguna celda imputada, marcada en la columna `imputado`), estamentos del Servicio Civil.
- **Internacionales**: NY Fed SCE (ofertas, contraofertas, salario de reserva), Y Combinator (desenlaces, supervivencia, por industria, las 19 chilenas), JobHop (duración de empleos y cambios de ocupación), Get on Board (sueldos en dólares), Ask a Manager (sueldos en EE.UU.), transiciones de ocupación en EE.UU., Job-to-Job del Census, aplicabilidad de IA por ocupación (Microsoft), cáncer (IARC) y duelo (Leopold y Lechner).

Dos tablas de rubro no son intercambiables: `esi_ingreso_rubro` clasifica por la empresa que paga y `esi_ingreso_rubro_edad` por la empresa donde se trabaja. Para decisiones usa la segunda.

## Regenerar y validar

Desde `datos_laborales/`:

```bash
python3 -I scripts/simulador/tablas_base.py      # tablas desde derivados/*.json
python3 -I scripts/simulador/esi_extra.py         # tablas nuevas de la ESI (lee esi_ine/esi_2025_personas.csv)
python3 -I scripts/simulador/internacional.py     # SCE, YC, Get on Board, Ask a Manager, transiciones
python3 -I scripts/simulador/construir.py         # JSON del paquete, índice y catálogo plano
python3 -I simulador/referencia/validar.py 4000   # revisión completa
python3 -I simulador/referencia/paridad.py /tmp/casos.json && node simulador/referencia/paridad.cjs /tmp/casos.json
```

`internacional_jobhop.py` necesita pyarrow; se corrió con la rueda que estaba en la caché de uv.

El validador revisa que cada expresión respete la gramática, que use variables, parámetros, tablas y columnas que existen, que cada fuente citada esté en `fuentes.json` y que cada `luego` apunte a algo. Después evalúa todo el catálogo en miles de estados al azar y exige pesos positivos, probabilidades entre 0 y 1 que no sumen más de 1, y efectos con números finitos o categorías válidas. Última corrida: 290 expresiones y 4.000 estados, sin errores. La paridad dio 57.000 de 57.000 casos iguales entre Python y JavaScript.

## Lo que falta

- **Trabajo por cuenta propia en el motor del juego.** La decisión `independizarse` y las tablas de la ESI ya están; el motor del juego todavía no la usa. Es la mayor brecha del benchmark: 13% a 24% de los ocupados en Chile, 3% a 4% en el juego.
- **Sin edad en el SCE.** La tabla de ofertas es para menores de 62. El único corte por edad sale de las series publicadas por la NY Fed (`sce_publicado_por_edad`).
- **Supervivencia de empresas en Chile.** El 80% a 1 año y el 43,2% a 5 años vienen de una fuente secundaria. El INE no publica tablas de supervivencia por cohorte.
- **Sesgo de YC.** Las startups de Y Combinator son una élite; una startup chilena cualquiera cierra más.
