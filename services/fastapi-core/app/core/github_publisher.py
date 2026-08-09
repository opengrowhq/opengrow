"""GitHub PR publishing gateway — the ONLY place the GitHub API is called.

Publishes a Markdown document to a repo by:
  1. resolving the base branch head SHA,
  2. creating (or reusing) a feature branch,
  3. writing the file via the Contents API,
  4. opening (or returning the existing) pull request.

BYOK: callers can pass a resolved tenant token; otherwise the gateway falls back
to settings.GITHUB_TOKEN (env in lite, Infisical in prod). No GitHub SDK — plain
REST via httpx, to keep the dependency surface tight.
"""

from __future__ import annotations

import base64
import re
from typing import Any
from urllib.parse import quote

import httpx

from app.config import get_settings

_API_VERSION = "2022-11-28"

# Allowlists for user-supplied values interpolated into GitHub API URLs. Validating
# against these (and URL-encoding on use) keeps every request pinned to the
# configured GitHub host — a caller can't smuggle a different host/path via the
# repo, branch, or file path.
_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
_REF_RE = re.compile(r"^[A-Za-z0-9._/-]{1,255}$")


class GitHubPublishError(Exception):
    """Raised for any non-recoverable failure talking to the GitHub API."""


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": _API_VERSION,
    }


def parse_repo(repo: str) -> tuple[str, str]:
    parts = repo.strip().strip("/").split("/")
    if len(parts) != 2 or not all(parts):
        raise GitHubPublishError(f"Invalid repo '{repo}' — expected 'owner/name'")
    owner, name = parts
    if not _OWNER_RE.match(owner) or not _NAME_RE.match(name):
        raise GitHubPublishError(
            f"Invalid repo '{repo}' — illegal owner/name characters"
        )
    return owner, name


def _validate_ref(ref: str, *, kind: str) -> str:
    """Validate a git ref/branch name before it goes into an API URL."""
    if (
        not _REF_RE.match(ref)
        or ".." in ref
        or ref.startswith("/")
        or ref.endswith("/")
    ):
        raise GitHubPublishError(f"Invalid {kind} '{ref}'")
    return ref


def _validate_path(path: str) -> str:
    """Validate a repo file path before it goes into an API URL."""
    p = path.strip().lstrip("/")
    if not _REF_RE.match(p) or ".." in p:
        raise GitHubPublishError(f"Invalid path '{path}'")
    return p


