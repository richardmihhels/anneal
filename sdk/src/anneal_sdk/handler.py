from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, cast

if TYPE_CHECKING:
    from langchain_core.callbacks import BaseCallbackHandler as _CallbackBase
    from langchain_core.messages import BaseMessage
else:
    try:
        from langchain_core.callbacks import BaseCallbackHandler as _CallbackBase
        from langchain_core.messages import BaseMessage
    except ImportError:

        class _CallbackBase:  # type: ignore[no-redef]
            """Fallback base when the optional LangChain extra is not installed."""

        BaseMessage = Any  # type: ignore[misc,assignment]

from .scrub import scrub


class _RunSender(Protocol):
    def send_langsmith_run(self, run: dict[str, Any]) -> None: ...


class AnnealCallbackHandler(_CallbackBase):
    """LangChain/LangGraph callback handler that streams runs to Anneal.

    Inherits LangChain's callback base when the optional dependency is installed,
    while remaining importable for users who only send runs directly.

    Minimal integration::

        from anneal_sdk import AnnealClient

        client = AnnealClient("https://anneal.example.com", api_key="ann-xxx")
        app.invoke(inputs, config={"callbacks": [client.callback_handler("my-agent-v1")]})
    """

    def __init__(self, client: _RunSender, agent_id: str) -> None:
        self._client = client
        self._agent_id = agent_id
        self._runs: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    # ── LangChain callback protocol ───────────────────────────────────────────

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: dict[str, Any],
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._start_run(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=self._run_name(serialized, "chain"),
            run_type="chain",
            inputs=inputs,
            tags=tags,
            metadata=metadata,
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
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._start_run(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=self._run_name(serialized, "tool"),
            run_type="tool",
            inputs=inputs if inputs is not None else {"input": input_str},
            tags=tags,
            metadata=metadata,
        )

    def on_tool_end(
        self,
        output: Any,
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
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._start_run(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=self._run_name(serialized, "llm"),
            run_type="llm",
            inputs={"prompts": prompts},
            tags=tags,
            metadata=metadata,
        )

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._start_run(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=self._run_name(serialized, "chat_model"),
            run_type="llm",
            inputs={"messages": messages},
            tags=tags,
            metadata=metadata,
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
            outputs["generations"] = response.generations
        if getattr(response, "llm_output", None) is not None:
            outputs["llm_output"] = response.llm_output
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

    @staticmethod
    def _run_name(serialized: dict[str, Any] | None, default: str) -> str:
        name = (serialized or {}).get("name")
        return name if isinstance(name, str) and name else default

    def _start_run(
        self,
        *,
        run_id: uuid.UUID,
        parent_run_id: uuid.UUID | None,
        name: str,
        run_type: str,
        inputs: dict[str, Any],
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            run_metadata = dict(metadata or {})
            run_metadata["agent_id"] = self._agent_id
            run: dict[str, Any] = {
                "id": str(run_id),
                "name": name,
                "run_type": run_type,
                "start_time": datetime.now(UTC).isoformat(),
                "end_time": None,
                "inputs": scrub(inputs),
                "outputs": None,
                "error": None,
                "tags": [f"agent_id:{self._agent_id}"] + (tags or []),
                "extra": {"metadata": scrub(run_metadata)},
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
        completed_run: dict[str, Any] | None = None
        with self._lock:
            run = self._runs.get(str(run_id))
            if run is None:
                return
            run["end_time"] = datetime.now(UTC).isoformat()
            run["outputs"] = scrub(outputs or {})
            run["error"] = cast(str | None, scrub(error)) if error is not None else None

            # Only flush the top-level run (no parent_run_id).
            if "parent_run_id" not in run:
                completed_run = run
                self._prune(str(run_id))

        # Enqueue outside the run-tree lock so a slow client cannot stall callbacks.
        if completed_run is not None:
            self._client.send_langsmith_run(completed_run)

    def _prune(self, run_id: str) -> None:
        run = self._runs.pop(run_id, None)
        if run is None:
            return
        for child in run.get("child_runs", []):
            self._prune(child["id"])
