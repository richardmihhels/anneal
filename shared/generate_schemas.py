#!/usr/bin/env python
"""Generate JSON schemas from pydantic models into shared/schemas/."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from shared.models import (  # noqa: E402
    Alarm,
    EvalResult,
    FailureCluster,
    OptimizationRun,
    ProposedChange,
    Span,
    Trace,
    WeeklyDigest,
)

MODELS = [
    Trace,
    Span,
    FailureCluster,
    OptimizationRun,
    ProposedChange,
    EvalResult,
    Alarm,
    WeeklyDigest,
]
SCHEMA_DIR = Path(__file__).parent / "schemas"
SCHEMA_DIR.mkdir(exist_ok=True)

for model in MODELS:
    schema = model.model_json_schema()
    out = SCHEMA_DIR / f"{model.__name__}.json"
    out.write_text(json.dumps(schema, indent=2) + "\n")
    print(f"wrote {out.relative_to(Path(__file__).parent.parent)}")
