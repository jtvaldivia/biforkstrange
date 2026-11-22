# Bifurca: desarrollo

## Arranque

```bash
cp backend/.env.example backend/.env      # CORS_ORIGINS y, opcional, ANTHROPIC_API_KEY
cp frontend/.env.example frontend/.env    # VITE_API_URL
make install
make back    # http://localhost:8000/docs
make front   # http://localhost:5173
make test
```

No hay base de datos: el juego no guarda estado en el servidor.

## Producción (Render)

`make back` es para desarrollo: un solo proceso con `--reload`, que atiende las partidas en fila (diez
`/partida` a la vez esperan ~2 s cada una). En producción corre `backend/scripts/prod.sh` (o `make prod`
en local): uvicorn con `--workers`, sin `--reload`, en `0.0.0.0:$PORT`.

**Comando de arranque del servicio de la API** (Render → Settings → Start Command), con *Root Directory*
`backend`:

```bash
sh scripts/prod.sh
```

Si el servicio no usa `backend` como raíz, `sh backend/scripts/prod.sh`. El script usa `uv run` si `uv` está
instalado y si no `python -m uvicorn` con las dependencias ya instaladas en el build.

Variables de entorno:

| Servicio | Variable | Ejemplo | Para qué |
|---|---|---|---|
| API | `ANTHROPIC_API_KEY` | `sk-ant-...` | Leer el CV con Claude y narrar. Sin ella, el perfil se llena a mano y los textos salen de plantillas |
| API | `CORS_ORIGINS` | `["https://bifurca.onrender.com"]` | Orígenes que pueden llamar a la API. Va en **formato JSON** (una lista entre corchetes con comillas dobles); una URL suelta no se lee |
| API | `WEB_CONCURRENCY` | `2` | Procesos de uvicorn. Cada uno usa ~170 MB después de jugar: 2 caben en 512 MB. Más procesos solo ayudan si el plan tiene más CPUs |
| Front | `VITE_API_URL` | `https://bifurca-api.onrender.com` | URL de la API. Vite la mete en el build: si cambia, hay que volver a construir el front |

`PORT` lo pone Render. En local, el backend lee estas mismas variables de `backend/.env` (incluida
`ANTHROPIC_API_KEY`); una variable de entorno pesa más que el `.env`.

El juego no guarda estado entre llamadas, así que cualquier proceso puede atender cualquier request. Lo
único en memoria por proceso es el caché de comparaciones (`partida.py`), que se rehace si falta.

## Backend (`backend/app`)

Las dependencias van en una sola dirección: `api → services → sim`.

| Capa | Qué contiene |
|---|---|
| `sim/motor/` | El motor del juego (abajo). Dominio puro, sin FastAPI. |
| `sim/data/` | El panel ELSOC que usa la validación (`motor/validacion.py`). |
| `schemas/` | Modelos Pydantic de entrada y salida de la API. |
| `services/` | Lo que usa Claude: leer el perfil y narrar. |
| `api/` | Rutas delgadas. |
| `core/` | Configuración y clientes externos. |

**Agregar una decisión:** va en el paquete (`backend/simulador/decisiones.json`), no en el código. Ver [docs/COMO-FUNCIONA.md](docs/COMO-FUNCIONA.md).

### Motor del juego (`backend/app/sim/motor`)

El juego corre sobre el paquete de datos de `backend/simulador/` (decisiones, eventos, parámetros y tablas; los conteos, con `make supuestos`). El motor no reescribe esas reglas: las ejecuta. Para cambiar una probabilidad o un efecto se edita el paquete, no el código.