async def publish_markdown(
    *,
    repo: str,
    path: str,
    content: str,
    branch: str,
    commit_message: str,
    pr_title: str,
    pr_body: str,
    base_branch: str | None = None,
    token: str | None = None,
    draft: bool = False,
    labels: list[str] | None = None,
    reviewers: list[str] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    token = token or settings.GITHUB_TOKEN
    if not token:
        raise GitHubPublishError("GitHub publishing not configured — set GITHUB_TOKEN.")
    owner, name = parse_repo(repo)
    path = _validate_path(path)
    _validate_ref(branch, kind="branch")
    if base_branch:
        _validate_ref(base_branch, kind="base branch")
    api = settings.GITHUB_API_URL.rstrip("/")
    base_url = f"{api}/repos/{owner}/{name}"
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")

    async with httpx.AsyncClient(timeout=30, headers=_headers(token)) as client:

        async def _get(url: str) -> httpx.Response:
            return await client.get(url)

        # 1. Resolve base branch (default branch if not given) + its head SHA.
        if not base_branch:
            repo_resp = await _get(base_url)
            if repo_resp.status_code == 404:
                raise GitHubPublishError(f"Repo not found or no access: {repo}")
            repo_resp.raise_for_status()
            base_branch = repo_resp.json()["default_branch"]

        ref_resp = await _get(f"{base_url}/git/ref/heads/{quote(base_branch, safe='')}")
        if ref_resp.status_code != 200:
            raise GitHubPublishError(
                f"Base branch '{base_branch}' not found ({ref_resp.status_code})"
            )
        base_sha = ref_resp.json()["object"]["sha"]

        # 2. Create the feature branch (ignore 422 = already exists → reuse it).
        create_ref = await client.post(
            f"{base_url}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": base_sha},
        )
        if create_ref.status_code not in (201, 422):
            raise GitHubPublishError(
                f"Could not create branch '{branch}' ({create_ref.status_code}): "
                f"{create_ref.text[:200]}"
            )

        # 3. Write the file (include existing sha on the branch if updating).
        existing = await _get(
            f"{base_url}/contents/{quote(path, safe='/')}?ref={quote(branch, safe='')}"
        )
        put_body: dict[str, Any] = {
            "message": commit_message,
            "content": b64,
            "branch": branch,
        }
        if existing.status_code == 200:
            put_body["sha"] = existing.json()["sha"]
        put = await client.put(
            f"{base_url}/contents/{quote(path, safe='/')}", json=put_body
        )
        if put.status_code not in (200, 201):
            raise GitHubPublishError(
                f"Could not write '{path}' ({put.status_code}): {put.text[:200]}"
            )
        commit_sha = put.json().get("commit", {}).get("sha")

        # 4. Open the PR (on 422 the PR likely already exists → return it).
        pr = await client.post(
            f"{base_url}/pulls",
            json={
                "title": pr_title,
                "head": branch,
                "base": base_branch,
                "body": pr_body,
                "draft": draft,
            },
        )
        if pr.status_code == 201:
            data = pr.json()
        elif pr.status_code == 422:
            existing_prs = await _get(
                f"{base_url}/pulls?head={owner}:{quote(branch, safe='')}&state=open"
            )
            items = existing_prs.json() if existing_prs.status_code == 200 else []
            if not items:
                raise GitHubPublishError(
                    f"Could not open PR ({pr.status_code}): {pr.text[:200]}"
                )
            data = items[0]
        else:
            raise GitHubPublishError(
                f"Could not open PR ({pr.status_code}): {pr.text[:200]}"
            )

        # 5. Best-effort labels + reviewers — never fatal to the publish.
        warnings: list[str] = []
        pr_number = data["number"]
        if labels:
            resp = await client.post(
                f"{base_url}/issues/{pr_number}/labels", json={"labels": labels}
            )
            if resp.status_code not in (200, 201):
                warnings.append(f"Could not apply labels ({resp.status_code}).")
        if reviewers:
            resp = await client.post(
                f"{base_url}/pulls/{pr_number}/requested_reviewers",
                json={"reviewers": reviewers},
            )
            if resp.status_code not in (200, 201):
                warnings.append(f"Could not request reviewers ({resp.status_code}).")

        return {
            "pr_url": data["html_url"],
            "pr_number": pr_number,
            "branch": branch,
            "base_branch": base_branch,
            "path": path,
            "commit_sha": commit_sha,
            "warnings": warnings,
        }


async def get_pull_request_status(
    *, repo: str, pr_number: int, token: str | None = None
) -> dict[str, Any]:
    settings = get_settings()
    token = token or settings.GITHUB_TOKEN
    if not token:
        raise GitHubPublishError("GitHub publishing not configured — set GITHUB_TOKEN.")
    owner, name = parse_repo(repo)
    api = settings.GITHUB_API_URL.rstrip("/")
    url = f"{api}/repos/{owner}/{name}/pulls/{pr_number}"

    async with httpx.AsyncClient(timeout=30, headers=_headers(token)) as client:
        resp = await client.get(url)
        if resp.status_code == 404:
            raise GitHubPublishError(f"Pull request not found: {repo}#{pr_number}")
        if resp.status_code != 200:
            raise GitHubPublishError(
                f"Could not read PR status ({resp.status_code}): {resp.text[:200]}"
            )
        data = resp.json()
        return {
            "pr_url": data["html_url"],
            "pr_number": data["number"],
            "state": data["state"],
            "merged": bool(data.get("merged")),
            "merged_at": data.get("merged_at"),
        }


async def validate_token(token: str) -> dict[str, Any]:
    """Cheap pre-storage check of a tenant-supplied token via GET /user.

    Returns the token owner's profile on success; raises GitHubPublishError
    when GitHub rejects the token or is unreachable.
    """
    settings = get_settings()
    api = settings.GITHUB_API_URL.rstrip("/")
    async with httpx.AsyncClient(timeout=10, headers=_headers(token)) as client:
        try:
            resp = await client.get(f"{api}/user")
        except httpx.HTTPError as e:
            raise GitHubPublishError(f"Could not reach GitHub: {e}") from e
    if resp.status_code == 401:
        raise GitHubPublishError("GitHub rejected the token (401 Unauthorized)")
    if resp.status_code != 200:
        raise GitHubPublishError(f"Token check failed ({resp.status_code})")
    return resp.json()
