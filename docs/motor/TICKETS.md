# Motor del paquete: tickets

Rama: `feat/trayectoria-ultimo-trabajo`. Reemplaza al esqueleto (`sim/engine.py`) como motor del juego.

**Qué ve la persona.** Llena su perfil, elige la duda que la trajo y ve cómo les fue a 500 gemelos suyos con cada opción. Elige, un dado decide qué le pasa a ella, avanza un año y el mundo le reparte otra carta. A los 10 años ve su vida frente a la de sus gemelos.

**De dónde salen las reglas.** Del paquete de datos, copiado en `backend/simulador/`: 43 decisiones, 16 eventos, 67 parámetros, 90 variables y 49 tablas. El motor no reescribe esas reglas: las ejecuta.

## Piezas (`backend/app/sim/motor/`)

| Archivo | Qué hace |
|---|---|
| `paquete.py` | Carga el paquete y traduce cada fórmula a una función de Python (unas 50 veces más rápido que el evaluador de referencia, con el mismo resultado) |
| `azar.py` | Dados con suerte compartida: cada sorteo se identifica por gemelo, año y sitio, no por orden |
| `perfil.py` | De los 9 campos del perfil a las 74 variables iniciales |
| `motor.py` | El año: mundo, decisión, dado del resultado, eventos, cierre. Se puede detener, copiar y seguir |
| `politicas.py` | Quién decide: la persona, los gemelos por inercia, o la población |
| `gemelos.py` | 500 gemelos por opción, con los mismos dados |
| `partida.py` | La partida de la persona, sin guardar nada: se vuelve a jugar entera en cada llamada |

## Tickets

| # | Ticket | Listo cuando | Estado |
|---|---|---|---|
| M1 | Cargar y compilar el paquete | Medido: 500 gemelos por 10 años en 0,1 s | Hecho |
| M2 | Loop anual y efectos con duración | Una vida corre 32 años sin error con las 37 decisiones laborales | Hecho |
| M3 | Gemelos y partida | Comparar opciones toma cerca de 1 s; una partida de 10 años se juega completa | Hecho |
| M4 | API del juego | `GET /api/juego/catalogo`, `POST /api/juego/dudas`, `POST /api/juego/partida` | Hecho |
| M5 | Pruebas del núcleo y revisión | Paridad con el evaluador de referencia, suerte compartida, efectos con duración, repetición exacta de una partida; revisión buscando errores sembrados | En curso |
| M6 | Validar contra Chile y calibrar | Cohorte de 5.000 desde los 18 contra las 37 metas del paquete; informe con cuántas cuadran | Hecho: 25 a 26 de 37 (ver `VALIDACION.md`) |
| M7 | Jugar desde el terminal | `make jugar` lleva una partida completa; `make comparar` y `make validar` | Hecho |
| M8 | Pantalla del juego | Perfil, duda, carta con opciones lado a lado, dado, año siguiente, cierre | Hecho |
| M9 | Aplicar el feedback de M5 y M6 | Tests en verde; `DEV.md` actualizado | En curso: aplicado lo de M6, M7 y M8 |
| M10 | Perfil armado por tu Claude | La app da un prompt; lo pegas en tu Claude, que te conoce; su respuesta (bloque `gemelo-laboral`) se pega o sube en la app y llena el perfil y la duda sin llamar a un modelo. Texto libre: lo lee Claude si hay credenciales | Hecho (`services/perfil_doc.py`, `make jugar` con `--desde`, `python -m app.cli prompt`) |
| M11 | Cartas con historia | Cada carta cuenta quién te escribe y desde qué empresa, según tu rubro y tipo de empresa; sin cifras en el texto | Hecho para 23 decisiones (`motor/narrativa.py`); el resto muestra la pregunta del paquete |
| M12 | Errores pendientes de la revisión del núcleo | 21 hallazgos que eran tests `xfail(strict=True)` en `tests/test_motor_*.py` | 1 corregido (dados repetidos en el mismo año); quedan 20. Los tests se sacaron para acelerar la suite: la descripción de cada uno está en `git show c7136b9:backend/tests/test_motor_hallazgos.py` |