| Archivo | Qué hace |
|---|---|
| `paquete.py` | Carga el paquete y traduce cada fórmula a una función de Python |
| `azar.py` | Dados con suerte compartida: cada sorteo se identifica por copia, año y sitio |
| `perfil.py` | De los 9 campos del perfil a las variables iniciales |
| `motor.py` | El año: mundo, decisión, dado del resultado, eventos, cierre |
| `politicas.py` | Quién decide: la persona, las copias por inercia o la población (pesos calibrados) |
| `gemelos.py` | 50 mundos: en cada uno la copia vive todas las opciones con los mismos dados |
| `partida.py` | La partida de la persona; no guarda nada, se vuelve a jugar en cada llamada |
| `validacion.py` | Cohorte de 5.000 personas contra las 37 metas del paquete y el panel ELSOC |
| `supuestos.py` | Cada parámetro con su calidad (dato, mixto, supuesto), fuente y país |
| `empresas.py` | Un empleador u oferta real (SII, Get on Board, Y Combinator, empleospublicos.cl) como ejemplo de cada opción de trabajo; no entra a la simulación |

API: `GET /api/juego/catalogo`, `POST /api/juego/dudas`, `POST /api/juego/partida`, `GET /api/juego/supuestos`, `GET /api/juego/validacion?n=1000`. Pantalla: `frontend/src/features/juego` (ruta `/`).

```bash
make jugar DUDA=unirse_a_startup   # partida en el terminal
make comparar DUDA=oferta_externa  # solo la tabla de copias de una decisión
make validar                       # cuántas metas de Chile cuadran
make supuestos CALIDAD=supuesto    # qué números siguen siendo supuestos del equipo
```

Las empresas reales están en `backend/data/empresas/` y se regeneran con `backend/scripts/datos_empresas.py`. Son referencia: la historia de cada carta usa empresas ficticias (`narrativa.py`) para no inventar hechos sobre empresas que existen.

Los supuestos que pone el motor (lo que el paquete no define) están listados en `docs/motor/TICKETS.md`; el resultado de la validación, en `docs/motor/VALIDACION.md`.

## Frontend (`frontend/src`)

- `app/`: shell de la app.
- `features/<feature>/`: todo lo de una funcionalidad (api, tipos, hooks, componentes); se expone por su `index.ts`.
- `shared/`: config, cliente HTTP y utilidades sin dominio.

Importa con el alias `@/` (apunta a `src/`).

### Kit de UI (`shared/ui`)

Componentes del Claude Design "Gemelo Laboral · simulador de vida". Todo se importa desde `@/shared/ui`; los estilos (`shared/ui/styles/vida.css`, clases `vd-*`) se cargan una vez en `main.tsx`. La paleta vive en las variables de `:root` de ese archivo.

- Layout: `Screen` (tono `dia`/`noche`, `scene`), `ScreenHeader`, `ScreenFooter`, `Stack`, `Row`, `Panel`, `SunCard`, `NightBand`, `SlowReveal`
- Texto: `Heading`, `Text`, `Meta`, `Pill`, `BigNumber`, `Narrative`
- Acciones y controles: `Button`, `IconButton`, `Chip`, `ChipGroup`, `Segmented`, `Slider`, `Tag`
- Juego: `IndicatorGrid`/`Indicator` (dinero, carrera, bienestar, vida), `DecisionCard`/`DecisionList` + `DecisionArt`
- Personas: `Notification`, `Avatar`, `PeopleTally`, `DotRow`, `DotLegend`, `MissedList`
- Gráficos: `LinesChart`, `RangeCompare` (rangos Monte Carlo A vs B), `VisitsTimeline`, `StationTimeline`, `YearTicker`
- Escenas: `LifePathHero`, `TravelScene`, `OfficeScene`

Las escenas animadas usan un reloj CSS (`--vd-t`): pon `scene="once"` en el `Screen` y usa `revealAt` en indicadores y notificaciones para que entren en su momento (ver `shared/ui/scene.ts`).

## Plantilla

El proyecto sale de `template/` con cookiecutter. Para cambiar la estructura base, edita la plantilla y regenera desde la carpeta padre:

```bash
cookiecutter --no-input -f -o .. template
```
