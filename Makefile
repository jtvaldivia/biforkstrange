.PHONY: install back front test jugar menu comparar supuestos validar datos
PERFIL ?= perfiles/ejemplo.json
DATOS ?= ../../datos_laborales
install:
	cd backend && uv sync
	cd frontend && npm install
back:
	cd backend && uv run uvicorn app.main:app --reload --port 8000
front:
	cd frontend && npm run dev
test:
	cd backend && uv run pytest -q

# --- simulador en la terminal (ver backend/MODELOS.md); usa PERFIL=perfiles/tu_perfil.json
jugar:
	cd backend && uv run python -m app.cli jugar --perfil $(PERFIL)
menu:
	cd backend && uv run python -m app.cli menu --perfil $(PERFIL)
comparar:
	cd backend && uv run python -m app.cli comparar --perfil $(PERFIL)
supuestos:
	cd backend && uv run python -m app.cli supuestos
validar:
	cd backend && uv run python -m app.cli validar
datos:
	cd backend && uv run scripts/build_sim_data.py --datos "$(DATOS)"
