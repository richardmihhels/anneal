# Dataset Specification — Synthetic Trace Generator

This document specifies exactly what the Prompt 2 generator must produce.
Two engineers reading this document independently should produce generators
whose outputs are statistically indistinguishable in distribution.

---

## 1. Target Volume

| Dimension                  | Value                                      |
|----------------------------|--------------------------------------------|
| Total traces               | **500**                                    |
| Minimum traces per failure category | **30**                            |
| Minimum success traces     | **200**                                    |
| Agent ID (all traces)      | `cascade-support-v1`                       |
| Date range                 | 2025-01-01 through 2025-03-31              |

---

## 2. Label Distribution

Generate traces in the following proportions. These reflect a realistic V1
production agent where most runs succeed but failures are oversampled relative
to true production rates so every category has sufficient training coverage.

| Label                    | Target fraction | Minimum count |
|--------------------------|-----------------|---------------|
| `success`                | 40%             | 200           |
| `wrong_tool`             | 12%             | 60            |
| `hallucinated_policy`    | 10%             | 50            |
| `unresolved_ticket`      | 12%             | 60            |
| `premature_escalation`   | 12%             | 60            |
| `policy_violation`       | 10%             | 50            |
| `scope_creep`            | 4%              | 20            |
| **Total**                | **100%**        | **500**       |

### Sub-type requirements within categories

**`wrong_tool` must include at least:**
- 15 traces where `check_subscription` was called when `lookup_order` was needed
- 10 traces where `lookup_order` was called when `search_kb` was needed
- 10 traces where `escalate_to_human` was the first call without any self-service attempt
- 10 traces where `issue_refund` was called for a non-refund intent
- 15 traces with other wrong-tool combinations

**`policy_violation` must include at least:**
- 15 traces with out-of-window refunds (purchase_date >30 days before trace date)
- 10 traces with over-limit credits (amount_usd >50)
- 10 traces with Enterprise-account refunds
- 10 traces where cumulative 90-day credit cap exceeded
- 5 traces with partial refunds

**`hallucinated_policy` must include at least:**
- 15 traces with wrong refund window stated (the most common failure)
- 10 traces with invented compensation programs
- 10 traces with wrong escalation thresholds
- 15 traces with other false policy claims

---

## 3. Diversity Requirements

The generator must randomize across all dimensions below. Every cell in the
cross-product need not appear, but no single value should account for >30%
of the total dataset in any dimension.

### 3a. Customer tier

| Tier         | Target fraction |
|--------------|-----------------|
| `starter`    | 20%             |
| `pro`        | 35%             |
| `business`   | 30%             |
| `enterprise` | 15%             |

### 3b. Ticket type

Every trace must be assigned exactly one primary `ticket_type`:

| Type                  | Description                                   | Target fraction |
|-----------------------|-----------------------------------------------|-----------------|
| `refund`              | Customer requests money back                  | 22%             |
| `billing_question`    | Question about charges, invoices, dates       | 18%             |
| `subscription_change` | Upgrade, downgrade, or cancellation request   | 18%             |
| `credit_request`      | Request for account credit / compensation     | 12%             |
| `product_question`    | Feature question, how-to, documentation       | 15%             |
| `account_issue`       | Login, SSO, permissions, account settings     | 10%             |
| `other`               | Anything not covered above                    | 5%              |

### 3c. Customer tone

Assign one of these values to `metadata.customer_tone`:

| Tone          | Description                                          | Target fraction |
|---------------|------------------------------------------------------|-----------------|
| `neutral`     | Matter-of-fact, no emotional language                | 45%             |
| `frustrated`  | Expresses dissatisfaction, urgency, or irritation    | 35%             |
| `polite`      | Explicitly appreciative or apologetic in phrasing    | 20%             |

Frustrated tone must appear in at least 40% of `policy_violation` and
`unresolved_ticket` traces, since real escalations skew toward frustrated users.

### 3d. Conversation length

`conversation_length` is the number of complete user→agent→(tool?)→agent cycles.

| Length      | Turns | Target fraction |
|-------------|-------|-----------------|
| `short`     | 1     | 35%             |
| `medium`    | 2–3   | 45%             |
| `long`      | 4–6   | 20%             |

`premature_escalation` traces must be `short` (the escalation happens before
any real back-and-forth). `unresolved_ticket` traces must skew medium-to-long
(the agent makes multiple attempts before failing).

---

## 4. Required Fields per Trace

Every generated trace must fully populate the following fields, with no null
values except where noted.

### Trace-level fields

