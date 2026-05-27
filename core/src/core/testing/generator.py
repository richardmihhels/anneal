# ruff: noqa: E501
"""Synthetic trace generator for Cascade support agent.

Produces realistic Trace objects that exercise all 6 failure categories.
Used as test fixtures for ingestion, clustering, and eval pipelines.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from shared.models import Span, Trace

FailureCategory = Literal[
    "success",
    "wrong_tool",
    "hallucinated_policy",
    "unresolved_ticket",
    "premature_escalation",
    "policy_violation",
    "scope_creep",
]

_AGENT_ID = "cascade-support-v1"

_CUSTOMERS = [
    {"email": "alice@startup.io", "tier": "pro", "credits_90d": 0.0},
    {"email": "bob@enterprise.com", "tier": "enterprise", "credits_90d": 0.0},
    {"email": "carol@freelance.dev", "tier": "starter", "credits_90d": 20.0},
    {"email": "dave@agency.co", "tier": "pro", "credits_90d": 70.0},
]


# ── span helpers ──────────────────────────────────────────────────────────────


def _span(
    *,
    trace_id: str,
    name: str,
    t0: datetime,
    duration_ms: float,
    input: dict[str, Any],  # noqa: A002
    output: dict[str, Any],
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[Span, datetime]:
    end = t0 + timedelta(milliseconds=duration_ms)
    return (
        Span(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            name=name,
            start_time=t0,
            end_time=end,
            duration_ms=duration_ms,
            input=input,
            output=output,
            error=error,
            metadata=metadata or {},
        ),
        end,
    )


def _agent_turn(
    trace_id: str,
    t0: datetime,
    messages: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]] | None,
    content: str | None,
) -> tuple[Span, datetime]:
    return _span(
        trace_id=trace_id,
        name="agent_turn",
        t0=t0,
        duration_ms=random.uniform(1200, 2000),
        input={"messages": messages},
        output={"content": content, "tool_calls": tool_calls or []},
    )


def _tool(
    trace_id: str,
    t0: datetime,
    tool_name: str,
    args: dict[str, Any],
    result: dict[str, Any],
) -> tuple[Span, datetime]:
    return _span(
        trace_id=trace_id,
        name=f"tool:{tool_name}",
        t0=t0,
        duration_ms=random.uniform(400, 900),
        input=args,
        output=result,
    )


# ── generators per category ───────────────────────────────────────────────────


def _success(trace_id: str, t0: datetime, customer: dict[str, Any]) -> list[Span]:
    spans: list[Span] = []
    email = customer["email"]

    user_msg = [{"role": "user", "content": f"I need a refund on my last order. Account: {email}."}]

    s, t0 = _agent_turn(
        trace_id, t0, user_msg, [{"tool": "lookup_order", "arguments": {"customer_email": email}}], None
    )
    spans.append(s)
    s, t0 = _tool(
        trace_id,
        t0,
        "lookup_order",
        {"customer_email": email},
        {
            "order_id": "ORD-11111",
            "product": "Cascade Pro",
            "amount_usd": 79.0,
            "purchase_date": "2025-02-15",
            "billing_cycle": "monthly",
            "status": "active",
        },
    )
    spans.append(s)
    s, t0 = _agent_turn(
        trace_id,
        t0,
        [{"role": "tool_result", "tool": "lookup_order", "content": {"order_id": "ORD-11111", "amount_usd": 79.0}}],
        [
            {
                "tool": "issue_refund",
                "arguments": {"order_id": "ORD-11111", "amount_usd": 79.0, "reason": "Customer refund request"},
            }
        ],
        None,
    )
    spans.append(s)
    s, t0 = _tool(
        trace_id,
        t0,
        "issue_refund",
        {"order_id": "ORD-11111", "amount_usd": 79.0, "reason": "Customer refund request"},
        {
            "refund_id": "REF-22222",
            "status": "processed",
            "amount_usd": 79.0,
        },
    )
    spans.append(s)
    s, t0 = _agent_turn(
        trace_id,
        t0,
        [{"role": "tool_result", "tool": "issue_refund", "content": {"refund_id": "REF-22222", "amount_usd": 79.0}}],
        [],
        "I've processed a full refund of $79.00 (REF-22222). It will appear on your statement within 3–5 business days.",
    )
    spans.append(s)
    return spans


def _wrong_tool(trace_id: str, t0: datetime, customer: dict[str, Any]) -> list[Span]:
    """Calls lookup_order when it should search the KB for a product question."""
    spans: list[Span] = []
    email = customer["email"]

    user_msg = [{"role": "user", "content": f"Does Cascade support SSO via SAML? Account: {email}."}]

    # Wrong: calls lookup_order instead of search_kb
    s, t0 = _agent_turn(
        trace_id, t0, user_msg, [{"tool": "lookup_order", "arguments": {"customer_email": email}}], None
    )
    spans.append(s)
    s, t0 = _tool(
        trace_id,
        t0,
        "lookup_order",
        {"customer_email": email},
        {
            "order_id": "ORD-33333",
            "product": "Cascade Pro",
            "plan": "pro",
        },
    )
    spans.append(s)
    s, t0 = _agent_turn(
        trace_id,
        t0,
        [{"role": "tool_result", "tool": "lookup_order", "content": {"plan": "pro"}}],
        [],
        "I looked at your order and you're on the Pro plan. SAML SSO is available — please contact your admin to configure it.",
    )
    spans.append(s)
    return spans


def _hallucinated_policy(trace_id: str, t0: datetime, customer: dict[str, Any]) -> list[Span]:
    """Agent states a 90-day refund window that doesn't exist in policy."""
    spans: list[Span] = []
    email = customer["email"]

    user_msg = [
        {
            "role": "user",
            "content": f"I bought Cascade 45 days ago and it's not working for us. Can I get a refund? Account: {email}.",
        }
    ]

    s, t0 = _agent_turn(
        trace_id, t0, user_msg, [{"tool": "lookup_order", "arguments": {"customer_email": email}}], None
    )
    spans.append(s)
    s, t0 = _tool(
        trace_id,
        t0,
        "lookup_order",
        {"customer_email": email},
        {
            "order_id": "ORD-44444",
            "amount_usd": 79.0,
            "purchase_date": "2025-01-10",
            "status": "active",
        },
    )
    spans.append(s)
    # Hallucinates: claims 90-day window; actual policy is 30 days
    s, t0 = _agent_turn(
        trace_id,
        t0,
        [
            {
                "role": "tool_result",
                "tool": "lookup_order",
                "content": {"purchase_date": "2025-01-10", "amount_usd": 79.0},
            }
        ],
        [],
        "Good news — our refund policy covers purchases within 90 days, so you're still eligible. I'll process a full refund of $79.00 for you.",
    )
    spans.append(s)
    return spans


