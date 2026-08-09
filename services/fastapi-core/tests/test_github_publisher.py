"""Unit tests for the GitHub PR publishing gateway.

The real GitHub API is never contacted: publish_markdown() builds its own
httpx.AsyncClient, so we swap in a configurable httpx.MockTransport that
records every request and returns scripted responses. This exercises the full
control flow (default-branch resolution, branch reuse on 422, file-update SHA,
PR reuse on 422, and every error path) with no network and no real token.
"""

from __future__ import annotations

import base64
import asyncio
import json
import re
from types import SimpleNamespace

import httpx
import pytest

from app.core import github_publisher as gh
from app.core.github_publisher import (
    GitHubPublishError,
    _validate_path,
    _validate_ref,
    get_pull_request_status,
    parse_repo,
    publish_markdown,
    validate_token,
)

PUBLISH_ARGS = {
    "repo": "owner/repo",
    "path": "content/post.md",
    "content": "# Title\n\nBody text.\n",
    "branch": "opengrow/abc",
    "commit_message": "content: Title",
    "pr_title": "Title",
    "pr_body": "via OpenGrow",
    "base_branch": None,
}


class MockGitHub:
    """Scriptable stand-in for the subset of the GitHub REST API used here."""

    def __init__(self, **overrides):
        self.calls: list[tuple[str, str]] = []
        self.put_bodies: list[dict] = []
        self.pr_bodies: list[dict] = []
        self.cfg = {
            "labels_status": 200,
            "reviewers_status": 201,
            "repo_status": 200,
            "default_branch": "main",
            "ref_status": 200,
            "base_sha": "BASE_SHA",
            "create_ref_status": 201,
            "contents_get_status": 404,
            "contents_get_sha": "EXISTING_SHA",
            "put_status": 201,
            "commit_sha": "COMMIT_SHA",
            "pulls_status": 201,
            "pr_url": "https://github.com/owner/repo/pull/7",
            "pr_number": 7,
            "existing_pulls": [],
            "pr_get_status": 200,
            "pr_get_state": "open",
            "pr_get_merged": False,
            "pr_get_merged_at": None,
            "user_status": 200,
            "user_login": "octocat",
        }
        self.cfg.update(overrides)

    def handler(self, request: httpx.Request) -> httpx.Response:
        c = self.cfg
        method = request.method
        path = request.url.path
        self.calls.append((method, path))

        if method == "GET" and re.fullmatch(r"/repos/[^/]+/[^/]+", path):
            if c["repo_status"] != 200:
                return httpx.Response(c["repo_status"], json={"message": "nope"})
            return httpx.Response(200, json={"default_branch": c["default_branch"]})

        if method == "GET" and "/git/ref/heads/" in path:
            if c["ref_status"] != 200:
                return httpx.Response(c["ref_status"], json={"message": "no ref"})
            return httpx.Response(200, json={"object": {"sha": c["base_sha"]}})

        if method == "POST" and path.endswith("/git/refs"):
            return httpx.Response(c["create_ref_status"], json={})

        if "/contents/" in path and method == "GET":
            if c["contents_get_status"] == 200:
                return httpx.Response(200, json={"sha": c["contents_get_sha"]})
            return httpx.Response(c["contents_get_status"], json={"message": "x"})

        if "/contents/" in path and method == "PUT":
            self.put_bodies.append(json.loads(request.content))
            return httpx.Response(
                c["put_status"], json={"commit": {"sha": c["commit_sha"]}}
            )

        if path.endswith("/pulls") and method == "POST":
            self.pr_bodies.append(json.loads(request.content))
            return httpx.Response(
                c["pulls_status"],
                json={"html_url": c["pr_url"], "number": c["pr_number"]},
            )

        if path.endswith("/pulls") and method == "GET":
            return httpx.Response(200, json=c["existing_pulls"])

        if method == "POST" and re.fullmatch(
            r"/repos/[^/]+/[^/]+/issues/\d+/labels", path
        ):
            return httpx.Response(c["labels_status"], json=[])

        if method == "POST" and re.fullmatch(
            r"/repos/[^/]+/[^/]+/pulls/\d+/requested_reviewers", path
        ):
            return httpx.Response(c["reviewers_status"], json={})

        if method == "GET" and re.fullmatch(r"/repos/[^/]+/[^/]+/pulls/\d+", path):
            if c["pr_get_status"] != 200:
                return httpx.Response(c["pr_get_status"], json={"message": "no pr"})
            return httpx.Response(
                200,
                json={
                    "html_url": c["pr_url"],
                    "number": c["pr_number"],
                    "state": c["pr_get_state"],
                    "merged": c["pr_get_merged"],
                    "merged_at": c["pr_get_merged_at"],
                },
            )

        if method == "GET" and path == "/user":
            if c["user_status"] != 200:
                return httpx.Response(c["user_status"], json={"message": "bad creds"})
            return httpx.Response(200, json={"login": c["user_login"]})

        return httpx.Response(500, json={"message": f"unhandled {method} {path}"})


