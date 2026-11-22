# Agarrar la pala: desarrollo

## Arranque

```bash
cp backend/.env.example backend/.env      # SUPABASE_URL y SUPABASE_SERVICE_KEY
cp frontend/.env.example frontend/.env    # VITE_SUPABASE_URL y VITE_SUPABASE_ANON_KEY
make install
make back    # http://localhost:8000/docs
make front   # http://localhost:5173
make test
```

Sin credenciales de Supabase el backend guarda las corridas en memoria.

## Backend (`backend/app`)

Las dependencias van en una sola dirección: `api → services → (sim, repositories)`.

| Capa | Qué contiene |
|---|---|
| `sim/` | Dominio puro (numpy, sin FastAPI ni DB). `state.py` es el estado vectorizado, `engine.py` el loop Monte Carlo, `metrics.py` los resúmenes por año. |
| `sim/decisions/` | Una clase por decisión. Se registran solas al heredar de `Decision`. |
| `schemas/` | Modelos Pydantic de entrada y salida de la API. |
| `repositories/` | Persistencia detrás de un `Protocol`: Supabase o memoria. |
| `services/` | Casos de uso que orquestan motor y repositorio. |
| `api/` | Rutas delgadas. `deps.py` es el único lugar que elige implementaciones. |
| `core/` | Configuración y clientes externos. |

**Agregar una decisión:** crear una subclase en `sim/decisions/catalog.py` con `key`, `label` y `apply()` (o heredar de `ParametricDecision` y fijar tres números). Aparece sola en `GET /api/decisions`.

**Agregar un atributo del gemelo:** sumarlo a `State` (o usar `state.extra`) y resumirlo en `metrics.py`.

### Motor del juego (`backend/app/sim/motor`)

El juego corre sobre el paquete de datos de `backend/simulador/` (43 decisiones, 16 eventos, 67 parámetros, 50 tablas). El motor no reescribe esas reglas: las ejecuta. Para cambiar una probabilidad o un efecto se edita el paquete, no el código.

| Archivo | Qué hace |
|---|---|
| `paquete.py` | Carga el paquete y traduce cada fórmula a una función de Python |
| `azar.py` | Dados con suerte compartida: cada sorteo se identifica por gemelo, año y sitio |
| `perfil.py` | De los 9 campos del perfil a las variables iniciales |
| `motor.py` | El año: mundo, decisión, dado del resultado, eventos, cierre |
| `politicas.py` | Quién decide: la persona, los gemelos por inercia o la población (pesos calibrados) |
| `gemelos.py` | 500 gemelos por opción con los mismos dados |
| `partida.py` | La partida de la persona; no guarda nada, se vuelve a jugar en cada llamada |
| `validacion.py` | Cohorte de 5.000 personas contra las 37 metas del paquete y el panel ELSOC |
| `supuestos.py` | Cada parámetro con su calidad (dato, mixto, supuesto), fuente y país |
| `empresas.py` | Un empleador u oferta real (SII, Get on Board, Y Combinator, empleospublicos.cl) como ejemplo de cada opción de trabajo; no entra a la simulación |

API: `GET /api/juego/catalogo`, `POST /api/juego/dudas`, `POST /api/juego/partida`, `GET /api/juego/supuestos`, `GET /api/juego/validacion?n=1000`. Pantalla: `frontend/src/features/juego` (ruta `/`).

```bash
make jugar DUDA=unirse_a_startup   # partida en el terminal
make comparar DUDA=oferta_externa  # solo la tabla de gemelos de una decisión
make validar                       # cuántas metas de Chile cuadran
make supuestos CALIDAD=supuesto    # qué números siguen siendo supuestos del equipo
```

Las empresas reales están en `backend/data/empresas/` y se regeneran con `backend/scripts/datos_empresas.py`. Son referencia: la historia de cada carta usa empresas ficticias (`narrativa.py`) para no inventar hechos sobre empresas que existen.

Los supuestos que pone el motor (lo que el paquete no define) están listados en `docs/motor/TICKETS.md`; el resultado de la validación, en `docs/motor/VALIDACION.md`.

El esqueleto anterior (`sim/engine.py`, `sim/decisions/`, `sim/labor.py`) sigue en `/simulacion` y en `make simular`, pero el juego ya no lo usa.

## Frontend (`frontend/src`)

- `app/`: shell de la app.
- `features/<feature>/`: todo lo de una funcionalidad (api, tipos, hooks, componentes); se expone por su `index.ts`.
- `shared/`: config, cliente HTTP, Supabase y utilidades sin dominio.

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

Las escenas animadas usan un reloj CSS (`--vd-t`): pon `scene="once"` en el `Screen` y usa `revealAt` en indicadores y notificaciones para que entren en su momento (ver `shared/ui/scene.ts`). Catálogo vivo y las 8 pantallas armadas con el kit en **http://localhost:5173/ui** (`features/ui-kit`).

## Deploy (Render)

La rama `produccion` es lo que está en línea. Para publicar, abre un PR de `main` a `produccion` y mergéalo. El CI (`.github/workflows/ci.yml`) corre los tests y el build, y Render despliega solo si pasan.

`render.yaml` define los dos servicios: la API (`agarrar-la-pala-api`, Python, plan Standard) y el front (`agarrar-la-pala`, sitio estático con rewrite a `index.html`). El front se rebuildea solo si cambia algo en `frontend/`.

Antes de pushear, `uv.lock` tiene que estar al día (`cd backend && uv lock`): Render instala con `uv sync --frozen`.

## Plantilla

El proyecto sale de `template/` con cookiecutter. Para cambiar la estructura base, edita la plantilla y regenera desde la carpeta padre:

```bash
cookiecutter --no-input -f -o .. template
```