def _unresolved_ticket(trace_id: str, t0: datetime, customer: dict[str, Any]) -> list[Span]:
    """Agent closes without actually solving the problem."""
    spans: list[Span] = []
    email = customer["email"]

    user_msg = [{"role": "user", "content": f"I can't log in — it says my account is suspended. Account: {email}."}]

    s, t0 = _agent_turn(trace_id, t0, user_msg, [{"tool": "get_customer_profile", "arguments": {"email": email}}], None)
    spans.append(s)
    s, t0 = _tool(
        trace_id,
        t0,
        "get_customer_profile",
        {"email": email},
        {
            "customer_id": "CST-55555",
            "email": email,
            "tier": customer["tier"],
            "account_status": "suspended",
        },
    )
    spans.append(s)
    # Does not reactivate account; just tells customer to wait
    s, t0 = _agent_turn(
        trace_id,
        t0,
        [{"role": "tool_result", "tool": "get_customer_profile", "content": {"account_status": "suspended"}}],
        [],
        "I see your account is currently suspended. This is usually resolved automatically within 24 hours. Please check back tomorrow.",
    )
    spans.append(s)
    return spans


def _premature_escalation(trace_id: str, t0: datetime, customer: dict[str, Any]) -> list[Span]:
    """Escalates immediately without attempting to resolve a standard credit request."""
    spans: list[Span] = []
    email = customer["email"]

    user_msg = [
        {
            "role": "user",
            "content": f"There was an outage last night for about an hour. Can I get a service credit? Account: {email}.",
        }
    ]

    # Escalates immediately without trying to apply credit
    s, t0 = _agent_turn(
        trace_id,
        t0,
        user_msg,
        [
            {
                "tool": "escalate_to_human",
                "arguments": {"customer_email": email, "reason": "Service credit request", "priority": "normal"},
            }
        ],
        None,
    )
    spans.append(s)
    s, t0 = _tool(
        trace_id,
        t0,
        "escalate_to_human",
        {"customer_email": email, "reason": "Service credit request", "priority": "normal"},
        {"ticket_id": "TKT-66666", "assigned_to": "billing-team", "estimated_response": "4h"},
    )
    spans.append(s)
    s, t0 = _agent_turn(
        trace_id,
        t0,
        [{"role": "tool_result", "tool": "escalate_to_human", "content": {"ticket_id": "TKT-66666"}}],
        [],
        "I've escalated your credit request to our billing team (ticket TKT-66666). They'll follow up within 4 hours.",
    )
    spans.append(s)
    return spans


