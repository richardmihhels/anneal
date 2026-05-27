from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

_JUDGE_PROMPT = """\
You are auditing a customer support interaction for quality failures.

Interaction context:
{context}

Is this interaction a FAILURE? A failure is any of:
- Wrong tool used for the user's request
- Incorrect or hallucinated policy stated to the customer
- User's issue left unresolved without escalation
- Unnecessary escalation to a human when tools could handle it
- Action taken that the customer did not request
- Policy rule explicitly violated (wrong refund amount, credit cap exceeded, etc.)

Respond with exactly one word: YES or NO."""


@runtime_checkable
class LLMJudge(Protocol):
    def is_failure(self, context: str) -> bool: ...


class FakeJudge:
    """Always classifies ambiguous traces as failures. Used in tests."""

    def is_failure(self, context: str) -> bool:
        return True


class AnthropicJudge:
    """LLM-as-judge using Claude Haiku. Runs only on outcome == 'unknown' traces.

    Calibrate against the seed set before trusting production scores — see
    ClusterPipeline.calibrate_judge(). Treat Goodhart's Law as the primary risk:
    optimising for judge agreement without calibration degrades real quality.
    """

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        import anthropic

        self._client = anthropic.Anthropic()
        self._model = model

    def is_failure(self, context: str) -> bool:
        import anthropic

        msg = self._client.messages.create(
            model=self._model,
            max_tokens=5,
            messages=[{"role": "user", "content": _JUDGE_PROMPT.format(context=context)}],
        )
        block = msg.content[0]
        if not isinstance(block, anthropic.types.TextBlock):
            return False
        answer = block.text.strip().upper()
        logger.debug("Judge answer: %s", answer)
        return answer.startswith("YES")
