# Evals Directory

This directory contains the ground-truth specifications and hand-authored fixtures
that all downstream Anneal components depend on. Nothing in this directory is
generated; every artifact was hand-authored and human-reviewed.

---

## Directory Contents

```
evals/
├── agent-under-test.md    # V1 agent spec: system prompt, tool schemas, policy doc
├── failure-taxonomy.md    # Precise definitions of the 6 failure categories
├── dataset-spec.md        # Specification for the Prompt 2 synthetic trace generator
├── seed-set/              # 25–30 hand-labeled traces (ground truth for judge calibration)
│   └── trace-NNN.json
└── README.md              # This file
```

---

## How Each Artifact Feeds Downstream Prompts

### Prompt 2 — Synthetic Dataset Generator
`dataset-spec.md` is the direct input. The generator must produce exactly the
trace structure, label distribution, and diversity mix defined there. The seed
set must **not** be used as training examples for the generator.

`agent-under-test.md` provides the agent's system prompt, tool schemas, and
policy document so the generator can produce realistic, policy-aware traces.

### Prompt 3 — Failure Clustering
`failure-taxonomy.md` defines the clusters the system must discover. The taxonomy
is the evaluation target: a clustering that recovers the 6 categories (at the
correct granularity) scores well; a clustering that merges `wrong_tool` with
`policy_violation` or splits `unresolved_ticket` into 8 micro-clusters does not.

The seed set provides labeled examples for validating cluster assignments and
computing cluster purity metrics.

### Prompt 4 — LLM-as-Judge
The seed set is the **calibration ground truth**. The judge is considered
calibrated when its labels agree with the seed set labels at ≥85% on a held-out
partition of the seed set (10 traces withheld from calibration prompting).

`failure-taxonomy.md` is the judge's reference document — it is included in
the judge's system prompt so the judge applies consistent definitions.

`agent-under-test.md` provides the judge with the policy document it needs to
identify `hallucinated_policy` and `policy_violation` failures.

### Prompt 5 — GEPA / DSPy Optimization
The seed set is **never used as GEPA training data** (see rule below).

`agent-under-test.md` is the artifact GEPA optimizes: the system prompt and
policy document are the target for improvement. The tool schemas and company
policy are fixed constraints GEPA must respect.

The failure categories from `failure-taxonomy.md` define the optimization
objective: reduce the frequency of each failure category in the holdout eval set.

---

## The Seed Set Rule

> **The seed set (`evals/seed-set/`) is calibration ground truth.
> It must never be used as GEPA training data, as few-shot examples in a
> generator prompt, or as positive/negative examples in any optimization loop.**

The seed set's value comes entirely from being untouched by any automated
process. Once any automated system has seen the seed-set labels, those labels
can no longer serve as an unbiased ground truth for evaluating that system.

In practice this means:
- The Prompt 2 generator receives `dataset-spec.md` and `agent-under-test.md`
  but must not receive the seed-set files.
- The Prompt 4 judge calibration uses the seed set for *calibration prompting*
  (showing the judge labeled examples to set its scoring behavior), but a 10-trace
  held-out partition is never shown to the judge during calibration and is used
  only for measuring judge agreement rate.
- The Prompt 5 GEPA optimizer receives only the holdout eval set (drawn from
  the Prompt 2 synthetic dataset), not the seed set.

---

## Seed Set Schema

Every file in `evals/seed-set/` is a JSON object conforming to the `Trace`
schema defined in `shared/src/shared/models.py`. Validate with:

```sh
uv run python - <<'EOF'
import json, sys
from pathlib import Path
sys.path.insert(0, "shared/src")
from shared.models import Trace

errors = []
for f in sorted(Path("evals/seed-set").glob("trace-*.json")):
    try:
        Trace(**json.loads(f.read_text()))
        print(f"✓ {f.name}")
    except Exception as e:
        print(f"✗ {f.name}: {e}")
        errors.append(f.name)
sys.exit(1 if errors else 0)
EOF
```

### Label fields (within `metadata`)

| Field                | Type         | Required | Description                                          |
|----------------------|--------------|----------|------------------------------------------------------|
| `label`              | string       | yes      | One of the 7 category values (or `"success"`)        |
| `failure_category`   | string\|null | yes      | Same as `label` for failures; `null` for `"success"` |
| `rationale`          | string       | yes      | One sentence: *why* this label, referencing the spans |
| `annotator`          | string       | yes      | Always `"human"` in this seed set                    |
| `customer_tier`      | string       | yes      | `starter`, `pro`, `business`, or `enterprise`        |
| `ticket_type`        | string       | yes      | See dataset-spec.md §3b for valid values             |
| `customer_tone`      | string       | yes      | `neutral`, `frustrated`, or `polite`                 |
