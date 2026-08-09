import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  cleanGitHubPublishForm,
  defaultGitHubPublishForm,
  validateGitHubPublishForm,
} from "./publish-form.mjs";

describe("GitHub publish form helpers", () => {
  it("builds backend-aligned defaults from a content piece", () => {
    assert.deepEqual(
      defaultGitHubPublishForm({ id: "abc-123", title: "Launch post" }),
      {
        repo: "",
        path: "content/abc-123.md",
        base_branch: "",
        branch: "opengrow/abc-123",
        commit_message: "content: Launch post",
        pr_title: "Launch post",
        pr_body: "Published via OpenGrow - content piece abc-123.",
        draft: false,
        labels: "",
        reviewers: "",
      },
    );
  });

  it("uses a slugged blog path and branch for blog posts", () => {
    const form = defaultGitHubPublishForm({
      id: "abc-123",
      title: "Why Founders Should Blog Before Launch!",
      format: "blog_post",
    });

    assert.equal(form.path, "content/posts/why-founders-should-blog-before-launch.md");
    assert.equal(form.branch, "opengrow/why-founders-should-blog-before-launch");
  });

  it("seeds repo/base_branch from last-used memory when present", () => {
    const form = defaultGitHubPublishForm(
      { id: "x", title: "T" },
      { repo: "owner/blog", base_branch: "main" },
    );
    assert.equal(form.repo, "owner/blog");
    assert.equal(form.base_branch, "main");
  });

  it("removes optional blank values before submit", () => {
    assert.deepEqual(
      cleanGitHubPublishForm({
        repo: " owner/repo ",
        path: " ",
        base_branch: "",
        branch: " opengrow/post ",
      }),
      { repo: "owner/repo", branch: "opengrow/post" },
    );
  });

  it("parses labels/reviewers comma strings into arrays and keeps draft boolean", () => {
    const c = cleanGitHubPublishForm({
      repo: "o/n",
      draft: true,
      labels: "docs, seo , docs",
      reviewers: "alice",
    });
    assert.deepEqual(c.labels, ["docs", "seo"]);
    assert.deepEqual(c.reviewers, ["alice"]);
    assert.equal(c.draft, true);
    assert.equal(c.repo, "o/n");
  });

  it("omits empty label/reviewer fields", () => {
    const c = cleanGitHubPublishForm({ repo: "o/n", labels: "", reviewers: "  " });
    assert.equal("labels" in c, false);
    assert.equal("reviewers" in c, false);
  });
});

describe("validateGitHubPublishForm", () => {
  it("requires a repo and rejects malformed ones", () => {
    assert.ok(validateGitHubPublishForm({}).repo);
    assert.ok(validateGitHubPublishForm({ repo: "noslash" }).repo);
    assert.ok(validateGitHubPublishForm({ repo: "o/n/x" }).repo);
    assert.ok(validateGitHubPublishForm({ repo: "ow ner/name" }).repo);
  });

  it("accepts a well-formed repo", () => {
    assert.equal(validateGitHubPublishForm({ repo: "owner/name" }).repo, undefined);
  });

  it("rejects invalid branch / base branch refs", () => {
    assert.ok(validateGitHubPublishForm({ repo: "o/n", branch: "a..b" }).branch);
    assert.ok(validateGitHubPublishForm({ repo: "o/n", base_branch: "/lead" }).base_branch);
    assert.equal(
      validateGitHubPublishForm({ repo: "o/n", branch: "opengrow/x-1.2" }).branch,
      undefined,
    );
  });

  it("rejects a path traversal", () => {
    assert.ok(validateGitHubPublishForm({ repo: "o/n", path: "../etc/passwd" }).path);
    assert.equal(
      validateGitHubPublishForm({ repo: "o/n", path: "content/x.md" }).path,
      undefined,
    );
  });
});
