# Getting started

Anneal has two explicit modes:

- **Demo mode** is a zero-service product tour backed by synthetic records.
- **Production mode** persists real traces and refuses to start with incomplete infrastructure or credentials.

## 1. Run the product demo

Install Python and dashboard dependencies from the repository root:

```sh
make setup
make demo
```

Open <http://localhost:3000/login> and choose **Continue to Prompt 7 Demo**.
No production data is used or accepted by this dashboard process.

## 2. Start the local services

Install Docker, then run:

```sh
make dev
```

This starts Postgres and ClickHouse with health checks, then runs the core API
and an API-backed dashboard. Local defaults are:

```text
ANNEAL_ENDPOINT=http://localhost:8000
ANNEAL_ORG_ID=org_demo
ANNEAL_API_KEY=dev_optional
```

Stop the API with `Ctrl-C`; stop the database containers with `make stop`.
If another project already uses a database port, set `POSTGRES_PORT`,
`CLICKHOUSE_HTTP_PORT`, or `CLICKHOUSE_NATIVE_PORT` before `make dev`.

## 3. Install the SDK

Before the first PyPI release:

```sh
pip install "anneal-sdk[langchain] @ git+https://github.com/richardmihhels/anneal.git@main#subdirectory=sdk"
```

Inside this monorepo:

```sh
pip install -e "./sdk[langchain]"
```

## 4. Attach the callback

```python
from anneal_sdk import AnnealClient

anneal = AnnealClient.from_env()
handler = anneal.callback_handler(agent_id="support-agent-v1")

result = graph.invoke(
    {"messages": messages},
    config={"callbacks": [handler]},
)

anneal.flush()
```

`flush()` is useful in scripts, tests, and jobs that exit immediately after the
graph call. Long-running applications should call `close()` during shutdown or
use `AnnealClient` as a context manager.

## 5. Configure authentication

One self-hosted organization can use:

```sh
export ANNEAL_ENV=production
export ANNEAL_ORG_ID=org_acme
export ANNEAL_API_KEY="$(openssl rand -hex 32)"
```

Multiple organizations use a JSON key map:

```sh
export ANNEAL_API_KEYS_JSON='{"org_acme":"key-one","org_beta":"key-two"}'
```

Production startup fails if API authentication, Postgres, or ClickHouse is not
configured. The organization in trace metadata never overrides the authenticated
organization.

## 6. Configure weekly optimization

Copy the validated example:

```sh
cp anneal.example.yml /secure/path/anneal.yml
export ANNEAL_CONFIG_PATH=/secure/path/anneal.yml
```

Each customer supplies a baseline prompt, repository target, and at least four
human-labeled judge calibration examples containing both `pass` and `fail`.
Unknown configuration fields are rejected.

The worker also requires:

- `POSTGRES_URL`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GITHUB_APP_ID`
- `GITHUB_APP_PRIVATE_KEY`
- `ANNEAL_AGENT_RUNNER_URL`

The agent runner receives a scrubbed trace and an `AgentConfig`, replays the
case in a non-production environment, and returns a response string. This is
the only customer-specific runtime adapter Anneal requires.

Run once:

```sh
ANNEAL_MODE=production ANNEAL_TRIGGER_NOW=true uv run python -m worker.main
```

Run continuously to use the built-in Monday 02:00 UTC scheduler:

```sh
ANNEAL_MODE=production uv run python -m worker.main
```

Azure uses a Container Apps scheduled job instead of the in-process scheduler.

## 7. Verify the owned path

```sh
make lint
make test
cd dashboard && npm test -- --runInBand
cd dashboard && npm run test:e2e
```

The offline smoke test intentionally uses a fake GitHub gateway and deterministic
eval components. It verifies Anneal's owned safety and tenancy behavior without
creating external branches or pull requests.
