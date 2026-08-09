// Repo/ref rules mirror the backend (schemas/publication.py + core/github_publisher.py)
// so invalid input is caught inline instead of returning a raw 502.
const REPO_RE = /^[^/\s]+\/[^/\s]+$/;
const REF_RE = /^[A-Za-z0-9._/-]{1,255}$/;

function slugify(value) {
  return (
    String(value || "")
      .toLowerCase()
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-") || "post"
  );
}

function refInvalid(ref) {
  return (
    !REF_RE.test(ref) ||
    ref.includes("..") ||
    ref.startsWith("/") ||
    ref.endsWith("/")
  );
}

export function defaultGitHubPublishForm(content, lastUsed) {
  const id = content?.id ?? "";
  const title = content?.title?.trim() || "Untitled";
  const slug = slugify(title);
  const isBlogPost = content?.format === "blog_post";
  const path = isBlogPost ? `content/posts/${slug}.md` : id ? `content/${id}.md` : "";
  return {
    repo: lastUsed?.repo ?? "",
    path,
    base_branch: lastUsed?.base_branch ?? "",
    branch: isBlogPost ? `opengrow/${slug}` : id ? `opengrow/${id}` : "",
    commit_message: `content: ${title}`,
    pr_title: title,
    pr_body: id ? `Published via OpenGrow - content piece ${id}.` : "",
    draft: false,
    labels: "",
    reviewers: "",
  };
}

// Comma-separated string -> trimmed, de-duped, non-empty array.
export function parseList(value) {
  if (Array.isArray(value)) return value;
  if (typeof value !== "string") return [];
  const seen = new Set();
  const out = [];
  for (const raw of value.split(",")) {
    const s = raw.trim();
    if (s && !seen.has(s)) {
      seen.add(s);
      out.push(s);
    }
  }
  return out;
}

/**
 * @param {Record<string, unknown>} form
 * @returns {import("./api").PublishGitHubInput}
 */
export function cleanGitHubPublishForm(form) {
  /** @type {Record<string, unknown>} */
  const out = {};
  for (const [key, value] of Object.entries(form)) {
    if (key === "labels" || key === "reviewers") {
      const arr = parseList(value);
      if (arr.length) out[key] = arr;
      continue;
    }
    if (key === "draft") {
      out.draft = !!value;
      continue;
    }
    const v = typeof value === "string" ? value.trim() : value;
    if (v !== "" && v != null) out[key] = v;
  }
  return out;
}

// Returns a { field: message } map; empty object means the form is valid.
export function validateGitHubPublishForm(form) {
  const errors = {};
  const repo = (form.repo ?? "").trim();
  if (!repo) errors.repo = "Enter a repo (owner/name).";
  else if (!REPO_RE.test(repo)) errors.repo = "Use the format owner/name.";

  const branch = (form.branch ?? "").trim();
  if (branch && refInvalid(branch)) errors.branch = "Invalid branch name.";

  const base = (form.base_branch ?? "").trim();
  if (base && refInvalid(base)) errors.base_branch = "Invalid base branch name.";

  const path = (form.path ?? "").trim();
  if (path) {
    const p = path.replace(/^\/+/, "");
    if (!REF_RE.test(p) || p.includes("..")) errors.path = "Invalid file path.";
  }
  return errors;
}

// Per-workspace memory of the last repo/base branch used, so the form
// pre-fills instead of making the user retype owner/repo each time.
export function lastUsedKey(slug) {
  return `opengrow.gh-publish.${slug || "default"}`;
}

export function loadLastUsed(slug) {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(lastUsedKey(slug));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveLastUsed(slug, value) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      lastUsedKey(slug),
      JSON.stringify({
        repo: value?.repo ?? "",
        base_branch: value?.base_branch ?? "",
      }),
    );
  } catch {
    // ignore storage failures (private mode, quota) — memory is best-effort
  }
}