def install(monkeypatch, mock: MockGitHub, token: str = "test-token") -> None:
    """Route the publisher's httpx client through the mock and fake settings."""
    real_client = httpx.AsyncClient

    def make_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(mock.handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(gh.httpx, "AsyncClient", make_client)
    monkeypatch.setattr(
        gh,
        "get_settings",
        lambda: SimpleNamespace(
            GITHUB_TOKEN=token, GITHUB_API_URL="https://api.github.com"
        ),
    )


def run(monkeypatch, mock: MockGitHub, token: str = "test-token", **overrides):
    install(monkeypatch, mock, token=token)
    return asyncio.run(publish_markdown(**{**PUBLISH_ARGS, **overrides}))


def run_status(
    monkeypatch,
    mock: MockGitHub,
    token: str = "test-token",
    repo: str = "owner/repo",
    pr_number: int = 7,
):
    install(monkeypatch, mock, token=token)
    return asyncio.run(get_pull_request_status(repo=repo, pr_number=pr_number))


def test_explicit_token_bypasses_settings_token(monkeypatch):
    mock = MockGitHub()
    install(monkeypatch, mock, token="")

    result = asyncio.run(publish_markdown(**PUBLISH_ARGS, token="tenant-token"))

    assert result["pr_number"] == 7
    assert mock.calls


def test_explicit_token_used_for_status(monkeypatch):
    mock = MockGitHub()
    install(monkeypatch, mock, token="")

    result = asyncio.run(
        get_pull_request_status(repo="owner/repo", pr_number=7, token="tenant-token")
    )

    assert result["pr_number"] == 7


# --------------------------------------------------------------------------- #
# validate_token
# --------------------------------------------------------------------------- #


def test_validate_token_ok(monkeypatch):
    mock = MockGitHub()
    install(monkeypatch, mock, token="tenant-token")

    profile = asyncio.run(validate_token("tenant-token"))

    assert profile["login"] == "octocat"
    assert mock.calls == [("GET", "/user")]


def test_validate_token_rejected(monkeypatch):
    mock = MockGitHub(user_status=401)
    install(monkeypatch, mock, token="bad-token")

    with pytest.raises(GitHubPublishError, match="rejected"):
        asyncio.run(validate_token("bad-token"))


# --------------------------------------------------------------------------- #
# parse_repo
# --------------------------------------------------------------------------- #
def test_parse_repo_valid():
    assert parse_repo("owner/name") == ("owner", "name")
    assert parse_repo(" /owner/name/ ") == ("owner", "name")


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "owner",
        "owner/name/extra",
        "/",
        "owner/",
        # illegal characters that could smuggle a different URL host/path (SSRF)
        "ow ner/name",
        "owner/na me",
        "e@vil/name",
        "owner/na%2Fme",
        "owner/na\nme",
    ],
)
def test_parse_repo_invalid(bad):
    with pytest.raises(GitHubPublishError):
        parse_repo(bad)


