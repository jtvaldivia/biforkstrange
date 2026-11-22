# BiforkStrange: desarrollo

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

## Gemelo: encuestas adaptativas (`backend/app/twin`, `frontend/src/features/twin`)

Pantalla en **http://localhost:5173/gemelo**. Cuatro flujos: preguntas adaptativas (CAT bayesiano sobre 26 dimensiones), examen a ciegas (el gemelo predice antes de que respondas), recalibración e informe.

- `twin/`: dominio puro. `dims.py` (catálogo y pesos de ajuste), `cat.py` (qué preguntar, actualización, claridad, deriva), `metrics.py` (acierto, calibración, log-score), `context.py` y `prompts.py`.
- `services/twin_brain.py`: llamadas a Claude con structured outputs. Sin `ANTHROPIC_API_KEY` usa `OfflineBrain` (preguntas de prueba, sin costo).
- `repositories/twin_profiles.py`: un documento JSON por persona con `version`. Toda escritura manda la versión del cliente; si quedó vieja, la API responde 409 con el perfil actual (una pestaña vieja no pisa datos más nuevos).
- Migración: `supabase/migrations/0002_twin_profiles.sql`.

**Explicaciones del simulador.** `sim/explain.py` arma el "por qué" de cada año a partir del modelo (no de un LLM): la decisión, el desgaste que arrastras y tus rasgos. `sim/personality.py` define cómo cada rasgo medido del gemelo ajusta las palancas de cada decisión (crecimiento, riesgo, desgaste), con peso según su certeza (sd 30 = no pesa, sd ≤ 12 = pesa entero). `POST /api/simulations/compare` corre A y B con la misma semilla para que la diferencia sea solo la decisión. Para agregar una decisión con explicación: define `why` en `catalog.py` y, si quieres, sus modificadores en `BY_DECISION`.

## Tu historia (`backend/app/story`, `frontend/src/features/story`)

La pantalla principal (`/`). La persona cuenta dónde está hoy y vive su historia año a año: cada año elige en un dilema y Claude narra el capítulo.

- **Qué pasa lo decide el motor; cómo se cuenta lo decide Claude.** `story/engine.py` simula 400 vidas con la misma semilla y sigue una (la tuya). Si en esa vida quedas sin pega o te quemas, el capítulo lo cuenta. Las demás vidas dan el contexto ("le pasa a 1 de cada 8").
- `story/qualitative.py` traduce los números a palabras ("plata justa", "energía al límite"). Son neutras en género porque el narrador las copia. Los números nunca salen al cliente.
- `story/prompts.py` y `story/teller.py`: apertura, capítulo (incluye el dilema siguiente), clasificación de respuestas libres a una decisión del catálogo, y epílogo. `OfflineTeller` sin API key.
- Las opciones de cada dilema son propias de la historia, pero cada una mapea a una clave del catálogo (`sim/decisions/catalog.py`), que es lo que mueve el motor.
- Si hay gemelo (`profile_id`), su contexto entra al prompt y sus rasgos ajustan las decisiones (`sim/personality.py`).
- **Cada año depende del anterior.** En el motor, `sim/carryover.py`: lo estudiado rinde los 3 años siguientes, volver tras un año sin pega cuesta (pero recuperas casi el sueldo de antes) y cambiarse de pega dos años seguidos sube el riesgo. En la historia, el narrador mantiene un `hilo` (dónde vive, trabajo, su gente, lo que quedó abierto) que recibe al año siguiente, y ve las opciones que ya ofreció para no repetirlas (`check_dilemma` rechaza repetidas o genéricas y reintenta).
- `choose` pide el número de capítulo que ve el cliente: un doble clic no escribe dos capítulos (409).
- Migración: `supabase/migrations/0003_stories.sql`.

## Plantilla

El proyecto sale de `template/` con cookiecutter. Para cambiar la estructura base, edita la plantilla y regenera desde la carpeta padre:

```bash
cookiecutter --no-input -f -o .. template
```
