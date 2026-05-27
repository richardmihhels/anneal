from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GitHubGateway(Protocol):
    """Minimal GitHub surface needed to open an Anneal PR."""

    def get_file(self, repo: str, path: str, ref: str) -> tuple[str, str]:
        """Return (content, sha) for the file at path on ref."""
        ...

    def create_branch(self, repo: str, branch: str, from_ref: str) -> None:
        """Create a new branch pointing at the tip of from_ref."""
        ...

    def update_file(
        self,
        repo: str,
        path: str,
        content: str,
        sha: str,
        branch: str,
        message: str,
    ) -> None:
        """Commit content to path on branch, replacing the blob with sha."""
        ...

    def create_pr(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        label: str,
    ) -> str:
        """Open a pull request tagged with label. Returns the PR URL."""
        ...

    def find_open_pr(self, repo: str, label: str) -> str | None:
        """Return URL of an open PR tagged with label, or None."""
        ...


@dataclass
class FakeGitHubGateway:
    """In-memory gateway for tests. Not thread-safe."""

    _files: dict[str, dict[str, tuple[str, str]]] = field(default_factory=dict)
    _prs: list[dict[str, str]] = field(default_factory=list)

    def add_file(self, repo: str, path: str, content: str, sha: str = "abc123") -> None:
        self._files.setdefault(repo, {})[path] = (content, sha)

    def get_file(self, repo: str, path: str, ref: str) -> tuple[str, str]:
        try:
            return self._files[repo][path]
        except KeyError:
            raise FileNotFoundError(f"{repo}/{path}@{ref} not found in fake gateway")

    def create_branch(self, repo: str, branch: str, from_ref: str) -> None:
        pass  # no-op: branches are implicit in the fake

    def update_file(
        self,
        repo: str,
        path: str,
        content: str,
        sha: str,
        branch: str,
        message: str,
    ) -> None:
        self._files.setdefault(repo, {})[path] = (content, sha + "-updated")

    def create_pr(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        label: str,
    ) -> str:
        url = f"https://github.com/{repo}/pull/{len(self._prs) + 1}"
        self._prs.append(
            {
                "repo": repo,
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "label": label,
                "url": url,
                "state": "open",
            }
        )
        return url

    def find_open_pr(self, repo: str, label: str) -> str | None:
        for pr in self._prs:
            if pr["repo"] == repo and pr["label"] == label and pr["state"] == "open":
                return pr["url"]
        return None

    @property
    def opened_prs(self) -> list[dict[str, str]]:
        return list(self._prs)


class GitHubAppClient:
    """Real GitHub gateway authenticated as a GitHub App installation.

    Reads GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY from the environment if not
    passed explicitly. The App must be installed on every target repo.

    Setup: https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps
    """

    def __init__(self, app_id: int, private_key: str) -> None:
        import github

        auth = github.Auth.AppAuth(app_id, private_key)
        self._integration = github.GithubIntegration(auth=auth)

    def _repo(self, repo: str) -> Any:
        owner, name = repo.split("/", 1)
        installation = self._integration.get_repo_installation(owner, name)
        g = self._integration.get_github_for_installation(installation.id)
        return g.get_repo(repo)

    def get_file(self, repo: str, path: str, ref: str) -> tuple[str, str]:
        r = self._repo(repo)
        obj = r.get_contents(path, ref=ref)
        if isinstance(obj, list):
            raise ValueError(f"{path} is a directory")
        content = base64.b64decode(obj.content).decode()
        return content, obj.sha

    def create_branch(self, repo: str, branch: str, from_ref: str) -> None:
        r = self._repo(repo)
        sha = r.get_branch(from_ref).commit.sha
        r.create_git_ref(ref=f"refs/heads/{branch}", sha=sha)

    def update_file(
        self,
        repo: str,
        path: str,
        content: str,
        sha: str,
        branch: str,
        message: str,
    ) -> None:
        r = self._repo(repo)
        r.update_file(path, message, content, sha, branch=branch)

    def create_pr(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        label: str,
    ) -> str:
        import github

        r = self._repo(repo)
        try:
            r.get_label(label)
        except github.GithubException:
            r.create_label(label, color="0075ca")
        pr = r.create_pull(title=title, body=body, head=head, base=base)
        pr.add_to_labels(label)
        return str(pr.html_url)

    def find_open_pr(self, repo: str, label: str) -> str | None:

        r = self._repo(repo)
        prs = r.get_pulls(state="open")
        for pr in prs:
            for lbl in pr.labels:
                if lbl.name == label:
                    return str(pr.html_url)
        return None
