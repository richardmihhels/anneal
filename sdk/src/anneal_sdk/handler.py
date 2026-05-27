from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import AnnealClient


class AnnealCallbackHandler:
    """LangChain/LangGraph callback handler that streams runs to Anneal.

    Implements the LangChain callback protocol via duck typing — no langchain
    import required at class-definition time.

    Minimal integration::

        from anneal_sdk import AnnealClient

        client = AnnealClient("https://anneal.example.com", api_key="ann-xxx")
        app.invoke(inputs, config={"callbacks": [client.callback_handler("my-agent-v1")]})
    """

    def __init__(self, client: AnnealClient, agent_id: str) -> None:
        self._client = client
        self._agent_id = agent_id
        self._runs: dict[str, dict[str, Any]] = {}

    # ── LangChain callback protocol ───────────────────────────────────────────

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        self._start_run(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=serialized.get("name", "chain"),
            run_type="chain",
            inputs=inputs,
            tags=tags,
        )

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        self._end_run(run_id=run_id, outputs=outputs)

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        self._end_run(run_id=run_id, error=str(error))

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self._start_run(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=serialized.get("name", "tool"),
            run_type="tool",
            inputs={"input": input_str},
        )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        self._end_run(run_id=run_id, outputs={"output": output})

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        self._end_run(run_id=run_id, error=str(error))

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self._start_run(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=serialized.get("name", "llm"),
            run_type="llm",
            inputs={"prompts": prompts},
        )

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        outputs: dict[str, Any] = {}
        if hasattr(response, "generations"):
            outputs["generations"] = [[{"text": g.text} for g in gen] for gen in response.generations]
        self._end_run(run_id=run_id, outputs=outputs)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        self._end_run(run_id=run_id, error=str(error))

    # ── internal ──────────────────────────────────────────────────────────────

    def _start_run(
        self,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None,
        name: str,
        run_type: str,
        inputs: dict[str, Any],
        tags: list[str] | None = None,
    ) -> None:
        run: dict[str, Any] = {
            "id": str(run_id),
            "name": name,
            "run_type": run_type,
            "start_time": datetime.now(UTC).isoformat(),
            "end_time": None,
            "inputs": inputs,
            "outputs": None,
            "error": None,
            "tags": [f"agent_id:{self._agent_id}"] + (tags or []),
            "extra": {"metadata": {"agent_id": self._agent_id}},
            "child_runs": [],
        }
        if parent_run_id is not None:
            run["parent_run_id"] = str(parent_run_id)
            parent = self._runs.get(str(parent_run_id))
            if parent is not None:
                parent["child_runs"].append(run)
        self._runs[str(run_id)] = run

    def _end_run(
        self,
        *,
        run_id: uuid.UUID,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        run = self._runs.get(str(run_id))
        if run is None:
            return
        run["end_time"] = datetime.now(UTC).isoformat()
        run["outputs"] = outputs or {}
        run["error"] = error

        # Only flush the top-level run (no parent_run_id)
        if "parent_run_id" not in run:
            self._client.send_langsmith_run(run)
            # Clean up completed run tree
            self._prune(str(run_id))

    def _prune(self, run_id: str) -> None:
        run = self._runs.pop(run_id, None)
        if run is None:
            return
        for child in run.get("child_runs", []):
            self._prune(child["id"])
