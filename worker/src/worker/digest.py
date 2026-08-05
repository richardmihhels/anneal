"""Weekly digest composer and notifier."""

from __future__ import annotations

import logging
import os
import smtplib
from dataclasses import dataclass
from datetime import timedelta
from email.mime.text import MIMEText
from typing import Protocol, runtime_checkable

from shared.models import (
    Alarm,
    EvalResult,
    FailureCluster,
    OptimizationRun,
    ProposedChange,
    WeeklyDigest,
)

from worker.models import RunEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DigestPR:
    url: str
    title: str
    change_id: str


@runtime_checkable
class DigestNotifier(Protocol):
    def send(self, digest: WeeklyDigest) -> None: ...


class FakeDigestNotifier:
    def __init__(self) -> None:
        self.sent: list[WeeklyDigest] = []

    def send(self, digest: WeeklyDigest) -> None:
        self.sent.append(digest)


class SMTPDigestNotifier:
    """Send weekly digest emails via SMTP.

    Required env vars:
      ANNEAL_SMTP_HOST, ANNEAL_SMTP_PORT (default 587),
      ANNEAL_SMTP_USER, ANNEAL_SMTP_PASSWORD,
      ANNEAL_DIGEST_FROM, ANNEAL_DIGEST_TO
    """

    def __init__(self) -> None:
        self._host = os.environ["ANNEAL_SMTP_HOST"]
        self._port = int(os.environ.get("ANNEAL_SMTP_PORT", "587"))
        self._user = os.environ["ANNEAL_SMTP_USER"]
        self._password = os.environ["ANNEAL_SMTP_PASSWORD"]
        self._from_addr = os.environ["ANNEAL_DIGEST_FROM"]
        self._to_addr = os.environ["ANNEAL_DIGEST_TO"]

    def send(self, digest: WeeklyDigest) -> None:
        msg = MIMEText(digest.email_body, "plain", "utf-8")
        msg["Subject"] = digest.subject
        msg["From"] = self._from_addr
        msg["To"] = self._to_addr

        try:
            with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(self._user, self._password)
                smtp.sendmail(self._from_addr, [self._to_addr], msg.as_string())
            logger.info("Weekly digest sent for run %s", digest.optimization_run_id)
        except Exception:
            logger.exception("Failed to send weekly digest %s", digest.id)


def compose_weekly_digest(
    *,
    run: OptimizationRun,
    events: list[RunEvent],
    clusters: list[FailureCluster],
    proposed_changes: list[ProposedChange],
    eval_results: list[EvalResult],
    previous_eval_results: list[EvalResult],
    alarms: list[Alarm],
    prs: list[DigestPR],
) -> WeeklyDigest:
    week_end = run.created_at
    week_start = week_end - timedelta(days=7)
    shipped = len(prs) > 0
    published_change_ids = {pr.change_id for pr in prs}
    published_changes = [change for change in proposed_changes if change.id in published_change_ids]
    health_evals = (
        [result for result in eval_results if result.proposed_change_id in published_change_ids]
        if shipped
        else eval_results
    )
    clusters_sorted = sorted(clusters, key=lambda c: c.size, reverse=True)
    health_direction = _health_direction(health_evals, previous_eval_results)
    summary = _summary(run, events, published_changes, eval_results, prs)
    body = _render_body(
        run=run,
        summary=summary,
        clusters=clusters_sorted,
        health_direction=health_direction,
        alarms=alarms,
        prs=prs,
    )

    return WeeklyDigest(
        optimization_run_id=run.id,
        organization_id=run.organization_id,
        agent_id=run.agent_id,
        week_start=week_start,
        week_end=week_end,
        subject=f"Anneal weekly digest: {run.agent_id}",
        summary=summary,
        pr_shipped=shipped,
        pr_urls=[pr.url for pr in prs],
        health_direction=health_direction,
        alarm_ids=[alarm.id for alarm in alarms],
        email_body=body,
        page_body=body,
    )


