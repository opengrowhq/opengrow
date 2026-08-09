import pytest
from pydantic import ValidationError

from app.schemas.publication import PublishGitHubRequest


def test_publish_github_request_strips_optional_blanks():
    payload = PublishGitHubRequest(
        repo=" owner/repo ",
        path=" ",
        base_branch=" main ",
        branch=" opengrow/post ",
        commit_message=" content: Post ",
        pr_title=" Post ",
        pr_body=" ",
    )

    assert payload.repo == "owner/repo"
    assert payload.path is None
    assert payload.base_branch == "main"
    assert payload.branch == "opengrow/post"
    assert payload.commit_message == "content: Post"
    assert payload.pr_title == "Post"
    assert payload.pr_body is None


@pytest.mark.parametrize("repo", ["", "owner", "owner/repo/extra", "owner /repo"])
def test_publish_github_request_rejects_invalid_repo(repo):
    with pytest.raises(ValidationError):
        PublishGitHubRequest(repo=repo)