| Field           | Type     | Notes                                                       |
|-----------------|----------|-------------------------------------------------------------|
| `id`            | string   | UUID v4                                                     |
| `agent_id`      | string   | Always `"cascade-support-v1"`                               |
| `session_id`    | string   | UUID v4, unique per trace                                   |
| `created_at`    | datetime | ISO 8601 with timezone, within 2025-01-01–2025-03-31        |
| `outcome`       | string   | `"success"` for success traces; `"failure"` for all others  |
| `spans`         | array    | See span requirements below                                 |
| `metadata.label` | string  | The ground-truth label (one of 7 categories above)          |
| `metadata.failure_category` | string\|null | Same as label for failures; `null` for success |
| `metadata.rationale` | string | One sentence explaining why this label was assigned     |
| `metadata.customer_email` | string | Fictional email, consistent within session             |
| `metadata.customer_tier` | string | One of the 4 tier values                               |
| `metadata.ticket_type` | string | One of the 7 ticket types                               |
| `metadata.customer_tone` | string | One of the 3 tone values                               |
| `metadata.conversation_length` | string | `"short"`, `"medium"`, or `"long"`             |

### Span requirements

Every trace must contain a minimum of **2 spans** and a maximum of **10 spans**.
Every span must populate all required fields in the `Span` schema.

**Span types and naming conventions:**

| Span name pattern             | Meaning                                        |
|-------------------------------|------------------------------------------------|
| `agent_turn`                  | LLM processing step; may produce tool calls    |
| `tool:get_customer_profile`   | Tool execution — get_customer_profile          |
| `tool:lookup_order`           | Tool execution — lookup_order                  |
| `tool:check_subscription`     | Tool execution — check_subscription            |
| `tool:search_kb`              | Tool execution — search_kb                     |
| `tool:issue_refund`           | Tool execution — issue_refund                  |
| `tool:apply_credit`           | Tool execution — apply_credit                  |
| `tool:update_subscription`    | Tool execution — update_subscription           |
| `tool:escalate_to_human`      | Tool execution — escalate_to_human             |

**`agent_turn` span structure:**

```json
{
  "input": {
    "messages": [
      {"role": "user", "content": "<the user's message>"}
    ]
  },
  "output": {
    "content": "<assistant text response, or null if tool call>",
    "tool_calls": [
      {"tool": "<tool_name>", "arguments": {<tool input>}}
    ]
  }
}
```

`tool_calls` is an empty array `[]` when the agent produces a text response.
`content` is `null` when the agent produces only tool calls.

**Tool span structure:**

```json
{
  "input": {<exact arguments passed to the tool>},
  "output": {<tool return value, including all fields from the output schema>},
  "error": null
}
```

For deliberate failure scenarios (e.g., `issue_refund` called outside the
window), set `output.status = "failed"` and `output.failure_reason` to a
short explanation. Do **not** use the `error` field for business-logic failures;
reserve `error` for tool infrastructure errors (timeouts, unavailable).

### Timing constraints

- `duration_ms` for `agent_turn` spans: sample from Normal(1400, 400), clipped to [600, 3000]
- `duration_ms` for tool spans: sample from Normal(650, 200), clipped to [150, 1500]
- `end_time` = `start_time` + `duration_ms` milliseconds
- Spans are sequential (no overlap); each span starts 10–50ms after the previous ends
- Trace `created_at` = start time of the first span

---

## 5. Realism Constraints

The generator must produce data that a human reviewer would find plausible as
real customer support interactions.

- Customer emails must be fictional but plausible (firstname.lastname@company.tld)
- Order IDs use format `ORD-NNNNN` (5-digit number)
- Refund IDs: `REF-NNNNN`
- Credit IDs: `CRD-NNNNN`
- Ticket IDs: `TKT-NNNNN`
- Customer IDs: `CST-NNNNN`
- Plan amounts: Starter $29, Pro $79, Business $149, Enterprise $0 (custom)
- For `policy_violation` / out-of-window refund traces: the `purchase_date` in
  the `tool:lookup_order` output must be 31–120 days before `created_at`
- For valid refund traces: `purchase_date` must be 1–28 days before `created_at`
- `credits_issued_last_90d_usd` from `get_customer_profile` must be consistent
  with any prior credits visible in the same trace

---

## 6. What the Generator Must NOT Do

- Do not reuse the 25–30 seed traces from `evals/seed-set/`. These are
  calibration ground truth and must remain unseen by the generator and by GEPA.
- Do not copy user-message text verbatim from the seed set.
- Do not produce traces where the `label` field is inconsistent with the
  observable span data (the labeler logic must derive the label from the spans).
- Do not produce traces with `outcome: "unknown"` — every synthetic trace has a
  deterministic label.