## Reglas que el paquete deja al simulador (supuestos del motor)

El paquete dice qué pasa con cada decisión y evento. Esto lo decide el motor y hay que decirlo si se muestra:

- **Recesión al inicio del año**, para que la decisión y los eventos del año ya la vean.
- **Los efectos de un resultado leen el estado de antes del resultado.** Así "el sueldo queda en 0" y "el finiquito es sueldo por años" funcionan juntos.
- **Cierre de año:** ahorro según la tasa del percentil, retorno real de 3%, pago del crédito con 10% del sueldo, +1,5 de oficio por año trabajado, antigüedad, titulación al terminar los semestres.
- **Quien estudia algo que no está en el catálogo de carreras:** dura 8 semestres y se titula universitario; 5 y técnico si su institución es un IP o un CFT; con un título universitario, es un postgrado de 4 (`perfil.SEMESTRES_SIN_CARRERA`). Sin dato de cuánto lleva, entró a los 18 y va al día.
- **Rubro del primer empleo:** se sortea según cuánta gente ocupada hay en cada rubro (ESI).
- **Salida del trabajo por cuenta propia:** 5,5% al año vuelve a buscar empleo (calibrado contra la proporción de independientes por edad). El paquete no trae esa salida.
- **Sin trabajo no hay sueldo:** si una regla deja buscando sin llevar el sueldo a cero, el motor lo hace y guarda el último sueldo.
- **Empleo sin tipo de empresa o con rubro incoherente:** se sortea el tipo de empresa; el rubro "Administración pública" queda solo para el Estado.
- **La partida dura 10 años de edad**, no 10 rondas: un doctorado ocupa 5.
- **Dentro de una opción** (a qué rubro, a qué región), si la persona no elige, los gemelos van al rubro que mejor paga y a la región con más gente.
- **Valores iniciales que la persona no declara:** contactos 30, oficio 50, ahorro de dos sueldos, sin pareja ni hijos.
- **Cómo deciden los gemelos:** no buscan cambios; cuando la vida los obliga (cesantía, una oferta) responden con pesos fijos (`politicas.py`).
- **El alza anual descuenta el ascenso promedio, no el tuyo** (`ASCENSO_POBLACION`, supuesto). El perfil por edad de la ESI ya trae los ascensos promedio, así que se resta la probabilidad de ascenso promedio de la población de tu tramo de edad por el alza media de un ascenso (7,5%). Quien asciende más que el promedio gana más. El número sale de la cohorte de validación; si cambian el ascenso o los pesos, hay que medirlo de nuevo.
- **El fundador que ya tenía empresa parte de su sueldo declarado** (variable `base_empresa`). Su empresa gana, cada año, `base_empresa × (1 + años de empresa / 4) × su suerte` (la regla del paquete), con `base_empresa = sueldo declarado / (1 + años de empresa / 4)`: el primer año gana, en la mediana, lo que declaró. Quien recién emprende parte de `MICRO_MEDIANA` (400 mil, EME). Supuesto a revisar: la suerte del año (lognormal 0,3 a 4) es la misma que la de quien recién emprende, aunque de una empresa ya andando se sabe más, y el crecimiento por años de empresa no tiene tope.
- **El ingreso por cuenta propia crece con la edad como en la ESI** (evento `alza_independiente`, variable derivada `crecimiento_cuenta_propia`). Cada año se multiplica por la razón entre la mediana de cuenta propia de la banda de edad siguiente y la de la actual (`esi_ingreso_categoria_formalidad`, formal o informal según `formal`), anualizada y acotada a ±6%. Supuestos a revisar: es un corte transversal leído como trayectoria (como `crecimiento_esi`), las medianas por banda tienen ruido de muestra (por eso el formal sube y baja por tramos) y no hay ruido individual ni efecto de la recesión.
- **Solo lo laboral:** fuera las 6 decisiones de vida personal y los eventos de salud, duelo y pareja.
