"""Alarm email notifier: calm, precise, fires rarely."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Protocol, runtime_checkable

from shared.models import Alarm

logger = logging.getLogger(__name__)


def _format_email_body(alarm: Alarm) -> str:
    return (
        f"Anneal detected a statistically significant spike in your agent '{alarm.agent_id}'.\n\n"
        f"Failure category : {alarm.category}\n"
        f"Baseline rate    : {alarm.baseline_rate:.1%}  (previous {alarm.window_hours}h)\n"
        f"Current rate     : {alarm.current_rate:.1%}  (last {alarm.window_hours}h)\n"
        f"Affected convs   : {alarm.affected_trace_count}\n"
        f"First detected   : {alarm.first_detected.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"{alarm.cause_hypothesis}\n\n"
        f"Suggested next step: Review the {alarm.affected_trace_count} most recent "
        f"'{alarm.category}' conversations in your trace dashboard to identify a "
        f"common pattern, then decide whether a prompt change or upstream fix is needed.\n\n"
        f"---\n"
        f"This alarm fires only when the rate increase is statistically significant "
        f"(p < 0.05). You will not receive another alert for this category "
        f"for 24 hours unless the spike continues.\n"
    )


def _format_subject(alarm: Alarm) -> str:
    return f"[Anneal] {alarm.category} spike on {alarm.agent_id} — {alarm.baseline_rate:.1%} → {alarm.current_rate:.1%}"


@runtime_checkable
class AlarmNotifier(Protocol):
    def send(self, alarm: Alarm) -> None: ...


class FakeEmailNotifier:
    """Captures sent emails for tests."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send(self, alarm: Alarm) -> None:
        self.sent.append(
            {
                "subject": _format_subject(alarm),
                "body": _format_email_body(alarm),
                "alarm_id": alarm.id,
            }
        )


class LoggingAlarmNotifier:
    """Log detected alarms when SMTP delivery is not configured."""

    def send(self, alarm: Alarm) -> None:
        logger.warning("%s", _format_subject(alarm))


class SMTPEmailNotifier:
    """Send alarm emails via SMTP.

    Required env vars:
      ANNEAL_SMTP_HOST, ANNEAL_SMTP_PORT (default 587),
      ANNEAL_SMTP_USER, ANNEAL_SMTP_PASSWORD,
      ANNEAL_ALERT_FROM, ANNEAL_ALERT_TO
    """

    def __init__(self) -> None:
        self._host = os.environ["ANNEAL_SMTP_HOST"]
        self._port = int(os.environ.get("ANNEAL_SMTP_PORT", "587"))
        self._user = os.environ["ANNEAL_SMTP_USER"]
        self._password = os.environ["ANNEAL_SMTP_PASSWORD"]
        self._from_addr = os.environ["ANNEAL_ALERT_FROM"]
        self._to_addr = os.environ["ANNEAL_ALERT_TO"]

    def send(self, alarm: Alarm) -> None:
        msg = MIMEText(_format_email_body(alarm), "plain", "utf-8")
        msg["Subject"] = _format_subject(alarm)
        msg["From"] = self._from_addr
        msg["To"] = self._to_addr

        try:
            with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(self._user, self._password)
                smtp.sendmail(self._from_addr, [self._to_addr], msg.as_string())
            logger.info(
                "Alarm email sent for category '%s' on agent '%s'",
                alarm.category,
                alarm.agent_id,
            )
        except Exception:
            logger.exception("Failed to send alarm email for alarm %s", alarm.id)
