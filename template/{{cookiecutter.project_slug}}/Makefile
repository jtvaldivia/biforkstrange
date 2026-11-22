.PHONY: install back front test
install:
	cd backend && uv sync
	cd frontend && npm install
back:
	cd backend && uv run uvicorn app.main:app --reload --port {{cookiecutter.backend_port}}
front:
	cd frontend && npm run dev
test:
	cd backend && uv run pytest -q -n auto
