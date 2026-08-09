"""Pure prompt composition for article generation.

No I/O: callers pass the brief, the brand profile, and any retrieved context,
so every branch is unit-testable without a database or a model call.
"""

from __future__ import annotations

BRAND_BLOCK_MAX_CHARS = 1200
CONTEXT_CHAR_BUDGET = 5000
OUTLINE_MAX_TOKENS = 1200

_OUTLINE_SYSTEM = (
    "You are a senior content strategist. You plan long-form articles that rank and convert. "
    "Return ONLY a Markdown list: each section as '## <heading>' followed by 2-4 '- <point>' bullets. "
    "No preamble, no closing commentary."
)
_DRAFT_SYSTEM = (
    "You are a senior long-form writer. You write specific, useful articles with concrete examples "
    "and no filler. Return ONLY Markdown body content: '##' section headings and prose. "
    "Do not repeat the article title as an H1 and do not add frontmatter."
)


def draft_max_tokens(length_words: int) -> int:
    """~1.6 tokens per word plus headroom, bounded so a typo can't run away."""
    return max(2000, min(16000, int(length_words * 1.6) + 800))


def brand_system_block(profile: dict | None) -> str:
    if not profile:
        return ""
    parts: list[str] = []
    for key, label in (
        ("tone", "Brand tone"),
        ("audience", "Brand audience"),
        ("tagline", "Brand tagline"),
        ("value_proposition", "Value proposition"),
    ):
        value = profile.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(f"{label}: {value.strip()}")
    if not parts:
        return ""
    block = "Write in this brand's voice.\n" + "\n".join(parts)
    return block[:BRAND_BLOCK_MAX_CHARS]


def _context_block(context: list[dict] | None) -> str:
    if not context:
        return ""
    lines, used = [], 0
    for item in context:
        snippet = (item.get("snippet") or "").strip()
        if not snippet:
            continue
        room = CONTEXT_CHAR_BUDGET - used
        if room <= 0:
            break
        clipped = snippet[:room]
        used += len(clipped)
        lines.append(f"--- source: {item.get('filename') or 'asset'} ---\n{clipped}")
    if not lines:
        return ""
    return (
        "Reference material from the user's own files. Use it as source material for facts "
        "and specifics; do not quote it verbatim and do not mention these markers.\n\n"
        + "\n\n".join(lines)
    )


def _brief_lines(brief: dict) -> str:
    secondary = ", ".join(brief.get("secondary_keywords") or []) or "none"
    return "\n".join(
        [
            f"Topic: {brief.get('topic', '')}",
            f"Primary keyword: {brief.get('primary_keyword') or 'none'}",
            f"Secondary keywords: {secondary}",
            f"Audience: {brief.get('audience') or 'general'}",
            f"Goal: {brief.get('goal') or 'educate'}",
            f"Requested tone: {brief.get('tone') or 'match the brand voice'}",
            f"Target length: {brief.get('length_words', 1200)} words",
            f"Target sections: {brief.get('sections_target', 5)}",
            f"Extra notes: {brief.get('notes') or 'none'}",
        ]
    )


def _system(base: str, brand: dict | None) -> dict:
    block = brand_system_block(brand)
    return {"role": "system", "content": f"{base}\n\n{block}" if block else base}


def compose_outline_prompt(
    brief: dict, brand: dict | None = None, context: list[dict] | None = None
) -> list[dict]:
    user = [
        f"Plan an article with {brief.get('sections_target', 5)} sections.",
        "",
        _brief_lines(brief),
    ]
    ctx = _context_block(context)
    if ctx:
        user += ["", ctx]
    return [
        _system(_OUTLINE_SYSTEM, brand),
        {"role": "user", "content": "\n".join(user)},
    ]


def compose_draft_prompt(
    brief: dict,
    outline: list[dict],
    brand: dict | None = None,
    context: list[dict] | None = None,
) -> list[dict]:
    rendered = []
    for section in outline or []:
        rendered.append(f"## {section.get('heading', '').strip()}")
        for point in section.get("points") or []:
            rendered.append(f"- {point}")
    user = [
        f"Write the full article (~{brief.get('length_words', 1200)} words) "
        "following this approved outline exactly, in order.",
        "",
        "\n".join(rendered),
        "",
        _brief_lines(brief),
    ]
    ctx = _context_block(context)
    if ctx:
        user += ["", ctx]
    return [_system(_DRAFT_SYSTEM, brand), {"role": "user", "content": "\n".join(user)}]
