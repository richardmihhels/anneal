from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray


@runtime_checkable
class Embedder(Protocol):
    def embed(self, texts: list[str]) -> NDArray[np.float32]: ...


class TFIDFEmbedder:
    """Deterministic TF-IDF embedder. No API key required; used in tests and CLI.

    Fits a fresh vocabulary on each call, so results are consistent for the
    same input list but not portable across separate embed() calls.
    """

    def __init__(self, max_features: int = 512) -> None:
        self._max_features = max_features

    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import-untyped]
        from sklearn.preprocessing import normalize  # type: ignore[import-untyped]

        vec = TfidfVectorizer(max_features=self._max_features)
        X: NDArray[np.float32] = vec.fit_transform(texts).toarray().astype(np.float32)
        return normalize(X).astype(np.float32)  # type: ignore[no-any-return]


class OpenAIEmbedder:
    """Production embedder via OpenAI text-embedding-3-small.

    Requires OPENAI_API_KEY in the environment.
    Install: pip install openai
    """

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        import openai  # type: ignore[import-not-found]

        self._client = openai.OpenAI()
        self._model = model

    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return np.array([e.embedding for e in resp.data], dtype=np.float32)
