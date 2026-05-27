from __future__ import annotations

from typing import Protocol, runtime_checkable

_LABEL_PROMPT = """\
You are classifying a cluster of similar AI agent failures in a customer support system.

Here are up to three example interactions from this cluster:

{contexts}

Write a label for this failure pattern: 5-10 words, starting with a verb or noun.
Good examples: "Agent applies unsolicited billing credits", "Wrong tool used for FAQ questions"
Bad examples: "failure", "error", "the agent did something wrong"

Respond with only the label text — no explanation, no punctuation at the end."""


@runtime_checkable
class ClusterLabeler(Protocol):
    def label(self, contexts: list[str]) -> str: ...


class FakeLabeler:
    """Keyword-based labeler for tests and offline mode. No LLM required."""

    _KEYWORDS: list[tuple[str, str]] = [
        ("saml", "Wrong tool: product question routed to order lookup"),
        ("sso", "Wrong tool: product question routed to order lookup"),
        ("90 days", "Hallucinated refund window"),
        ("90-day", "Hallucinated refund window"),
        ("suspended", "Unresolved ticket: account issue deferred"),
        ("check back", "Unresolved ticket: issue deferred without escalation"),
        ("escalate_to_human", "Premature escalation before self-service attempt"),
        ("partial refund", "Policy violation: partial refund issued"),
        ("two weeks", "Policy violation: partial refund for partial usage"),
        ("goodwill", "Scope creep: unsolicited account action"),
        ("storage limit", "Scope creep: credit applied for informational query"),
    ]

    def label(self, contexts: list[str]) -> str:
        combined = " ".join(contexts[:3]).lower()
        for keyword, lbl in self._KEYWORDS:
            if keyword in combined:
                return lbl
        return "Unknown failure pattern"


class AnthropicLabeler:
    """Generate cluster labels using Claude Haiku."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        import anthropic

        self._client = anthropic.Anthropic()
        self._model = model

    def label(self, contexts: list[str]) -> str:
        import anthropic

        ctx_text = "\n\n---\n\n".join(contexts[:3])
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=30,
            messages=[{"role": "user", "content": _LABEL_PROMPT.format(contexts=ctx_text)}],
        )
        block = msg.content[0]
        if not isinstance(block, anthropic.types.TextBlock):
            return "Unknown failure pattern"
        return block.text.strip()
