from __future__ import annotations

import hashlib

from shared.models import EvalResult, ProposedChange

_MAX_TITLE_LEN = 72
_MAX_EXCERPT_LEN = 280
_MAX_PROMPT_LEN = 300


def _extract_cluster_description(rationale: str) -> str:
    """Parse 'Target failure: Foo bar (N cases...)' → 'Foo bar'."""
    for line in rationale.splitlines():
        if line.startswith("Target failure:"):
            rest = line[len("Target failure:"):].strip()
            return rest.split(" (")[0].strip()
    return "unknown failure pattern"


def _extract_failure_excerpt(rationale: str) -> str:
    """Parse the '> excerpt...' line from a rationale string."""
    for line in rationale.splitlines():
        if line.startswith("> "):
            return line[2:].strip()
    return ""


def idempotency_key(change: ProposedChange) -> str:
    """Stable 12-hex-char key for a change.

    Hashes (cluster_description, before_text) so the same cluster with the
    same baseline prompt produces the same label across weekly re-runs.
    If the baseline prompt has been updated, the key changes — no stale dedup.
    """
    description = _extract_cluster_description(change.rationale)
    content = f"{description}:{change.before}"
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def pr_label(change: ProposedChange) -> str:
    """GitHub label applied to every Anneal PR. Used for idempotency checks."""
    return f"anneal:{idempotency_key(change)}"


def build_pr_title(change: ProposedChange, ev: EvalResult) -> str:
    description = _extract_cluster_description(change.rationale)
    delta_pct = int(ev.delta * 100)
    suffix = f" (+{delta_pct}%, n={ev.sample_size})"
    max_desc = _MAX_TITLE_LEN - len(suffix)
    if len(description) > max_desc:
        description = description[: max_desc - 1] + "…"
    return f'Reduce "{description}" failures{suffix}'


def build_pr_body(change: ProposedChange, ev: EvalResult) -> str:
    description = _extract_cluster_description(change.rationale)
    excerpt = _extract_failure_excerpt(change.rationale)

    before = change.before[:_MAX_PROMPT_LEN]
    after = change.after[:_MAX_PROMPT_LEN]
    excerpt_display = excerpt[:_MAX_EXCERPT_LEN] + ("…" if len(excerpt) > _MAX_EXCERPT_LEN else "")

    baseline_pct = int(ev.baseline_score * 100)
    candidate_pct = int(ev.candidate_score * 100)
    delta_pct = int(ev.delta * 100)

    return f"""\
Anneal detected **{description}** in production traces and found a prompt change \
that fixes it.

**What changed**

```
# Before
{before}

# After
{after}
```

**A representative failure this addresses**

> {excerpt_display}

**Evidence**

{baseline_pct}% → {candidate_pct}% on {ev.sample_size} held-out interactions \
(+{delta_pct}%, p={ev.p_value:.3f}, judge agreement {ev.judge_agreement_rate:.0%}).

**Do not merge if**
- This failure pattern is no longer appearing in production traces
- You have modified the agent config since this PR was opened
- A re-run on fresh traces shows Δ ≤ 0 (current baseline: {baseline_pct}%)
"""


def build_silence_report(clusters_evaluated: int) -> str:
    """Positive summary emitted when nothing is worth shipping this week."""
    if clusters_evaluated == 0:
        return "No failure clusters found this week — agent is performing well."
    return (
        f"No regressions. Anneal evaluated {clusters_evaluated} failure cluster"
        f"{'s' if clusters_evaluated != 1 else ''} and found no prompt change "
        f"that beats the current baseline with statistical significance (p < 0.05). "
        f"Nothing shipped — which is the right call."
    )
