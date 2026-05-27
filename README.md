# Anneal

Dependabot for AI agent prompts and skills.

## Setup

```sh
uv sync
cd dashboard && npm install
```

Copy `.env.example` to `.env` and fill in secrets.

## Commands

| Command          | Description                                      |
|------------------|--------------------------------------------------|
| `make dev`       | Start Postgres + ClickHouse, API, and dashboard  |
| `make test`      | Run Python tests                                 |
| `make lint`      | ruff + mypy + tsc                                |
| `make build`     | Production build of the dashboard                |
| `make schemas`   | Regenerate JSON schemas from pydantic models     |

## Architecture

- `core/` — FastAPI optimization engine (Python 3.12)
- `worker/` — Weekly optimization job runner (Python 3.12)
- `dashboard/` — Next.js 15 App Router UI
- `shared/` — Pydantic models + JSON schemas consumed by both sides
