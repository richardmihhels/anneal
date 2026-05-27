.PHONY: setup dev test lint build schemas

setup:
	uv sync
	cd dashboard && npm install

dev:
	docker-compose up -d
	cd dashboard && npm run dev &
	uv run uvicorn core.main:app --reload --port 8000

test:
	uv run pytest -v

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy core/src worker/src shared/src
	cd dashboard && npm run typecheck

build:
	cd dashboard && npm run build

schemas:
	uv run python shared/generate_schemas.py
