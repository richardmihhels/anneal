from __future__ import annotations

from shared.models import Trace


def extract_context(trace: Trace) -> str:
    """Produce a compact text summary of a trace for embedding.

    Captures: first user message, tool sequence, and final agent response.
    This is the unit the embedder sees — keep it representative but short.
    """
    parts: list[str] = []

    # First user message
    for span in trace.spans:
        if span.name == "agent_turn":
            for msg in span.input.get("messages", []):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    content = msg.get("content", "")
                    parts.append(f"USER: {content}")
                    break
            break

    # Tool call sequence in order
    tools = [span.name[5:] for span in trace.spans if span.name.startswith("tool:")]
    if tools:
        parts.append(f"TOOLS: {' → '.join(tools)}")

    # Final non-empty agent response
    for span in reversed(trace.spans):
        if span.name == "agent_turn":
            content = span.output.get("content")
            if content:
                parts.append(f"RESPONSE: {content}")
                break

    return "\n".join(parts)
