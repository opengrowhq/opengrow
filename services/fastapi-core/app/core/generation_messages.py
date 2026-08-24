"""Prompt composition for generation rows (shared by worker + orchestrator)."""

from __future__ import annotations


def build_generation_messages(
    db, gen, brand=None, context=None
) -> tuple[list[dict], int]:
    """Compose (messages, max_tokens) for a generation row based on its kind.

    kind="article_outline" / "article_draft" use the server-side article prompts;
    anything else keeps the original single-message marketing-copy behaviour.

    ``brand``/``context`` are the article-grounding inputs computed by the
    caller (``run_generation`` or the orchestrator). They are passed explicitly
    (never round-tripped through ``metadata_json``) so internal prompt inputs
    stay out of the persisted row.
    """
    from sqlalchemy.orm import Session

    from app.core.article_prompt import (
        OUTLINE_MAX_TOKENS,
        compose_draft_prompt,
        compose_outline_prompt,
        draft_max_tokens,
    )
    from app.core.playbook import get_active_system_template_sync
    from app.models.playbook import PlaybookKind

    meta = gen.metadata_json or {}
    kind = meta.get("kind")
    brief = meta.get("article") or {}

    # Playbook lookup needs a real DB round-trip, so it's only attempted from
    # the sync `Session` worker/orchestrator contexts that actually make the
    # LLM call — matches article_grounding.ground_article's same convention.
    playbook_kind = None
    if kind == "article_outline":
        playbook_kind = PlaybookKind.ARTICLE_OUTLINE
    elif kind == "article_draft":
        playbook_kind = PlaybookKind.ARTICLE_DRAFT
    elif kind is None:
        playbook_kind = PlaybookKind.GENERIC_COPY

    system_template = None
    if db is not None and isinstance(db, Session) and playbook_kind is not None:
        system_template = get_active_system_template_sync(
            db, gen.tenant_id, playbook_kind
        )

    if kind == "article_outline":
        return (
            compose_outline_prompt(brief, brand, context, system_template),
            OUTLINE_MAX_TOKENS,
        )
    if kind == "article_draft":
        outline = meta.get("outline") or []
        try:
            words = int(brief.get("length_words") or 1200)
        except (TypeError, ValueError):
            words = 1200
        return (
            compose_draft_prompt(brief, outline, brand, context, system_template),
            draft_max_tokens(words),
        )

    ref_hint = ""
    if getattr(gen, "reference_asset_id", None) and db is not None:
        from app.models.asset import Asset

        asset = db.get(Asset, gen.reference_asset_id)
        if asset:
            ref_hint = (
                f"\n\nReference brand asset: {asset.filename} ({asset.content_type})."
            )
    return (
        [
            {
                "role": "system",
                "content": system_template
                or "You write concise, high-quality marketing copy.",
            },
            {"role": "user", "content": gen.brief + ref_hint},
        ],
        2000,
    )
