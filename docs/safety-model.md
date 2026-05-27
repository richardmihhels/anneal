# Safety Model

Anneal's core promise is not "more prompt changes." It is fewer changes that
are very likely to help.

## Holdout Separation

The optimizer can inspect production failures and train cases, but a candidate
must win on a held-out eval set before it can be published. This keeps the
candidate from merely memorizing the traces that inspired it.

The worker records the holdout size in run events. The dashboard surfaces it in
run detail so reviewers can see whether a shipped PR had enough evidence.

## Judge Calibration

LLM-as-judge scoring is treated as a risk, not a source of truth. Each customer
configuration carries a seed set of human-labeled pass/fail examples. Anneal
uses those examples to measure judge agreement and records the agreement rate on
eval results.

Low agreement means the eval is not trustworthy enough to justify shipping.
That should lead to a better seed set or a narrower eval, not a looser gate.

## The Stays Silent Gate

Anneal refuses to open a PR when:

- There are too few traces to form a meaningful cluster.
- No repeated failure cluster is found.
- A candidate improves training cases but fails the holdout.
- The candidate delta is not statistically significant.
- The judge calibration is not trustworthy.
- Publishing crashes or a duplicate PR is already open.

The silent state is a product feature. A week with no PR should mean "nothing
cleared the bar," not "the system broke." The dashboard renders this explicitly
with the cluster count, rejected candidates, and the silence report.

## Org And Secret Boundaries

Every trace and optimization run carries `organization_id`. The SDK sends it in
`X-Anneal-Org` and run metadata, ingestion persists it, the worker copies it to
`OptimizationRun`, and the dashboard filters by the signed session org before
rendering.

The SDK and API scrub likely secrets before persistence. Agent API keys should
stay in the customer's environment and must not be put into prompts or eval
contexts.