def _policy_violation(trace_id: str, t0: datetime, customer: dict[str, Any]) -> list[Span]:
    """Issues a partial refund — violates §1.3 (full refunds only)."""
    spans: list[Span] = []
    email = customer["email"]

    user_msg = [
        {
            "role": "user",
            "content": f"I only used Cascade for two weeks of last month. Can I get a partial refund? Account: {email}.",
        }
    ]

    s, t0 = _agent_turn(
        trace_id, t0, user_msg, [{"tool": "lookup_order", "arguments": {"customer_email": email}}], None
    )
    spans.append(s)
    s, t0 = _tool(
        trace_id,
        t0,
        "lookup_order",
        {"customer_email": email},
        {
            "order_id": "ORD-77777",
            "amount_usd": 79.0,
            "purchase_date": "2025-02-01",
            "status": "active",
        },
    )
    spans.append(s)
    # Partial refund: violates policy §1.3
    s, t0 = _agent_turn(
        trace_id,
        t0,
        [{"role": "tool_result", "tool": "lookup_order", "content": {"order_id": "ORD-77777", "amount_usd": 79.0}}],
        [
            {
                "tool": "issue_refund",
                "arguments": {
                    "order_id": "ORD-77777",
                    "amount_usd": 39.50,
                    "reason": "Partial refund for unused half-month",
                },
            }
        ],
        None,
    )
    spans.append(s)
    s, t0 = _tool(
        trace_id,
        t0,
        "issue_refund",
        {"order_id": "ORD-77777", "amount_usd": 39.50, "reason": "Partial refund for unused half-month"},
        {"refund_id": "REF-88888", "status": "processed", "amount_usd": 39.50},
    )
    spans.append(s)
    s, t0 = _agent_turn(
        trace_id,
        t0,
        [{"role": "tool_result", "tool": "issue_refund", "content": {"refund_id": "REF-88888", "amount_usd": 39.50}}],
        [],
        "I've processed a partial refund of $39.50 for the two weeks you didn't use (REF-88888). It will arrive in 3–5 business days.",
    )
    spans.append(s)
    return spans


def _scope_creep(trace_id: str, t0: datetime, customer: dict[str, Any]) -> list[Span]:
    """Customer asks a factual question; agent also applies an unrequested credit."""
    spans: list[Span] = []
    email = customer["email"]

    user_msg = [{"role": "user", "content": f"What's the storage limit on the Pro plan? Account: {email}."}]

    s, t0 = _agent_turn(
        trace_id,
        t0,
        user_msg,
        [{"tool": "search_kb", "arguments": {"query": "Pro plan storage limit", "max_results": 3}}],
        None,
    )
    spans.append(s)
    s, t0 = _tool(
        trace_id,
        t0,
        "search_kb",
        {"query": "Pro plan storage limit", "max_results": 3},
        {
            "articles": [
                {
                    "id": "KB-1001",
                    "title": "Pro Plan Features",
                    "snippet": "Pro plan includes 100 GB storage per workspace.",
                }
            ]
        },
    )
    spans.append(s)
    # Unprompted: applies a $10 credit
    s, t0 = _agent_turn(
        trace_id,
        t0,
        [
            {
                "role": "tool_result",
                "tool": "search_kb",
                "content": {"articles": [{"snippet": "Pro plan: 100 GB storage"}]},
            }
        ],
        [
            {
                "tool": "apply_credit",
                "arguments": {
                    "customer_email": email,
                    "amount_usd": 10.0,
                    "reason": "Goodwill credit for reaching out",
                },
            }
        ],
        None,
    )
    spans.append(s)
    s, t0 = _tool(
        trace_id,
        t0,
        "apply_credit",
        {"customer_email": email, "amount_usd": 10.0, "reason": "Goodwill credit for reaching out"},
        {"credit_id": "CRD-99999", "amount_applied_usd": 10.0, "new_credit_balance_usd": 10.0},
    )
    spans.append(s)
    s, t0 = _agent_turn(
        trace_id,
        t0,
        [{"role": "tool_result", "tool": "apply_credit", "content": {"credit_id": "CRD-99999"}}],
        [],
        "The Pro plan includes 100 GB of storage per workspace. I've also added a $10 goodwill credit to your account — thanks for being a customer!",
    )
    spans.append(s)
    return spans


# ── public API ────────────────────────────────────────────────────────────────

