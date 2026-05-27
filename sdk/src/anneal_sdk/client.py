from __future__ import annotations

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
        timeout: float = 10.0,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._headers: dict[str, str] = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._timeout = timeout
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1000)
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    # ── public API ────────────────────────────────────────────────────────────

    def send_langsmith_run(self, run: dict[str, Any]) -> None:
        """Enqueue a LangSmith-format run for async ingestion (secrets scrubbed)."""
        try:
            self._queue.put_nowait(scrub(run))
        except queue.Full:
            pass  # drop under backpressure; observability > reliability here

    def callback_handler(self, agent_id: str) -> AnnealCallbackHandler:
        from .handler import AnnealCallbackHandler  # noqa: PLC0415

        return AnnealCallbackHandler(self, agent_id=agent_id)

    # ── background worker ─────────────────────────────────────────────────────

    def _worker(self) -> None:
        while True:
            run = self._queue.get()
            try:
                with httpx.Client(timeout=self._timeout) as http:
                    http.post(
                        f"{self._endpoint}/ingest/langsmith",
                        json=run,
                        headers=self._headers,
                    )
            except Exception:
                pass  # best-effort; never crash the agent
