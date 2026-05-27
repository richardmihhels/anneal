# anneal-sdk

Trace streaming SDK for Anneal.

## Install

```bash
pip install anneal-sdk[langchain]
```

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

The SDK sends LangSmith-shaped runs to `/ingest/langsmith`, scrubs likely
secrets, and adds `X-Anneal-Org` plus `extra.metadata.organization_id` so the
dashboard only reads traces for the signed organization.
