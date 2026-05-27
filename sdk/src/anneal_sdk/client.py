from __future__ import annotations

import os
import queue
import threading
from typing import TYPE_CHECKING, Any

import httpx

from .scrub import scrub

if TYPE_CHECKING:
    from .handler import AnnealCallbackHandler


class AnnealClient:
    """Thread-safe fire-and-forget client that streams traces to an Anneal endpoint.

    Usage::

        client = AnnealClient("https://anneal.example.com", api_key="ann-xxx")
        # pass client.callback_handler() to LangGraph
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str | None = None,
        *,
        organization_id: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._headers: dict[str, str] = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._organization_id = organization_id
        if organization_id:
            self._headers["X-Anneal-Org"] = organization_id
        self._timeout = timeout
        self._queue: queue.Queue[dict[str, Any] | None] = queue.Queue(maxsize=1000)
        self._closed = False
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    # ── public API ────────────────────────────────────────────────────────────

    @classmethod
    def from_env(cls, *, timeout: float = 10.0) -> AnnealClient:
        """Create a client from ANNEAL_ENDPOINT, ANNEAL_API_KEY, and ANNEAL_ORG_ID."""
        return cls(
            endpoint=os.getenv("ANNEAL_ENDPOINT", "http://localhost:8000"),
            api_key=os.getenv("ANNEAL_API_KEY"),
            organization_id=os.getenv("ANNEAL_ORG_ID", "org_demo"),
            timeout=timeout,
        )

    def send_langsmith_run(self, run: dict[str, Any]) -> None:
        """Enqueue a LangSmith-format run for async ingestion (secrets scrubbed)."""
        if self._closed:
            return
        try:
            self._queue.put_nowait(self._prepare_run(run))
        except queue.Full:
            pass  # drop under backpressure; observability > reliability here

    def callback_handler(self, agent_id: str) -> AnnealCallbackHandler:
        from .handler import AnnealCallbackHandler  # noqa: PLC0415

        return AnnealCallbackHandler(self, agent_id=agent_id)

    def flush(self) -> None:
        """Block until all queued traces have been attempted."""
        self._queue.join()

    def close(self) -> None:
        """Drain the queue and stop the background worker."""
        if self._closed:
            return
        self._closed = True
        self.flush()
        self._queue.put(None)
        self._thread.join(timeout=self._timeout)

    def __enter__(self) -> AnnealClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ── background worker ─────────────────────────────────────────────────────

    def _prepare_run(self, run: dict[str, Any]) -> dict[str, Any]:
        clean = scrub(run)
        if self._organization_id:
            extra = clean.setdefault("extra", {})
            if isinstance(extra, dict):
                metadata = extra.setdefault("metadata", {})
                if isinstance(metadata, dict):
                    metadata.setdefault("organization_id", self._organization_id)
        return clean

    def _worker(self) -> None:
        while True:
            run = self._queue.get()
            try:
                if run is None:
                    return
                with httpx.Client(timeout=self._timeout) as http:
                    http.post(
                        f"{self._endpoint}/ingest/langsmith",
                        json=run,
                        headers=self._headers,
                    )
            except Exception:
                pass  # best-effort; never crash the agent
            finally:
                self._queue.task_done()
