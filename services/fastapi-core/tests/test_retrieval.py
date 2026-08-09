import pytest

from app.core.retrieval import cosine, rank_local_assets
from app.workers.tasks import asset_snippet


def test_snippet_is_bounded_and_stripped():
    assert asset_snippet("  hello  ") == "hello"
    assert len(asset_snippet("x" * 10_000)) == 2000


def test_snippet_handles_empty():
    assert asset_snippet("") == ""
    assert asset_snippet(None) == ""


def test_cosine_basics():
    assert cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine([0, 0], [1, 0]) == 0.0  # zero vector is safe, not a crash


def test_rank_local_assets_orders_by_similarity_and_limits():
    rows = [
        ("a1", "near.md", [1.0, 0.0]),
        ("a2", "far.md", [0.0, 1.0]),
        ("a3", "mid.md", [0.7, 0.7]),
    ]
    ranked = rank_local_assets(rows, [1.0, 0.0], k=2)
    assert [r["asset_id"] for r in ranked] == ["a1", "a3"]
    assert ranked[0]["filename"] == "near.md"
    assert ranked[0]["score"] >= ranked[1]["score"]


def test_rank_local_assets_skips_missing_vectors():
    assert (
        rank_local_assets([("a1", "x.md", None), ("a2", "y.md", [])], [1.0], k=3) == []
    )
