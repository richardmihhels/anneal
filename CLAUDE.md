Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

Tradeoff: These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

Touch only what you must. Clean up only your own mess.

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

These guidelines are working if: fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

# Anneal — Project Constitution

## What we're building
Anneal is "Dependabot for AI agent prompts and skills." It ingests an agent's
production traces, clusters failures, runs GEPA/DSPy reflective optimization
against a held-out eval set, and opens a GitHub PR each week with a statistically
gated improvement. Core philosophy: LESS optimization that is ALWAYS net-positive
beats MORE optimization that overfits. The product refuses to ship noisy updates.

## Target user (V1, do not broaden)
Lead AI engineer at a 50–500-person company running a LangGraph customer-support
agent in production.

## Architecture
- `core/` — Python 3.12, FastAPI, DSPy + GEPA. The optimization engine.
- `dashboard/` — Next.js 15 (App Router), TypeScript, Tailwind. Linear-grade taste.
- `worker/` — Python, runs the weekly optimization job (async).
- `shared/` — JSON schemas shared between core and dashboard.
- Postgres (metadata) + ClickHouse (traces/spans). Local: docker-compose.

## Non-negotiable engineering rules
- Every PR Anneal opens MUST be gated by a holdout eval; never ship a regression.
- LLM-as-judge scores must be calibrated against a human-labeled seed set; log
  judge agreement rate. Treat Goodhart's Law as the primary risk.
- Strict typing: mypy --strict for Python, no `any` in TS.
- Every module ships with tests. No module is "done" without them.
- Secrets via env only. Agent API keys NEVER pass through an LLM context.
- Conventional commits. Small, reviewable diffs.

## Precedence
When the behavioral guidelines (simplicity, minimal code) appear to conflict
with the non-negotiable engineering rules, the engineering rules win. Holdout
gating, judge calibration, leakage prevention, idempotency, and tests are
core requirements, not speculative robustness — never simplify them away.

## Taste rules (the Anneal differentiator)
- The dashboard looks like Linear/Raycast, not Grafana. Calm, dense, fast.
- The PR Anneal opens reads like a thoughtful senior colleague: one-line summary,
  one before/after example, the eval delta with significance, a "do not merge if"
  guard. No walls of text.
- Opinionated defaults. Minimal knobs. When unsure, the product stays quiet.

## On scope boundaries
Each build prompt is intentionally scoped and withholds later context. If
something is unclear because it belongs to a later prompt, do NOT ask and do
NOT build ahead — note it as an assumption and stay within the current prompt's
stated scope. Only ask when something is unclear WITHIN the current scope.

## How to work
Build strictly in the order of the numbered prompts. At the start of each
session, read this file and the current repo state before writing code.
After Prompt 1.5 and Prompt 4, the human reviews the failure taxonomy/seed set
and the judge calibration respectively before the next session begins.