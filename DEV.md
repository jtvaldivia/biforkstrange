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
| `sim/` | Dominio puro (numpy, sin FastAPI ni DB): el motor de simulación. Ver [`backend/MODELOS.md`](backend/MODELOS.md). |
| `sim/modules/` | Un archivo por módulo anual: trabajo, familia, finanzas, bienestar y red de contactos. |
| `sim/data/` | Tablas agregadas que usa el motor. Se regeneran con `make datos` desde la carpeta de microdatos, que no va al repo. |
| `cli.py` | Terminal para probar el simulador: `make jugar`, `make menu`, `make comparar`. |
| `schemas/` | Modelos Pydantic de entrada y salida de la API. |
| `repositories/` | Persistencia detrás de un `Protocol`: Supabase o memoria. |
| `services/` | Casos de uso que orquestan motor y repositorio. |
| `api/` | Rutas delgadas. `deps.py` es el único lugar que elige implementaciones. |
| `core/` | Configuración y clientes externos. |

**Agregar una decisión:** sumarla a `CATALOGO` e `intencion()` en `sim/decisions.py` y hacer que el módulo que corresponda lea esa intención. Aparece sola en `GET /api/decisions` y en el menú del juego.

**Agregar un atributo del gemelo:** sumarlo a `Estado` en `sim/state.py`, moverlo en un módulo y resumirlo en `sim/metrics.py`.

**Agregar o cambiar un parámetro:** va en `sim/params.py`, con su fuente y marcado como dato, derivado o supuesto.

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

## Plantilla

El proyecto salió de `template/` con cookiecutter. La plantilla ya no está al día: no tiene el kit de UI ni el motor de simulación, así que regenerar con `-f` sobrescribe trabajo. Úsala solo para crear un proyecto nuevo:

```bash
cookiecutter --no-input -f -o .. template
```
