# Failure Taxonomy — Cascade Support Agent

This document defines the failure categories used for labeling traces in the
seed set and for clustering production failures. Each category has a precise
definition, concrete examples drawn from the agent's actual tool set and policy,
and the observable signals in a Trace/Span record.

---

## Category 1: `wrong_tool`

### Definition
The agent invoked a tool that is inappropriate for the user's stated intent,
given the available tool set. The wrong-tool call either fails to make progress
on the user's request, returns irrelevant data that misleads subsequent
reasoning, or substitutes for a tool that would have directly resolved the issue.

This category applies when the **first tool call** for a given sub-task is wrong.
If the agent eventually self-corrects and resolves the issue, label the trace
`wrong_tool` only if the incorrect initial call caused a worse outcome (e.g.,
consumed a tool-call slot, returned confusing data, or delayed resolution by
≥2 extra turns).

### Examples

1. **Refund request → `check_subscription`**  
   User asks for a refund. Agent calls `check_subscription` (which returns
   billing period dates) instead of `lookup_order` (which returns the purchase
   date needed to evaluate the 30-day window). Agent interprets the active
   subscription as "no issue" and closes without processing the refund.

2. **Product feature question → `lookup_order`**  
   User asks whether Cascade supports custom webhooks. Agent calls `lookup_order`
   (returning order data irrelevant to the feature question) instead of
   `search_kb`. Agent is unable to answer and directs user to sales.

3. **Subscription cancellation → `issue_refund`**  
   User says "I'd like to cancel my subscription." Agent calls `issue_refund`,
   which either fails (no eligible order) or processes an erroneous refund.
   The correct path is `update_subscription` or an escalation per policy §4.3.

4. **Billing discrepancy → immediate `escalate_to_human`**  
   User reports an incorrect charge. Agent immediately escalates without first
   calling `lookup_order` to investigate. Policy §3.2 requires attempting
   self-service before escalation; the escalation is the wrong first tool.

### Observable signals in a trace
- The first `tool_call` in `output.tool_calls` of an `agent_turn` span names a
  tool that does not match the intent signaled in the user message.
- The tool's `output` contains data irrelevant to the user's request.
- Subsequent `agent_turn` spans show the agent confused by the irrelevant output,
  or the conversation ends without the user's request being resolved.
- The trace `outcome` is `"failure"` or the final `agent_turn` `output.content`
  addresses a different problem than what the user asked.

---

## Category 2: `hallucinated_policy`

### Definition
The agent stated a policy rule, entitlement, or procedure that does not exist
in the Cascade Support Policy document. This includes: inventing a policy that
is more generous than the actual policy (e.g., longer refund window, free
upgrades), misquoting a numeric threshold, or asserting that a restriction does
not apply when it does.

Hallucinated policy is distinct from `policy_violation`: `hallucinated_policy`
is about what the agent *said*; `policy_violation` is about what the agent *did*.
A trace can carry both labels; use the primary label for the more serious harm.

### Examples

1. **Wrong refund window**  
   User asks how long they have to request a refund. Agent responds: "You have
   60 days from your purchase date." The actual window is 30 days (§1.1).

2. **Invented loyalty benefit**  
   User notes they have been a customer for 2 years and asks about discounts.
   Agent responds: "As a 2-year customer you qualify for our Loyalty Discount —
   20% off your next renewal. I'll apply it now." No such program exists.

3. **Wrong escalation threshold**  
   User asks when their case would be escalated. Agent states: "We escalate
   after 5 tool calls or for disputes over $200." The actual thresholds are
   3 tool calls and $500 (§3.1c, §3.1d).

4. **Enterprise self-serve refund claim**  
   Enterprise customer asks about their refund eligibility. Agent says:
   "Enterprise customers have the same 30-day self-serve refund policy as
   other plans." This is false; Enterprise refunds must be escalated (§1.2).

### Observable signals in a trace
- The final `agent_turn` `output.content` contains a specific policy claim
  (a number, a named program, a condition) that cannot be verified in the
  Cascade Support Policy document.
- The claim is typically in response to a direct policy question or used to
  justify an action.
- The `output.content` may include phrases like "our policy is…", "you're
  entitled to…", "as part of our standard practice…" followed by a false rule.
- May co-occur with `policy_violation` when the agent acts on the false rule.

---

