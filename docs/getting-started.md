# Getting Started

This guide gets a LangGraph support-agent team from a fresh checkout to traces
in the dashboard.

## 1. Start Anneal Locally

```sh
uv sync
cd dashboard && npm install
make dev
```

Open `http://localhost:3000/login` and continue to the Prompt 7 demo org. The
dashboard is backed by Prompt 7 synthetic run records until your own traces are
ingested.

## 2. Install The SDK

In the agent repo:

```sh
pip install anneal-sdk[langchain]
```

From this monorepo:

```sh
pip install -e ./sdk[langchain]
```

## 3. Configure Environment

Use the org id from the dashboard Connect page:

```sh
export ANNEAL_ENDPOINT=http://localhost:8000
export ANNEAL_ORG_ID=org_demo
export ANNEAL_API_KEY=dev_optional
```

`ANNEAL_API_KEY` is optional in local development. Production should require it
at the API edge before traces are accepted.

## 4. Attach To LangGraph

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

`flush()` is useful in scripts, tests, and jobs where the Python process exits
immediately after the graph call.

## 5. Configure PR Publishing

Add an `anneal.yml` beside the agent config:

```yaml
organization_id: org_demo
agent_id: cascade-support-v1
repo: acme/support-agent
config_path: agent/prompts.py
base_branch: main

seed_set:
  - context: "I've processed your refund of $79. It will arrive in 3-5 days."
    label: pass
  - context: "I cannot help with billing. Please contact billing@company.com."
    label: fail
```

The GitHub App flow is stubbed in the dashboard. The worker path is already
exercised with `FakeGitHubGateway`; production uses `GitHubAppClient` with
`GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY`.

## 6. Run The Smoke Test

```sh
uv run pytest worker/tests/test_v1_smoke.py
```

Expected path:

1. Fresh org id is created in the test.
2. SDK emits a LangSmith-shaped run.
3. FastAPI ingests the trace with `X-Anneal-Org`.
4. Worker clusters failures and evaluates a mutation.
5. Fake GitHub gateway opens a PR.
6. Stored run is scoped to the same org id for the dashboard.
