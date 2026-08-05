from __future__ import annotations

from typing import Protocol, runtime_checkable

MUTATION_BUDGET = 4
"""Maximum candidate prompts evaluated per failure cluster.

Rationale: GEPA generates targeted mutations via LLM reflection, not random
search — diminishing returns set in fast. The first two variants address the
most obvious fixes for a given failure pattern; the next two explore alternative
phrasings. Beyond four, eval harness call cost grows linearly without proportional
quality gain. Increase per-cluster budgets for high-severity clusters only.
"""


@runtime_checkable
class PromptMutator(Protocol):
    def mutate(self, prompt: str, failure_examples: list[str], budget: int) -> list[str]:
        """Return up to `budget` candidate prompt strings.

        Each string is a complete replacement for `prompt`, not a diff.
        The list may be shorter than `budget` if the LLM produces duplicates.
        """
        ...


class FakeMutator:
    """Deterministic mutator for tests. No API key required."""

    def mutate(self, prompt: str, failure_examples: list[str], budget: int) -> list[str]:
        excerpt = failure_examples[0][:40].strip() if failure_examples else "failures"
        return [f"{prompt} [mutation-{i}: address {excerpt}]" for i in range(budget)]


class GEPAMutator:
    """Reflective prompt mutation via DSPy + Claude (GEPA algorithm).

    Generates `budget` independent candidate prompts, each conditioned on the
    cluster's failure examples. The eval harness acts as the fitness function —
    GEPAMutator only proposes; it never decides what ships.

    Requires ANTHROPIC_API_KEY in the environment.
    """

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        import dspy  # type: ignore[import-untyped]

        # DSPy enables diskcache by default. diskcache 5.6.3 has no patched
        # release for PYSEC-2026-2447, which can deserialize a malicious cache
        # entry when another process can write to its cache directory. Anneal's
        # worker does not need persistence between optimization runs, so retain
        # in-memory caching and remove the vulnerable disk boundary entirely.
        dspy.configure_cache(enable_disk_cache=False, enable_memory_cache=True)

        class _MutationSignature(dspy.Signature):  # type: ignore[misc]
            """Improve an AI agent's system prompt to fix a specific failure pattern.

            Write a complete replacement system prompt — not a diff, not commentary.
            Focus only on the stated failure pattern; preserve all other behaviour.
            """

            current_prompt: str = dspy.InputField(desc="System prompt to improve")
            failure_description: str = dspy.InputField(desc="One-sentence name of the failure pattern")
            failure_examples: str = dspy.InputField(desc="Up to three example failure interactions, separated by ---")
            improved_prompt: str = dspy.OutputField(desc="Complete improved system prompt")

        self._lm = dspy.LM(f"anthropic/{model}", max_tokens=512)
        self._predictor = dspy.Predict(_MutationSignature)

    def mutate(self, prompt: str, failure_examples: list[str], budget: int) -> list[str]:
        import dspy

        examples_text = "\n---\n".join(failure_examples[:3])
        candidates: list[str] = []

        with dspy.context(lm=self._lm):
            for _ in range(budget):
                result = self._predictor(
                    current_prompt=prompt,
                    failure_description="agent failure",
                    failure_examples=examples_text,
                )
                candidate: str = result.improved_prompt
                if candidate and candidate not in candidates:
                    candidates.append(candidate)

        return candidates
