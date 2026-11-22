# {{cookiecutter.project_name}}: desarrollo

## Arranque

```bash
cp backend/.env.example backend/.env      # CORS_ORIGINS y, opcional, ANTHROPIC_API_KEY
cp frontend/.env.example frontend/.env    # VITE_API_URL
make install
make back    # http://localhost:{{cookiecutter.backend_port}}/docs
make front   # http://localhost:5173
make test
```

No hay base de datos: el juego no guarda estado en el servidor y las corridas de `/api/simulations` viven en memoria.

## Backend (`backend/app`)

Las dependencias van en una sola dirección: `api → services → (sim, repositories)`.

| Capa | Qué contiene |
|---|---|
| `sim/` | Dominio puro (numpy, sin FastAPI ni DB). `state.py` es el estado vectorizado, `engine.py` el loop Monte Carlo, `metrics.py` los resúmenes por año. |
| `sim/decisions/` | Una clase por decisión. Se registran solas al heredar de `Decision`. |
| `schemas/` | Modelos Pydantic de entrada y salida de la API. |
| `repositories/` | Persistencia detrás de un `Protocol` (hoy, en memoria). |
| `services/` | Casos de uso que orquestan motor y repositorio. |
| `api/` | Rutas delgadas. `deps.py` es el único lugar que elige implementaciones. |
| `core/` | Configuración y clientes externos. |

**Agregar una decisión:** crear una subclase en `sim/decisions/catalog.py` con `key`, `label` y `apply()` (o heredar de `ParametricDecision` y fijar tres números). Aparece sola en `GET /api/decisions`.

**Agregar un atributo del gemelo:** sumarlo a `State` (o usar `state.extra`) y resumirlo en `metrics.py`.

## Frontend (`frontend/src`)

- `app/`: shell de la app.
- `features/<feature>/`: todo lo de una funcionalidad (api, tipos, hooks, componentes); se expone por su `index.ts`.
- `shared/`: config, cliente HTTP y utilidades sin dominio.

Importa con el alias `@/` (apunta a `src/`).

## Plantilla

El proyecto sale de `template/` con cookiecutter. Para cambiar la estructura base, edita la plantilla y regenera desde la carpeta padre:

```bash
cookiecutter --no-input -f -o .. template
```
