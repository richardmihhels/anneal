from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

MIN_JUDGE_AGREEMENT = 0.75
"""Judge must agree with human labels ≥75% of the time.

Rationale: below this threshold, optimization signal is dominated by judge noise
rather than real quality change. Goodhart's Law risk becomes unacceptable.
"""

_SCORE_PROMPT = """\
You are evaluating whether an AI agent responded correctly to a customer request.

Interaction context:
{context}

Did the agent respond CORRECTLY? A correct response:
- Used the right tool for the request
- Stated accurate policy information
- Resolved the user's issue or escalated appropriately
- Did not take actions the user did not request

Respond with exactly one word: YES or NO."""


class JudgeCalibrationError(Exception):
    """Raised when judge–human agreement falls below MIN_JUDGE_AGREEMENT."""


@runtime_checkable
class EvalJudge(Protocol):
    def score(self, context: str) -> float: ...


class FakeEvalJudge:
    """Deterministic judge for tests. Returns 1.0 for 'pass', 0.0 for 'fail' based on context."""

    def __init__(self, default_score: float = 1.0) -> None:
        self._default = default_score

    def score(self, context: str) -> float:
        return self._default


class AnthropicEvalJudge:
    """LLM-as-judge using Claude Haiku. Returns 1.0 (pass) or 0.0 (fail)."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        import anthropic

        self._client = anthropic.Anthropic()
        self._model = model

    def score(self, context: str) -> float:
        import anthropic

        msg = self._client.messages.create(
            model=self._model,
            max_tokens=5,
            messages=[{"role": "user", "content": _SCORE_PROMPT.format(context=context)}],
        )
        block = msg.content[0]
        if not isinstance(block, anthropic.types.TextBlock):
            return 0.0
        answer = block.text.strip().upper()
        logger.debug("EvalJudge answer: %s", answer)
        return 1.0 if answer.startswith("YES") else 0.0


def calibrate(judge: EvalJudge, seed_contexts: list[str], human_labels: list[str]) -> float:
    """Compare judge scores against human labels. Raise if agreement < MIN_JUDGE_AGREEMENT.

    Args:
        judge: The judge to calibrate.
        seed_contexts: Interaction contexts from the human-labeled seed set.
        human_labels: "pass" or "fail" for each context.

    Returns:
        Agreement rate in [0, 1].

    Raises:
        JudgeCalibrationError: If agreement rate < MIN_JUDGE_AGREEMENT.
        ValueError: If inputs are empty or different lengths.
    """
    if not seed_contexts:
        raise ValueError("seed_contexts must not be empty")
    if len(seed_contexts) != len(human_labels):
        raise ValueError("seed_contexts and human_labels must have the same length")

    agreed = 0
    for ctx, human_label in zip(seed_contexts, human_labels):
        judge_pass = judge.score(ctx) >= 0.5
        human_pass = human_label == "pass"
        if judge_pass == human_pass:
            agreed += 1

    rate = agreed / len(seed_contexts)
    logger.info("Judge calibration: %.1f%% agreement (%d/%d)", rate * 100, agreed, len(seed_contexts))

    if rate < MIN_JUDGE_AGREEMENT:
        raise JudgeCalibrationError(
            f"Judge agreement {rate:.1%} is below the required threshold of {MIN_JUDGE_AGREEMENT:.1%}. "
            f"Do not use this judge for optimization — scores are too noisy relative to human labels."
        )

    return rate
