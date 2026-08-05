from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel

_KEY_PAT = re.compile(r"(?i)(api[_-]?key|secret[_-]?key|auth[_-]?token|password|bearer|authorization)")
_VAL_PAT = re.compile(r"(sk-ant-[A-Za-z0-9\-_]{20,}|sk-[A-Za-z0-9\-_]{20,}|Bearer\s+[A-Za-z0-9\-_\.]{10,})")

_REDACTED = "[REDACTED]"


def scrub(obj: Any) -> Any:
    """Convert a value to JSON-safe data while recursively removing secrets."""
    if isinstance(obj, BaseModel):
        return scrub(obj.model_dump(mode="json"))
    if is_dataclass(obj) and not isinstance(obj, type):
        return scrub(asdict(obj))
    if isinstance(obj, Mapping):
        return {str(k): _maybe_redact(str(k), scrub(v)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [scrub(item) for item in obj]
    if isinstance(obj, str):
        return _VAL_PAT.sub(_REDACTED, obj)
    if isinstance(obj, Enum):
        return scrub(obj.value)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    return _VAL_PAT.sub(_REDACTED, str(obj))


def _maybe_redact(key: str, value: Any) -> Any:
    if _KEY_PAT.search(key) and isinstance(value, str) and value:
        return _REDACTED
    return value
