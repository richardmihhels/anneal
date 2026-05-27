# Anneal

Anneal is Dependabot for AI agent prompts and skills.

It ingests production traces from a LangGraph support agent, clusters repeated
failures, tries prompt or skill changes against a held-out eval set, and opens a
GitHub PR only when the candidate beats the baseline. If the evidence is weak,
Anneal stays silent.

## V1 Scope

The first customer is a lead AI engineer at a 50-500 person company running a
LangGraph customer-support agent in production.

V1 includes:

- Org-scoped dashboard with a signed local credentials session.
- SDK package for LangGraph/LangChain callback tracing.
- FastAPI ingestion for LangSmith-shaped runs and OTLP JSON.
- Weekly worker pipeline: cluster, optimize, evaluate, publish PR or stay quiet.
- Safety model based on holdout separation, judge calibration, and statistical gates.

Auth choice: Auth.js. The repo currently uses a small signed credentials adapter
in `dashboard/lib/auth.ts` so local development and the smoke test work without
a hosted identity provider. The session shape is intentionally provider-neutral:
replace the local adapter with an Auth.js provider before hosted signup and
billing.

## Quickstart

```sh
uv sync
cd dashboard && npm install
```

Copy `.env.example` to `.env` if you need real service credentials. Local demos
run without LLM or GitHub credentials by using fakes and Prompt 7 synthetic run
records.

Start everything:

```sh
make dev
```

Open `http://localhost:3000/login`, continue to the Prompt 7 demo org, then use:

- `Overview` for eval trend, regressions prevented, and PRs shipped.
- `Runs` for optimization timelines and run details.
- `Connect` for SDK setup and the org id to send with traces.

## SDK Quickstart

Install the package in your agent repo:

```sh
pip install anneal-sdk[langchain]
```

For local development from this monorepo:

```sh
pip install -e ./sdk[langchain]
```

Set the endpoint and organization from the Connect page:

```sh
export ANNEAL_ENDPOINT=http://localhost:8000
export ANNEAL_ORG_ID=org_demo
export ANNEAL_API_KEY=dev_optional
```

Attach the callback handler to a LangGraph invocation:

```python
from anneal_sdk import AnnealClient

anneal = AnnealClient.from_env()
handler = anneal.callback_handler(agent_id="cascade-support-v1")

result = graph.invoke(
    {"messages": messages},
    config={"callbacks": [handler]},
)

anneal.flush()
```

The SDK scrubs likely secrets, sends traces to `/ingest/langsmith`, and includes
the organization id in both `X-Anneal-Org` and run metadata.

## Smoke Test

The V1 smoke test stays offline but exercises the full owned path:

```sh
uv run pytest worker/tests/test_v1_smoke.py
```

It creates a fresh org id, emits a trace through the SDK callback handler,
ingests it through FastAPI, runs the worker on org-scoped traces, opens a PR
through the fake GitHub gateway, and verifies the stored run is visible only to
that org.

## Commands

| Command | Description |
| --- | --- |
| `make dev` | Start Postgres, ClickHouse, API, and dashboard |
| `make test` | Run Python tests |
| `make lint` | Run ruff, mypy, and dashboard typecheck |
| `make build` | Build the dashboard |
| `make schemas` | Regenerate JSON schemas from shared Pydantic models |

Dashboard-only checks:

```sh
cd dashboard
npm test
npm run typecheck
npm run test:e2e
```

## Architecture

- `core/` - FastAPI ingestion, clustering, evals, optimizer, GitHub publisher.
- `worker/` - Weekly optimization cycle and run/event store.
- `sdk/` - Installable Python SDK for LangGraph/LangChain tracing.
- `dashboard/` - Next.js 15 App Router UI.
- `shared/` - Pydantic models and generated JSON schemas.

## Docs

- [Getting started](docs/getting-started.md)
- [Safety model](docs/safety-model.md)
- [Contributing](CONTRIBUTING.md)