def _summary(
    run: OptimizationRun,
    events: list[RunEvent],
    proposed_changes: list[ProposedChange],
    eval_results: list[EvalResult],
    prs: list[DigestPR],
) -> str:
    if prs:
        changed = _change_summary(proposed_changes)
        noun = "PR" if len(prs) == 1 else "PRs"
        return f"Anneal shipped {len(prs)} {noun} this week. {changed}"

    holdout_size = _holdout_size(events)
    rejected = _rejected_count(events)
    if rejected > 0:
        holdout = f" on holdout n={holdout_size}" if holdout_size is not None else " on the holdout"
        noun = "candidate pattern" if rejected == 1 else "candidate patterns"
        return (
            f"No PR shipped this week. Anneal evaluated {rejected} {noun}{holdout}; "
            "none beat the current baseline with statistical confidence, so the safe outcome was to hold."
        )

    if eval_results:
        return (
            "No PR shipped this week. The baseline remained the strongest result on the holdout, "
            "so Anneal kept the agent unchanged."
        )

    return (
        "No PR shipped this week. No failure pattern produced a statistically useful prompt change, "
        "so Anneal kept the agent unchanged."
    )


def _change_summary(proposed_changes: list[ProposedChange]) -> str:
    if not proposed_changes:
        return "The shipped PR is linked below."
    first = proposed_changes[0]
    return f"It changed {first.target}: {first.rationale.splitlines()[0][:140]}."


def _render_body(
    *,
    run: OptimizationRun,
    summary: str,
    clusters: list[FailureCluster],
    health_direction: str,
    alarms: list[Alarm],
    prs: list[DigestPR],
) -> str:
    lines = [
        f"Weekly digest for {run.agent_id}",
        "",
        summary,
        "",
        "Failure clusters",
    ]

    if clusters:
        for cluster in clusters:
            lines.append(f"- {cluster.description} ({cluster.size} conversations)")
    else:
        lines.append("- No failure cluster crossed the threshold this week.")

    lines.extend(["", "Agent health", f"- {health_direction}", "", "Alarms"])
    if alarms:
        for alarm in sorted(alarms, key=lambda a: a.affected_trace_count, reverse=True):
            lines.append(
                f"- {alarm.category}: {alarm.current_rate:.1%} vs {alarm.baseline_rate:.1%} baseline; "
                f"{alarm.affected_trace_count} conversations affected."
            )
    else:
        lines.append("- No regression alarms fired this week.")

    if prs:
        lines.extend(["", "PRs"])
        for pr in prs:
            lines.append(f"- {pr.title}: {pr.url}")

    return "\n".join(lines)


def _health_direction(current: list[EvalResult], previous: list[EvalResult]) -> str:
    current_score = _average([er.candidate_score for er in current])
    previous_score = _average([er.candidate_score for er in previous])
    if current_score is None:
        return "No eval score was recorded for this run; the health chart will show this gap."
    if previous_score is None:
        return f"Eval score is {current_score:.1%}; no prior week is available for comparison."

    delta = current_score - previous_score
    if abs(delta) < 0.01:
        return f"Stable week over week at {current_score:.1%}."
    if delta > 0:
        return f"Improved by {delta:.1%} week over week to {current_score:.1%}."
    return f"Down {abs(delta):.1%} week over week to {current_score:.1%}; review the clusters above."


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _holdout_size(events: list[RunEvent]) -> int | None:
    for event in events:
        if event.stage == "optimization" and event.event == "completed":
            value = event.metadata.get("holdout_size")
            return value if isinstance(value, int) else None
    return None


def _rejected_count(events: list[RunEvent]) -> int:
    for event in events:
        if event.stage == "optimization" and event.event == "completed":
            value = event.metadata.get("rejected")
            return value if isinstance(value, int) else 0
    return 0
