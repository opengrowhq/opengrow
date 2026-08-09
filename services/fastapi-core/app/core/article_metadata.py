"""Article metadata helpers shared by the content router and the orchestrator."""

from __future__ import annotations


def article_content_metadata(base: dict | None, article: dict | None) -> dict | None:
    """Copy publish-relevant article fields onto the content piece's metadata.

    `_render_markdown` reads these at publish time, so the content piece never
    needs to reach back into the generation that produced it.
    """
    if not article:
        return base
    fields: dict = {}
    for key in ("slug", "description"):
        value = article.get(key)
        if isinstance(value, str) and value.strip():
            fields[key] = value.strip()
    tags = article.get("tags")
    if isinstance(tags, list):
        seen, cleaned = set(), []
        for tag in tags:
            t = tag.strip() if isinstance(tag, str) else tag
            if t and t not in seen:
                seen.add(t)
                cleaned.append(t)
        if cleaned:
            fields["tags"] = cleaned
    if not fields:
        return base
    return {**(base or {}), "article": fields}
