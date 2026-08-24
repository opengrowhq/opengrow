import uuid

from app.core.content_recommendations import (
    build_recommendations,
    score_decay,
    score_growth,
)

PIECE_ID = uuid.uuid4()


def test_score_decay_zero_below_min_events():
    assert score_decay({"events": 0}, {"events": 2}) == 0.0


def test_score_decay_zero_when_not_decaying():
    assert score_decay({"events": 50}, {"events": 40}) == 0.0


def test_score_decay_positive_past_threshold():
    score = score_decay({"events": 20}, {"events": 100})  # -80%
    assert score > 0.0


def test_score_decay_scales_with_severity():
    mild = score_decay({"events": 65}, {"events": 100})  # -35%
    severe = score_decay({"events": 5}, {"events": 100})  # -95%
    assert 0 < mild < severe <= 1.0


def test_score_growth_zero_below_min_events():
    assert score_growth({"events": 10}, {"events": 2}) == 0.0


def test_score_growth_zero_when_flat():
    assert score_growth({"events": 55}, {"events": 50}) == 0.0


def test_score_growth_positive_past_threshold():
    assert score_growth({"events": 200}, {"events": 100}) > 0.0  # +100%


def test_build_recommendations_flags_decaying_published_piece():
    pieces = [{"id": PIECE_ID, "title": "Old post"}]
    current = {PIECE_ID: {"events": 10}}
    previous = {PIECE_ID: {"events": 100}}

    recs = build_recommendations(pieces, current_counts=current, previous_counts=previous)

    assert len(recs) == 1
    assert recs[0]["kind"] == "REFRESH"
    assert recs[0]["content_piece_id"] == PIECE_ID
    assert "Old post" in recs[0]["title"]
    assert recs[0]["score"] > 0


def test_build_recommendations_flags_growing_published_piece():
    pieces = [{"id": PIECE_ID, "title": "Hot post"}]
    current = {PIECE_ID: {"events": 300}}
    previous = {PIECE_ID: {"events": 100}}

    recs = build_recommendations(pieces, current_counts=current, previous_counts=previous)

    assert len(recs) == 1
    assert recs[0]["kind"] == "DOUBLE_DOWN"


def test_build_recommendations_ignores_flat_piece():
    pieces = [{"id": PIECE_ID, "title": "Steady post"}]
    current = {PIECE_ID: {"events": 52}}
    previous = {PIECE_ID: {"events": 50}}

    recs = build_recommendations(pieces, current_counts=current, previous_counts=previous)

    assert recs == []


def test_build_recommendations_ignores_piece_with_no_events():
    pieces = [{"id": PIECE_ID, "title": "Unread post"}]
    recs = build_recommendations(pieces, current_counts={}, previous_counts={})
    assert recs == []


def test_build_recommendations_sorts_by_score_descending():
    id_a, id_b = uuid.uuid4(), uuid.uuid4()
    pieces = [{"id": id_a, "title": "A"}, {"id": id_b, "title": "B"}]
    current = {id_a: {"events": 50}, id_b: {"events": 5}}
    previous = {id_a: {"events": 100}, id_b: {"events": 100}}  # both decay, B worse

    recs = build_recommendations(pieces, current_counts=current, previous_counts=previous)

    assert [r["content_piece_id"] for r in recs] == [id_b, id_a]