@pytest.mark.parametrize(
    "bad", ["bad branch", "a/../b", "/lead", "trail/", "x\ny", "~x"]
)
def test_validate_ref_rejects_bad(bad):
    with pytest.raises(GitHubPublishError):
        _validate_ref(bad, kind="branch")


def test_validate_ref_accepts_normal():
    assert _validate_ref("feature/x-1.2", kind="branch") == "feature/x-1.2"


@pytest.mark.parametrize("bad", ["../etc/passwd", "a/../b", "x y", "ba\nd", "p%2Fq"])
def test_validate_path_rejects_bad(bad):
    with pytest.raises(GitHubPublishError):
        _validate_path(bad)


def test_validate_path_strips_leading_slash():
    assert _validate_path("/content/post.md") == "content/post.md"


# --------------------------------------------------------------------------- #
# happy paths
# --------------------------------------------------------------------------- #
def test_happy_path_new_file(monkeypatch):
    mock = MockGitHub()
    result = run(monkeypatch, mock)

    assert result == {
        "pr_url": "https://github.com/owner/repo/pull/7",
        "pr_number": 7,
        "branch": "opengrow/abc",
        "base_branch": "main",
        "path": "content/post.md",
        "commit_sha": "COMMIT_SHA",
        "warnings": [],
    }
    methods = [m for m, _ in mock.calls]
    assert methods == ["GET", "GET", "POST", "GET", "PUT", "POST"]

    body = mock.put_bodies[0]
    assert body["branch"] == "opengrow/abc"
    assert body["message"] == "content: Title"
    assert "sha" not in body  # new file → no update sha
    assert base64.b64decode(body["content"]).decode() == PUBLISH_ARGS["content"]


def test_explicit_base_branch_skips_repo_lookup(monkeypatch):
    mock = MockGitHub()
    result = run(monkeypatch, mock, base_branch="develop")

    assert result["base_branch"] == "develop"
    # Repo-metadata lookup only happens when base_branch is not supplied.
    assert not any(re.fullmatch(r"/repos/[^/]+/[^/]+", p) for _, p in mock.calls)


def test_existing_file_includes_update_sha(monkeypatch):
    mock = MockGitHub(contents_get_status=200)
    run(monkeypatch, mock)
    assert mock.put_bodies[0]["sha"] == "EXISTING_SHA"


def test_branch_already_exists_is_reused(monkeypatch):
    # 422 on ref creation means the branch exists already → reuse, don't fail.
    mock = MockGitHub(create_ref_status=422)
    result = run(monkeypatch, mock)
    assert result["pr_number"] == 7


def test_pr_already_exists_returns_existing(monkeypatch):
    mock = MockGitHub(
        pulls_status=422,
        existing_pulls=[
            {"html_url": "https://github.com/owner/repo/pull/9", "number": 9}
        ],
    )
    result = run(monkeypatch, mock)
    assert result["pr_number"] == 9
    assert result["pr_url"] == "https://github.com/owner/repo/pull/9"


# --------------------------------------------------------------------------- #
# error paths
# --------------------------------------------------------------------------- #
def test_missing_token_raises_before_any_call(monkeypatch):
    mock = MockGitHub()
    with pytest.raises(GitHubPublishError, match="not configured"):
        run(monkeypatch, mock, token="")
    assert mock.calls == []


def test_repo_not_found_raises(monkeypatch):
    mock = MockGitHub(repo_status=404)
    with pytest.raises(GitHubPublishError, match="not found or no access"):
        run(monkeypatch, mock)


def test_base_branch_not_found_raises(monkeypatch):
    mock = MockGitHub(ref_status=404)
    with pytest.raises(GitHubPublishError, match="Base branch"):
        run(monkeypatch, mock, base_branch="ghost")


def test_create_branch_unexpected_status_raises(monkeypatch):
    mock = MockGitHub(create_ref_status=500)
    with pytest.raises(GitHubPublishError, match="Could not create branch"):
        run(monkeypatch, mock)


def test_file_write_failure_raises(monkeypatch):
    mock = MockGitHub(put_status=500)
    with pytest.raises(GitHubPublishError, match="Could not write"):
        run(monkeypatch, mock)


