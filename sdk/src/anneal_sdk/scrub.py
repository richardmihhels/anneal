from __future__ import annotations

import re
from typing import Any

_KEY_PAT = re.compile(r"(?i)(api[_-]?key|secret[_-]?key|auth[_-]?token|password|bearer|authorization)")
_VAL_PAT = re.compile(r"(sk-ant-[A-Za-z0-9\-_]{20,}|sk-[A-Za-z0-9\-_]{20,}|Bearer\s+[A-Za-z0-9\-_\.]{10,})")

_REDACTED = "[REDACTED]"


def scrub(obj: Any) -> Any:
    """Recursively remove secrets from a JSON-serialisable structure."""
    if isinstance(obj, dict):
        return {k: _maybe_redact(k, scrub(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(item) for item in obj]
    if isinstance(obj, str):
        return _VAL_PAT.sub(_REDACTED, obj)
    return obj


def _maybe_redact(key: str, value: Any) -> Any:
    if _KEY_PAT.search(key) and isinstance(value, str) and value:
        return _REDACTED
    return value