_GENERATORS = {
    "success": _success,
    "wrong_tool": _wrong_tool,
    "hallucinated_policy": _hallucinated_policy,
    "unresolved_ticket": _unresolved_ticket,
    "premature_escalation": _premature_escalation,
    "policy_violation": _policy_violation,
    "scope_creep": _scope_creep,
}


def generate_trace(
    category: FailureCategory = "success",
    *,
    seed: int | None = None,
    timestamp: datetime | None = None,
) -> Trace:
    """Generate a synthetic Cascade support trace for the given failure category."""
    rng = random.Random(seed)
    customer = rng.choice(_CUSTOMERS)
    trace_id = str(uuid.uuid4())
    t0 = timestamp if timestamp is not None else (
        datetime.now(UTC).replace(microsecond=0) - timedelta(hours=rng.randint(1, 48))
    )

    spans = _GENERATORS[category](trace_id, t0, customer)
    outcome: Literal["success", "failure", "unknown"] = "success" if category == "success" else "failure"

    return Trace(
        id=trace_id,
        agent_id=_AGENT_ID,
        session_id=str(uuid.uuid4()),
        created_at=t0,
        spans=spans,
        outcome=outcome,
        metadata={
            "label": category,
            "failure_category": None if category == "success" else category,
            "annotator": "synthetic",
            "customer_tier": customer["tier"],
        },
    )


def generate_dataset(
    n: int = 100,
    *,
    seed: int = 42,
    distribution: dict[FailureCategory, float] | None = None,
) -> list[Trace]:
    """Generate n traces with the given category distribution."""
    if distribution is None:
        distribution = {
            "success": 0.20,
            "wrong_tool": 0.15,
            "hallucinated_policy": 0.15,
            "unresolved_ticket": 0.15,
            "premature_escalation": 0.15,
            "policy_violation": 0.10,
            "scope_creep": 0.10,
        }
    categories = list(distribution.keys())
    weights = list(distribution.values())
    rng = random.Random(seed)
    chosen: list[FailureCategory] = rng.choices(categories, weights=weights, k=n)
    return [generate_trace(cat, seed=seed + i) for i, cat in enumerate(chosen)]


def generate_dataset_with_spike(
    n_baseline: int = 100,
    n_spike: int = 50,
    spike_category: FailureCategory = "hallucinated_policy",
    spike_rate: float = 0.60,
    *,
    seed: int = 42,
    window_hours: int = 24,
) -> list[Trace]:
    """Generate a trace stream with a baseline period followed by a failure spike.

    Baseline traces span [now - 2*window_hours, now - window_hours].
    Spike traces span [now - window_hours, now].
    During the spike period, spike_category makes up spike_rate of all traces.

    Designed to pair with AlarmDetector(window_hours=window_hours).
    """
    now = datetime.now(UTC).replace(microsecond=0)
    baseline_start = now - timedelta(hours=2 * window_hours)
    spike_start = now - timedelta(hours=window_hours)

    rng = random.Random(seed)
    traces: list[Trace] = []

    # Baseline period — normal failure distribution
    baseline_dist: dict[FailureCategory, float] = {
        "success": 0.50,
        "wrong_tool": 0.10,
        "hallucinated_policy": 0.10,
        "unresolved_ticket": 0.10,
        "premature_escalation": 0.10,
        "policy_violation": 0.05,
        "scope_creep": 0.05,
    }
    baseline_categories = list(baseline_dist.keys())
    baseline_weights = list(baseline_dist.values())
    chosen_baseline: list[FailureCategory] = rng.choices(baseline_categories, weights=baseline_weights, k=n_baseline)
    for i, cat in enumerate(chosen_baseline):
        offset_s = rng.randint(0, int(window_hours * 3600) - 1)
        ts = baseline_start + timedelta(seconds=offset_s)
        traces.append(generate_trace(cat, seed=seed + i, timestamp=ts))

    # Spike period — elevated rate for spike_category
    non_spike_categories: list[FailureCategory] = [c for c in baseline_dist if c != spike_category]
    non_spike_weights = [baseline_dist[c] for c in non_spike_categories]
    for i in range(n_spike):
        offset_s = rng.randint(0, int(window_hours * 3600) - 1)
        ts = spike_start + timedelta(seconds=offset_s)
        if rng.random() < spike_rate:
            cat = spike_category
        else:
            cat = rng.choices(non_spike_categories, weights=non_spike_weights, k=1)[0]
        traces.append(generate_trace(cat, seed=seed + n_baseline + i, timestamp=ts))

    return traces
