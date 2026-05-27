from __future__ import annotations

import logging
from dataclasses import dataclass

from shared.models import EvalResult, ProposedChange

from core.github.client import GitHubGateway
from core.github.pr import build_pr_body, build_pr_title, build_silence_report, pr_label
from core.optimizer.engine import OptimizationResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpenedPR:
    url: str
    title: str
    change_id: str


@dataclass(frozen=True)
class PublishResult:
    opened: tuple[OpenedPR, ...]
    skipped_existing: int
    skipped_failed_gate: int
    silence_report: str | None  # set when nothing was opened and no PRs existed

    @property
    def anything_opened(self) -> bool:
        return len(self.opened) > 0


class PRPublisher:
    """Opens gated, idempotent GitHub PRs for each surviving ProposedChange.

    Hard gates:
    - Skips any change whose EvalResult.passed is False.
    - Skips any change where the before text is not found verbatim in the
      config file (patch application would be unsafe).

    Idempotency:
    - Before opening a PR, checks for an existing open PR with the same
      anneal:{key} label. If found, skips. Key is stable across re-runs as
      long as the cluster description and baseline prompt are unchanged.

    Silence path:
    - When no PRs are opened and no pre-existing Anneal PRs cover the batch,
      PublishResult.silence_report contains a positive summary message.
    """

    def __init__(
        self,
        gateway: GitHubGateway,
        repo: str,
        config_path: str,
        base_branch: str = "main",
    ) -> None:
        self._gateway = gateway
        self._repo = repo
        self._config_path = config_path
        self._base_branch = base_branch

    def publish(self, result: OptimizationResult) -> PublishResult:
        """Publish surviving changes as PRs. Returns a summary of what happened."""
        opened: list[OpenedPR] = []
        skipped_existing = 0
        skipped_failed_gate = 0

        paired = list(zip(result.proposed_changes, result.eval_results))

        for change, ev in paired:
            # Hard gate — belt-and-suspenders; optimizer should never emit non-passing changes
            if not ev.passed:
                logger.warning(
                    "Skipping change %s: EvalResult.passed=False (delta=%.3f, p=%.4f)",
                    change.id,
                    ev.delta,
                    ev.p_value,
                )
                skipped_failed_gate += 1
                continue

            label = pr_label(change)

            existing = self._gateway.find_open_pr(self._repo, label)
            if existing:
                logger.info("Skipping change %s: open PR already exists (%s)", change.id, existing)
                skipped_existing += 1
                continue

            pr = self._open_pr(change, ev)
            if pr is not None:
                opened.append(pr)

        silence = None
        if not opened and skipped_existing == 0:
            silence = build_silence_report(len(paired))

        return PublishResult(
            opened=tuple(opened),
            skipped_existing=skipped_existing,
            skipped_failed_gate=skipped_failed_gate,
            silence_report=silence,
        )

    def _open_pr(self, change: ProposedChange, ev: EvalResult) -> OpenedPR | None:
        try:
            content, sha = self._gateway.get_file(self._repo, self._config_path, self._base_branch)
        except FileNotFoundError:
            logger.warning(
                "Config file %s not found in %s — skipping change %s",
                self._config_path,
                self._repo,
                change.id,
            )
            return None

        patched = content.replace(change.before, change.after, 1)
        if patched == content:
            logger.warning(
                "Before-text not found verbatim in %s — skipping change %s. "
                "The config may have been updated since this change was generated.",
                self._config_path,
                change.id,
            )
            return None

        branch = f"anneal/{change.id[:8]}"
        title = build_pr_title(change, ev)
        body = build_pr_body(change, ev)
        label = pr_label(change)

        try:
            self._gateway.create_branch(self._repo, branch, self._base_branch)
            self._gateway.update_file(
                self._repo,
                self._config_path,
                patched,
                sha,
                branch,
                f"fix(prompt): {title}",
            )
            url = self._gateway.create_pr(self._repo, title, body, branch, self._base_branch, label)
        except Exception:
            logger.exception("Failed to open PR for change %s", change.id)
            return None

        logger.info("Opened PR for change %s: %s", change.id, url)
        return OpenedPR(url=url, title=title, change_id=change.id)