def test_pr_creation_failure_raises(monkeypatch):
    mock = MockGitHub(pulls_status=500)
    with pytest.raises(GitHubPublishError, match="Could not open PR"):
        run(monkeypatch, mock)


def test_pr_conflict_with_no_existing_pr_raises(monkeypatch):
    mock = MockGitHub(pulls_status=422, existing_pulls=[])
    with pytest.raises(GitHubPublishError, match="Could not open PR"):
        run(monkeypatch, mock)


# --------------------------------------------------------------------------- #
# PR status refresh
# --------------------------------------------------------------------------- #
def test_get_pull_request_status_open(monkeypatch):
    mock = MockGitHub()
    result = run_status(monkeypatch, mock)

    assert result == {
        "pr_url": "https://github.com/owner/repo/pull/7",
        "pr_number": 7,
        "state": "open",
        "merged": False,
        "merged_at": None,
    }


def test_get_pull_request_status_merged(monkeypatch):
    mock = MockGitHub(
        pr_get_state="closed",
        pr_get_merged=True,
        pr_get_merged_at="2026-07-22T10:00:00Z",
    )
    result = run_status(monkeypatch, mock)

    assert result["state"] == "closed"
    assert result["merged"] is True
    assert result["merged_at"] == "2026-07-22T10:00:00Z"


def test_get_pull_request_status_not_found_raises(monkeypatch):
    mock = MockGitHub(pr_get_status=404)
    with pytest.raises(GitHubPublishError, match="Pull request not found"):
        run_status(monkeypatch, mock)


# --------------------------------------------------------------------------- #
# PR options: draft / labels / reviewers
# --------------------------------------------------------------------------- #
def test_publish_request_accepts_pr_options():
    from app.schemas.publication import PublishGitHubRequest

    r = PublishGitHubRequest(
        repo="o/n", draft=True, labels=["docs", "  ", "docs"], reviewers=["alice"]
    )
    assert r.draft is True
    assert r.labels == ["docs"]  # trimmed, de-duped, blanks dropped
    assert r.reviewers == ["alice"]


def test_publish_request_defaults_no_pr_options():
    from app.schemas.publication import PublishGitHubRequest

    r = PublishGitHubRequest(repo="o/n")
    assert r.draft is False
    assert r.labels == []
    assert r.reviewers == []


def test_config_out_has_display_name():
    from app.schemas.publication import GitHubPublishConfigOut

    c = GitHubPublishConfigOut(configured=True, api_url="x", display_name="Main")
    assert c.display_name == "Main"


def test_publish_applies_draft_labels_reviewers(monkeypatch):
    mock = MockGitHub()
    result = run(monkeypatch, mock, draft=True, labels=["docs"], reviewers=["alice"])

    # draft flag forwarded on the PR-create call
    assert mock.pr_bodies[0]["draft"] is True
    # labels + reviewers calls were made
    paths = [p for _, p in mock.calls]
    assert any(p.endswith("/issues/7/labels") for p in paths)
    assert any(p.endswith("/pulls/7/requested_reviewers") for p in paths)
    # all succeeded → no warnings
    assert result["warnings"] == []


def test_label_reviewer_failure_is_nonfatal(monkeypatch):
    mock = MockGitHub(labels_status=500, reviewers_status=422)
    result = run(monkeypatch, mock, labels=["docs"], reviewers=["alice"])

    # publish still succeeds (PR opened) …
    assert result["pr_url"] == "https://github.com/owner/repo/pull/7"
    # … but both non-fatal failures are surfaced as warnings
    assert len(result["warnings"]) == 2


def test_no_pr_options_skips_label_reviewer_calls(monkeypatch):
    mock = MockGitHub()
    run(monkeypatch, mock)  # default PUBLISH_ARGS: no labels/reviewers
    paths = [p for _, p in mock.calls]
    assert not any("/labels" in p for p in paths)
    assert not any("/requested_reviewers" in p for p in paths)
