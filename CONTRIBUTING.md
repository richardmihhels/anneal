# Contributing

Anneal optimizes production agents, so regressions and noisy PRs are product
bugs. Keep changes small, typed, and verified.

## Setup

```sh
uv sync
cd dashboard && npm install
```

## Checks

Run the smallest useful check while developing, then the broader checks before a
commit:

```sh
uv run pytest
cd dashboard && npm test
cd dashboard && npm run typecheck
```

For the V1 customer path:

```sh
uv run pytest worker/tests/test_v1_smoke.py
cd dashboard && npm run test:e2e
```

## Standards

- Python is 3.12 with strict typing for source modules.
- TypeScript should avoid `any`.
- Shared schema changes start in `shared/src/shared/models.py`; regenerate with
  `python shared/generate_schemas.py`.
- Secrets come from environment variables only.
- Conventional commits are required.

## Safety Invariants

Do not weaken these without an explicit product decision:

- A PR must pass a held-out eval.
- Judge scores must be calibrated against human-labeled seed examples.
- Failed, low-confidence, duplicate, or noisy changes must stay silent.
- Dashboard and API data must remain scoped by organization.

## Dashboard Taste

The dashboard should feel closer to Linear or Raycast than Grafana: dense,
quiet, fast, and opinionated. Empty weeks should be reassuring and explicit.
