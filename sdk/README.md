# anneal-sdk

Trace streaming SDK for Anneal.

## Install

```bash
pip install "anneal-sdk[langchain] @ git+https://github.com/richardmihhels/anneal.git@main#subdirectory=sdk"
```

`pip install anneal-sdk[langchain]` becomes available after the first tagged
release is published to PyPI.

For local development from this repo:

```bash
pip install -e ./sdk[langchain]
```

## LangGraph Quickstart

Set the endpoint and organization shown in the dashboard Connect page:

```bash
export ANNEAL_ENDPOINT=http://localhost:8000
export ANNEAL_ORG_ID=org_demo
export ANNEAL_API_KEY=dev_optional
```

Attach the callback handler when invoking your graph:

```python
from anneal_sdk import AnnealClient

anneal = AnnealClient.from_env()
handler = anneal.callback_handler(agent_id="cascade-support-v1")

result = graph.invoke(
    {"messages": messages},
    config={"callbacks": [handler]},
)

# Useful in scripts and tests so the trace is visible before the process exits.
anneal.flush()
```

The SDK sends LangSmith-shaped runs to `/ingest/langsmith`, converts LangChain
messages and other common Python values to JSON, scrubs likely secrets, and
adds `Authorization`, `X-Anneal-Org`, and `extra.metadata.organization_id`.
The server derives tenancy from the authenticated header; trace metadata cannot
override it.

Delivery is asynchronous and best-effort: an unavailable Anneal server never
interrupts the host agent, while delivery failures are emitted through Python's
standard logging system. The `langchain` extra is tested with LangChain Core
1.4.x.

Use the client as a context manager in long-running code when practical:

```python
with AnnealClient.from_env() as anneal:
    graph.invoke(
        {"messages": messages},
        config={"callbacks": [anneal.callback_handler("support-agent-v1")]},
    )
```