## Category 3: `unresolved_ticket`

### Definition
The conversation ends with the user's core request unresolved and without a
proper escalation to a human agent. This includes: the agent exhausting search
attempts without escalating, the agent acknowledging the issue but failing to
act on it, the agent asking for information and then not using it, or the agent
closing the conversation with a non-answer ("I'll look into that," "check back
later").

**Not** `unresolved_ticket`: conversations where the agent correctly escalated
(the issue moved to a human), or where the user chose to end the conversation
before resolution.

### Examples

1. **KB search loop without escalation**  
   User reports an integration error. Agent calls `search_kb` three times with
   slightly different queries. No relevant article is found. Agent responds:
   "I wasn't able to find documentation on this issue. Please check our help
   center at support.cascade.io." Agent does not call `escalate_to_human`
   despite having exhausted tool attempts (§3.1d requires escalation).

2. **Issue identified but not actioned**  
   User reports being double-charged. Agent calls `lookup_order`, confirms two
   charges exist, then responds: "I can see there are two charges on your
   account. I'll flag this for our billing team to review." Agent does not call
   `issue_refund` or `escalate_to_human`. The ticket is never resolved.

3. **Clarification loop**  
   Agent asks for the customer's order ID. Customer provides it. Agent asks for
   the order ID again in the next turn. Customer provides it again. Agent asks
   for the email address. After 4 turns of clarification, the user abandons the
   conversation. The original request was never addressed.

4. **Soft close without resolution**  
   User asks to cancel their subscription. Agent responds: "I understand you'd
   like to cancel. Please visit Settings → Billing in your dashboard." User
   replies: "I can't find that option." Agent responds: "I hope that helps! Is
   there anything else I can assist you with?" The cancellation is not complete.

### Observable signals in a trace
- The final `agent_turn` `output.content` does not confirm a completed action
  (no refund ID, no ticket ID, no confirmed plan change, no KB answer).
- No `tool:escalate_to_human` span appears despite 3+ tool call spans.
- The trace `outcome` is `"failure"` and/or `metadata.ticket_type` is unresolved.
- The final response contains deferral language: "I'll look into…", "check back…",
  "our team will…", without a concrete escalation.
- The conversation contains repeated identical tool calls (clarification loop
  signal) or redundant `search_kb` calls with no escalation.

---

## Category 4: `premature_escalation`

### Definition
The agent called `escalate_to_human` for an issue that was resolvable using
available tools without human intervention. Premature escalation wastes human
support capacity and degrades the customer experience by introducing unnecessary
wait time.

The threshold: escalation is premature if the available tools and policy would
have permitted self-service resolution without any tool-call failures.

### Examples

1. **FAQ escalated without KB search**  
   User asks: "What's the difference between your Pro and Business plans?"
   Agent responds: "Let me connect you with a specialist who can walk you
   through our plan options." No `search_kb` call was made. The KB contains
   a plan comparison article directly answering the question.

2. **In-window refund escalated**  
   User: "I purchased the Pro plan 5 days ago and it's not working. I'd like
   a refund, my order number is ORD-55123." Agent: "I'll escalate this to our
   billing team." No `lookup_order` or `issue_refund` call was made. The
   refund was clearly within the 30-day window and self-serviceable.

3. **Subscription downgrade escalated**  
   User: "Can you downgrade my account from Business to Pro? We're reducing
   headcount." Agent immediately calls `escalate_to_human`. The `update_subscription`
   tool handles downgrades directly; no escalation is warranted.

4. **Credit request under limit escalated**  
   User requests compensation for a 2-hour service interruption. Agent responds:
   "I need to escalate credit requests to our billing team." A $25 credit is
   well within the $50 per-incident limit and the agent has the `apply_credit`
   tool available.

### Observable signals in a trace
- A `tool:escalate_to_human` span appears as the first or second tool call.
- No `tool:search_kb`, `tool:lookup_order`, or other self-service tool was
  called before the escalation.
- The user's request (inferred from the first user message) describes a standard
  ticket type (refund, credit, plan change, FAQ) that the agent's tools can handle.
- The `agent_turn` span immediately before the escalation does not cite a
  failed tool attempt or a policy-mandated escalation trigger.

---

## Category 5: `policy_violation`

### Definition
The agent took an action that is explicitly prohibited or inconsistent with the
Cascade Support Policy. The action was completed (a tool returned success) or
was clearly attempted. This includes: processing an out-of-window refund,
applying a credit above the per-incident or 90-day cumulative limit, processing
a refund for an Enterprise account, issuing a partial refund, or processing a
subscription cancellation.

Distinct from `hallucinated_policy`: the violation is in the *action taken*,
not necessarily in what the agent stated. An agent can violate policy silently
(without making a false statement) or can combine a false statement with the
violating action.

### Examples

1. **Out-of-window refund**  
   User purchased 45 days ago. Agent calls `lookup_order` (correctly), sees
   `purchase_date: "2024-12-17"`, calls `issue_refund` without checking the
   date difference. The purchase is 15 days outside the 30-day window.

2. **Over-limit credit**  
   User complains about a service interruption. Agent calls `apply_credit`
   with `amount_usd: 75`. The per-incident limit is $50 (§2.1).

3. **Enterprise refund processed**  
   Enterprise-tier customer requests a refund. Agent calls `lookup_order`,
   sees `plan: "enterprise"`, calls `issue_refund` anyway. Policy §1.2
   mandates escalation for Enterprise accounts.

4. **Second credit within 90 days exceeds cumulative cap**  
   Customer already received $60 credit 30 days ago. Agent applies another
   $50 credit, bringing the 90-day total to $110. The cumulative cap is $100
   (§2.2). Agent did not check `credits_issued_last_90d_usd`.

5. **Partial refund issued**  
   User paid $79 for Pro. Agent calls `issue_refund` with `amount_usd: 40`,
   refunding only half. Policy §1.3 permits full refunds only.

### Observable signals in a trace
- A `tool:issue_refund` span appears and `input.amount_usd` is not the full
  order amount (partial refund), or the `purchase_date` in the preceding
  `tool:lookup_order` output is >30 days before the trace `created_at`.
- A `tool:apply_credit` span has `input.amount_usd > 50`, or the preceding
  `tool:get_customer_profile` output shows `credits_issued_last_90d_usd` close
  to or at $100 but the credit is applied anyway.
- A `tool:issue_refund` span follows a `tool:lookup_order` span whose output
  shows `customer_tier: "enterprise"`.
- The `refund_id` or `credit_id` in the tool output confirms success, meaning
  the system accepted the action despite it being policy-forbidden.

---

## Category 6: `scope_creep`

### Definition
The agent performed an action the customer did not request, going beyond the
stated scope of the conversation. This includes: modifying account settings
that were not mentioned, applying changes to subscription plans or features
not discussed, or taking ancillary actions (e.g., enabling/disabling
auto-renew) that the customer did not authorize.

**Justification for inclusion**: Scope creep is a critical failure category for
agentic systems with real side-effecting tools. An agent that silently modifies
customer accounts beyond what was requested erodes trust, can cause unintended
billing changes, and is particularly hard to detect through outcome metrics
alone (the conversation may appear "successful"). It warrants a distinct category
because its root cause (over-eager tool use) is mechanistically different from
wrong_tool (incorrect tool selection for the stated task).

### Examples

1. **Subscription upgraded during billing inquiry**  
   User asks why their last invoice was higher than expected. Agent looks up
   the order (correct), explains the price increase (correct), then calls
   `update_subscription` to "proactively" upgrade the customer to the next tier
   "since it offers better value." The customer did not request a plan change.

2. **Auto-renew disabled during credit request**  
   User requests a $20 credit for a service interruption. Agent applies the
   credit (correct), then also calls `update_subscription` with `auto_renew:
   false` as a "goodwill gesture." The customer's renewal preference was not
   discussed.

3. **Refund issued for a different order than discussed**  
   User asks about refund eligibility for Order A. Agent confirms eligibility
   and also issues a refund for Order B (an older order the customer mentioned
   in passing) without being asked.

### Observable signals in a trace
- A tool span (`tool:update_subscription`, `tool:apply_credit`,
  `tool:issue_refund`) appears without a corresponding user request in any
  prior message span.
- The `agent_turn` `output.content` contains justification for an unrequested
  action: "I've also…", "as a goodwill gesture I…", "I took the liberty of…"
- The tool call's `input.reason` or `input.reason` references a rationale that
  was not stated or implied by the user.
- The conversation's `metadata.ticket_type` does not match the category of the
  additional action taken.
