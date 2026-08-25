"""Pure scoring logic for the attribution-loop recommendation engine: turns
per-content-piece current-vs-previous-period counts (the same shape
app.routers.analytics._content_counts_for_period already computes for
/content-trends) into REFRESH / DOUBLE_DOWN / NEW_TOPIC suggestions.

No I/O: callers pass in already-fetched counts/pieces, so every branch is
unit-testable without a database — mirrors app.core.quality_score's
pure-function contract for the same reason.
"""

from __future__ import annotations

from app.core.analytics_window import trend_delta

DECAY_THRESHOLD_PERCENT = -30  # events dropped 30%+ vs. the prior window
GROWTH_THRESHOLD_PERCENT = 50  # events grew 50%+ vs. the prior window
MIN_EVENTS_FOR_SIGNAL = 3  # ignore noise from single-digit event counts
MIN_PUBLISHED_FOR_GAP_SIGNAL = 3  # fewer tagged pieces = no real "coverage" yet
MAX_NEW_TOPIC_SUGGESTIONS = 3  # cap per sweep — don't drown out real signals


def _events_delta_percent(current: dict, previous: dict) -> int | None:
    return trend_delta(current.get("events", 0), previous.get("events", 0))["percent"]


def score_decay(current: dict, previous: dict) -> float:
    """0.0 (no decay signal) to 1.0 (severe decay). Requires a real prior
    baseline (MIN_EVENTS_FOR_SIGNAL) so a piece with barely any traffic
    doesn't get flagged from noise — going from 2 events to 0 is not a
    meaningful decay signal, going from 200 to 60 is."""
    if previous.get("events", 0) < MIN_EVENTS_FOR_SIGNAL:
        return 0.0
    percent = _events_delta_percent(current, previous)
    if percent is None or percent > DECAY_THRESHOLD_PERCENT:
        return 0.0
    # -30% -> ~0.3, -100% -> 1.0, linear beyond the threshold
    return min(1.0, abs(percent) / 100)


def score_growth(current: dict, previous: dict) -> float:
    """0.0 (no growth signal) to 1.0 (strong growth), same shape as
    score_decay but for the DOUBLE_DOWN direction."""
    if previous.get("events", 0) < MIN_EVENTS_FOR_SIGNAL:
        return 0.0
    percent = _events_delta_percent(current, previous)
    if percent is None or percent < GROWTH_THRESHOLD_PERCENT:
        return 0.0
    return min(1.0, percent / 200)


def refresh_rationale(title: str, percent: int | None, current_events: int) -> str:
    pct_text = f"{abs(percent)}%" if percent is not None else "sharply"
    return (
        f'"{title}" traffic/engagement dropped {pct_text} vs. the prior period '
        f"({current_events} events now) — refreshing it (updated facts, "
        "broader keyword coverage, a stronger intro) is usually higher-leverage "
        "than starting a new piece from zero."
    )


def double_down_rationale(title: str, percent: int | None, current_events: int) -> str:
    pct_text = f"{percent}%" if percent is not None else "significantly"
    return (
        f'"{title}" is growing ({pct_text} vs. the prior period, {current_events} '
        "events now) — a follow-up piece on the same topic/keyword family can "
        "capture more of the same demand while it's working."
    )


def new_topic_rationale(missing_tag: str, covered_tags: list[str]) -> str:
    coverage = ", ".join(sorted(covered_tags)[:5]) or "your existing topics"
    return (
        f'No published content covers "{missing_tag}" yet, even though it '
        f"appears in your brief history alongside {coverage} — a gap worth "
        "filling rather than adding more depth to already-covered ground."
    )


def find_topic_gaps(pieces: list[dict]) -> list[dict]:
    """pieces: [{"id": UUID, "title": str, "tags": list[str] | None}, ...]
    PUBLISHED pieces, same filtering contract as build_recommendations.

    A "gap" here is a tag that shows up on exactly one published piece —
    someone touched the topic once but never built it into a real cluster.
    That's a much weaker, noisier signal than REFRESH/DOUBLE_DOWN's real
    traffic deltas (no attribution data involved at all, just co-occurrence
    of tags across a tenant's own published tags), so scores are capped
    below any confirmed decay/growth score and the result is capped to
    MAX_NEW_TOPIC_SUGGESTIONS — a tag that's simply rare isn't necessarily a
    real content gap, and flooding the queue with them would drown out the
    two evidence-backed kinds.

    Requires MIN_PUBLISHED_FOR_GAP_SIGNAL published pieces with at least one
    tag each; with too few tagged pieces "appears once" is meaningless (it's
    just "hasn't had a second post yet", true of nearly every tag early on).
    """
    tagged = [p for p in pieces if p.get("tags")]
    if len(tagged) < MIN_PUBLISHED_FOR_GAP_SIGNAL:
        return []

    tag_counts: dict[str, int] = {}
    for piece in tagged:
        for tag in piece["tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    covered_tags = [t for t, count in tag_counts.items() if count > 1]
    single_occurrence = sorted(t for t, count in tag_counts.items() if count == 1)

    out: list[dict] = []
    for tag in single_occurrence[:MAX_NEW_TOPIC_SUGGESTIONS]:
        out.append(
            {
                "kind": "NEW_TOPIC",
                "content_piece_id": None,
                "title": f'Write more on "{tag}"',
                "rationale": new_topic_rationale(tag, covered_tags),
                # Below MIN_EVENTS decay/growth's minimum nonzero score
                # (>0.3 for a decay right at DECAY_THRESHOLD_PERCENT) so a
                # real, attribution-backed suggestion always sorts first.
                "score": 0.2,
            }
        )
    return out


def build_recommendations(
    pieces: list[dict],
    *,
    current_counts: dict,
    previous_counts: dict,
) -> list[dict]:
    """pieces: [{"id": UUID, "title": str, "tags": list[str] | None}, ...] —
    PUBLISHED pieces only is the caller's job to filter (a DRAFT piece
    decaying isn't meaningful; tags come from
    ContentPiece.metadata_json["article"]["tags"]). Returns a list of
    {"kind", "content_piece_id", "title", "rationale", "score"} dicts, the
    caller turns these into ContentRecommendation rows.
    """
    out: list[dict] = find_topic_gaps(pieces)
    for piece in pieces:
        cur = current_counts.get(piece["id"], {})
        prev = previous_counts.get(piece["id"], {})
        percent = _events_delta_percent(cur, prev)

        decay = score_decay(cur, prev)
        if decay > 0:
            out.append(
                {
                    "kind": "REFRESH",
                    "content_piece_id": piece["id"],
                    "title": f'Refresh "{piece["title"]}"',
                    "rationale": refresh_rationale(
                        piece["title"], percent, cur.get("events", 0)
                    ),
                    "score": decay,
                }
            )
            continue  # a piece is either decaying or growing, never both

        growth = score_growth(cur, prev)
        if growth > 0:
            out.append(
                {
                    "kind": "DOUBLE_DOWN",
                    "content_piece_id": piece["id"],
                    "title": f'Write a follow-up to "{piece["title"]}"',
                    "rationale": double_down_rationale(
                        piece["title"], percent, cur.get("events", 0)
                    ),
                    "score": growth,
                }
            )
    return sorted(out, key=lambda r: r["score"], reverse=True)
