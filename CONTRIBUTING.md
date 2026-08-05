# Contributing

Anneal optimizes production agents, so regressions and noisy PRs are product
bugs. Keep changes small, typed, and verified.

## Setup

```sh
make setup
make setup-browser  # required only for local Playwright tests
```

## Checks

Run the smallest useful check while developing, then the broader checks before a
commit:

```sh
make lint
make test-all
make build
```

For the V1 customer path:

```sh
uv run pytest worker/tests/test_v1_smoke.py
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

## Releasing the SDK

Update `sdk/pyproject.toml` and `CHANGELOG.md` together, merge a fully green
commit to `main`, then publish a GitHub release tagged `v<version>`. The release
workflow rejects a tag that does not match the package version, reruns the SDK
tests, builds both distributions, and publishes through PyPI trusted publishing.
